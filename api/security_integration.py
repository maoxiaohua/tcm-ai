#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全系统集成到FastAPI主应用
Security System Integration for TCM AI Platform
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import time

# 导入我们的安全组件
from core.security.rbac_system import (
    get_current_user, session_manager, UserSession, UserRole, 
    require_role, require_permission, Permission
)
from core.security.smart_router import smart_router, auth_handler
from core.security.security_monitor import security_monitor

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件 - 集成所有安全功能"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            # 1. 安全路由检查和用户分发  
            if request.url.path == "/":
                # 主页恢复早期问诊界面
                return FileResponse("/opt/tcm-ai/static/index_v2.html")
            elif request.url.path in ["/patient", "/patient/", "/patient-portal"]:
                # 重定向患者相关页面到智能工作流
                return RedirectResponse(url="/smart", status_code=302)
            elif request.url.path in ["/admin", "/admin/"]:
                # 检查管理员认证状态 - 使用统一认证系统
                # 从多个来源获取session_token
                session_token = None
                
                # 1. 从Authorization头获取
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    session_token = auth_header[7:]  # 移除 "Bearer " 前缀
                    logger.info(f"从Authorization头获取token: {session_token[:20]}...")
                
                # 2. 从cookie获取
                if not session_token:
                    session_token = request.cookies.get("session_token")
                    if session_token:
                        logger.info(f"从cookie获取token: {session_token[:20]}...")
                    else:
                        logger.info(f"未找到session_token cookie，可用cookies: {list(request.cookies.keys())}")
                
                # 如果没有token，重定向到登录
                if not session_token:
                    return RedirectResponse(url="/login", status_code=302)
                
                # 验证token并检查用户角色 - 使用统一认证系统
                import sqlite3
                try:
                    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
                    cursor = conn.cursor()
                    
                    logger.info(f"验证token: {session_token[:20]}...")
                    
                    # 检查统一session token是否有效
                    cursor.execute("""
                        SELECT u.global_user_id, s.session_status
                        FROM unified_users u
                        JOIN unified_sessions s ON u.global_user_id = s.user_id
                        WHERE s.session_id = ? AND s.session_status = 'active'
                        AND datetime(s.expires_at) > datetime('now')
                    """, (session_token,))
                    
                    session_row = cursor.fetchone()
                    logger.info(f"Session查询结果: {session_row}")
                    
                    if not session_row:
                        conn.close()
                        logger.info("Session无效或过期，重定向到登录")
                        # token无效或过期，重定向到登录
                        return RedirectResponse(url="/login", status_code=302)
                    
                    user_id, session_status = session_row
                    logger.info(f"找到用户: {user_id}, session状态: {session_status}")
                    
                    # 检查用户是否有管理员角色
                    cursor.execute("""
                        SELECT role_name
                        FROM user_roles_new
                        WHERE user_id = ? AND is_active = 1 AND is_primary = 1
                        AND UPPER(role_name) IN ('ADMIN', 'SUPERADMIN')
                    """, (user_id,))
                    
                    role_row = cursor.fetchone()
                    logger.info(f"角色查询结果: {role_row}")
                    conn.close()
                    
                    if not role_row:
                        logger.info("用户非管理员，重定向到登录")
                        # 非管理员用户，重定向到登录
                        return RedirectResponse(url="/login", status_code=302)
                    
                    logger.info(f"管理员权限验证成功，用户: {user_id}, 角色: {role_row[0]}")
                    # 权限验证成功，直接返回管理员页面
                    return FileResponse('/opt/tcm-ai/static/admin/index.html')
                        
                except Exception as e:
                    logger.error(f"Admin auth check error: {e}")
                    return RedirectResponse(url="/login", status_code=302)
            
            # 2. 继续处理请求
            response = await call_next(request)
            
            # 3. 记录API访问日志
            process_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            current_user = await self._get_current_user_safe(request)
            
            security_monitor.log_api_access(
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "Unknown"),
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                response_time_ms=process_time,
                user_id=current_user.user_id if current_user else None,
                session_token=current_user.session_token if current_user else None
            )
            
            return response
            
        except Exception as e:
            # 记录异常
            logger.error(f"Security middleware error: {str(e)}", exc_info=True)
            
            # 记录为安全事件
            security_monitor.log_api_access(
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "Unknown"),
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
                response_time_ms=(time.time() - start_time) * 1000,
                user_id=None,
                session_token=None
            )
            
            # 继续处理请求，让其他错误处理机制处理
            return await call_next(request)
    
    async def _get_current_user_safe(self, request: Request) -> Optional[UserSession]:
        """安全地获取当前用户，不抛出异常"""
        try:
            return await get_current_user(request)
        except:
            return None
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

def setup_security_system(app: FastAPI):
    """
    设置安全系统到FastAPI应用
    
    Args:
        app: FastAPI应用实例
    """
    logger.info("Setting up security system...")
    
    # 1. 添加安全中间件
    app.add_middleware(SecurityMiddleware)
    
    # 2. 添加安全相关路由
    setup_security_routes(app)
    
    # 3. 设置定期任务（清理过期会话等）
    setup_background_tasks(app)
    
    logger.info("Security system setup completed")

def setup_security_routes(app: FastAPI):
    """设置安全相关的路由"""
    
    @app.post("/api/auth/login")
    async def login_endpoint(request: Request, login_data: dict):
        """用户登录接口"""
        username = login_data.get("username")
        password = login_data.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        success, session, message = await auth_handler.login(username, password, request)
        
        if success:
            # 构建用户信息，包含详细字段
            user_data = {
                "user_id": session.user_id,
                "role": session.role.value,
                "permissions": [p.value for p in session.permissions]
            }
            
            # 如果会话中有用户详细信息，添加到响应中
            if hasattr(session, 'user_details') and session.user_details:
                details = session.user_details
                user_data.update({
                    "username": details.get("username"),
                    "email": details.get("email"),
                    "nickname": details.get("nickname"),
                    "registration_type": details.get("registration_type")
                })
            
            response = {
                "success": True,
                "message": message,
                "user": user_data,
                "redirect_url": smart_router.interface_mappings[session.role],
                "token": session.session_token  # 添加token字段到响应中
            }
            
            # 设置安全cookie
            from fastapi.responses import JSONResponse
            json_response = JSONResponse(response)
            json_response.set_cookie(
                key="session_token",
                value=session.session_token,
                httponly=True,
                secure=False,  # 开发环境使用HTTP，设置为False
                samesite="strict",
                max_age=24*3600  # 24小时
            )
            return json_response
        else:
            raise HTTPException(status_code=401, detail=message)
    
    @app.post("/api/auth/logout")
    async def logout_endpoint(current_user: UserSession = Depends(get_current_user)):
        """用户登出接口"""
        success = await auth_handler.logout(current_user.session_token)
        
        from fastapi.responses import JSONResponse
        response = JSONResponse({"success": success, "message": "已退出登录"})
        response.delete_cookie("session_token")
        return response
    
    @app.get("/api/auth/profile")
    async def get_profile(current_user: UserSession = Depends(get_current_user)):
        """获取当前用户信息"""
        # 🔧 修复：兼容统一认证系统的 roles 和旧系统的 role
        # 获取角色信息
        if hasattr(current_user, 'primary_role'):
            # 统一认证系统
            role_value = current_user.primary_role
            all_roles = current_user.roles if hasattr(current_user, 'roles') else [role_value]
        elif hasattr(current_user, 'role'):
            # 旧RBAC系统
            role_value = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
            all_roles = [role_value]
        else:
            role_value = "UNKNOWN"
            all_roles = []

        # 构建基本用户信息
        user_data = {
            "user_id": current_user.user_id,
            "role": role_value,
            "roles": all_roles,  # 新增：返回所有角色
            "permissions": [p.value if hasattr(p, 'value') else p for p in getattr(current_user, 'permissions', [])],
            "session_info": {
                "created_at": current_user.created_at.isoformat(),
                "last_activity": current_user.last_activity.isoformat(),
                "expires_at": current_user.expires_at.isoformat()
            }
        }
        
        # 如果会话中有用户详细信息，添加到响应中
        if hasattr(current_user, 'user_details') and current_user.user_details:
            details = current_user.user_details
            user_data.update({
                "username": details.get("username"),
                "email": details.get("email"),
                "nickname": details.get("nickname"),
                "registration_type": details.get("registration_type")
            })
        else:
            # 如果会话中没有详细信息，从统一users表获取
            import sqlite3
            try:
                conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
                cursor = conn.cursor()
                
                # 从统一的users表获取用户信息
                cursor.execute("""
                    SELECT username, email, nickname, registration_type, role
                    FROM users WHERE user_id = ?
                """, (current_user.user_id,))
                
                row = cursor.fetchone()
                if row:
                    username, email, nickname, registration_type, role = row
                    user_data.update({
                        "username": username,
                        "email": email,
                        "nickname": nickname,
                        "registration_type": registration_type,
                        "role": role
                    })
                
                conn.close()
            except Exception as e:
                # 如果数据库查询失败，不影响基本信息返回
                pass
        
        return {
            "success": True,
            "user": user_data
        }
    
    @app.get("/api/security/dashboard")
    @require_role([UserRole.ADMIN, UserRole.SUPERADMIN])
    async def security_dashboard(current_user: UserSession = Depends(get_current_user)):
        """安全仪表板数据（仅管理员）"""
        dashboard_data = security_monitor.get_security_dashboard_data()
        return {"success": True, "data": dashboard_data}
    
    @app.get("/api/security/alerts")
    @require_role([UserRole.ADMIN, UserRole.SUPERADMIN])
    async def get_security_alerts(current_user: UserSession = Depends(get_current_user)):
        """获取安全告警（仅管理员）"""
        alerts = security_monitor.analyze_security_events()
        return {
            "success": True,
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "description": alert.description,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "user_id": alert.user_id,
                    "ip_address": alert.ip_address,
                    "event_count": alert.event_count,
                    "is_resolved": alert.is_resolved
                }
                for alert in alerts
            ]
        }
    
    @app.get("/api/security/metrics")
    @require_role([UserRole.ADMIN, UserRole.SUPERADMIN])
    async def get_security_metrics(current_user: UserSession = Depends(get_current_user)):
        """获取系统安全指标（仅管理员）"""
        metrics = security_monitor.get_system_metrics()
        return {
            "success": True,
            "metrics": {
                "timestamp": metrics.timestamp.isoformat(),
                "total_sessions": metrics.total_sessions,
                "active_sessions": metrics.active_sessions,
                "failed_logins_1h": metrics.failed_logins_1h,
                "suspicious_activities_1h": metrics.suspicious_activities_1h,
                "api_calls_1h": metrics.api_calls_1h,
                "unique_ips_1h": metrics.unique_ips_1h,
                "error_rate_1h": metrics.error_rate_1h,
                "avg_response_time_ms": metrics.avg_response_time_ms
            }
        }
    
    # 保护现有的路由
    # 医生界面路由已移至main.py，使用优化版本
    # @app.get("/doctor")
    # @app.get("/doctor/")
    # async def doctor_interface(current_user: UserSession = Depends(get_current_user)):
    #     """医生界面（需要医生权限）"""
    #     if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPERADMIN]:
    #         return {"success": False, "detail": f"Access denied. Required roles: ['doctor', 'admin', 'superadmin']. Your role: {current_user.role.value}"}
    #     return FileResponse("/opt/tcm-ai/static/doctor/index.html")
    
    # 管理员路由已在main.py中定义，此处移除以避免冲突
    # 中间件会处理权限检查

def setup_background_tasks(app: FastAPI):
    """设置后台任务"""
    
    @app.on_event("startup")
    async def startup_event():
        """应用启动时的任务"""
        logger.info("Starting security background tasks...")
        
        # 可以在这里添加定期清理任务
        # 例如：清理过期会话、生成安全报告等
        
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时的清理任务"""
        logger.info("Shutting down security system...")

# 创建一个函数来保护现有的API路由
def protect_api_routes(app: FastAPI):
    """为现有的API路由添加权限保护"""
    
    # 保护医生相关API
    def add_doctor_protection():
        original_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and route.path.startswith('/api/doctor'):
                original_routes.append((route.path, route.methods, route.endpoint))
        
        # 重新定义受保护的路由
        for path, methods, endpoint in original_routes:
            # 这里可以添加装饰器保护
            pass
    
    # 保护管理相关API  
    def add_admin_protection():
        original_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and route.path.startswith('/api/admin'):
                original_routes.append((route.path, route.methods, route.endpoint))
        
        # 重新定义受保护的路由
        for path, methods, endpoint in original_routes:
            # 这里可以添加装饰器保护
            pass
    
    add_doctor_protection()
    add_admin_protection()

# 工具函数：检查权限的装饰器
def check_permission(permission: Permission):
    """权限检查装饰器工厂"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user
            current_user = kwargs.get('current_user')
            if not current_user or permission not in current_user.permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"权限不足。需要权限：{permission.value}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator