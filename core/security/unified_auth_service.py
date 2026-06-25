#!/usr/bin/env python3
"""
统一认证服务 - Unified Authentication Service
整合RBAC、unified_users、doctors三套系统为一个统一的认证服务

核心功能:
1. 统一登录入口 (支持患者、医生、管理员)
2. 统一会话管理 (基于unified_sessions)
3. 统一权限控制 (基于user_roles_new)
4. 向下兼容 (支持旧系统token)
"""

import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum

from fastapi import Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================
# 数据模型定义
# ============================================

class UserRole(str, Enum):
    """用户角色枚举"""
    ANONYMOUS = "ANONYMOUS"
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"
    SUPERADMIN = "SUPERADMIN"


@dataclass
class UserSession:
    """用户会话信息"""
    session_id: str              # 会话ID (session_token)
    user_id: str                 # 用户ID (global_user_id)
    username: str                # 用户名
    display_name: str            # 显示名称
    roles: List[str]             # 角色列表 ['DOCTOR', 'ADMIN']
    primary_role: str            # 主要角色

    # 会话信息
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    device_info: Dict[str, Any]

    # 扩展信息
    profile: Dict[str, Any]      # 角色专属信息 (医生信息、患者信息等)
    permissions: Set[str]        # 权限集合

    # 状态
    is_active: bool = True
    session_status: str = 'active'


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str
    login_method: str = "password"
    device_info: Optional[Dict[str, Any]] = None


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    session_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    roles: Optional[List[str]] = None
    profile: Optional[Dict[str, Any]] = None
    message: str = ""


# ============================================
# 统一认证服务核心类
# ============================================

class UnifiedAuthService:
    """统一认证服务"""

    def __init__(self, db_path: str = "/home/ute/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        logger.info("🔐 统一认证服务初始化...")

    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============================================
    # 登录认证
    # ============================================

    async def login(
        self,
        username: str,
        password: str,
        login_method: str = "password",
        device_info: Optional[Dict] = None,
        request: Optional[Request] = None
    ) -> LoginResponse:
        """
        统一登录入口

        支持:
        - 用户名/邮箱/手机号登录
        - 患者、医生、管理员统一认证
        - 自动加载角色和权限
        """
        try:
            logger.info(f"🔑 统一登录: username={username}")

            # 1. 验证用户凭据
            user = self._verify_credentials(username, password)
            if not user:
                return LoginResponse(
                    success=False,
                    message="用户名或密码错误"
                )

            # 2. 检查账户状态
            if user['account_status'] != 'active':
                return LoginResponse(
                    success=False,
                    message=f"账户状态异常: {user['account_status']}"
                )

            # 3. 获取用户角色
            roles = self._get_user_roles(user['global_user_id'])
            if not roles:
                return LoginResponse(
                    success=False,
                    message="用户未分配角色,请联系管理员"
                )

            # 4. 创建会话
            session = await self._create_session(
                user=user,
                roles=roles,
                login_method=login_method,
                device_info=device_info,
                request=request
            )

            # 5. 加载角色专属信息
            profile = self._load_role_profile(user['global_user_id'], roles)

            # 6. 更新最后登录时间
            self._update_last_login(user['global_user_id'])

            logger.info(f"✅ 登录成功: user={username}, roles={[r['role_name'] for r in roles]}")

            return LoginResponse(
                success=True,
                session_token=session['session_id'],
                user={
                    'user_id': user['global_user_id'],
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'email': user['email'],
                    'phone': user['phone_number'],
                    'role': roles[0]['role_name'].lower() if roles else 'patient',
                    'primary_role': roles[0]['role_name'].lower() if roles else 'patient',
                },
                roles=[r['role_name'] for r in roles],
                profile=profile,
                message="登录成功"
            )

        except Exception as e:
            logger.error(f"❌ 登录失败: {e}", exc_info=True)
            return LoginResponse(
                success=False,
                message=f"登录失败: {str(e)}"
            )

    def _verify_credentials(self, username: str, password: str) -> Optional[Dict]:
        """验证用户凭据"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 支持用户名、邮箱、手机号登录
            cursor.execute("""
                SELECT *
                FROM unified_users
                WHERE (username = ? OR email = ? OR phone_number = ?)
                AND account_status = 'active'
            """, (username, username, username))

            user = cursor.fetchone()
            if not user:
                return None

            user_dict = dict(user)

            # 验证密码
            if not self._verify_password(password, user_dict['password_hash'], user_dict['salt']):
                return None

            return user_dict

        finally:
            conn.close()

    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        try:
            # 使用pbkdf2_hmac验证密码
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            ).hex()

            return computed_hash == password_hash
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False

    def _get_user_roles(self, user_id: str) -> List[Dict]:
        """获取用户角色"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM user_roles_new
                WHERE user_id = ?
                AND is_active = 1
                AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY is_primary DESC, assigned_at DESC
            """, (user_id,))

            roles = [dict(row) for row in cursor.fetchall()]
            return roles

        finally:
            conn.close()

    async def _create_session(
        self,
        user: Dict,
        roles: List[Dict],
        login_method: str,
        device_info: Optional[Dict],
        request: Optional[Request]
    ) -> Dict:
        """创建会话"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 生成session_id
            session_id = self._generate_session_token()

            # 获取IP和User-Agent
            ip_address = "unknown"
            user_agent = "unknown"
            if request:
                ip_address = request.client.host if request.client else "unknown"
                user_agent = request.headers.get("User-Agent", "unknown")

            # 创建会话记录
            expires_at = datetime.now() + timedelta(days=7)  # 7天有效期

            cursor.execute("""
                INSERT INTO unified_sessions (
                    session_id, user_id, device_id, device_type, device_name,
                    ip_address, user_agent, session_status, login_method,
                    created_at, last_activity_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user['global_user_id'],
                device_info.get('device_id') if device_info else None,
                device_info.get('device_type') if device_info else None,
                device_info.get('device_name') if device_info else None,
                ip_address,
                user_agent,
                'active',
                login_method,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                expires_at.isoformat()
            ))

            conn.commit()

            return {
                'session_id': session_id,
                'expires_at': expires_at
            }

        finally:
            conn.close()

    def _generate_session_token(self) -> str:
        """生成会话token"""
        return secrets.token_urlsafe(32)

    def _load_role_profile(self, user_id: str, roles: List[Dict]) -> Dict:
        """加载角色专属信息"""
        profile = {}
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            for role in roles:
                role_name = role['role_name']

                if role_name == 'DOCTOR':
                    # 加载医生信息
                    cursor.execute("""
                        SELECT *
                        FROM doctors
                        WHERE user_id = ?
                    """, (user_id,))

                    doctor = cursor.fetchone()
                    if doctor:
                        profile['doctor'] = dict(doctor)

                elif role_name == 'PATIENT':
                    # 加载患者信息
                    cursor.execute("""
                        SELECT *
                        FROM patients
                        WHERE user_id = ?
                    """, (user_id,))

                    patient = cursor.fetchone()
                    if patient:
                        profile['patient'] = dict(patient)

            return profile

        finally:
            conn.close()

    def _update_last_login(self, user_id: str):
        """更新最后登录时间"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE unified_users
                SET last_login_at = ?
                WHERE global_user_id = ?
            """, (datetime.now().isoformat(), user_id))

            conn.commit()
        finally:
            conn.close()

    # ============================================
    # 会话验证
    # ============================================

    async def verify_session(
        self,
        session_token: str,
        request: Optional[Request] = None
    ) -> Optional[UserSession]:
        """
        验证会话

        Returns:
            UserSession对象 或 None (会话无效)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 1. 查询会话
            cursor.execute("""
                SELECT s.*, u.*
                FROM unified_sessions s
                JOIN unified_users u ON s.user_id = u.global_user_id
                WHERE s.session_id = ?
                AND s.session_status = 'active'
                AND s.expires_at > datetime('now')
                AND u.account_status = 'active'
            """, (session_token,))

            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            session_data = dict(row)

            # 2. 获取用户角色
            roles = self._get_user_roles(session_data['user_id'])
            if not roles:
                conn.close()
                return None

            # 3. 加载角色专属信息
            profile = self._load_role_profile(session_data['user_id'], roles)

            # 4. 更新最后活动时间
            cursor.execute("""
                UPDATE unified_sessions
                SET last_activity_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_token))
            conn.commit()
            conn.close()

            # 5. 构建UserSession对象
            primary_role = next(
                (r['role_name'] for r in roles if r.get('is_primary')),
                roles[0]['role_name'] if roles else 'ANONYMOUS'
            )

            user_session = UserSession(
                session_id=session_token,
                user_id=session_data['user_id'],
                username=session_data['username'],
                display_name=session_data['display_name'],
                roles=[r['role_name'] for r in roles],
                primary_role=primary_role,
                created_at=datetime.fromisoformat(session_data['created_at']),
                expires_at=datetime.fromisoformat(session_data['expires_at']),
                last_activity=datetime.now(),
                ip_address=session_data['ip_address'],
                user_agent=session_data['user_agent'],
                device_info={},
                profile=profile,
                permissions=set(),
                is_active=True,
                session_status=session_data['session_status']
            )

            logger.debug(f"✅ 会话验证成功: user={session_data['username']}, roles={user_session.roles}")
            return user_session

        except Exception as e:
            logger.error(f"❌ 会话验证失败: {e}", exc_info=True)
            return None

    # ============================================
    # 登出
    # ============================================

    async def logout(self, session_token: str) -> bool:
        """登出"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE unified_sessions
                SET session_status = 'logged_out',
                    last_activity_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_token))

            conn.commit()
            conn.close()

            logger.info(f"✅ 登出成功: session={session_token[:16]}...")
            return True

        except Exception as e:
            logger.error(f"❌ 登出失败: {e}")
            return False


# 全局单例
unified_auth_service = UnifiedAuthService()
