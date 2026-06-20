#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话管理API路由
为前端提供会话状态管理和同步功能
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime
from app.services import local_sqlite_service as sqlite_service

router = APIRouter(prefix="/api/session", tags=["会话管理"])

class SessionUpdateRequest(BaseModel):
    """会话更新请求"""
    user_id: str
    session_data: Dict[str, Any]
    action: Optional[str] = "update"

@router.post("/update")
async def update_session(request: SessionUpdateRequest, req: Request):
    """更新会话状态"""
    try:
        # 获取客户端信息
        ip_address = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("User-Agent", "unknown")
        now = datetime.now().isoformat()

        sqlite_service.update_user_session_activity(
            user_id=request.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            now_iso=now,
        )
        
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
        session = sqlite_service.fetch_latest_session_status(user_id)
        
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
        deleted_count = sqlite_service.delete_user_sessions(user_id)
        
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
        active_sessions = sqlite_service.fetch_active_sessions_last_day()
        
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
