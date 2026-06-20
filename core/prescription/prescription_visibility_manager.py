#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处方可见性管理器 - 智汇中医工作流核心模块
实现付费前处方隐藏机制，保护知识产权
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import sqlite3
import json
from config.settings import PATHS

logger = logging.getLogger(__name__)

@dataclass
class PrescriptionVisibility:
    """处方可见性状态"""
    prescription_id: str
    is_visible_to_patient: bool
    payment_required: bool
    payment_amount: float
    visibility_unlock_time: datetime = None
    unlock_reason: str = ""
    
class PrescriptionVisibilityManager:
    """处方可见性管理器"""
    
    def __init__(self):
        self.db_path = PATHS['user_db']
    
    def set_prescription_visibility(self, prescription_id: str, visible: bool, 
                                  unlock_reason: str = "") -> bool:
        """设置处方对患者的可见性"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                unlock_time = datetime.now() if visible else None
                
                conn.execute("""
                    UPDATE prescriptions SET
                        is_visible_to_patient = ?,
                        visibility_unlock_time = ?
                    WHERE id = ?
                """, (visible, unlock_time, prescription_id))
                
                # 简化日志记录
                logger.info(f"处方可见性变更: {prescription_id} -> {visible} ({unlock_reason})")
                
                conn.commit()
                
                logger.info(f"处方可见性更新: {prescription_id} -> {visible} ({unlock_reason})")
                return True
                
        except Exception as e:
            logger.error(f"设置处方可见性失败: {e}")
            return False
    
    def check_prescription_visibility(self, prescription_id: str, patient_id: str) -> PrescriptionVisibility:
        """检查处方对特定患者的可见性"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 获取处方基本信息  
                prescription = conn.execute("""
                    SELECT p.*, c.patient_id, c.status as consultation_status
                    FROM prescriptions p
                    JOIN consultations c ON p.consultation_id = c.uuid
                    WHERE p.id = ? AND c.patient_id = ?
                """, (prescription_id, patient_id)).fetchone()
                
                if not prescription:
                    logger.error(f"处方不存在或不属于该患者: {prescription_id}")
                    return PrescriptionVisibility(
                        prescription_id=prescription_id,
                        is_visible_to_patient=False,
                        payment_required=True,
                        payment_amount=0.0
                    )
                
                # 检查支付状态
                payment_status = conn.execute("""
                    SELECT o.status as payment_status, o.total_amount
                    FROM orders o
                    WHERE o.consultation_id = ?
                    ORDER BY o.created_at DESC LIMIT 1
                """, (prescription['consultation_id'],)).fetchone()
                
                is_paid = payment_status and payment_status['payment_status'] == 'paid'
                payment_required = not is_paid
                payment_amount = float(prescription['prescription_fee'] or 88.00)
                
                # 如果已支付，自动设置为可见
                if is_paid and not prescription['is_visible_to_patient']:
                    self.set_prescription_visibility(
                        prescription_id, True, "payment_completed"
                    )
                    visibility = True
                    unlock_time = datetime.now()
                else:
                    visibility = bool(prescription['is_visible_to_patient'])
                    unlock_time = (datetime.fromisoformat(prescription['visibility_unlock_time']) 
                                 if prescription['visibility_unlock_time'] else None)
                
                return PrescriptionVisibility(
                    prescription_id=prescription_id,
                    is_visible_to_patient=visibility,
                    payment_required=payment_required,
                    payment_amount=payment_amount if payment_required else 0.0,
                    visibility_unlock_time=unlock_time
                )
                
        except Exception as e:
            logger.error(f"检查处方可见性失败: {e}")
            return PrescriptionVisibility(
                prescription_id=prescription_id,
                is_visible_to_patient=False,
                payment_required=True,
                payment_amount=88.00
            )
    
    def get_masked_prescription(self, prescription_id: str, patient_id: str) -> Dict[str, Any]:
        """获取脱敏的处方信息（未付费时显示）"""
        try:
            visibility = self.check_prescription_visibility(prescription_id, patient_id)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                prescription = conn.execute("""
                    SELECT p.*, c.tcm_syndrome, c.symptoms_analysis, d.name as doctor_name
                    FROM prescriptions p
                    JOIN consultations c ON p.consultation_id = c.uuid
                    JOIN doctors d ON c.selected_doctor_id = d.id
                    WHERE p.id = ?
                """, (prescription_id,)).fetchone()
                
                if not prescription:
                    return {'error': '处方不存在'}
                
                if visibility.is_visible_to_patient:
                    # 已付费，返回完整处方
                    return {
                        'prescription_id': prescription_id,
                        'visible': True,
                        'doctor_name': prescription['doctor_name'],
                        'tcm_syndrome': prescription['tcm_syndrome'],
                        'symptoms_analysis': prescription['symptoms_analysis'],
                        'herbs': prescription['ai_prescription'],
                        'dosage_instructions': prescription['dosage_instructions'],
                        'notes': prescription['notes'],
                        'created_at': prescription['created_at'],
                        'status': prescription['status']
                    }
                else:
                    # 未付费，返回脱敏信息
                    herbs_data = json.loads(prescription['ai_prescription'] or '[]')
                    masked_herbs = []
                    
                    for herb in herbs_data:
                        masked_herbs.append({
                            'name': '***',  # 药材名称隐藏
                            'dosage': '***',  # 用量隐藏
                            'unit': herb.get('unit', 'g')
                        })
                    
                    return {
                        'prescription_id': prescription_id,
                        'visible': False,
                        'payment_required': visibility.payment_required,
                        'payment_amount': visibility.payment_amount,
                        'doctor_name': prescription['doctor_name'],
                        'tcm_syndrome': prescription['tcm_syndrome'],
                        'symptoms_analysis': prescription['symptoms_analysis'][:100] + '...' if prescription['symptoms_analysis'] else '',
                        'herbs': masked_herbs,
                        'herbs_count': len(herbs_data),
                        'dosage_instructions': '处方详情需要支付后查看',
                        'notes': '完整的用药指导和注意事项需要支付后查看',
                        'unlock_message': f'支付 ¥{visibility.payment_amount} 查看完整处方详情',
                        'created_at': prescription['created_at'],
                        'status': prescription['status']
                    }
                    
        except Exception as e:
            logger.error(f"获取脱敏处方失败: {e}")
            return {'error': '获取处方信息失败'}
    
    def unlock_prescription_after_payment(self, consultation_id: str, order_id: str) -> bool:
        """支付完成后解锁处方"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取关联的处方
                prescription = conn.execute("""
                    SELECT id FROM prescriptions 
                    WHERE consultation_id = ?
                """, (consultation_id,)).fetchone()
                
                if not prescription:
                    logger.error(f"未找到关联处方: {consultation_id}")
                    return False
                
                prescription_id = prescription[0]
                
                # 解锁处方可见性
                success = self.set_prescription_visibility(
                    prescription_id, True, f"payment_completed_order_{order_id}"
                )
                
                if success:
                    logger.info(f"支付后处方解锁成功: {prescription_id} (订单: {order_id})")
                
                return success
                
        except Exception as e:
            logger.error(f"支付后解锁处方失败: {e}")
            return False
    
    def get_prescription_unlock_statistics(self) -> Dict[str, Any]:
        """获取处方解锁统计数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 总处方数
                total_prescriptions = conn.execute("""
                    SELECT COUNT(*) FROM prescriptions
                """).fetchone()[0]
                
                # 已解锁处方数
                unlocked_prescriptions = conn.execute("""
                    SELECT COUNT(*) FROM prescriptions
                    WHERE is_visible_to_patient = 1
                """).fetchone()[0]
                
                # 今日解锁数
                today_unlocked = conn.execute("""
                    SELECT COUNT(*) FROM prescriptions
                    WHERE is_visible_to_patient = 1 
                    AND DATE(visibility_unlock_time) = DATE('now')
                """).fetchone()[0]
                
                # 支付转化率
                total_consultations = conn.execute("""
                    SELECT COUNT(*) FROM consultations
                    WHERE status = 'completed'
                """).fetchone()[0]
                
                paid_orders = conn.execute("""
                    SELECT COUNT(*) FROM orders
                    WHERE status = 'paid'
                """).fetchone()[0]
                
                conversion_rate = (paid_orders / total_consultations * 100) if total_consultations > 0 else 0
                
                return {
                    'total_prescriptions': total_prescriptions,
                    'unlocked_prescriptions': unlocked_prescriptions,
                    'unlock_rate': (unlocked_prescriptions / total_prescriptions * 100) if total_prescriptions > 0 else 0,
                    'today_unlocked': today_unlocked,
                    'payment_conversion_rate': round(conversion_rate, 2)
                }
                
        except Exception as e:
            logger.error(f"获取处方解锁统计失败: {e}")
            return {}
    
    def batch_update_prescription_fees(self, new_fee: float) -> int:
        """批量更新处方费用"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE prescriptions 
                    SET prescription_fee = ?
                    WHERE prescription_fee != ? OR prescription_fee IS NULL
                """, (new_fee, new_fee))
                
                updated_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"批量更新处方费用成功: {updated_count} 条记录更新为 ¥{new_fee}")
                return updated_count
                
        except Exception as e:
            logger.error(f"批量更新处方费用失败: {e}")
            return 0