#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话管理API路由
为前端提供会话状态管理和同步功能
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sqlite3
import json
from datetime import datetime

router = APIRouter(prefix="/api/session", tags=["会话管理"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

class SessionUpdateRequest(BaseModel):
    """会话更新请求"""
    user_id: str
    session_data: Dict[str, Any]
    action: Optional[str] = "update"

@router.post("/update")
async def update_session(request: SessionUpdateRequest, req: Request):
    """更新会话状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 确保表存在（使用实际的表结构）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT,
                role TEXT,
                permissions TEXT,
                created_at TEXT,
                expires_at TEXT,
                ip_address TEXT,
                user_agent TEXT,
                last_activity TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # 获取客户端信息
        ip_address = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("User-Agent", "unknown")
        now = datetime.now().isoformat()
        
        # 检查是否已存在会话
        cursor.execute("""
            SELECT session_token FROM user_sessions 
            WHERE user_id = ? 
            ORDER BY last_activity DESC LIMIT 1
        """, (request.user_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有会话
            cursor.execute("""
                UPDATE user_sessions 
                SET last_activity = ?, 
                    ip_address = ?,
                    user_agent = ?
                WHERE session_token = ?
            """, (
                now,
                ip_address,
                user_agent,
                existing['session_token']
            ))
        else:
            # 创建新会话token
            import uuid
            session_token = f"temp_{request.user_id}_{int(datetime.now().timestamp())}"
            
            cursor.execute("""
                INSERT INTO user_sessions 
                (session_token, user_id, role, last_activity, ip_address, user_agent, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_token,
                request.user_id,
                "patient",  # 默认角色
                now,
                ip_address,
                user_agent,
                now,
                1
            ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "会话状态更新成功",
            "timestamp": now
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"会话更新失败: {str(e)}",
            "error": "session_update_failed"
        }

@router.get("/status/{user_id}")
async def get_session_status(user_id: str):
    """获取用户会话状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_sessions 
            WHERE user_id = ? 
            ORDER BY updated_at DESC LIMIT 1
        """, (user_id,))
        
        session = cursor.fetchone()
        conn.close()
        
        if session:
            session_dict = dict(session)
            try:
                session_dict['session_data'] = json.loads(session_dict['session_data'])
            except json.JSONDecodeError:
                session_dict['session_data'] = {}
            
            return {
                "success": True,
                "data": session_dict,
                "message": "会话状态获取成功"
            }
        else:
            return {
                "success": True,
                "data": None,
                "message": "未找到会话记录"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"获取会话状态失败: {str(e)}",
            "error": "session_status_failed"
        }

@router.delete("/clear/{user_id}")
async def clear_user_sessions(user_id: str):
    """清理用户会话数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM user_sessions 
            WHERE user_id = ?
        """, (user_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"已清理{deleted_count}个会话记录",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"清理会话失败: {str(e)}",
            "error": "session_clear_failed"
        }

@router.get("/active")
async def get_active_sessions():
    """获取活跃会话列表（管理员功能）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最近24小时内的活跃会话
        cursor.execute("""
            SELECT user_id, COUNT(*) as session_count, 
                   MAX(updated_at) as last_activity,
                   ip_address, user_agent
            FROM user_sessions 
            WHERE datetime(updated_at) > datetime('now', '-1 day')
            GROUP BY user_id
            ORDER BY last_activity DESC
        """)
        
        active_sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "data": active_sessions,
            "message": f"获取到{len(active_sessions)}个活跃会话",
            "total": len(active_sessions)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取活跃会话失败: {str(e)}",
            "error": "active_sessions_failed"
        }