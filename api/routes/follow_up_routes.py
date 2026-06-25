#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随访提醒API路由
为前端提供随访管理功能的后端支持
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sqlite3
from datetime import datetime, timedelta
from core.unified_account.account_manager import unified_account_manager

router = APIRouter(prefix="/api/follow-up", tags=["随访管理"])


def _first_non_empty(*values: Any) -> Optional[Any]:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
            continue
        if value is not None:
            return value
    return None


def _resolve_request_user_id(req: Request, payload_user_id: Optional[str] = None) -> str:
    """优先使用payload/header中的用户ID，再回退认证会话"""
    user_id = _first_non_empty(
        payload_user_id,
        req.headers.get("X-User-ID"),
        req.headers.get("X-UserId"),
        req.headers.get("X-Patient-ID"),
        req.headers.get("X-Patient-Id"),
    )
    if user_id:
        return str(user_id)

    auth_header = req.headers.get("Authorization") or req.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        session_id = auth_header.replace("Bearer ", "", 1).strip()
        try:
            session = unified_account_manager.get_session(session_id)
            if session and getattr(session, "user_id", None):
                return str(session.user_id)
        except Exception:
            pass

    return "guest"

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/home/ute/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

class CreateFollowUpRequest(BaseModel):
    """创建随访提醒请求"""
    title: str
    message: Optional[str] = None
    content: Optional[str] = None
    text: Optional[str] = None
    scheduled_days: Optional[int] = None
    days_after: Optional[int] = None
    patient_id: Optional[str] = None
    user_id: Optional[str] = None
    userId: Optional[str] = None
    patientId: Optional[str] = None
    consultation_id: Optional[str] = None
    related_consultation_id: Optional[str] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None

class PostponeFollowUpRequest(BaseModel):
    """延期随访请求"""
    postpone_days: Optional[int] = None
    days: Optional[int] = None
    delay_days: Optional[int] = None

class FollowUpResponse(BaseModel):
    """随访响应"""
    success: bool
    message: str
    data: Optional[Any] = None

@router.get("/reminders")
async def get_follow_up_reminders(request: Request):
    """获取当前用户的随访提醒"""
    try:
        user_id = _resolve_request_user_id(request)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否有follow_up_reminders表，如果没有则创建
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_up_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                consultation_id TEXT
            )
        """)
        
        # 获取待处理的随访提醒
        cursor.execute("""
            SELECT * FROM follow_up_reminders 
            WHERE user_id = ? AND status = 'pending' 
            AND DATE(scheduled_date) <= DATE('now')
            ORDER BY scheduled_date ASC
        """, (user_id,))
        
        reminders = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return FollowUpResponse(
            success=True,
            message=f"获取到{len(reminders)}个待处理提醒",
            data=reminders
        )
        
    except Exception as e:
        return FollowUpResponse(
            success=False,
            message=f"获取随访提醒失败: {str(e)}",
            data=[]
        )

@router.get("/list")
async def get_follow_up_list(request: Request, status: Optional[str] = None):
    """获取随访列表"""
    try:
        user_id = _resolve_request_user_id(request)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 确保表存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_up_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                consultation_id TEXT
            )
        """)
        
        # 根据状态过滤
        if status:
            cursor.execute("""
                SELECT * FROM follow_up_reminders 
                WHERE user_id = ? AND status = ?
                ORDER BY scheduled_date DESC
            """, (user_id, status))
        else:
            cursor.execute("""
                SELECT * FROM follow_up_reminders 
                WHERE user_id = ?
                ORDER BY scheduled_date DESC
            """, (user_id,))
        
        follow_ups = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return FollowUpResponse(
            success=True,
            message=f"获取到{len(follow_ups)}个随访记录",
            data=follow_ups
        )
        
    except Exception as e:
        return FollowUpResponse(
            success=False,
            message=f"获取随访列表失败: {str(e)}",
            data=[]
        )

@router.post("/create")
async def create_follow_up_reminder(request: CreateFollowUpRequest, req: Request):
    """创建随访提醒"""
    try:
        user_id = _resolve_request_user_id(
            req,
            _first_non_empty(request.patient_id, request.user_id, request.userId, request.patientId),
        )
        reminder_message = _first_non_empty(request.message, request.content, request.text, "随访提醒") or "随访提醒"
        scheduled_days = _first_non_empty(request.scheduled_days, request.days_after, 7) or 7
        try:
            scheduled_days = int(scheduled_days)
        except (TypeError, ValueError):
            scheduled_days = 7
        if scheduled_days < 0:
            scheduled_days = 0
        consultation_id = _first_non_empty(
            request.consultation_id,
            request.related_consultation_id,
            request.conversation_id,
            request.session_id,
        )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 确保表存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_up_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                consultation_id TEXT
            )
        """)
        
        # 计算预约日期
        scheduled_date = (datetime.now() + timedelta(days=scheduled_days)).isoformat()
        
        # 插入随访提醒
        cursor.execute("""
            INSERT INTO follow_up_reminders 
            (user_id, title, message, scheduled_date, created_at, consultation_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            request.title,
            reminder_message,
            scheduled_date,
            datetime.now().isoformat(),
            consultation_id
        ))
        
        follow_up_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return FollowUpResponse(
            success=True,
            message="随访提醒创建成功",
            data={
                "follow_up_id": follow_up_id,
                "scheduled_date": scheduled_date
            }
        )
        
    except Exception as e:
        return FollowUpResponse(
            success=False,
            message=f"创建随访提醒失败: {str(e)}"
        )

@router.post("/{follow_up_id}/complete")
async def complete_follow_up(follow_up_id: int, req: Request):
    """完成随访"""
    try:
        user_id = _resolve_request_user_id(req)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 更新随访状态
        cursor.execute("""
            UPDATE follow_up_reminders 
            SET status = 'completed', completed_at = ?
            WHERE id = ? AND user_id = ?
        """, (datetime.now().isoformat(), follow_up_id, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return FollowUpResponse(
                success=False,
                message="随访记录不存在或无权限"
            )
        
        conn.commit()
        conn.close()
        
        return FollowUpResponse(
            success=True,
            message="随访已完成"
        )
        
    except Exception as e:
        return FollowUpResponse(
            success=False,
            message=f"完成随访失败: {str(e)}"
        )

@router.post("/{follow_up_id}/postpone")
async def postpone_follow_up(follow_up_id: int, request: PostponeFollowUpRequest, req: Request):
    """延期随访"""
    try:
        user_id = _resolve_request_user_id(req)
        postpone_days = _first_non_empty(request.postpone_days, request.days, request.delay_days)
        if postpone_days is None:
            return FollowUpResponse(success=False, message="缺少postpone_days/days参数")
        try:
            postpone_days = int(postpone_days)
        except (TypeError, ValueError):
            return FollowUpResponse(success=False, message="延期天数格式无效")
        if postpone_days <= 0:
            return FollowUpResponse(success=False, message="延期天数必须大于0")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前随访信息
        cursor.execute("""
            SELECT scheduled_date FROM follow_up_reminders 
            WHERE id = ? AND user_id = ?
        """, (follow_up_id, user_id))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return FollowUpResponse(
                success=False,
                message="随访记录不存在或无权限"
            )
        
        # 计算新的预约日期
        current_date = datetime.fromisoformat(row['scheduled_date'])
        new_date = current_date + timedelta(days=postpone_days)
        
        # 更新预约日期
        cursor.execute("""
            UPDATE follow_up_reminders 
            SET scheduled_date = ?
            WHERE id = ? AND user_id = ?
        """, (new_date.isoformat(), follow_up_id, user_id))
        
        conn.commit()
        conn.close()
        
        return FollowUpResponse(
            success=True,
            message=f"随访已延期{postpone_days}天",
            data={
                "new_scheduled_date": new_date.isoformat()
            }
        )
        
    except Exception as e:
        return FollowUpResponse(
            success=False,
            message=f"延期随访失败: {str(e)}"
        )

@router.delete("/{follow_up_id}")
async def delete_follow_up(follow_up_id: int, req: Request):
    """删除随访提醒"""
    try:
        user_id = _resolve_request_user_id(req)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除随访提醒
        cursor.execute("""
            DELETE FROM follow_up_reminders 
            WHERE id = ? AND user_id = ?
        """, (follow_up_id, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return FollowUpResponse(
                success=False,
                message="随访记录不存在或无权限"
            )
        
        conn.commit()
        conn.close()
        
        return FollowUpResponse(
            success=True,
            message="随访提醒已删除"
        )
        
    except Exception as e:
        return FollowUpResponse(
            success=False,
            message=f"删除随访提醒失败: {str(e)}"
        )

@router.get("/statistics")
async def get_follow_up_statistics(req: Request):
    """获取随访统计信息"""
    try:
        user_id = _resolve_request_user_id(req)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 确保表存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_up_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                consultation_id TEXT
            )
        """)
        
        # 统计各状态的随访数量
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM follow_up_reminders 
            WHERE user_id = ?
            GROUP BY status
        """, (user_id,))
        
        status_counts = dict(cursor.fetchall())
        
        # 获取即将到期的随访（未来7天内）
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM follow_up_reminders 
            WHERE user_id = ? AND status = 'pending' 
            AND DATE(scheduled_date) BETWEEN DATE('now') AND DATE('now', '+7 days')
        """, (user_id,))
        
        upcoming_count = cursor.fetchone()['count']
        
        # 获取过期未处理的随访
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM follow_up_reminders 
            WHERE user_id = ? AND status = 'pending' 
            AND DATE(scheduled_date) < DATE('now')
        """, (user_id,))
        
        overdue_count = cursor.fetchone()['count']
        
        conn.close()
        
        return FollowUpResponse(
            success=True,
            message="统计信息获取成功",
            data={
                "total": sum(status_counts.values()),
                "pending": status_counts.get('pending', 0),
                "completed": status_counts.get('completed', 0),
                "upcoming": upcoming_count,
                "overdue": overdue_count,
                "status_breakdown": status_counts
            }
        )
        
    except Exception as e:
        return FollowUpResponse(
            success=False,
            message=f"获取统计信息失败: {str(e)}"
        )
