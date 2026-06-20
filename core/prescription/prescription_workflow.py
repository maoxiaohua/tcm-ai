"""
处方状态流转管理模块
管理处方从创建到完成的整个生命周期
"""
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

class PrescriptionStatus(Enum):
    """处方状态枚举"""
    PENDING = "pending"                    # 待审查
    DOCTOR_REVIEWING = "doctor_reviewing"   # 医生审查中  
    APPROVED = "approved"                   # 医生已批准
    REJECTED = "rejected"                   # 医生已拒绝
    PATIENT_CONFIRMED = "patient_confirmed" # 患者已确认
    PAID = "paid"                          # 已支付
    DECOCTION_SUBMITTED = "decoction_submitted"  # 已提交代煎
    PROCESSING = "processing"               # 处理中
    SHIPPED = "shipped"                     # 已发货
    DELIVERED = "delivered"                 # 已送达
    COMPLETED = "completed"                 # 已完成

class PrescriptionWorkflow:
    """处方工作流管理器"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        
        # 定义状态转换规则
        self.status_transitions = {
            PrescriptionStatus.PENDING: [
                PrescriptionStatus.DOCTOR_REVIEWING,
                PrescriptionStatus.APPROVED,
                PrescriptionStatus.REJECTED
            ],
            PrescriptionStatus.DOCTOR_REVIEWING: [
                PrescriptionStatus.APPROVED,
                PrescriptionStatus.REJECTED
            ],
            PrescriptionStatus.APPROVED: [
                PrescriptionStatus.PATIENT_CONFIRMED,
                PrescriptionStatus.REJECTED  # 患者可以拒绝
            ],
            PrescriptionStatus.PATIENT_CONFIRMED: [
                PrescriptionStatus.PAID
            ],
            PrescriptionStatus.PAID: [
                PrescriptionStatus.DECOCTION_SUBMITTED,
                PrescriptionStatus.COMPLETED  # 如果不需要代煎可直接完成
            ],
            PrescriptionStatus.DECOCTION_SUBMITTED: [
                PrescriptionStatus.PROCESSING
            ],
            PrescriptionStatus.PROCESSING: [
                PrescriptionStatus.SHIPPED
            ],
            PrescriptionStatus.SHIPPED: [
                PrescriptionStatus.DELIVERED
            ],
            PrescriptionStatus.DELIVERED: [
                PrescriptionStatus.COMPLETED
            ]
        }
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_prescription_status(self, prescription_id: int) -> Optional[str]:
        """获取处方当前状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT status FROM prescriptions WHERE id = ?", (prescription_id,))
            row = cursor.fetchone()
            return row['status'] if row else None
        finally:
            conn.close()
    
    def can_transition_to(self, current_status: str, target_status: str) -> bool:
        """检查是否可以从当前状态转换到目标状态"""
        try:
            current_enum = PrescriptionStatus(current_status)
            target_enum = PrescriptionStatus(target_status)
            
            allowed_transitions = self.status_transitions.get(current_enum, [])
            return target_enum in allowed_transitions
        except ValueError:
            return False
    
    def update_prescription_status(self, prescription_id: int, new_status: str, 
                                 notes: str = "", updated_by: Optional[int] = None) -> bool:
        """更新处方状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取当前状态
            current_status = self.get_prescription_status(prescription_id)
            if not current_status:
                return False
            
            # 检查状态转换是否合法
            if not self.can_transition_to(current_status, new_status):
                print(f"非法状态转换: {current_status} -> {new_status}")
                return False
            
            # 更新处方状态
            update_fields = ["status = ?", "updated_at = datetime('now')"]
            update_values = [new_status]
            
            # 根据状态更新相应的时间字段
            if new_status == PrescriptionStatus.APPROVED.value:
                update_fields.append("reviewed_at = datetime('now')")
            elif new_status == PrescriptionStatus.PATIENT_CONFIRMED.value:
                update_fields.append("confirmed_at = datetime('now')")
            
            # 如果有更新人员信息，记录更新人
            if updated_by:
                update_fields.append("doctor_id = ?")
                update_values.append(updated_by)
            
            update_sql = f"UPDATE prescriptions SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(prescription_id)
            
            cursor.execute(update_sql, update_values)
            
            # 记录状态变更日志
            self._log_status_change(cursor, prescription_id, current_status, new_status, notes, updated_by)
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            print(f"更新处方状态失败: {e}")
            return False
        finally:
            conn.close()
    
    def _log_status_change(self, cursor, prescription_id: int, old_status: str, 
                          new_status: str, notes: str, updated_by: Optional[int]):
        """记录状态变更日志"""
        try:
            # 这里可以创建一个状态变更日志表
            # 暂时使用prescription_changes表记录
            cursor.execute("""
                INSERT INTO prescription_changes 
                (prescription_id, changed_by, change_type, change_reason)
                VALUES (?, ?, ?, ?)
            """, (prescription_id, updated_by, f"{old_status}->{new_status}", notes))
        except Exception as e:
            print(f"记录状态变更失败: {e}")
    
    def get_prescriptions_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """根据状态获取处方列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT p.*, d.name as doctor_name, d.speciality as doctor_speciality
                FROM prescriptions p
                LEFT JOIN doctors d ON p.doctor_id = d.id
                WHERE p.status = ?
                ORDER BY p.created_at DESC
                LIMIT ?
            """, (status, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_status_statistics(self) -> Dict[str, int]:
        """获取各状态处方统计"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM prescriptions 
                GROUP BY status
            """)
            
            return {row['status']: row['count'] for row in cursor.fetchall()}
        finally:
            conn.close()
    
    def auto_process_paid_prescriptions(self):
        """自动处理已支付的处方"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 查找已支付但需要代煎的订单
            cursor.execute("""
                SELECT p.id, o.id as order_id, o.decoction_required
                FROM prescriptions p
                JOIN orders o ON p.id = o.prescription_id
                WHERE p.status = 'paid' AND o.payment_status = 'paid'
            """)
            
            paid_prescriptions = cursor.fetchall()
            
            for prescription in paid_prescriptions:
                if prescription['decoction_required']:
                    # 需要代煎的处方
                    self.update_prescription_status(
                        prescription['id'], 
                        PrescriptionStatus.DECOCTION_SUBMITTED.value,
                        "自动提交代煎"
                    )
                    
                    # 创建代煎订单记录
                    self._create_decoction_order(cursor, prescription['order_id'])
                else:
                    # 不需要代煎的处方直接完成
                    self.update_prescription_status(
                        prescription['id'],
                        PrescriptionStatus.COMPLETED.value,
                        "无需代煎，直接完成"
                    )
            
            conn.commit()
            return len(paid_prescriptions)
            
        except Exception as e:
            conn.rollback()
            print(f"自动处理已支付处方失败: {e}")
            return 0
        finally:
            conn.close()
    
    def _create_decoction_order(self, cursor, order_id: int):
        """创建代煎订单"""
        try:
            # 生成代煎订单号
            import uuid
            decoction_order_no = f"DC{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:6]}"
            
            cursor.execute("""
                INSERT INTO decoction_orders 
                (order_id, provider_name, decoction_order_no, status)
                VALUES (?, ?, ?, ?)
            """, (order_id, "默认代煎商", decoction_order_no, "submitted"))
            
            print(f"创建代煎订单成功: {decoction_order_no}")
            
        except Exception as e:
            print(f"创建代煎订单失败: {e}")
    
    def get_prescription_workflow_info(self, prescription_id: int) -> Dict[str, Any]:
        """获取处方完整工作流信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取处方基本信息
            cursor.execute("""
                SELECT p.*, d.name as doctor_name, d.speciality as doctor_speciality
                FROM prescriptions p
                LEFT JOIN doctors d ON p.doctor_id = d.id
                WHERE p.id = ?
            """, (prescription_id,))
            
            prescription = cursor.fetchone()
            if not prescription:
                return {}
            
            prescription_dict = dict(prescription)
            
            # 获取订单信息
            cursor.execute("""
                SELECT * FROM orders WHERE prescription_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (prescription_id,))
            
            order = cursor.fetchone()
            prescription_dict['order'] = dict(order) if order else None
            
            # 获取代煎信息
            if order:
                cursor.execute("""
                    SELECT * FROM decoction_orders WHERE order_id = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (order['id'],))
                
                decoction = cursor.fetchone()
                prescription_dict['decoction'] = dict(decoction) if decoction else None
            
            # 获取状态变更历史
            cursor.execute("""
                SELECT * FROM prescription_changes 
                WHERE prescription_id = ?
                ORDER BY created_at ASC
            """, (prescription_id,))
            
            changes = [dict(row) for row in cursor.fetchall()]
            prescription_dict['status_history'] = changes
            
            return prescription_dict
            
        except Exception as e:
            print(f"获取处方工作流信息失败: {e}")
            return {}
        finally:
            conn.close()

# 全局工作流管理器实例
prescription_workflow = PrescriptionWorkflow()