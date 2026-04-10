#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户会话历史API路由
为历史记录页面提供完整的会话数据
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime
from app.services import local_sqlite_service as sqlite_service

router = APIRouter(prefix="/api/user", tags=["用户会话"])

# 导入统一认证系统
import sys
sys.path.append('/opt/tcm-ai')
from core.unified_account.account_manager import unified_account_manager

async def get_current_user_from_header(authorization: Optional[str] = Header(None)):
    """从Header中获取当前用户"""
    try:
        if not authorization:
            return None

        if not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="认证头格式错误")

        session_id = authorization.replace('Bearer ', '').strip()
        if not session_id:
            raise HTTPException(status_code=401, detail="会话令牌为空")

        session = unified_account_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="会话已过期")

        user = unified_account_manager.get_user_by_id(session.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        return user, session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"认证失败: {str(e)}")

@router.get("/sessions")
async def get_user_sessions(user_id: str = None, authorization: Optional[str] = Header(None)):
    """获取用户的会话历史"""
    try:
        current_user_data = await get_current_user_from_header(authorization)

        resolved_user_id = user_id
        if current_user_data:
            current_user, _ = current_user_data
            resolved_user_id = current_user.global_user_id
            if user_id and user_id != resolved_user_id:
                raise HTTPException(status_code=403, detail="无权访问其他用户会话")
        elif not user_id:
            raise HTTPException(status_code=400, detail="缺少 user_id 或 Authorization")

        sessions = sqlite_service.fetch_user_sessions_summary(user_id=resolved_user_id)
        
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "sessions": [],
            "total": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/conversation/{session_id}")
async def get_conversation_detail(session_id: str, user_id: str = None, authorization: Optional[str] = Header(None)):
    """获取单个会话的详细信息"""
    try:
        current_user_data = await get_current_user_from_header(authorization)

        resolved_user_id = user_id
        if current_user_data:
            current_user, _ = current_user_data
            resolved_user_id = current_user.global_user_id
            if user_id and user_id != resolved_user_id:
                raise HTTPException(status_code=403, detail="无权访问其他用户会话")
        elif not user_id:
            raise HTTPException(status_code=400, detail="缺少 user_id 或 Authorization")

        detail_data = sqlite_service.fetch_conversation_detail_data(session_id, user_id=resolved_user_id)
        if not detail_data:
            raise HTTPException(status_code=404, detail="会话不存在")

        return {
            "success": True,
            **detail_data,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")

@router.delete("/sessions/clear")
async def clear_user_sessions(user_id: str = None, authorization: Optional[str] = Header(None)):
    """清空用户的所有会话历史"""
    try:
        current_user_data = await get_current_user_from_header(authorization)

        resolved_user_id = user_id
        if current_user_data:
            current_user, _ = current_user_data
            resolved_user_id = current_user.global_user_id
            if user_id and user_id != resolved_user_id:
                raise HTTPException(status_code=403, detail="无权清空其他用户会话")
        elif not user_id:
            raise HTTPException(status_code=400, detail="缺少 user_id 或 Authorization")

        clear_result = sqlite_service.clear_user_session_history(resolved_user_id)
        
        return {
            "success": True,
            "message": clear_result["message"],
            "deleted_count": clear_result["deleted_count"],
            "table_stats": clear_result["table_stats"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空历史记录失败: {str(e)}")
