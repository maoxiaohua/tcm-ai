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
from typing import Optional, List, Dict, Any
import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime

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
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 从统一用户表获取数据
        cursor.execute("""
            SELECT u.global_user_id, u.username, u.display_name, u.email, 
                   u.phone_number, u.account_status, u.created_at, u.last_login_at,
                   GROUP_CONCAT(r.role_name) as roles
            FROM unified_users u
            LEFT JOIN user_roles_new r ON u.global_user_id = r.user_id AND r.is_active = 1
            GROUP BY u.global_user_id
            ORDER BY u.created_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row["global_user_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "email": row["email"] or "未设置",
                "phone_number": row["phone_number"] or "未设置",
                "account_status": row["account_status"],
                "roles": row["roles"].split(",") if row["roles"] else [],
                "created_at": row["created_at"],
                "last_login_at": row["last_login_at"] or "从未登录"
            })
        
        return {
            "success": True,
            "users": users,
            "total": len(users)
        }
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {e}")
    finally:
        conn.close()

@router.put("/users/{user_id}")
async def update_user(
    user_id: str, 
    user_data: UserUpdateRequest,
    admin: bool = Depends(get_current_admin)
):
    """更新用户信息"""
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    try:
        # 检查用户是否存在
        cursor.execute("SELECT global_user_id FROM unified_users WHERE global_user_id = ?", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 构建更新字段
        update_fields = []
        values = []
        
        if user_data.username:
            update_fields.append("username = ?")
            values.append(user_data.username)
        
        if user_data.display_name:
            update_fields.append("display_name = ?")
            values.append(user_data.display_name)
        
        if user_data.email:
            update_fields.append("email = ?")
            values.append(user_data.email)
        
        if user_data.phone_number:
            update_fields.append("phone_number = ?")
            values.append(user_data.phone_number)
        
        if user_data.account_status:
            update_fields.append("account_status = ?")
            values.append(user_data.account_status)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有提供更新字段")
        
        # 添加更新时间
        update_fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(user_id)
        
        update_query = f"""
            UPDATE unified_users 
            SET {', '.join(update_fields)}
            WHERE global_user_id = ?
        """
        
        cursor.execute(update_query, values)
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="更新失败")
        
        logger.info(f"管理员更新用户信息成功: {user_id}")
        
        return {
            "success": True,
            "message": "用户信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {e}")
    finally:
        conn.close()

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    password_data: PasswordResetRequest,
    admin: bool = Depends(get_current_admin)
):
    """重置用户密码"""
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    try:
        # 检查用户是否存在
        cursor.execute("SELECT global_user_id, username FROM unified_users WHERE global_user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 验证密码长度
        if len(password_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        
        # 生成新密码哈希
        password_hash, salt = hash_password_pbkdf2(password_data.new_password)
        
        # 更新密码
        cursor.execute("""
            UPDATE unified_users 
            SET password_hash = ?, salt = ?, password_changed_at = ?
            WHERE global_user_id = ?
        """, (password_hash, salt, datetime.now().isoformat(), user_id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="密码重置失败")
        
        logger.info(f"管理员重置用户密码成功: {user[1]} ({user_id})")
        
        return {
            "success": True,
            "message": "密码重置成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"重置用户密码失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {e}")
    finally:
        conn.close()

@router.get("/system/stats")
async def get_system_stats(admin: bool = Depends(get_current_admin)):
    """获取系统统计信息"""
    
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    try:
        stats = {}
        
        # 用户统计
        cursor.execute("SELECT COUNT(*) FROM unified_users")
        stats["total_users"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM unified_users WHERE account_status = 'active'")
        stats["active_users"] = cursor.fetchone()[0]
        
        # 角色统计
        cursor.execute("""
            SELECT role_name, COUNT(*) as count 
            FROM user_roles_new 
            WHERE is_active = 1 
            GROUP BY role_name
        """)
        stats["roles"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 会话统计
        cursor.execute("SELECT COUNT(*) FROM unified_sessions WHERE session_status = 'active'")
        stats["active_sessions"] = cursor.fetchone()[0]
        
        # 处方统计
        cursor.execute("SELECT COUNT(*) FROM prescriptions")
        stats["total_prescriptions"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE status = 'pending'")
        stats["pending_prescriptions"] = cursor.fetchone()[0]
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {e}")
    finally:
        conn.close()

# 导出路由器
__all__ = ["router"]