#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员API路由
Admin API Routes

功能包括：
1. 用户管理：查看、编辑、重置密码
2. 系统监控
3. 数据统计

Author: TCM-AI Admin Team
Date: 2025-09-22
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import hashlib
import secrets
import logging
from datetime import datetime
from app.services import local_sqlite_service as sqlite_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["管理员"])

class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""
    username: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    account_status: Optional[str] = None

class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    new_password: str

def hash_password_pbkdf2(password: str, salt: str = None) -> tuple:
    """使用PBKDF2哈希密码"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    password_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000  # 100K 迭代
    ).hex()
    
    return password_hash, salt

def get_current_admin():
    """验证管理员权限（简化版）"""
    # TODO: 实现真正的管理员权限验证
    return True

@router.get("/users")
async def get_all_users(admin: bool = Depends(get_current_admin)):
    """获取所有用户列表"""
    try:
        users = sqlite_service.fetch_admin_users_overview()
        
        return {
            "success": True,
            "users": users,
            "total": len(users)
        }
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {e}")

@router.put("/users/{user_id}")
async def update_user(
    user_id: str, 
    user_data: UserUpdateRequest,
    admin: bool = Depends(get_current_admin)
):
    """更新用户信息"""
    try:
        update_result = sqlite_service.update_admin_user(
            user_id=user_id,
            user_data=user_data.model_dump(),
            updated_at=datetime.now().isoformat(),
        )
        if update_result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="用户不存在")
        if update_result["status"] == "no_fields":
            raise HTTPException(status_code=400, detail="没有提供更新字段")
        if update_result["status"] != "updated":
            raise HTTPException(status_code=500, detail="更新失败")
        
        logger.info(f"管理员更新用户信息成功: {user_id}")
        
        return {
            "success": True,
            "message": "用户信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {e}")

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    password_data: PasswordResetRequest,
    admin: bool = Depends(get_current_admin)
):
    """重置用户密码"""
    try:
        user = sqlite_service.fetch_admin_user_identity(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 验证密码长度
        if len(password_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        
        # 生成新密码哈希
        password_hash, salt = hash_password_pbkdf2(password_data.new_password)
        
        updated = sqlite_service.admin_update_user_password(
            user_id=user_id,
            password_hash=password_hash,
            salt=salt,
            changed_at=datetime.now().isoformat(),
        )

        if not updated:
            raise HTTPException(status_code=500, detail="密码重置失败")
        
        logger.info(f"管理员重置用户密码成功: {user['username']} ({user_id})")
        
        return {
            "success": True,
            "message": "密码重置成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置用户密码失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {e}")

@router.get("/system/stats")
async def get_system_stats(admin: bool = Depends(get_current_admin)):
    """获取系统统计信息"""
    try:
        stats = sqlite_service.fetch_admin_system_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {e}")

# 导出路由器
__all__ = ["router"]
