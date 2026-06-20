#!/usr/bin/env python3
"""
统一登录API路由
提供所有用户类型的统一登录、登出、会话管理
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from core.security.unified_auth_service import (
    unified_auth_service,
    LoginRequest,
    LoginResponse,
    UserSession
)
from api.dependencies.unified_auth_deps import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/auth", tags=["unified-auth"])


# ============================================
# 请求/响应模型
# ============================================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    display_name: str
    role: str = "PATIENT"  # 默认注册为患者


class LogoutRequest(BaseModel):
    """登出请求"""
    session_token: Optional[str] = None


# ============================================
# 登录/登出
# ============================================

@router.post("/login", response_model=LoginResponse)
async def unified_login(
    request: Request,
    login_req: LoginRequest
):
    """
    统一登录入口

    支持:
    - 患者登录
    - 医生登录
    - 管理员登录

    认证方式:
    - 用户名/密码
    - 邮箱/密码
    - 手机号/密码
    """
    logger.info(f"🔐 统一登录请求: {login_req.username}")

    result = await unified_auth_service.login(
        username=login_req.username,
        password=login_req.password,
        login_method=login_req.login_method,
        device_info=login_req.device_info,
        request=request
    )

    if not result.success:
        raise HTTPException(status_code=401, detail=result.message)

    logger.info(f"✅ 登录成功: {login_req.username}, roles={result.roles}")
    return result


@router.post("/logout")
async def unified_logout(
    current_user: UserSession = Depends(get_current_user)
):
    """统一登出"""
    logger.info(f"🚪 登出请求: {current_user.username}")

    success = await unified_auth_service.logout(current_user.session_id)

    if not success:
        raise HTTPException(status_code=500, detail="登出失败")

    return {
        "success": True,
        "message": "登出成功"
    }


# ============================================
# 会话管理
# ============================================

@router.get("/session")
async def get_session_info(
    current_user: UserSession = Depends(get_current_user)
):
    """
    获取当前会话信息

    用于:
    - 验证登录状态
    - 获取用户信息和角色
    - 前端状态同步
    """
    return {
        "success": True,
        "session": {
            "session_id": current_user.session_id,
            "user_id": current_user.user_id,
            "username": current_user.username,
            "display_name": current_user.display_name,
            "roles": current_user.roles,
            "primary_role": current_user.primary_role,
            "profile": current_user.profile,
            "created_at": current_user.created_at.isoformat(),
            "expires_at": current_user.expires_at.isoformat(),
            "is_active": current_user.is_active
        }
    }


@router.get("/verify")
async def verify_session(
    current_user: Optional[UserSession] = Depends(get_current_user_optional)
):
    """
    验证会话(不抛出异常)

    Returns:
        - authenticated: true/false
        - user: 用户信息 (如果已认证)
    """
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "user_id": current_user.user_id,
                "username": current_user.username,
                "display_name": current_user.display_name,
                "roles": current_user.roles,
                "primary_role": current_user.primary_role
            }
        }
    else:
        return {
            "authenticated": False,
            "user": None
        }


# ============================================
# 用户信息
# ============================================

@router.get("/me")
async def get_current_user_info(
    current_user: UserSession = Depends(get_current_user)
):
    """
    获取当前用户完整信息

    包括:
    - 基本信息
    - 角色列表
    - 角色专属信息 (医生/患者)
    """
    return {
        "success": True,
        "user": {
            "user_id": current_user.user_id,
            "username": current_user.username,
            "display_name": current_user.display_name,
            "roles": current_user.roles,
            "primary_role": current_user.primary_role,
            "profile": current_user.profile,
            "session_info": {
                "created_at": current_user.created_at.isoformat(),
                "expires_at": current_user.expires_at.isoformat(),
                "last_activity": current_user.last_activity.isoformat()
            }
        }
    }


# ============================================
# 兼容性路由 (支持旧系统)
# ============================================

@router.get("/doctor/current")
async def get_current_doctor_compat(
    current_user: UserSession = Depends(get_current_user)
):
    """
    兼容旧的医生端API: /api/doctor/current

    为前端决策树页面等旧代码提供兼容
    """
    if 'DOCTOR' not in current_user.roles:
        raise HTTPException(status_code=403, detail="需要医生权限")

    doctor_info = current_user.profile.get('doctor', {})

    return {
        "success": True,
        "role": "doctor",
        "name": current_user.display_name,
        "id": doctor_info.get('id'),
        "user_id": current_user.user_id,
        "license_no": doctor_info.get('license_no'),
        "speciality": doctor_info.get('speciality'),
        "hospital": doctor_info.get('hospital'),
        "doctor": doctor_info
    }


# 导出路由
__all__ = ["router"]
