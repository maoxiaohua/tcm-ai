#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一认证API路由
Unified Authentication API Routes

解决现有问题：
1. 多套认证接口不统一
2. 权限检查逻辑分散
3. 会话管理不一致
4. 跨设备数据同步缺失

Version: 1.0
Author: TCM-AI架构师
Date: 2025-09-20
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

# 导入统一账户管理器
import sys
sys.path.append('/opt/tcm-ai')
from core.unified_account.account_manager import (
    unified_account_manager,
    UnifiedUser,
    UserSession,
    UserType,
    AuthMethod
)

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# 创建路由器
router = APIRouter(prefix="/api/v2/auth", tags=["统一认证v2"])

# ================================================================
# Pydantic 模型定义
# ================================================================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str
    device_name: Optional[str] = None
    remember_me: bool = False

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    display_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_type: UserType = UserType.PATIENT

class AuthResponse(BaseModel):
    """认证响应"""
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    permissions: Optional[List[str]] = None
    redirect_url: Optional[str] = None

class UserProfileResponse(BaseModel):
    """用户资料响应"""
    success: bool
    user: Optional[Dict[str, Any]] = None
    data_sync: Optional[Dict[str, Any]] = None

class DataSyncRequest(BaseModel):
    """数据同步请求"""
    data_type: str
    data_key: str
    data_content: Dict[str, Any]

# ================================================================
# 辅助函数
# ================================================================

def get_client_info(request: Request) -> tuple[str, str, str]:
    """获取客户端信息"""
    ip_address = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
        request.headers.get("X-Real-IP") or
        (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("User-Agent", "Unknown")
    device_id = request.headers.get("X-Device-ID", "")
    
    return ip_address, user_agent, device_id

def format_user_response(user: UnifiedUser) -> Dict[str, Any]:
    """格式化用户响应"""
    return {
        "id": user.global_user_id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "primary_role": user.primary_role.value,
        "account_status": user.account_status.value,
        "security_level": user.security_level.value,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "two_factor_enabled": user.two_factor_enabled,
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "user_preferences": user.user_preferences,
        "privacy_settings": user.privacy_settings
    }

def format_session_response(session: UserSession) -> Dict[str, Any]:
    """格式化会话响应"""
    return {
        "session_id": session.session_id,
        "device_type": session.device_type,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "risk_score": session.risk_score
    }

def get_redirect_url(user_type: UserType) -> str:
    """根据用户类型获取重定向URL"""
    redirect_map = {
        UserType.PATIENT: "/",
        UserType.DOCTOR: "/doctor",
        UserType.ADMIN: "/admin",
        UserType.SUPERADMIN: "/admin"
    }
    return redirect_map.get(user_type, "/")

async def get_current_user_session(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> tuple[Optional[UnifiedUser], Optional[UserSession]]:
    """获取当前用户和会话"""
    
    # 尝试从Authorization头获取token
    session_id = None
    if credentials:
        session_id = credentials.credentials
    
    # 如果没有token，尝试从cookie获取
    if not session_id:
        session_id = request.cookies.get("session_token")
    
    if not session_id:
        return None, None
    
    # 获取会话
    session = unified_account_manager.get_session(session_id)
    if not session:
        return None, None
    
    # 获取用户
    user = unified_account_manager.get_user_by_id(session.user_id)
    if not user:
        return None, None
    
    return user, session

def require_permission(permission_code: str):
    """权限检查装饰器"""
    async def permission_checker(
        current_user_session: tuple = Depends(get_current_user_session)
    ):
        user, session = current_user_session
        if not user or not session:
            raise HTTPException(status_code=401, detail="未登录")
        
        if not unified_account_manager.has_permission(user.global_user_id, permission_code):
            raise HTTPException(
                status_code=403, 
                detail=f"权限不足，需要权限: {permission_code}"
            )
        
        return user, session
    
    return permission_checker

# ================================================================
# API 路由实现
# ================================================================

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, req: Request):
    """用户登录"""
    try:
        ip_address, user_agent, device_id = get_client_info(req)
        
        # 验证输入
        if not request.username.strip() or not request.password.strip():
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        # 认证用户
        user, session = unified_account_manager.authenticate_user(
            username=request.username.strip(),
            password=request.password.strip(),
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id
        )
        
        if not user or not session:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 获取用户权限
        permissions = list(unified_account_manager.get_user_permissions(user.global_user_id))
        
        # 构建响应
        response_data = AuthResponse(
            success=True,
            message="登录成功",
            user=format_user_response(user),
            session=format_session_response(session),
            permissions=permissions,
            redirect_url=get_redirect_url(user.primary_role)
        )
        
        logger.info(f"用户登录成功: {user.username} ({user.global_user_id})")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录过程出错: {e}")
        raise HTTPException(status_code=500, detail="登录服务暂时不可用")

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, req: Request):
    """用户注册"""
    try:
        ip_address, user_agent, device_id = get_client_info(req)
        
        # 验证输入
        if not request.username.strip() or not request.password.strip():
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        if len(request.password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        
        # 创建用户
        user = unified_account_manager.create_user(
            username=request.username.strip(),
            password=request.password,
            display_name=request.display_name.strip(),
            user_type=request.user_type,
            email=request.email,
            phone_number=request.phone_number
        )
        
        # 自动登录新用户
        user, session = unified_account_manager.authenticate_user(
            username=request.username.strip(),
            password=request.password,
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id
        )
        
        # 获取用户权限
        permissions = list(unified_account_manager.get_user_permissions(user.global_user_id))
        
        response_data = AuthResponse(
            success=True,
            message="注册成功",
            user=format_user_response(user),
            session=format_session_response(session),
            permissions=permissions,
            redirect_url=get_redirect_url(user.primary_role)
        )
        
        logger.info(f"用户注册成功: {user.username} ({user.global_user_id})")
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"注册过程出错: {e}")
        raise HTTPException(status_code=500, detail="注册服务暂时不可用")

@router.post("/logout")
async def logout(
    req: Request,
    current_user_session: tuple = Depends(get_current_user_session)
):
    """用户登出"""
    try:
        user, session = current_user_session
        
        if session:
            unified_account_manager.invalidate_session(session.session_id)
            logger.info(f"用户登出: {user.username if user else 'unknown'}")
        
        return {"success": True, "message": "登出成功"}
        
    except Exception as e:
        logger.error(f"登出过程出错: {e}")
        return {"success": False, "message": "登出失败"}

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user_session: tuple = Depends(get_current_user_session)
):
    """获取用户资料"""
    user, session = current_user_session
    
    if not user or not session:
        raise HTTPException(status_code=401, detail="未登录")
    
    # 获取用户同步数据
    sync_data = unified_account_manager.get_user_data(user.global_user_id)
    
    return UserProfileResponse(
        success=True,
        user=format_user_response(user),
        data_sync=sync_data
    )

@router.get("/permissions")
async def get_permissions(
    current_user_session: tuple = Depends(get_current_user_session)
):
    """获取用户权限列表"""
    user, session = current_user_session
    
    if not user or not session:
        raise HTTPException(status_code=401, detail="未登录")
    
    permissions = list(unified_account_manager.get_user_permissions(user.global_user_id))
    
    return {
        "success": True,
        "permissions": permissions,
        "user_id": user.global_user_id,
        "primary_role": user.primary_role.value
    }

@router.post("/sync-data")
async def sync_data(
    request: DataSyncRequest,
    req: Request,
    current_user_session: tuple = Depends(get_current_user_session)
):
    """同步用户数据"""
    user, session = current_user_session
    
    if not user or not session:
        raise HTTPException(status_code=401, detail="未登录")
    
    success = unified_account_manager.sync_user_data(
        user_id=user.global_user_id,
        data_type=request.data_type,
        data_key=request.data_key,
        data_content=request.data_content,
        sync_source=session.session_id
    )
    
    if success:
        return {"success": True, "message": "数据同步成功"}
    else:
        raise HTTPException(status_code=500, detail="数据同步失败")

@router.get("/sync-data/{data_type}")
async def get_sync_data(
    data_type: str,
    current_user_session: tuple = Depends(get_current_user_session)
):
    """获取同步数据"""
    user, session = current_user_session
    
    if not user or not session:
        raise HTTPException(status_code=401, detail="未登录")
    
    data = unified_account_manager.get_user_data(user.global_user_id, data_type)
    
    return {
        "success": True,
        "data_type": data_type,
        "data": data
    }

@router.get("/sessions")
async def get_user_sessions(
    current_user_session: tuple = Depends(get_current_user_session)
):
    """获取用户所有会话"""
    user, session = current_user_session
    
    if not user or not session:
        raise HTTPException(status_code=401, detail="未登录")
    
    # 这里需要实现获取用户所有会话的方法
    # 为了简化，暂时返回当前会话
    return {
        "success": True,
        "sessions": [format_session_response(session)]
    }

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user_session: tuple = Depends(get_current_user_session)
):
    """撤销指定会话"""
    user, current_session = current_user_session
    
    if not user or not current_session:
        raise HTTPException(status_code=401, detail="未登录")
    
    # 验证会话属于当前用户（安全检查）
    target_session = unified_account_manager.get_session(session_id)
    if not target_session or target_session.user_id != user.global_user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    unified_account_manager.invalidate_session(session_id)
    
    return {"success": True, "message": "会话已撤销"}

@router.get("/check-permission/{permission_code}")
async def check_permission(
    permission_code: str,
    current_user_session: tuple = Depends(get_current_user_session)
):
    """检查权限"""
    user, session = current_user_session
    
    if not user or not session:
        return {"has_permission": False, "reason": "未登录"}
    
    has_permission = unified_account_manager.has_permission(
        user.global_user_id, 
        permission_code
    )
    
    return {
        "has_permission": has_permission,
        "permission_code": permission_code,
        "user_id": user.global_user_id
    }

# ================================================================
# 管理员专用接口
# ================================================================

@router.get("/admin/users")
async def list_users(
    page: int = 1,
    size: int = 20,
    current_user_session: tuple = Depends(require_permission("user:view_all"))
):
    """管理员：获取用户列表"""
    # 这里需要实现分页查询用户的功能
    # 为了简化，暂时返回模拟数据
    return {
        "success": True,
        "message": "用户列表功能开发中",
        "page": page,
        "size": size,
        "total": 0,
        "users": []
    }

@router.get("/admin/audit-logs")
async def get_audit_logs(
    page: int = 1,
    size: int = 50,
    event_type: Optional[str] = None,
    current_user_session: tuple = Depends(require_permission("audit:view"))
):
    """管理员：获取审计日志"""
    # 这里需要实现审计日志查询功能
    return {
        "success": True,
        "message": "审计日志功能开发中",
        "page": page,
        "size": size,
        "event_type": event_type,
        "logs": []
    }

# ================================================================
# 系统维护接口
# ================================================================

@router.post("/maintenance/cleanup-sessions")
async def cleanup_expired_sessions(
    current_user_session: tuple = Depends(require_permission("system:config"))
):
    """系统管理员：清理过期会话"""
    try:
        unified_account_manager.cleanup_expired_sessions()
        return {"success": True, "message": "过期会话清理完成"}
    except Exception as e:
        logger.error(f"清理过期会话失败: {e}")
        raise HTTPException(status_code=500, detail="清理操作失败")

@router.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        # 简单的数据库连接测试
        test_user = unified_account_manager.get_user_by_id("test")
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0",
            "database_connected": True
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# ================================================================
# 向后兼容接口
# ================================================================

@router.post("/legacy/login")
async def legacy_login(request: LoginRequest, req: Request):
    """向后兼容的登录接口"""
    # 调用新的登录接口
    response = await login(request, req)
    
    # 转换为旧格式
    if response.success and response.user:
        return {
            "success": True,
            "user": {
                "id": response.user["id"],
                "username": response.user["username"],
                "role": response.user["primary_role"],
                "name": response.user["display_name"],
                "token": response.session["session_id"] if response.session else None
            },
            "redirect_url": response.redirect_url
        }
    else:
        return {
            "success": False,
            "message": response.message
        }

# 导出路由器
__all__ = ["router"]