#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处方审核API路由
实现完整的处方审核流程：支付 → 提交审核 → 医生审核 → 患者获得最终处方
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prescription-review", tags=["处方审核"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

class PaymentConfirmRequest(BaseModel):
    """支付确认请求"""
    prescription_id: int
    payment_amount: float
    payment_method: str = "alipay"

class DoctorReviewRequest(BaseModel):
    """医生审核请求"""
    prescription_id: int
    doctor_id: str
    action: str  # "approve" 或 "modify"
    modified_prescription: Optional[str] = None
    doctor_notes: Optional[str] = None

@router.post("/payment-confirm")
async def confirm_payment(request: PaymentConfirmRequest):
    """
    确认支付并提交给医生审核 - 使用统一状态管理器
    患者支付成功后调用此接口
    """
    try:
        # 🔑 使用统一的状态管理器
        from core.prescription.prescription_status_manager import get_status_manager

        status_manager = get_status_manager()

        # 检查是否已支付
        current_status = status_manager.get_prescription_status(request.prescription_id)
        if not current_status:
            raise HTTPException(status_code=404, detail="处方不存在")

        if current_status['payment_status'] == 'paid':
            return {
                "success": True,
                "message": "处方已支付，无需重复操作",
                "status": "already_paid"
            }

        # 记录支付信息
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prescription_payment_logs (
                prescription_id, amount, payment_method, payment_time, status
            ) VALUES (?, ?, ?, datetime('now', 'localtime'), 'completed')
        """, (request.prescription_id, request.payment_amount, request.payment_method))
        conn.commit()
        conn.close()

        # 调用状态管理器更新支付状态
        result = status_manager.update_payment_status(
            prescription_id=request.prescription_id,
            payment_status='paid',
            payment_amount=request.payment_amount
        )

        if result['success']:
            logger.info(f"✅ 处方支付确认成功: prescription_id={request.prescription_id}, 已提交医生审核")

            return {
                "success": True,
                "message": "支付确认成功，处方已提交医生审核",
                "data": {
                    "prescription_id": request.prescription_id,
                    "status": result['new_status'],
                    "note": "处方正在等待医生审核，审核完成后即可配药"
                }
            }
        else:
            logger.error(f"❌ 支付确认失败: {result['message']}")
            return {
                "success": False,
                "message": result['message']
            }

    except Exception as e:
        logger.error(f"支付确认失败: {e}")
        return {
            "success": False,
            "message": f"支付确认失败: {str(e)}"
        }

@router.get("/doctor-queue/{doctor_id}")
async def get_doctor_review_queue(doctor_id: str):
    """
    获取医生的待审核处方列表
    医生工作台调用
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.id as prescription_id,
                p.consultation_id,
                p.patient_id,
                p.ai_prescription,
                p.diagnosis,
                p.symptoms,
                p.status,
                p.created_at,
                q.submitted_at,
                q.priority,
                c.conversation_log
            FROM prescriptions p
            JOIN doctor_review_queue q ON p.id = q.prescription_id
            LEFT JOIN consultations c ON p.consultation_id = c.uuid
            WHERE q.doctor_id = ? AND q.status = 'pending'
            ORDER BY q.priority DESC, q.submitted_at ASC
        """, (doctor_id,))
        
        pending_reviews = []
        for row in cursor.fetchall():
            # 提取患者主诉
            chief_complaint = "无记录"
            if row['conversation_log']:
                try:
                    log_data = json.loads(row['conversation_log'])
                    if isinstance(log_data, dict) and 'conversation_history' in log_data:
                        history = log_data['conversation_history']
                        if history and len(history) > 0:
                            first_query = history[0].get('patient_query', '')
                            if first_query:
                                chief_complaint = first_query[:50] + ("..." if len(first_query) > 50 else "")
                except:
                    pass
            
            pending_reviews.append({
                "prescription_id": row['prescription_id'],
                "consultation_id": row['consultation_id'],
                "patient_id": row['patient_id'],
                "chief_complaint": chief_complaint,
                "ai_prescription": row['ai_prescription'],
                "diagnosis": row['diagnosis'],
                "symptoms": row['symptoms'],
                "status": row['status'],
                "submitted_at": row['submitted_at'],
                "priority": row['priority']
            })
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "doctor_id": doctor_id,
                "pending_count": len(pending_reviews),
                "pending_reviews": pending_reviews
            }
        }
        
    except Exception as e:
        logger.error(f"获取医生审核队列失败: {e}")
        return {
            "success": False,
            "message": f"获取审核队列失败: {str(e)}"
        }

@router.post("/doctor-review")
async def doctor_review_prescription(request: DoctorReviewRequest):
    """
    医生审核处方 - 使用统一状态管理器
    """
    try:
        # 🔑 使用统一的状态管理器
        from core.prescription.prescription_status_manager import get_status_manager

        status_manager = get_status_manager()

        # 调用状态管理器进行审核
        result = status_manager.update_review_status(
            prescription_id=request.prescription_id,
            action=request.action,
            doctor_id=request.doctor_id,
            doctor_notes=request.doctor_notes,
            modified_prescription=request.modified_prescription
        )

        if result['success']:
            logger.info(f"✅ 处方审核完成: prescription_id={request.prescription_id}, action={request.action}")

            return {
                "success": True,
                "message": result['message'],
                "data": {
                    "prescription_id": result['prescription_id'],
                    "status": result['new_status'],
                    "review_status": result['review_status'],
                    "action": result['action'],
                    "reviewed_at": datetime.now().isoformat()
                }
            }
        else:
            logger.error(f"❌ 处方审核失败: {result['message']}")
            return {
                "success": False,
                "message": result['message']
            }

    except Exception as e:
        logger.error(f"处方审核失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"审核失败: {str(e)}"
        }

@router.get("/status/{prescription_id}")
async def get_prescription_review_status(prescription_id: int):
    """
    获取处方审核状态 - 使用统一状态管理器
    患者端调用查看审核进度
    """
    try:
        # 🔑 使用统一的状态管理器
        from core.prescription.prescription_status_manager import get_status_manager

        status_manager = get_status_manager()

        # 获取处方状态
        status_info = status_manager.get_prescription_status(prescription_id)
        if not status_info:
            return {
                "success": False,
                "message": f"处方ID {prescription_id} 不存在",
                "error_code": "PRESCRIPTION_NOT_FOUND"
            }

        # 获取显示信息
        display_info = status_manager.get_display_info(prescription_id)

        # 获取处方详细信息
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ai_prescription, doctor_prescription, doctor_notes, created_at
            FROM prescriptions
            WHERE id = ?
        """, (prescription_id,))

        prescription_detail = cursor.fetchone()
        conn.close()

        return {
            "success": True,
            "data": {
                "prescription_id": prescription_id,
                "status": status_info['status'],
                "review_status": status_info['review_status'],
                "payment_status": status_info['payment_status'],
                "status_description": display_info['status_description'],
                "display_text": display_info['display_text'],
                "action_required": display_info['action_required'],
                "is_visible": display_info['is_visible'],
                "can_pay": display_info['can_pay'],
                "doctor_notes": status_info['doctor_notes'],
                "final_prescription": prescription_detail['doctor_prescription'] or prescription_detail['ai_prescription'],
                "created_at": prescription_detail['created_at'],
                "reviewed_at": status_info['reviewed_at'],
                "confirmed_at": status_info['confirmed_at'],
                "has_doctor_modifications": bool(prescription_detail['doctor_prescription'])
            }
        }

    except Exception as e:
        logger.error(f"获取处方状态失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"获取状态失败: {str(e)}"
        }

@router.get("/all-prescriptions")
async def get_all_prescriptions(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    获取所有处方列表（医生端）- 支持筛选

    参数:
    - status: 处方状态筛选 (ai_generated, pending_review, approved, completed等)
    - payment_status: 支付状态筛选 (unpaid, paid)
    - limit: 返回数量限制
    - offset: 分页偏移量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 构建查询条件
        where_conditions = []
        params = []

        if status:
            where_conditions.append("p.status = ?")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # 查询处方列表
        query = f"""
            SELECT
                p.id as prescription_id,
                p.consultation_id,
                p.patient_id,
                p.ai_prescription,
                p.doctor_prescription,
                p.diagnosis,
                p.symptoms,
                p.status,
                p.created_at,
                p.reviewed_at,
                p.confirmed_at,
                p.doctor_notes,
                p.is_visible_to_patient,
                p.prescription_fee,
                c.conversation_log,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM prescription_payment_logs
                        WHERE prescription_id = p.id AND status = 'completed'
                    ) THEN 'paid'
                    ELSE 'unpaid'
                END as payment_status
            FROM prescriptions p
            LEFT JOIN consultations c ON p.consultation_id = c.uuid
            {where_clause}
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])
        cursor.execute(query, params)

        prescriptions = []
        for row in cursor.fetchall():
            # 提取患者主诉
            chief_complaint = "无记录"
            if row['conversation_log']:
                try:
                    log_data = json.loads(row['conversation_log'])
                    if isinstance(log_data, dict) and 'conversation_history' in log_data:
                        history = log_data['conversation_history']
                        if history and len(history) > 0:
                            first_query = history[0].get('patient_query', '')
                            if first_query:
                                chief_complaint = first_query[:100] + ("..." if len(first_query) > 100 else "")
                except:
                    pass

            # 如果需要按支付状态筛选
            if payment_status and row['payment_status'] != payment_status:
                continue

            prescriptions.append({
                "prescription_id": row['prescription_id'],
                "consultation_id": row['consultation_id'],
                "patient_id": row['patient_id'],
                "chief_complaint": chief_complaint,
                "ai_prescription": row['ai_prescription'],
                "doctor_prescription": row['doctor_prescription'],
                "final_prescription": row['doctor_prescription'] or row['ai_prescription'],
                "diagnosis": row['diagnosis'],
                "symptoms": row['symptoms'],
                "status": row['status'],
                "payment_status": row['payment_status'],
                "prescription_fee": row['prescription_fee'],
                "is_visible_to_patient": row['is_visible_to_patient'],
                "created_at": row['created_at'],
                "reviewed_at": row['reviewed_at'],
                "confirmed_at": row['confirmed_at'],
                "doctor_notes": row['doctor_notes'],
                "has_doctor_modifications": bool(row['doctor_prescription'])
            })

        # 获取总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM prescriptions p
            {where_clause}
        """
        cursor.execute(count_query, params[:-2])  # 排除limit和offset
        total_count = cursor.fetchone()['total']

        conn.close()

        return {
            "success": True,
            "data": {
                "prescriptions": prescriptions,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        }

    except Exception as e:
        logger.error(f"获取处方列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"获取处方列表失败: {str(e)}"
        }