#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一账户管理系统
Enterprise Account Management System

解决现有系统问题：
1. 账户身份混乱 - 统一身份管理
2. 权限控制分散 - 集中式RBAC
3. 跨设备数据不同步 - 统一数据同步
4. 硬编码账户安全风险 - 数据库管理

Version: 1.0
Author: TCM-AI架构师
Date: 2025-09-20
"""

import hashlib
import secrets
import uuid
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import logging
from contextlib import contextmanager
import sys

# 导入统一数据库连接模块
sys.path.append('/opt/tcm-ai')
from core.database import get_db_connection_context

logger = logging.getLogger(__name__)

class UserType(Enum):
    """用户类型枚举"""
    PATIENT = "patient"
    DOCTOR = "doctor" 
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

class AccountStatus(Enum):
    """账户状态枚举"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    DELETED = "deleted"

class SecurityLevel(Enum):
    """安全级别枚举"""
    BASIC = "basic"
    ENHANCED = "enhanced"
    PREMIUM = "premium"

class AuthMethod(Enum):
    """认证方式枚举"""
    PASSWORD = "password"
    SMS = "sms"
    EMAIL = "email"
    BIOMETRIC = "biometric"

@dataclass
class UnifiedUser:
    """统一用户模型"""
    global_user_id: str
    username: str
    email: Optional[str]
    phone_number: Optional[str]
    display_name: str
    primary_role: UserType
    account_status: AccountStatus
    security_level: SecurityLevel
    auth_methods: List[AuthMethod]
    email_verified: bool
    phone_verified: bool
    two_factor_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    user_preferences: Dict[str, Any]
    privacy_settings: Dict[str, Any]

@dataclass
class UserSession:
    """用户会话模型"""
    session_id: str
    user_id: str
    device_id: str
    device_type: str
    ip_address: str
    user_agent: str
    login_method: AuthMethod
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    risk_score: float
    session_data: Dict[str, Any]

@dataclass
class Permission:
    """权限模型"""
    code: str
    name: str
    category: str
    description: str
    risk_level: str

@dataclass
class SecurityEvent:
    """安全事件模型"""
    log_id: str
    user_id: Optional[str]
    event_type: str
    event_category: str
    event_result: str
    ip_address: Optional[str]
    event_details: Dict[str, Any]
    risk_level: str
    event_timestamp: datetime

class UnifiedAccountManager:
    """统一账户管理器"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """初始化数据库（如果新表不存在则创建）"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否已经迁移到新系统
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='unified_users'
            """)
            
            if not cursor.fetchone():
                logger.warning("统一账户系统表不存在，需要运行迁移脚本")
                # 这里可以选择自动运行迁移或者抛出异常
                # 为了安全，我们选择抛出异常，要求手动迁移
                raise Exception(
                    "统一账户系统未初始化。请先运行迁移脚本: "
                    "sqlite3 /opt/tcm-ai/data/user_history.sqlite < "
                    "/opt/tcm-ai/database/migrations/010_unified_account_system.sql"
                )
    
    @contextmanager
    def _get_db_connection(self):
        """获取数据库连接上下文管理器（使用统一连接模块）"""
        # 使用统一的数据库连接管理，确保外键约束已启用
        with get_db_connection_context() as conn:
            yield conn
    
    def _generate_user_id(self) -> str:
        """生成全局唯一用户ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = secrets.token_hex(6)
        return f"usr_{date_str}_{random_str}"
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = int(datetime.now().timestamp())
        random_str = secrets.token_hex(8)
        return f"sess_{timestamp}_{random_str}"
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """密码哈希"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000  # 迭代次数
        ).hex()
        
        return password_hash, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        expected_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(expected_hash, password_hash)
    
    def create_user(self, 
                   username: str,
                   password: str,
                   display_name: str,
                   user_type: UserType,
                   email: Optional[str] = None,
                   phone_number: Optional[str] = None,
                   created_by: Optional[str] = None) -> UnifiedUser:
        """创建新用户"""
        
        # 生成用户ID和密码哈希
        user_id = self._generate_user_id()
        password_hash, salt = self._hash_password(password)
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 检查用户名是否已存在
                cursor.execute(
                    "SELECT global_user_id FROM unified_users WHERE username = ?",
                    (username,)
                )
                if cursor.fetchone():
                    raise ValueError(f"用户名 {username} 已存在")
                
                # 检查邮箱是否已存在
                if email:
                    cursor.execute(
                        "SELECT global_user_id FROM unified_users WHERE email = ?",
                        (email,)
                    )
                    if cursor.fetchone():
                        raise ValueError(f"邮箱 {email} 已被使用")
                
                # 检查手机号是否已存在
                if phone_number:
                    cursor.execute(
                        "SELECT global_user_id FROM unified_users WHERE phone_number = ?",
                        (phone_number,)
                    )
                    if cursor.fetchone():
                        raise ValueError(f"手机号 {phone_number} 已被使用")
                
                # 插入用户记录
                cursor.execute("""
                    INSERT INTO unified_users 
                    (global_user_id, username, email, phone_number, display_name,
                     password_hash, salt, account_status, security_level,
                     auth_methods, created_at, password_changed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, username, email, phone_number, display_name,
                    password_hash, salt, AccountStatus.ACTIVE.value,
                    SecurityLevel.BASIC.value, json.dumps([AuthMethod.PASSWORD.value]),
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                
                # 分配默认角色
                cursor.execute("""
                    INSERT INTO user_roles 
                    (user_id, role, assigned_by, assigned_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    user_id, user_type.value.upper(),
                    created_by, datetime.now().isoformat()
                ))
                
                # 创建用户扩展配置
                cursor.execute("""
                    INSERT INTO user_extended_profiles (user_id) VALUES (?)
                """, (user_id,))
                
                conn.commit()
                
                # 记录安全事件
                self._log_security_event(
                    user_id=user_id,
                    event_type="user_created",
                    event_category="admin",
                    event_result="success",
                    event_details={
                        "username": username,
                        "user_type": user_type.value,
                        "created_by": created_by
                    },
                    risk_level="low"
                )
                
                logger.info(f"用户创建成功: {username} ({user_id})")
                
                # 返回用户对象
                return self.get_user_by_id(user_id)
                
            except Exception as e:
                conn.rollback()
                logger.error(f"用户创建失败: {e}")
                raise
    
    def authenticate_user(self, 
                         username: str, 
                         password: str,
                         ip_address: str,
                         user_agent: str,
                         device_id: Optional[str] = None) -> Tuple[Optional[UnifiedUser], Optional[UserSession]]:
        """用户认证"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 查找用户
            cursor.execute("""
                SELECT global_user_id, password_hash, salt, account_status,
                       login_attempts, locked_until
                FROM unified_users 
                WHERE username = ?
            """, (username,))
            
            user_row = cursor.fetchone()
            
            if not user_row:
                # 记录登录失败事件
                self._log_security_event(
                    user_id=None,
                    event_type="login_failed",
                    event_category="auth",
                    event_result="failure",
                    event_details={"username": username, "reason": "user_not_found"},
                    risk_level="medium",
                    ip_address=ip_address
                )
                return None, None
            
            user_id = user_row['global_user_id']
            password_hash = user_row['password_hash']
            salt = user_row['salt']
            account_status = user_row['account_status']
            login_attempts = user_row['login_attempts']
            locked_until = user_row['locked_until']
            
            # 检查账户状态
            if account_status != AccountStatus.ACTIVE.value:
                self._log_security_event(
                    user_id=user_id,
                    event_type="login_failed",
                    event_category="auth",
                    event_result="failure",
                    event_details={"username": username, "reason": f"account_{account_status}"},
                    risk_level="high",
                    ip_address=ip_address
                )
                return None, None
            
            # 检查账户锁定
            if locked_until:
                lock_time = datetime.fromisoformat(locked_until)
                if datetime.now() < lock_time:
                    self._log_security_event(
                        user_id=user_id,
                        event_type="login_failed",
                        event_category="auth",
                        event_result="failure",
                        event_details={"username": username, "reason": "account_locked"},
                        risk_level="high",
                        ip_address=ip_address
                    )
                    return None, None
            
            # 验证密码
            if not self._verify_password(password, password_hash, salt):
                # 增加失败次数
                new_attempts = login_attempts + 1
                
                # 如果失败次数超过5次，锁定账户1小时
                if new_attempts >= 5:
                    locked_until = (datetime.now() + timedelta(hours=1)).isoformat()
                    cursor.execute("""
                        UPDATE unified_users 
                        SET login_attempts = ?, locked_until = ?
                        WHERE global_user_id = ?
                    """, (new_attempts, locked_until, user_id))
                else:
                    cursor.execute("""
                        UPDATE unified_users 
                        SET login_attempts = ?
                        WHERE global_user_id = ?
                    """, (new_attempts, user_id))
                
                conn.commit()
                
                self._log_security_event(
                    user_id=user_id,
                    event_type="login_failed",
                    event_category="auth",
                    event_result="failure",
                    event_details={
                        "username": username, 
                        "reason": "invalid_password",
                        "attempts": new_attempts
                    },
                    risk_level="medium" if new_attempts < 3 else "high",
                    ip_address=ip_address
                )
                return None, None
            
            # 认证成功，重置失败次数
            cursor.execute("""
                UPDATE unified_users 
                SET login_attempts = 0, locked_until = NULL, last_login_at = ?
                WHERE global_user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
            
            # 获取用户完整信息
            user = self.get_user_by_id(user_id)
            
            # 创建会话
            session = self.create_session(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id or self._generate_device_id(user_agent),
                login_method=AuthMethod.PASSWORD
            )
            
            # 记录登录成功事件
            self._log_security_event(
                user_id=user_id,
                event_type="login_success",
                event_category="auth", 
                event_result="success",
                event_details={
                    "username": username,
                    "session_id": session.session_id,
                    "device_id": session.device_id
                },
                risk_level="low",
                ip_address=ip_address
            )
            
            logger.info(f"用户登录成功: {username} ({user_id})")
            return user, session
    
    def create_session(self,
                      user_id: str,
                      ip_address: str,
                      user_agent: str,
                      device_id: str,
                      login_method: AuthMethod,
                      expires_hours: int = 24) -> UserSession:
        """创建用户会话"""
        
        session_id = self._generate_session_id()
        now = datetime.now()
        expires_at = now + timedelta(hours=expires_hours)
        
        # 检测设备类型
        device_type = self._detect_device_type(user_agent)
        
        # 计算风险评分（简化版）
        risk_score = self._calculate_risk_score(user_id, ip_address, device_id)
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO unified_sessions
                (session_id, user_id, device_id, device_type, ip_address,
                 user_agent, login_method, created_at, last_activity_at,
                 expires_at, risk_score, session_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, device_id, device_type, ip_address,
                user_agent, login_method.value, now.isoformat(),
                now.isoformat(), expires_at.isoformat(), risk_score, "{}"
            ))
            
            conn.commit()
        
        return UserSession(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            device_type=device_type,
            ip_address=ip_address,
            user_agent=user_agent,
            login_method=login_method,
            created_at=now,
            last_activity_at=now,
            expires_at=expires_at,
            risk_score=risk_score,
            session_data={}
        )
    
    def get_user_by_id(self, user_id: str) -> Optional[UnifiedUser]:
        """根据用户ID获取用户信息"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.*, 
                       GROUP_CONCAT(r.role_name) as roles
                FROM unified_users u
                LEFT JOIN user_roles_new r ON u.global_user_id = r.user_id 
                    AND r.is_active = 1
                WHERE u.global_user_id = ?
                GROUP BY u.global_user_id
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 确定主要角色
            roles = row['roles'].split(',') if row['roles'] else []
            primary_role = UserType.PATIENT  # 默认角色
            
            # 按优先级确定主要角色
            role_priority = {
                'SUPERADMIN': UserType.SUPERADMIN,
                'ADMIN': UserType.ADMIN,
                'DOCTOR': UserType.DOCTOR,
                'PATIENT': UserType.PATIENT
            }
            
            for role_name in role_priority:
                if role_name in roles:
                    primary_role = role_priority[role_name]
                    break
            
            return UnifiedUser(
                global_user_id=row['global_user_id'],
                username=row['username'],
                email=row['email'],
                phone_number=row['phone_number'],
                display_name=row['display_name'],
                primary_role=primary_role,
                account_status=AccountStatus(row['account_status']),
                security_level=SecurityLevel(row['security_level']),
                auth_methods=[AuthMethod(method) for method in json.loads(row['auth_methods'])],
                email_verified=bool(row['email_verified']),
                phone_verified=bool(row['phone_verified']),
                two_factor_enabled=bool(row['two_factor_enabled']),
                created_at=datetime.fromisoformat(row['created_at']),
                last_login_at=datetime.fromisoformat(row['last_login_at']) if row['last_login_at'] else None,
                user_preferences=json.loads(row['user_preferences']),
                privacy_settings=json.loads(row['privacy_settings'])
            )
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话信息"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM unified_sessions 
                WHERE session_id = ? AND session_status = 'active'
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 检查会话是否过期
            expires_at = datetime.fromisoformat(row['expires_at'])
            if datetime.now() > expires_at:
                # 标记会话为过期
                cursor.execute("""
                    UPDATE unified_sessions 
                    SET session_status = 'expired'
                    WHERE session_id = ?
                """, (session_id,))
                conn.commit()
                return None
            
            # 更新最后活动时间
            cursor.execute("""
                UPDATE unified_sessions 
                SET last_activity_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            conn.commit()
            
            return UserSession(
                session_id=row['session_id'],
                user_id=row['user_id'],
                device_id=row['device_id'],
                device_type=row['device_type'],
                ip_address=row['ip_address'],
                user_agent=row['user_agent'],
                login_method=AuthMethod(row['login_method']),
                created_at=datetime.fromisoformat(row['created_at']),
                last_activity_at=datetime.fromisoformat(row['last_activity_at']),
                expires_at=expires_at,
                risk_score=float(row['risk_score']),
                session_data=json.loads(row['session_data'])
            )
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户权限列表"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT p.permission_code
                FROM user_roles_new ur
                JOIN role_permissions rp ON ur.role_name = rp.role_name
                JOIN permissions p ON rp.permission_code = p.permission_code
                WHERE ur.user_id = ? 
                    AND ur.is_active = 1 
                    AND rp.is_granted = 1
                    AND p.is_active = 1
                    AND (ur.expires_at IS NULL OR ur.expires_at > datetime('now'))
            """, (user_id,))
            
            permissions = {row['permission_code'] for row in cursor.fetchall()}
            return permissions
    
    def has_permission(self, user_id: str, permission_code: str) -> bool:
        """检查用户是否具有指定权限"""
        permissions = self.get_user_permissions(user_id)
        return permission_code in permissions
    
    def invalidate_session(self, session_id: str):
        """使会话失效"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 获取会话信息用于日志记录
            cursor.execute("""
                SELECT user_id, ip_address FROM unified_sessions 
                WHERE session_id = ?
            """, (session_id,))
            
            session_row = cursor.fetchone()
            
            # 标记会话为已撤销
            cursor.execute("""
                UPDATE unified_sessions 
                SET session_status = 'revoked'
                WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
            
            # 记录注销事件
            if session_row:
                self._log_security_event(
                    user_id=session_row['user_id'],
                    event_type="logout",
                    event_category="auth",
                    event_result="success",
                    event_details={"session_id": session_id},
                    risk_level="low",
                    ip_address=session_row['ip_address']
                )
    
    def sync_user_data(self, 
                      user_id: str,
                      data_type: str,
                      data_key: str,
                      data_content: Dict[str, Any],
                      sync_source: str) -> bool:
        """同步用户数据"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 检查是否存在数据
                cursor.execute("""
                    SELECT sync_id, data_version, data_content 
                    FROM user_data_sync
                    WHERE user_id = ? AND data_type = ? AND data_key = ?
                """, (user_id, data_type, data_key))
                
                existing_row = cursor.fetchone()
                
                if existing_row:
                    # 更新现有数据
                    new_version = existing_row['data_version'] + 1
                    cursor.execute("""
                        UPDATE user_data_sync
                        SET data_content = ?, data_version = ?, 
                            updated_at = ?, sync_source = ?, sync_status = 'synced'
                        WHERE sync_id = ?
                    """, (
                        json.dumps(data_content), new_version,
                        datetime.now().isoformat(), sync_source,
                        existing_row['sync_id']
                    ))
                else:
                    # 创建新数据记录
                    sync_id = f"sync_{int(datetime.now().timestamp())}_{secrets.token_hex(4)}"
                    cursor.execute("""
                        INSERT INTO user_data_sync
                        (sync_id, user_id, data_type, data_key, data_content,
                         data_version, sync_source, sync_status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sync_id, user_id, data_type, data_key,
                        json.dumps(data_content), 1, sync_source, 'synced',
                        datetime.now().isoformat(), datetime.now().isoformat()
                    ))
                
                conn.commit()
                return True
                
            except Exception as e:
                conn.rollback()
                logger.error(f"数据同步失败: {e}")
                return False
    
    def get_user_data(self, 
                     user_id: str,
                     data_type: Optional[str] = None) -> Dict[str, Any]:
        """获取用户同步数据"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            if data_type:
                cursor.execute("""
                    SELECT data_key, data_content, data_version, updated_at
                    FROM user_data_sync
                    WHERE user_id = ? AND data_type = ? AND sync_status = 'synced'
                    ORDER BY updated_at DESC
                """, (user_id, data_type))
            else:
                cursor.execute("""
                    SELECT data_type, data_key, data_content, data_version, updated_at
                    FROM user_data_sync
                    WHERE user_id = ? AND sync_status = 'synced'
                    ORDER BY data_type, updated_at DESC
                """, (user_id,))
            
            result = {}
            for row in cursor.fetchall():
                if data_type:
                    result[row['data_key']] = {
                        'content': json.loads(row['data_content']),
                        'version': row['data_version'],
                        'updated_at': row['updated_at']
                    }
                else:
                    if row['data_type'] not in result:
                        result[row['data_type']] = {}
                    result[row['data_type']][row['data_key']] = {
                        'content': json.loads(row['data_content']),
                        'version': row['data_version'],
                        'updated_at': row['updated_at']
                    }
            
            return result
    
    def _log_security_event(self,
                           event_type: str,
                           event_category: str,
                           event_result: str,
                           event_details: Dict[str, Any],
                           risk_level: str,
                           user_id: Optional[str] = None,
                           ip_address: Optional[str] = None):
        """记录安全事件"""
        
        log_id = f"audit_{int(datetime.now().timestamp())}_{secrets.token_hex(4)}"
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_audit_logs
                (log_id, user_id, event_type, event_category, event_result,
                 ip_address, event_details, risk_level, event_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, user_id, event_type, event_category, event_result,
                ip_address, json.dumps(event_details), risk_level,
                datetime.now().isoformat()
            ))
            
            conn.commit()
    
    def _generate_device_id(self, user_agent: str) -> str:
        """生成设备ID"""
        device_hash = hashlib.md5(user_agent.encode()).hexdigest()
        return f"device_{device_hash[:12]}"
    
    def _detect_device_type(self, user_agent: str) -> str:
        """检测设备类型"""
        user_agent_lower = user_agent.lower()
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
            return 'mobile'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            return 'tablet'
        else:
            return 'desktop'
    
    def _calculate_risk_score(self, user_id: str, ip_address: str, device_id: str) -> float:
        """计算风险评分（简化版）"""
        risk_score = 0.0
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 检查IP是否为新IP
            cursor.execute("""
                SELECT COUNT(*) as count FROM unified_sessions
                WHERE user_id = ? AND ip_address = ?
            """, (user_id, ip_address))
            
            if cursor.fetchone()['count'] == 0:
                risk_score += 0.3  # 新IP增加风险
            
            # 检查设备是否为新设备
            cursor.execute("""
                SELECT COUNT(*) as count FROM unified_sessions
                WHERE user_id = ? AND device_id = ?
            """, (user_id, device_id))
            
            if cursor.fetchone()['count'] == 0:
                risk_score += 0.2  # 新设备增加风险
            
        return min(risk_score, 1.0)
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE unified_sessions 
                SET session_status = 'expired'
                WHERE expires_at < datetime('now') AND session_status = 'active'
            """)
            
            expired_count = cursor.rowcount
            conn.commit()
            
            if expired_count > 0:
                logger.info(f"清理了 {expired_count} 个过期会话")

# 全局实例
unified_account_manager = UnifiedAccountManager()