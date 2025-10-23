#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业级RBAC权限控制系统
Role-Based Access Control with Security Audit
"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps
import logging
import sqlite3
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """用户角色枚举"""
    ANONYMOUS = "anonymous"      # 匿名用户
    PATIENT = "patient"         # 患者
    DOCTOR = "doctor"          # 医生
    ADMIN = "admin"            # 管理员
    SUPERADMIN = "superadmin"  # 超级管理员

class Permission(Enum):
    """权限枚举"""
    # 患者权限
    CHAT_ACCESS = "chat:access"
    HISTORY_VIEW = "history:view"
    PROFILE_EDIT = "profile:edit"
    
    # 医生权限
    PRESCRIPTION_REVIEW = "prescription:review"
    PATIENT_HISTORY_ACCESS = "patient_history:access"
    DOCTOR_DASHBOARD = "doctor:dashboard"
    
    # 管理员权限
    USER_MANAGEMENT = "user:management"
    SYSTEM_MONITOR = "system:monitor"
    DATA_EXPORT = "data:export"
    AUDIT_LOG_ACCESS = "audit:access"
    
    # 超级管理员权限
    SYSTEM_CONFIG = "system:config"
    DATABASE_ACCESS = "database:access"
    SECURITY_CONFIG = "security:config"

@dataclass
class UserSession:
    """用户会话信息"""
    user_id: str
    role: UserRole
    permissions: Set[Permission]
    session_token: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    last_activity: datetime
    is_active: bool = True

@dataclass
class SecurityEvent:
    """安全事件"""
    event_type: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    timestamp: datetime
    details: Dict[str, Any]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL

class RolePermissionManager:
    """角色权限管理器"""
    
    def __init__(self):
        self.role_permissions = self._init_role_permissions()
        
    def _init_role_permissions(self) -> Dict[UserRole, Set[Permission]]:
        """初始化角色权限映射"""
        return {
            UserRole.ANONYMOUS: {
                Permission.CHAT_ACCESS,  # 匿名可以问诊
            },
            UserRole.PATIENT: {
                Permission.CHAT_ACCESS,
                Permission.HISTORY_VIEW,
                Permission.PROFILE_EDIT,
            },
            UserRole.DOCTOR: {
                Permission.CHAT_ACCESS,
                Permission.HISTORY_VIEW,
                Permission.PROFILE_EDIT,
                Permission.PRESCRIPTION_REVIEW,
                Permission.PATIENT_HISTORY_ACCESS,
                Permission.DOCTOR_DASHBOARD,
            },
            UserRole.ADMIN: {
                # 管理员拥有所有医生权限 + 管理权限
                Permission.CHAT_ACCESS,
                Permission.HISTORY_VIEW,
                Permission.PROFILE_EDIT,
                Permission.PRESCRIPTION_REVIEW,
                Permission.PATIENT_HISTORY_ACCESS,
                Permission.DOCTOR_DASHBOARD,
                Permission.USER_MANAGEMENT,
                Permission.SYSTEM_MONITOR,
                Permission.DATA_EXPORT,
                Permission.AUDIT_LOG_ACCESS,
            },
            UserRole.SUPERADMIN: {
                # 超级管理员拥有所有权限
                *[p for p in Permission]
            }
        }
    
    def get_permissions(self, role: UserRole) -> Set[Permission]:
        """获取角色权限"""
        return self.role_permissions.get(role, set())
    
    def has_permission(self, role: UserRole, permission: Permission) -> bool:
        """检查角色是否有指定权限"""
        return permission in self.get_permissions(role)

class SessionManager:
    """会话管理器"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self.active_sessions: Dict[str, UserSession] = {}
        self.security_bearer = HTTPBearer(auto_error=False)
        self.role_manager = RolePermissionManager()
        self._init_database()
        
    def _init_database(self):
        """初始化会话数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT,
                role TEXT,
                permissions TEXT,  -- JSON格式存储权限列表
                created_at TEXT,
                expires_at TEXT,
                ip_address TEXT,
                user_agent TEXT,
                last_activity TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # 创建安全事件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TEXT,
                details TEXT,  -- JSON格式
                risk_level TEXT
            )
        """)
        
        # 创建用户角色表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                assigned_by TEXT,
                assigned_at TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, user_id: str, role: UserRole, 
                      ip_address: str, user_agent: str) -> UserSession:
        """创建新会话"""
        session_token = self._generate_secure_token()
        permissions = self.role_manager.get_permissions(role)
        
        now = datetime.now()
        expires_at = now + timedelta(hours=24)  # 24小时过期
        
        session = UserSession(
            user_id=user_id,
            role=role,
            permissions=permissions,
            session_token=session_token,
            created_at=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            last_activity=now
        )
        
        # 存储到内存和数据库
        self.active_sessions[session_token] = session
        self._save_session_to_db(session)
        
        # 记录登录事件
        self._log_security_event(
            event_type="USER_LOGIN",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"role": role.value},
            risk_level="LOW"
        )
        
        logger.info(f"Created session for user {user_id} with role {role.value}")
        return session
    
    def get_session(self, session_token: str) -> Optional[UserSession]:
        """获取会话信息"""
        if not session_token:
            return None
            
        # 先从内存查找
        session = self.active_sessions.get(session_token)
        if session and session.expires_at > datetime.now():
            # 更新最后活动时间
            session.last_activity = datetime.now()
            return session
            
        # 从数据库查找
        session = self._load_session_from_db(session_token)
        if session and session.expires_at > datetime.now():
            self.active_sessions[session_token] = session
            return session
            
        return None
    
    def invalidate_session(self, session_token: str):
        """使会话失效"""
        session = self.active_sessions.pop(session_token, None)
        if session:
            self._log_security_event(
                event_type="USER_LOGOUT",
                user_id=session.user_id,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                details={"session_duration": str(datetime.now() - session.created_at)},
                risk_level="LOW"
            )
        
        # 从数据库删除
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE session_token = ?", 
                      (session_token,))
        conn.commit()
        conn.close()
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        expired_tokens = [
            token for token, session in self.active_sessions.items()
            if session.expires_at <= now
        ]
        
        for token in expired_tokens:
            self.active_sessions.pop(token, None)
            
        # 从数据库删除过期会话
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE expires_at < ?",
                      (now.isoformat(),))
        conn.commit()
        conn.close()
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
    
    def _generate_secure_token(self) -> str:
        """生成安全的会话令牌"""
        return secrets.token_urlsafe(32)
    
    def _save_session_to_db(self, session: UserSession):
        """保存会话到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        permissions_json = json.dumps([p.value for p in session.permissions])
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_sessions 
            (session_token, user_id, role, permissions, created_at, expires_at,
             ip_address, user_agent, last_activity, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_token, session.user_id, session.role.value,
            permissions_json, session.created_at.isoformat(),
            session.expires_at.isoformat(), session.ip_address,
            session.user_agent, session.last_activity.isoformat(),
            int(session.is_active)
        ))
        
        conn.commit()
        conn.close()
    
    def _load_session_from_db(self, session_token: str) -> Optional[UserSession]:
        """从数据库加载会话 - 支持user_sessions和unified_sessions两个表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 🔑 关键修复：先查询user_sessions表（旧RBAC系统）
        cursor.execute("""
            SELECT user_id, role, permissions, created_at, expires_at,
                   ip_address, user_agent, last_activity, is_active
            FROM user_sessions WHERE session_token = ? AND is_active = 1
        """, (session_token,))

        row = cursor.fetchone()

        # 🔑 如果user_sessions中没有，查询unified_sessions表（新统一认证系统）
        if not row:
            logger.info(f"🔍 user_sessions中未找到token，尝试unified_sessions: {session_token[:20]}...")
            cursor.execute("""
                SELECT user_id, session_status, device_type, created_at, expires_at,
                       ip_address, user_agent, last_activity_at,
                       CASE WHEN session_status = 'active' THEN 1 ELSE 0 END
                FROM unified_sessions
                WHERE session_id = ? AND session_status = 'active'
            """, (session_token,))

            row = cursor.fetchone()

            if not row:
                logger.warning(f"⚠️ unified_sessions中也未找到token: {session_token[:20]}...")
                conn.close()
                return None

            # unified_sessions的字段映射不同，创建默认值
            user_id = row[0]
            session_role = None  # unified_sessions没有role字段，需要从user_roles查询
            logger.info(f"✅ 从unified_sessions加载会话: user={user_id}")
        else:
            user_id = row[0]
            session_role = row[1]
            logger.info(f"✅ 从user_sessions加载会话: user={user_id}, session_role={session_role}")

        # 🔑 关键修复：从user_roles表获取用户的实际角色（优先级高于session中缓存的角色）
        cursor.execute("""
            SELECT role FROM user_roles
            WHERE user_id = ? AND is_active = 1
            ORDER BY assigned_at DESC
            LIMIT 1
        """, (user_id,))

        role_row = cursor.fetchone()
        conn.close()

        # 如果user_roles表中有角色，使用它；否则使用session中的角色
        if role_row and role_row[0]:
            actual_role = UserRole(role_row[0])
            logger.info(f"✅ 从user_roles表加载角色: user={user_id}, role={actual_role.value}")
        else:
            actual_role = UserRole(session_role) if session_role else UserRole.ANONYMOUS
            logger.info(f"⚠️ 使用session中的角色: user={user_id}, role={actual_role.value}")

        # 根据实际角色更新权限
        permissions_from_role = self.role_manager.get_permissions(actual_role)

        return UserSession(
            user_id=user_id,
            role=actual_role,
            permissions=permissions_from_role,
            session_token=session_token,
            created_at=datetime.fromisoformat(row[3]),
            expires_at=datetime.fromisoformat(row[4]),
            ip_address=row[5],
            user_agent=row[6],
            last_activity=datetime.fromisoformat(row[7]),
            is_active=bool(row[8])
        )
    
    def _log_security_event(self, event_type: str, user_id: Optional[str],
                           ip_address: str, user_agent: str,
                           details: Dict[str, Any], risk_level: str):
        """记录安全事件"""
        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(),
            details=details,
            risk_level=risk_level
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO security_events 
            (event_type, user_id, ip_address, user_agent, timestamp, details, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_type, event.user_id, event.ip_address,
            event.user_agent, event.timestamp.isoformat(),
            json.dumps(event.details), event.risk_level
        ))
        
        conn.commit()
        conn.close()

class SecurityMiddleware:
    """安全中间件"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
    
    async def get_current_user(self, request: Request,
                              credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
                              ) -> UserSession:
        """获取当前用户会话"""
        # 获取IP和User-Agent
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        # 尝试从Authorization头获取token
        token = None
        if credentials and hasattr(credentials, 'credentials'):
            token = credentials.credentials
        
        # 如果没有token，尝试从cookie获取
        if not token:
            token = request.cookies.get("session_token")
        
        # 如果仍然没有token，创建匿名会话
        if not token:
            return self.session_manager.create_session(
                user_id="anonymous",
                role=UserRole.ANONYMOUS,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # 验证token
        session = self.session_manager.get_session(token)
        if not session:
            # Token无效，创建匿名会话
            self.session_manager._log_security_event(
                event_type="INVALID_TOKEN_ACCESS",
                user_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"token": token[:10] + "..."},
                risk_level="MEDIUM"
            )
            
            return self.session_manager.create_session(
                user_id="anonymous",
                role=UserRole.ANONYMOUS,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # 验证IP地址（可选的安全检查）
        if session.ip_address != ip_address:
            self.session_manager._log_security_event(
                event_type="IP_ADDRESS_CHANGE",
                user_id=session.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "original_ip": session.ip_address,
                    "new_ip": ip_address
                },
                risk_level="HIGH"
            )
        
        return session
    
    def require_permission(self, required_permission: Permission):
        """权限装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 从kwargs中获取current_user
                current_user = kwargs.get('current_user')
                if not current_user or required_permission not in current_user.permissions:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied. Required: {required_permission.value}"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 按优先级检查各种IP头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

# 全局实例
session_manager = SessionManager()
security_middleware = SecurityMiddleware(session_manager)

# 导出的依赖函数
async def get_current_user(request: Request,
                          credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
                          ) -> UserSession:
    """获取当前用户 - 供FastAPI依赖注入使用"""
    return await security_middleware.get_current_user(request, credentials)

def require_role(required_roles: List[UserRole]):
    """角色验证装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user or current_user.role not in required_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required roles: {[r.value for r in required_roles]}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_permission(required_permission: Permission):
    """权限验证装饰器"""
    return security_middleware.require_permission(required_permission)