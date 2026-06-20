#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处方状态管理中心 - 单一真相来源
解决处方状态在多个模块间不一致的问题
"""

import sqlite3
import logging
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class PrescriptionStatus(Enum):
    """处方主状态 - 精简为4个核心状态"""
    AI_GENERATED = "ai_generated"        # AI生成，等待支付
    PENDING_REVIEW = "pending_review"    # 已支付，等待医生审核
    APPROVED = "approved"                # 医生审核通过，可配药
    REJECTED = "rejected"                # 医生审核拒绝

class PaymentStatus(Enum):
    """支付状态"""
    PENDING = "pending"      # 待支付
    PAID = "paid"           # 已支付
    REFUNDED = "refunded"   # 已退款

class ReviewStatus(Enum):
    """审核状态"""
    NOT_SUBMITTED = "not_submitted"      # 未提交审核
    PENDING_REVIEW = "pending_review"    # 待审核
    APPROVED = "approved"                # 审核通过
    MODIFIED = "modified"                # 医生已调整（仍需最终批准）
    REJECTED = "rejected"                # 审核拒绝

# 🔑 状态转换规则 - 定义合法的状态流转路径
VALID_TRANSITIONS = {
    # 从AI生成状态可以：支付后进入审核，或直接拒绝
    PrescriptionStatus.AI_GENERATED: [
        PrescriptionStatus.PENDING_REVIEW,
        PrescriptionStatus.REJECTED
    ],

    # 从待审核状态可以：通过或拒绝
    PrescriptionStatus.PENDING_REVIEW: [
        PrescriptionStatus.APPROVED,
        PrescriptionStatus.REJECTED,
        PrescriptionStatus.PENDING_REVIEW  # 允许医生调整后保持待审核
    ],

    # 审核通过后不可再改变（终态）
    PrescriptionStatus.APPROVED: [],

    # 拒绝后不可再改变（终态）
    PrescriptionStatus.REJECTED: []
}


class PrescriptionStatusManager:
    """
    处方状态管理中心

    核心原则：
    1. 所有状态变更必须通过此管理器
    2. 状态转换必须符合业务规则
    3. 状态更新自动同步到数据库
    4. 提供统一的状态查询接口
    """

    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path

    def get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_prescription_status(self, prescription_id: int) -> Optional[Dict[str, Any]]:
        """
        获取处方的完整状态信息

        Returns:
            {
                'prescription_id': int,
                'status': str,              # 主状态
                'review_status': str,       # 审核状态
                'payment_status': str,      # 支付状态
                'is_visible_to_patient': bool,
                'doctor_notes': str,
                'reviewed_at': str,
                'confirmed_at': str
            }
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, status, review_status, payment_status,
                       is_visible_to_patient, doctor_notes,
                       reviewed_at, confirmed_at, created_at
                FROM prescriptions
                WHERE id = ?
            """, (prescription_id,))

            result = cursor.fetchone()
            conn.close()

            if not result:
                return None

            return {
                'prescription_id': result['id'],
                'status': result['status'],
                'review_status': result['review_status'],
                'payment_status': result['payment_status'],
                'is_visible_to_patient': bool(result['is_visible_to_patient']),
                'doctor_notes': result['doctor_notes'],
                'reviewed_at': result['reviewed_at'],
                'confirmed_at': result['confirmed_at'],
                'created_at': result['created_at']
            }

        except Exception as e:
            logger.error(f"获取处方状态失败: {e}")
            return None

    def _validate_status_transition(
        self,
        current_status: str,
        new_status: str
    ) -> Tuple[bool, str]:
        """
        验证状态转换是否合法

        Returns:
            (is_valid, error_message)
        """
        try:
            current = PrescriptionStatus(current_status)
            new = PrescriptionStatus(new_status)

            if new in VALID_TRANSITIONS.get(current, []):
                return True, ""
            else:
                return False, f"不允许从 {current.value} 转换到 {new.value}"

        except ValueError:
            return False, f"无效的状态值: {current_status} 或 {new_status}"

    def update_payment_status(
        self,
        prescription_id: int,
        payment_status: str,
        payment_amount: float = None
    ) -> Dict[str, Any]:
        """
        更新支付状态

        支付成功后自动触发：
        1. 更新payment_status为paid
        2. 更新主状态为pending_review
        3. 提交到医生审核队列
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 获取当前状态
            current_status_info = self.get_prescription_status(prescription_id)
            if not current_status_info:
                raise ValueError(f"处方ID {prescription_id} 不存在")

            current_status = current_status_info['status']

            # 支付成功时的状态转换
            if payment_status == PaymentStatus.PAID.value:
                # 验证状态转换
                is_valid, error_msg = self._validate_status_transition(
                    current_status,
                    PrescriptionStatus.PENDING_REVIEW.value
                )

                if not is_valid and current_status != PrescriptionStatus.PENDING_REVIEW.value:
                    logger.warning(f"状态转换警告: {error_msg}, 但继续执行支付更新")

                # 🔑 关键更新：支付后同步更新三个状态字段
                cursor.execute("""
                    UPDATE prescriptions
                    SET payment_status = 'paid',
                        status = 'pending_review',
                        review_status = 'pending_review',
                        is_visible_to_patient = 1,
                        visibility_unlock_time = datetime('now', 'localtime'),
                        confirmed_at = datetime('now', 'localtime')
                    WHERE id = ?
                """, (prescription_id,))

                # 确保提交到医生审核队列
                # 🔑 修复：使用COALESCE处理consultation_id为NULL的情况
                cursor.execute("""
                    INSERT OR REPLACE INTO doctor_review_queue (
                        prescription_id, doctor_id, consultation_id,
                        submitted_at, status, priority
                    )
                    SELECT ?,
                           doctor_id,
                           COALESCE(consultation_id, conversation_id, 'unknown_' || CAST(id AS TEXT)),
                           datetime('now', 'localtime'), 'pending', 'normal'
                    FROM prescriptions WHERE id = ?
                """, (prescription_id, prescription_id))

                # 同步问诊主状态，避免历史记录仍显示进行中
                cursor.execute("""
                    UPDATE consultations
                    SET status = 'pending_review',
                        updated_at = datetime('now', 'localtime')
                    WHERE uuid = (
                        SELECT COALESCE(consultation_id, conversation_id)
                        FROM prescriptions
                        WHERE id = ?
                    )
                """, (prescription_id,))

                # 同步doctor_sessions状态
                cursor.execute("""
                    UPDATE doctor_sessions
                    SET session_status = 'active',
                        last_updated = datetime('now', 'localtime')
                    WHERE session_id = (
                        SELECT COALESCE(consultation_id, conversation_id)
                        FROM prescriptions
                        WHERE id = ?
                    )
                """, (prescription_id,))

                logger.info(f"✅ 处方 {prescription_id} 支付成功，已进入审核队列")

            conn.commit()
            conn.close()

            return {
                "success": True,
                "prescription_id": prescription_id,
                "new_status": PrescriptionStatus.PENDING_REVIEW.value,
                "payment_status": payment_status,
                "message": "支付状态更新成功"
            }

        except Exception as e:
            logger.error(f"更新支付状态失败: {e}")
            return {
                "success": False,
                "prescription_id": prescription_id,
                "message": f"更新失败: {str(e)}"
            }

    def update_review_status(
        self,
        prescription_id: int,
        action: str,  # "approve" 或 "reject" 或 "modify"
        doctor_id: str,
        doctor_notes: str = None,
        modified_prescription: str = None
    ) -> Dict[str, Any]:
        """
        更新审核状态 - 医生审核处方时调用

        审核通过时自动触发：
        1. 更新review_status为approved
        2. 更新主状态为approved
        3. 标记患者可见
        4. 完成审核队列
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 获取当前状态
            current_status_info = self.get_prescription_status(prescription_id)
            if not current_status_info:
                raise ValueError(f"处方ID {prescription_id} 不存在")

            current_status = current_status_info['status']
            current_payment = current_status_info['payment_status']

            # 🔑 验证必须已支付才能审核
            if current_payment != PaymentStatus.PAID.value:
                return {
                    "success": False,
                    "prescription_id": prescription_id,
                    "message": f"处方尚未支付，无法审核（当前支付状态：{current_payment}）"
                }

            # 根据审核动作确定新状态
            if action == "approve":
                new_status = PrescriptionStatus.APPROVED.value
                new_review_status = ReviewStatus.APPROVED.value
                queue_status = 'completed'
                message = "处方审核通过"

            elif action == "reject":
                new_status = PrescriptionStatus.REJECTED.value
                new_review_status = ReviewStatus.REJECTED.value
                queue_status = 'completed'
                message = "处方审核拒绝"

            elif action == "modify":
                new_status = PrescriptionStatus.PENDING_REVIEW.value
                new_review_status = ReviewStatus.MODIFIED.value
                queue_status = 'pending'  # 调整后仍需最终批准
                message = "处方已调整，等待最终审核"

            else:
                raise ValueError(f"无效的审核动作: {action}")

            # 验证状态转换
            is_valid, error_msg = self._validate_status_transition(current_status, new_status)
            if not is_valid and action != "modify":
                logger.warning(f"状态转换警告: {error_msg}")

            # 🔑 关键更新：审核时同步更新所有相关字段
            if action == "modify":
                # 医生调整处方
                cursor.execute("""
                    UPDATE prescriptions
                    SET doctor_prescription = ?,
                        doctor_notes = ?,
                        review_status = ?,
                        reviewed_at = datetime('now', 'localtime')
                    WHERE id = ?
                """, (modified_prescription, doctor_notes, new_review_status, prescription_id))
            else:
                # 医生批准或拒绝
                cursor.execute("""
                    UPDATE prescriptions
                    SET status = ?,
                        review_status = ?,
                        doctor_notes = ?,
                        reviewed_at = datetime('now', 'localtime'),
                        is_visible_to_patient = ?
                    WHERE id = ?
                """, (
                    new_status,
                    new_review_status,
                    doctor_notes,
                    1 if action == "approve" else 0,
                    prescription_id
                ))

            # 更新审核队列
            cursor.execute("""
                UPDATE doctor_review_queue
                SET status = ?, completed_at = datetime('now', 'localtime')
                WHERE prescription_id = ?
            """, (queue_status, prescription_id))

            # 同步问诊与会话状态，保持历史记录状态一致
            if action in ("approve", "reject"):
                consultation_status = "completed"
                doctor_session_status = "completed"
            else:
                consultation_status = "pending_review"
                doctor_session_status = "active"

            cursor.execute("""
                UPDATE consultations
                SET status = ?, updated_at = datetime('now', 'localtime')
                WHERE uuid = (
                    SELECT COALESCE(consultation_id, conversation_id)
                    FROM prescriptions
                    WHERE id = ?
                )
            """, (consultation_status, prescription_id))

            cursor.execute("""
                UPDATE doctor_sessions
                SET session_status = ?, last_updated = datetime('now', 'localtime')
                WHERE session_id = (
                    SELECT COALESCE(consultation_id, conversation_id)
                    FROM prescriptions
                    WHERE id = ?
                )
            """, (doctor_session_status, prescription_id))

            # 记录审核历史
            cursor.execute("""
                INSERT INTO prescription_review_history (
                    prescription_id, doctor_id, action, modified_prescription,
                    doctor_notes, reviewed_at
                ) VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (prescription_id, doctor_id, action, modified_prescription, doctor_notes))

            conn.commit()
            conn.close()

            logger.info(f"✅ 处方 {prescription_id} 审核完成: {action}, 新状态: {new_status}")

            return {
                "success": True,
                "prescription_id": prescription_id,
                "action": action,
                "new_status": new_status,
                "review_status": new_review_status,
                "message": message
            }

        except Exception as e:
            logger.error(f"更新审核状态失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "prescription_id": prescription_id,
                "message": f"审核失败: {str(e)}"
            }

    def get_display_info(self, prescription_id: int) -> Dict[str, Any]:
        """
        获取患者端显示信息

        根据当前状态返回患者应该看到的信息：
        - 显示文本
        - 可见性
        - 需要的操作
        """
        status_info = self.get_prescription_status(prescription_id)
        if not status_info:
            return {
                "error": "处方不存在",
                "is_visible": False
            }

        status = status_info['status']
        review_status = status_info['review_status']
        payment_status = status_info['payment_status']

        # 🔑 状态显示逻辑 - 单一真相来源
        if status == PrescriptionStatus.AI_GENERATED.value:
            return {
                "display_text": "AI已生成处方，需要支付后提交医生审核",
                "action_required": "payment_required",
                "is_visible": False,
                "can_pay": True,
                "status_description": "待支付"
            }

        elif status == PrescriptionStatus.PENDING_REVIEW.value:
            return {
                "display_text": "处方正在医生审核中，请耐心等待...",
                "action_required": "waiting_review",
                "is_visible": True,
                "can_pay": False,
                "status_description": "审核中"
            }

        elif status == PrescriptionStatus.APPROVED.value:
            return {
                "display_text": "处方审核通过，可以配药",
                "action_required": "completed",
                "is_visible": True,
                "can_pay": False,
                "status_description": "已通过"
            }

        elif status == PrescriptionStatus.REJECTED.value:
            return {
                "display_text": "处方审核未通过，建议重新问诊",
                "action_required": "rejected",
                "is_visible": False,
                "can_pay": False,
                "status_description": "已拒绝"
            }

        else:
            return {
                "display_text": "状态未知",
                "action_required": "unknown",
                "is_visible": False,
                "can_pay": False,
                "status_description": "未知"
            }


# 🔑 全局单例 - 确保整个系统使用同一个实例
_status_manager_instance = None

def get_status_manager() -> PrescriptionStatusManager:
    """获取状态管理器单例"""
    global _status_manager_instance
    if _status_manager_instance is None:
        _status_manager_instance = PrescriptionStatusManager()
    return _status_manager_instance
