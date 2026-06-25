#!/usr/bin/env python3
"""
统一认证依赖 - Unified Authentication Dependencies
提供FastAPI的依赖注入函数,用于API路由的认证和权限控制
"""

import logging
from typing import Optional, List
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.security.unified_auth_service import (
    unified_auth_service,
    UserSession,
    UserRole
)
from core.doctor_management.doctor_auth import doctor_auth_manager
from core.security.rbac_system import get_current_user as rbac_get_current_user

logger = logging.getLogger(__name__)

# HTTP Bearer认证
security_bearer = HTTPBearer(auto_error=False)


# ============================================
# 核心认证依赖
# ============================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> UserSession:
    """
    统一的用户认证依赖 - 所有API的标准认证入口

    认证优先级:
    1. 统一认证系统 (unified_sessions) ✅ 优先
    2. 兼容医生JWT token ⚠️ 向下兼容
    3. 兼容RBAC token ⚠️ 向下兼容

    Returns:
        UserSession对象

    Raises:
        HTTPException 401: 未登录或会话过期
        HTTPException 403: 权限不足
    """
    # 1. 提取token
    token = _extract_token(request, credentials)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="未提供认证令牌"
        )

    # 2. 统一认证系统验证 (优先)
    user_session = await unified_auth_service.verify_session(token, request)

    if user_session:
        logger.debug(f"✅ 统一认证验证通过: {user_session.username}")
        return user_session

    # 3. 兼容模式: 尝试旧系统
    user_session = await _legacy_auth_fallback(token, request)

    if user_session:
        logger.warning(f"⚠️ 使用兼容认证: {user_session.username} (建议迁移到统一认证)")
        return user_session

    # 4. 认证失败
    raise HTTPException(
        status_code=401,
        detail="认证令牌无效或已过期,请重新登录"
    )


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials]
) -> Optional[str]:
    """提取token"""
    # 优先级1: Authorization头
    if credentials and credentials.credentials:
        return credentials.credentials

    # 优先级2: Header中的Authorization (兼容非标准格式)
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header.startswith('Bearer '):
            return auth_header.replace('Bearer ', '')
        return auth_header

    # 优先级3: Cookie
    if 'session_token' in request.cookies:
        return request.cookies['session_token']

    return None


async def _legacy_auth_fallback(
    token: str,
    request: Request
) -> Optional[UserSession]:
    """
    兼容旧系统认证 - 逐步废弃

    支持:
    1. 医生JWT token (doctor_auth_manager)
    2. RBAC token (user_sessions)
    """
    # 尝试1: 医生JWT验证
    try:
        logger.info(f"🔧 尝试医生JWT验证，token前20字符: {token[:20]}...")
        doctor_payload = doctor_auth_manager.verify_auth_token(token)
        if doctor_payload:
            logger.info(f"✅ 医生JWT验证成功: {doctor_payload}")
            # TODO: 将医生JWT会话迁移到unified_sessions
            return await _convert_doctor_jwt_to_session(token, doctor_payload, request)
        else:
            logger.info(f"❌ 医生JWT验证返回None")
    except Exception as e:
        logger.info(f"❌ 医生JWT验证失败: {e}", exc_info=True)

    # 尝试2: RBAC验证
    try:
        logger.info(f"🔧 尝试RBAC验证")
        from fastapi.security import HTTPAuthorizationCredentials
        rbac_session = await rbac_get_current_user(
            request,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )
        if rbac_session:
            logger.info(f"✅ RBAC验证成功: user_id={rbac_session.user_id}, role={rbac_session.role}")
            # TODO: 将RBAC会话迁移到unified_sessions
            return await _convert_rbac_to_session(rbac_session)
        else:
            logger.info(f"❌ RBAC验证返回None")
    except Exception as e:
        logger.info(f"❌ RBAC验证失败: {e}", exc_info=True)

    return None


async def _convert_doctor_jwt_to_session(
    token: str,
    doctor_payload: dict,
    request: Request
) -> Optional[UserSession]:
    """将医生JWT转换为UserSession"""
    import sqlite3
    from datetime import datetime, timedelta

    try:
        conn = sqlite3.connect("/home/ute/tcm-ai/data/user_history.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取医生信息
        cursor.execute("""
            SELECT * FROM doctors WHERE id = ? AND status = 'active'
        """, (doctor_payload['doctor_id'],))

        doctor = cursor.fetchone()
        conn.close()

        if not doctor:
            return None

        doctor_dict = dict(doctor)

        # 构建UserSession
        return UserSession(
            session_id=token,
            user_id=doctor_dict.get('user_id', f"doctor_{doctor_dict['id']}"),
            username=doctor_dict['license_no'],
            display_name=doctor_dict['name'],
            roles=['DOCTOR'],
            primary_role='DOCTOR',
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
            last_activity=datetime.now(),
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("User-Agent", "unknown"),
            device_info={},
            profile={'doctor': doctor_dict},
            permissions=set(),
            is_active=True,
            session_status='active'
        )

    except Exception as e:
        logger.error(f"医生JWT转换失败: {e}")
        return None


async def _convert_rbac_to_session(rbac_session) -> Optional[UserSession]:
    """将RBAC会话转换为UserSession"""
    from datetime import datetime

    try:
        return UserSession(
            session_id=rbac_session.session_token,
            user_id=rbac_session.user_id,
            username=rbac_session.user_id,
            display_name=rbac_session.user_id,
            roles=[rbac_session.role.value],
            primary_role=rbac_session.role.value,
            created_at=rbac_session.created_at,
            expires_at=rbac_session.expires_at,
            last_activity=rbac_session.last_activity,
            ip_address=rbac_session.ip_address,
            user_agent=rbac_session.user_agent,
            device_info={},
            profile={},
            permissions=rbac_session.permissions,
            is_active=rbac_session.is_active,
            session_status='active' if rbac_session.is_active else 'inactive'
        )

    except Exception as e:
        logger.error(f"RBAC会话转换失败: {e}")
        return None


# ============================================
# 角色权限控制依赖
# ============================================

def require_roles(*required_roles: str):
    """
    要求特定角色

    Usage:
        @router.get("/doctor/patients")
        async def get_patients(
            user: UserSession = Depends(require_roles('DOCTOR', 'ADMIN'))
        ):
            ...
    """
    async def dependency(user: UserSession = Depends(get_current_user)) -> UserSession:
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail=f"需要以下角色之一: {', '.join(required_roles)}"
            )
        return user

    return Depends(dependency)


def require_any_role(*required_roles: str):
    """要求任意一个角色 (别名)"""
    return require_roles(*required_roles)


def require_all_roles(*required_roles: str):
    """要求所有角色"""
    async def dependency(user: UserSession = Depends(get_current_user)) -> UserSession:
        if not all(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail=f"需要所有以下角色: {', '.join(required_roles)}"
            )
        return user

    return Depends(dependency)


# ============================================
# 便捷角色依赖
# ============================================

async def require_doctor(user: UserSession = Depends(get_current_user)) -> UserSession:
    """要求医生角色"""
    if 'DOCTOR' not in user.roles and 'ADMIN' not in user.roles:
        raise HTTPException(status_code=403, detail="需要医生权限")
    return user


async def require_patient(user: UserSession = Depends(get_current_user)) -> UserSession:
    """要求患者角色"""
    if 'PATIENT' not in user.roles and 'ADMIN' not in user.roles:
        raise HTTPException(status_code=403, detail="需要患者权限")
    return user


async def require_admin(user: UserSession = Depends(get_current_user)) -> UserSession:
    """要求管理员角色"""
    if 'ADMIN' not in user.roles and 'SUPERADMIN' not in user.roles:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ============================================
# 可选认证 (允许匿名访问)
# ============================================

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Optional[UserSession]:
    """
    可选认证 - 允许匿名访问

    Returns:
        UserSession 或 None (匿名用户)
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None
