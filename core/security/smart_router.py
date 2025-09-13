#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能路由分发系统
基于用户角色和权限的自动界面跳转
"""

from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
import logging

from .rbac_system import UserSession, UserRole, session_manager, get_current_user

logger = logging.getLogger(__name__)

class SmartRouter:
    """智能路由器 - 根据用户角色自动分发到合适的界面"""
    
    def __init__(self):
        self.interface_mappings = {
            UserRole.ANONYMOUS: "/",             # 匿名用户 → 主页问诊界面
            UserRole.PATIENT: "/smart",          # 患者 → 智能工作流界面
            UserRole.DOCTOR: "/doctor",          # 医生 → 医生界面
            UserRole.ADMIN: "/admin",            # 管理员 → 管理界面
            UserRole.SUPERADMIN: "/admin"        # 超级管理员 → 管理界面
        }
        
        # 界面对应的静态文件
        self.static_files = {
            "/smart": "/opt/tcm-ai/static/index_smart_workflow.html",
            "/doctor": "/opt/tcm-ai/static/doctor/index.html", 
            "/admin": "/opt/tcm-ai/static/admin/index.html"
        }
        
        # 受保护的路由（需要特定角色才能访问）
        self.protected_routes = {
            "/doctor": [UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPERADMIN],
            "/admin": [UserRole.ADMIN, UserRole.SUPERADMIN],
            "/smart": [UserRole.PATIENT, UserRole.ADMIN, UserRole.SUPERADMIN],  # 智能工作流需要登录
            "/api/doctor": [UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPERADMIN],
            "/api/admin": [UserRole.ADMIN, UserRole.SUPERADMIN]
        }
        
        # 需要强制登录的路径（匿名用户访问会重定向到登录页）
        self.login_required_paths = ["/smart", "/doctor", "/admin"]
    
    async def route_user(self, request: Request) -> Tuple[str, Optional[FileResponse]]:
        """
        智能用户路由分发
        
        Returns:
            (redirect_path, file_response): 重定向路径或文件响应
        """
        current_path = request.url.path
        current_user = await get_current_user(request, None)
        
        logger.info(f"Routing user {current_user.user_id} with role {current_user.role.value} to {current_path}")
        
        # 1. 如果访问根路径，根据角色重定向
        if current_path == "/" or current_path == "":
            target_interface = self.interface_mappings[current_user.role]
            return self._serve_interface(target_interface, current_user)
        
        # 2. 强制登录检查 - 匿名用户访问需要登录的路径时重定向到登录页
        if current_path in self.login_required_paths and current_user.role == UserRole.ANONYMOUS:
            logger.info(f"Anonymous user accessing {current_path}, redirecting to login")
            return "/login", None
        
        # 3. 如果访问受保护路由，检查权限
        if self._is_protected_route(current_path):
            allowed_roles = self._get_allowed_roles(current_path)
            if current_user.role not in allowed_roles:
                # 权限不足，重定向到合适的界面
                logger.warning(f"Access denied for user {current_user.user_id} to {current_path}")
                self._log_access_denied(current_user, current_path, request)
                
                target_interface = self.interface_mappings[current_user.role]
                return self._serve_interface(target_interface, current_user)
        
        # 4. 如果直接访问界面路径，验证权限并服务
        if current_path in self.static_files:
            allowed_roles = self.protected_routes.get(current_path, [UserRole.ANONYMOUS, UserRole.PATIENT, UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPERADMIN])
            if current_user.role in allowed_roles:
                return self._serve_interface(current_path, current_user)
            else:
                # 权限不足，重定向
                target_interface = self.interface_mappings[current_user.role]
                return self._serve_interface(target_interface, current_user)
        
        # 5. 其他情况，允许正常访问
        return current_path, None
    
    def _serve_interface(self, interface_path: str, user: UserSession) -> Tuple[str, FileResponse]:
        """服务界面文件"""
        static_file = self.static_files.get(interface_path)
        if static_file:
            # 记录界面访问
            self._log_interface_access(user, interface_path)
            
            response = FileResponse(static_file)
            
            # 设置安全头
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            # 如果用户有有效会话，设置session cookie
            if user.session_token and user.role != UserRole.ANONYMOUS:
                response.set_cookie(
                    key="session_token",
                    value=user.session_token,
                    httponly=True,
                    secure=False,  # 开发环境使用HTTP，设置为False
                    samesite="strict",
                    max_age=24*3600  # 24小时
                )
            
            return interface_path, response
        
        return interface_path, None
    
    def _is_protected_route(self, path: str) -> bool:
        """检查是否为受保护路由"""
        return any(path.startswith(protected) for protected in self.protected_routes.keys())
    
    def _get_allowed_roles(self, path: str) -> list:
        """获取路径允许的角色"""
        for protected_path, roles in self.protected_routes.items():
            if path.startswith(protected_path):
                return roles
        return []
    
    def _log_access_denied(self, user: UserSession, path: str, request: Request):
        """记录访问被拒绝事件"""
        session_manager._log_security_event(
            event_type="ACCESS_DENIED",
            user_id=user.user_id,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("User-Agent", "Unknown"),
            details={
                "requested_path": path,
                "user_role": user.role.value,
                "session_token": user.session_token[:10] + "..." if user.session_token else None
            },
            risk_level="MEDIUM"
        )
    
    def _log_interface_access(self, user: UserSession, interface_path: str):
        """记录界面访问"""
        session_manager._log_security_event(
            event_type="INTERFACE_ACCESS",
            user_id=user.user_id,
            ip_address=user.ip_address,
            user_agent=user.user_agent,
            details={
                "interface": interface_path,
                "user_role": user.role.value
            },
            risk_level="LOW"
        )

class AuthenticationHandler:
    """认证处理器"""
    
    def __init__(self, smart_router: SmartRouter):
        self.smart_router = smart_router
    
    async def login(self, username: str, password: str, 
                   request: Request) -> Tuple[bool, Optional[UserSession], str]:
        """
        用户登录处理
        
        Returns:
            (success, session, message)
        """
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        # 1. 验证用户凭据（这里需要集成实际的用户验证逻辑）
        user_info = await self._authenticate_user(username, password)
        
        if not user_info:
            # 登录失败
            session_manager._log_security_event(
                event_type="LOGIN_FAILED",
                user_id=username,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "invalid_credentials"},
                risk_level="MEDIUM"
            )
            return False, None, "用户名或密码错误"
        
        # 2. 创建会话
        session = session_manager.create_session(
            user_id=user_info["user_id"],
            role=UserRole(user_info["role"]),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 3. 将用户详细信息添加到会话中（用于前端显示）
        session.user_details = user_info
        
        return True, session, "登录成功"
    
    async def logout(self, session_token: str) -> bool:
        """用户登出"""
        if session_token:
            session_manager.invalidate_session(session_token)
            return True
        return False
    
    async def _authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        统一用户认证（仅查询users表）
        """
        import sqlite3
        import hashlib
        
        conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
        cursor = conn.cursor()
        
        # 统一查询users表（已包含所有用户）
        cursor.execute("""
            SELECT user_id, username, email, password_hash, nickname, 
                   registration_type, role, is_active, is_verified
            FROM users 
            WHERE (username = ? OR email = ?) 
            AND password_hash IS NOT NULL 
            AND is_active = 1
        """, (username, username))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        user_id, db_username, db_email, password_hash, nickname, registration_type, role, is_active, is_verified = row
        
        # 验证密码
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if input_hash != password_hash:
            return None
        
        return {
            "user_id": user_id,
            "role": role or "patient",  # 默认角色为patient
            "is_active": bool(is_active),
            "username": db_username,
            "email": db_email,
            "nickname": nickname,
            "registration_type": registration_type,
            "is_verified": bool(is_verified)
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

# 全局实例
smart_router = SmartRouter()
auth_handler = AuthenticationHandler(smart_router)