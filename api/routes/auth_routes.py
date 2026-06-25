"""
统一认证API路由
支持患者、医生、管理员多角色登录
"""
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sqlite3
import hashlib
import secrets
import uuid
import logging
from datetime import datetime, timedelta

from core.doctor_management.doctor_auth import doctor_auth_manager
from core.security.rbac_system import session_manager, UserRole

router = APIRouter(prefix="/api/auth", tags=["统一认证"])

def get_patient_device_count(patient_id: str) -> int:
    """获取患者设备登录次数"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT ip_address) as device_count
            FROM user_sessions 
            WHERE user_id = ? AND role = 'patient' AND is_active = 1
        """, (patient_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['device_count'] if result else 0
    except Exception as e:
        print(f"获取设备数量失败: {e}")
        return 0

def log_patient_login(patient_id: str, username: str, ip_address: str, user_agent: str):
    """记录患者登录信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 记录到用户会话表
        session_token = f"patient_session_{patient_id}_{int(datetime.now().timestamp())}"
        cursor.execute("""
            INSERT INTO user_sessions 
            (session_token, user_id, role, created_at, expires_at, ip_address, user_agent, last_activity, is_active)
            VALUES (?, ?, 'patient', ?, ?, ?, ?, ?, 1)
        """, (
            session_token,
            patient_id, 
            datetime.now().isoformat(),
            (datetime.now() + timedelta(days=30)).isoformat(),  # 30天过期
            ip_address,
            user_agent,
            datetime.now().isoformat()
        ))
        
        # 更新用户表的最后活跃时间
        cursor.execute("""
            UPDATE users 
            SET last_active = ?
            WHERE user_id = ?
        """, (datetime.now().isoformat(), patient_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 已记录患者登录: {username} ({patient_id}) from {ip_address}")
        return session_token
        
    except Exception as e:
        print(f"记录患者登录失败: {e}")
        return None

class LoginRequest(BaseModel):
    """统一登录请求"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None
    redirect_url: Optional[str] = None
    token: Optional[str] = None

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/home/ute/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

def verify_admin_credentials(username: str, password: str) -> Optional[Dict]:
    """验证管理员凭据（优先数据库，数据库无记录时回退到引导账号）"""
    import hashlib

    # 首先检查数据库中是否有管理员账号
    db_has_admins = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM admin_accounts WHERE role IN ('admin', 'superadmin', 'doctor')")
        db_has_admins = cursor.fetchone()[0] > 0
        conn.close()
    except Exception:
        pass

    # 检查数据库中的管理员账号
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, password_hash, role, is_active
            FROM admin_accounts
            WHERE username = ? AND role IN ('admin', 'superadmin', 'doctor')
        """, (username,))

        row = cursor.fetchone()
        conn.close()

        if row:
            user_id, password_hash, role, is_active = row

            if is_active:
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                if input_hash == password_hash:
                    # 为医生生成auth_token
                    if role == "doctor":
                        import secrets
                        auth_token = secrets.token_urlsafe(32)
                        return {
                            "id": user_id,
                            "username": username,
                            "role": role,
                            "name": "注册医生",
                            "token": auth_token
                        }
                    else:
                        return {
                            "id": user_id,
                            "username": username,
                            "role": role,
                            "name": "系统管理员" if role == "admin" else "超级管理员"
                        }
    except Exception as e:
        print(f"Database auth error: {e}")

    # 数据库无管理员时，回退到引导账号（仅首次运行/恢复模式）
    if not db_has_admins:
        bootstrap_accounts = {
            "admin": "admin123",
            "superadmin": "super123",
            "doctor": "doctor123"
        }
        if username in bootstrap_accounts and bootstrap_accounts[username] == password:
            import secrets
            logger = logging.getLogger(__name__)
            logger.warning(f"使用引导账号登录: {username}，请尽快创建数据库管理员账号")
            if username == "doctor":
                token = secrets.token_urlsafe(32)
                return {
                    "id": f"doctor_{username}",
                    "username": username,
                    "role": "doctor",
                    "name": "测试医生",
                    "token": token
                }
            else:
                return {
                    "id": f"admin_{username}",
                    "username": username,
                    "role": "admin" if username == "admin" else "superadmin",
                    "name": "系统管理员" if username == "admin" else "超级管理员"
                }

    return None

def verify_patient_credentials(username: str, password: str) -> Optional[Dict]:
    """验证患者凭据 - 使用unified_users表确保数据一致性"""
    import hashlib
    
    # 硬编码账号映射到固定ID，确保跨设备一致性
    patient_accounts = {
        "patient": {
            "password": "patient123",
            "fixed_id": "usr_20250920_fc25a1e356e4",  # 对应unified_users表中的patient用户
            "name": "测试患者001"
        },
        "test_patient": {
            "password": "test123", 
            "fixed_id": "usr_20250920_ef2b6bd221ed",  # 对应unified_users表中的test_patient用户
            "name": "测试患者002"
        }
    }
    
    if username in patient_accounts and patient_accounts[username]["password"] == password:
        account_info = patient_accounts[username]
        return {
            "id": account_info["fixed_id"],  # 使用unified格式的ID
            "username": username,
            "role": "patient",
            "name": account_info["name"],
            "login_time": datetime.now().isoformat(),
            "device_count": get_patient_device_count(account_info["fixed_id"])
        }
    
    # 修复：检查unified_users表中的患者账号（支持用户名/邮箱/手机号 + PBKDF2/SHA256密码）
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT uu.global_user_id, uu.username, uu.display_name,
                   uu.password_hash, uu.salt, ur.role_name
            FROM unified_users uu
            LEFT JOIN user_roles_new ur ON uu.global_user_id = ur.user_id AND ur.is_active = 1
            WHERE (uu.username = ? OR uu.email = ? OR uu.phone_number = ?)
              AND uu.account_status = 'active'
        """, (username, username, username))

        row = cursor.fetchone()
        conn.close()

        if row:
            global_user_id, db_username, display_name, password_hash, salt, role_name = row

            # 密码验证
            password_matches = False
            if password_hash and salt:
                # PBKDF2-SHA256 验证（统一认证格式）
                expected = hashlib.pbkdf2_hmac(
                    'sha256', password.encode('utf-8'),
                    salt.encode('utf-8'), 100000
                ).hex()
                password_matches = secrets.compare_digest(expected, password_hash)
            elif password_hash and ':' in password_hash:
                # 旧格式：salt:sha256(password+salt)
                parts = password_hash.split(':')
                if len(parts) == 2:
                    old_salt, stored_hash = parts
                    input_hash = hashlib.sha256((password + old_salt).encode()).hexdigest()
                    password_matches = (input_hash == stored_hash)
            elif password_hash:
                # 旧格式：裸 SHA-256
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                password_matches = (input_hash == password_hash)

            if password_matches:
                return {
                    "id": global_user_id,
                    "username": db_username,
                    "role": role_name.lower() if role_name else "patient",
                    "name": display_name or db_username,
                    "login_time": datetime.now().isoformat(),
                    "device_count": get_patient_device_count(global_user_id)
                }
    except Exception as e:
        print(f"Database patient auth error: {e}")
    
    return None

@router.post("/login", response_model=LoginResponse)
async def unified_login(request: LoginRequest, req: Request):
    """统一登录接口"""
    try:
        username = request.username.strip()
        password = request.password.strip()
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        user_info = None
        user_role = None
        redirect_url = None
        
        # 1. 尝试数据库认证（管理员、医生）
        admin_info = verify_admin_credentials(username, password)
        if admin_info:
            print(f"DEBUG: Using admin_info: {admin_info}")
            user_info = admin_info
            if admin_info["role"] == "doctor":
                user_role = UserRole.DOCTOR
                redirect_url = "/doctor"
            elif admin_info["role"] == "admin":
                user_role = UserRole.ADMIN
                redirect_url = "/admin"
            else:  # superadmin
                user_role = UserRole.SUPERADMIN
                redirect_url = "/admin"
        
        # 2. 尝试医生管理器登录（备用）
        if not user_info:
            doctor_result = doctor_auth_manager.login(username, password)
            if doctor_result:
                user_info = {
                    "id": str(doctor_result.get("doctor_id")),
                    "username": username,
                    "role": "doctor",
                    "name": doctor_result.get("doctor_name", "医生"),
                    "speciality": doctor_result.get("speciality"),
                    "token": doctor_result.get("auth_token")
                }
                user_role = UserRole.DOCTOR
                redirect_url = "/doctor"
        
        # 3. 尝试患者登录
        if not user_info:
            patient_info = verify_patient_credentials(username, password)
            if patient_info:
                user_info = patient_info
                user_role = UserRole.PATIENT
                redirect_url = "/"
                
                # 记录患者登录信息
                ip_address = req.client.host if req.client else "unknown"
                user_agent = req.headers.get("User-Agent", "unknown")
                patient_session_token = log_patient_login(
                    patient_info["id"], 
                    username, 
                    ip_address, 
                    user_agent
                )
                
                # 将会话token添加到用户信息中
                if patient_session_token:
                    user_info["session_token"] = patient_session_token
        
        # 验证失败
        if not user_info:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 创建会话
        ip_address = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("User-Agent", "unknown")
        
        # 保存用户信息中的token（如果存在）
        user_token = user_info.get("token")
        
        try:
            session = session_manager.create_session(
                user_id=user_info["id"],
                role=user_role,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            print(f"Session creation error: {e}")
            session = None
        
        # 确保token存在 - 优先使用用户信息中的token
        token = user_token or (session.session_token if session else None)
        if not token:
            import secrets
            token = secrets.token_urlsafe(32)
        
        # 将token添加到user_info中，确保前端可以获取到
        if token and isinstance(user_info, dict):
            user_info["token"] = token
        
        print(f"DEBUG: Final user_info: {user_info}")
        print(f"DEBUG: Final token: {token}")
        print(f"DEBUG: Session exists: {session is not None}")
        
        return LoginResponse(
            success=True,
            message="登录成功",
            user=user_info,
            redirect_url=redirect_url,
            token=token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录过程出错: {str(e)}")

@router.post("/logout")
async def logout(req: Request):
    """统一登出接口"""
    try:
        # 从Header或Cookie获取token
        auth_header = req.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = req.cookies.get("session_token")
        
        if token:
            session_manager.invalidate_session(token)
        
        return {"success": True, "message": "登出成功"}
        
    except Exception as e:
        return {"success": False, "message": f"登出失败: {str(e)}"}

@router.get("/profile")
async def get_profile(req: Request):
    """获取当前用户信息"""
    try:
        # 从session获取用户信息
        auth_header = req.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = req.cookies.get("session_token")
        
        if not token:
            raise HTTPException(status_code=401, detail="未登录")
        
        session = session_manager.get_session(token)
        if not session:
            raise HTTPException(status_code=401, detail="会话已过期")
        
        return {
            "success": True,
            "user": {
                "id": session.user_id,
                "role": session.role.value,
                "permissions": [p.value for p in session.permissions]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")
@router.get("/validate-session")
async def validate_session(authorization: Optional[str] = Header(None)):
    """
    验证session是否有效
    轻量级API，用于前端定期检查session状态
    """
    from core.unified_account.account_manager import unified_account_manager
    
    try:
        # 检查Authorization header
        if not authorization or not authorization.startswith('Bearer '):
            return {
                "valid": False,
                "reason": "missing_token"
            }
        
        # 提取session_id
        session_id = authorization.replace('Bearer ', '')
        
        # 查询session
        session = unified_account_manager.get_session(session_id)
        
        if not session:
            return {
                "valid": False,
                "reason": "session_not_found_or_expired"
            }
        
        # Session有效
        return {
            "valid": True,
            "user_id": session.user_id,
            "expires_at": session.expires_at.isoformat() if hasattr(session, 'expires_at') else None
        }
        
    except Exception as e:
        import logging
        logging.error(f"Session验证异常: {e}")
        return {
            "valid": False,
            "reason": "validation_error",
            "error": str(e)
        }
