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
    确认支付并提交给医生审核
    患者支付成功后调用此接口
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查处方是否存在
        cursor.execute("""
            SELECT id, consultation_id, doctor_id, status, payment_status
            FROM prescriptions 
            WHERE id = ?
        """, (request.prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        if prescription['payment_status'] == 'paid':
            return {
                "success": True,
                "message": "处方已支付，无需重复操作",
                "status": "already_paid"
            }
        
        # 更新支付状态和处方状态
        cursor.execute("""
            UPDATE prescriptions 
            SET payment_status = 'paid',
                status = 'pending_review',
                is_visible_to_patient = 1,
                visibility_unlock_time = datetime('now'),
                confirmed_at = datetime('now')
            WHERE id = ?
        """, (request.prescription_id,))
        
        # 记录支付信息（可以扩展支付详情表）
        cursor.execute("""
            INSERT OR REPLACE INTO prescription_payment_logs (
                prescription_id, amount, payment_method, payment_time, status
            ) VALUES (?, ?, ?, datetime('now'), 'completed')
        """, (request.prescription_id, request.payment_amount, request.payment_method))
        
        # 自动提交给医生审核 - 插入到医生工作队列
        cursor.execute("""
            INSERT OR REPLACE INTO doctor_review_queue (
                prescription_id, doctor_id, consultation_id, 
                submitted_at, status, priority
            ) VALUES (?, ?, ?, datetime('now'), 'pending', 'normal')
        """, (request.prescription_id, prescription['doctor_id'], prescription['consultation_id']))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 处方支付确认成功: prescription_id={request.prescription_id}, 已提交医生审核")
        
        return {
            "success": True,
            "message": "支付确认成功，处方已提交医生审核",
            "data": {
                "prescription_id": request.prescription_id,
                "status": "pending_review",
                "note": "处方正在等待医生审核，审核完成后即可配药"
            }
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
    医生审核处方
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查处方状态
        cursor.execute("""
            SELECT id, status, doctor_id FROM prescriptions WHERE id = ?
        """, (request.prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        if prescription['status'] != 'pending_review':
            return {
                "success": False,
                "message": "处方不在待审核状态"
            }
        
        # 更新处方状态
        if request.action == "approve":
            new_status = "doctor_approved"
            message = "处方审核通过"
        elif request.action == "modify":
            if not request.modified_prescription:
                raise HTTPException(status_code=400, detail="修改处方时必须提供修改后的处方内容")
            new_status = "doctor_modified"
            message = "处方已修改"
        else:
            raise HTTPException(status_code=400, detail="无效的审核操作")
        
        # 更新处方记录
        if request.action == "modify":
            cursor.execute("""
                UPDATE prescriptions 
                SET status = ?, 
                    doctor_prescription = ?,
                    doctor_notes = ?,
                    reviewed_at = datetime('now')
                WHERE id = ?
            """, (new_status, request.modified_prescription, request.doctor_notes, request.prescription_id))
        else:
            cursor.execute("""
                UPDATE prescriptions 
                SET status = ?,
                    doctor_notes = ?,
                    reviewed_at = datetime('now')
                WHERE id = ?
            """, (new_status, request.doctor_notes, request.prescription_id))
        
        # 更新审核队列
        cursor.execute("""
            UPDATE doctor_review_queue 
            SET status = 'completed', completed_at = datetime('now')
            WHERE prescription_id = ?
        """, (request.prescription_id,))
        
        # 记录审核历史
        cursor.execute("""
            INSERT INTO prescription_review_history (
                prescription_id, doctor_id, action, modified_prescription, 
                doctor_notes, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (request.prescription_id, request.doctor_id, request.action, 
               request.modified_prescription, request.doctor_notes))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 处方审核完成: prescription_id={request.prescription_id}, action={request.action}")
        
        return {
            "success": True,
            "message": message,
            "data": {
                "prescription_id": request.prescription_id,
                "status": new_status,
                "action": request.action,
                "reviewed_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"处方审核失败: {e}")
        return {
            "success": False,
            "message": f"审核失败: {str(e)}"
        }

@router.get("/status/{prescription_id}")
async def get_prescription_review_status(prescription_id: int):
    """
    获取处方审核状态
    患者端调用查看审核进度
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.id, p.status, p.payment_status, p.doctor_notes,
                p.ai_prescription, p.doctor_prescription,
                p.created_at, p.reviewed_at, p.confirmed_at,
                q.submitted_at, q.status as queue_status
            FROM prescriptions p
            LEFT JOIN doctor_review_queue q ON p.id = q.prescription_id
            WHERE p.id = ?
        """, (prescription_id,))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        conn.close()
        
        # 生成状态描述
        status_descriptions = {
            "ai_generated": "AI已生成处方，请支付解锁",
            "pending_review": "已支付，等待医生审核 - 请勿配药",
            "doctor_approved": "医生审核完成，可以配药",
            "doctor_modified": "医生已修改处方，可以配药"
        }
        
        return {
            "success": True,
            "data": {
                "prescription_id": prescription_id,
                "status": result['status'],
                "status_description": status_descriptions.get(result['status'], "未知状态"),
                "payment_status": result['payment_status'],
                "is_reviewed": result['status'] in ['doctor_approved', 'doctor_modified'],
                "is_modified": result['status'] == 'doctor_modified',
                "doctor_notes": result['doctor_notes'],
                "final_prescription": result['doctor_prescription'] or result['ai_prescription'],
                "created_at": result['created_at'],
                "reviewed_at": result['reviewed_at'],
                "submitted_at": result['submitted_at']
            }
        }
        
    except Exception as e:
        logger.error(f"获取处方状态失败: {e}")
        return {
            "success": False,
            "message": f"获取状态失败: {str(e)}"
        }