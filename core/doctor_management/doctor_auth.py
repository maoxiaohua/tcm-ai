"""
医生登录验证和权限管理模块
"""
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from dataclasses import asdict

# 临时修复: 直接定义简化的Doctor类，避免导入问题
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class DoctorStatus(Enum):
    """医生状态"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'

@dataclass
class Doctor:
    """医生数据类"""
    id: int
    name: str
    license_no: str
    phone: Optional[str] = None
    email: Optional[str] = None
    speciality: Optional[str] = None
    hospital: Optional[str] = None
    status: str = 'active'

class DoctorAuthManager:
    """医生认证管理器"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self.secret_key = "tcm_doctor_portal_secret_2025"  # 生产环境应使用环境变量
        
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            salt, password_hash = hashed.split(':')
            verify_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return password_hash == verify_hash.hex()
        except:
            return False
    
    def generate_auth_token(self, doctor_id: int, license_no: str) -> str:
        """生成JWT认证令牌"""
        payload = {
            'doctor_id': doctor_id,
            'license_no': license_no,
            'exp': datetime.utcnow() + timedelta(days=7),  # 7天有效期
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_auth_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def register_doctor(self, name: str, license_no: str, phone: str, 
                       email: str, password: str, speciality: str = None,
                       hospital: str = None) -> Optional[Doctor]:
        """注册新医生"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查执业证号是否已存在
            cursor.execute("SELECT id FROM doctors WHERE license_no = ?", (license_no,))
            if cursor.fetchone():
                return None
            
            # 密码哈希
            password_hash = self.hash_password(password)
            
            # 插入医生记录
            cursor.execute("""
                INSERT INTO doctors (name, license_no, phone, email, password_hash, speciality, hospital)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, license_no, phone, email, password_hash, speciality, hospital))
            
            doctor_id = cursor.lastrowid
            conn.commit()
            
            # 返回医生对象
            return Doctor(
                id=doctor_id,
                name=name,
                license_no=license_no,
                phone=phone,
                email=email,
                speciality=speciality,
                hospital=hospital,
                status=DoctorStatus.ACTIVE.value
            )
            
        except Exception as e:
            conn.rollback()
            print(f"医生注册失败: {e}")
            return None
        finally:
            conn.close()
    
    def login(self, license_no: str, password: str) -> Optional[Dict[str, Any]]:
        """医生登录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 查询医生信息
            cursor.execute("""
                SELECT * FROM doctors WHERE license_no = ? AND status = 'active'
            """, (license_no,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            doctor = dict(row)
            
            # 验证密码
            if not self.verify_password(password, doctor['password_hash']):
                return None
            
            # 生成认证令牌
            auth_token = self.generate_auth_token(doctor['id'], doctor['license_no'])
            
            # 更新最后登录时间和令牌
            cursor.execute("""
                UPDATE doctors SET auth_token = ?, last_login = datetime('now')
                WHERE id = ?
            """, (auth_token, doctor['id']))
            conn.commit()
            
            # 返回登录信息（不包含密码哈希）
            doctor.pop('password_hash', None)
            doctor['auth_token'] = auth_token
            
            return doctor
            
        except Exception as e:
            print(f"医生登录失败: {e}")
            return None
        finally:
            conn.close()
    
    def get_doctor_by_token(self, token: str) -> Optional[Doctor]:
        """通过令牌获取医生信息"""
        # 验证JWT令牌
        payload = self.verify_auth_token(token)
        if not payload:
            return None
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM doctors WHERE id = ? AND auth_token = ? AND status = 'active'
            """, (payload['doctor_id'], token))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            doctor_data = dict(row)
            doctor_data.pop('password_hash', None)  # 移除密码哈希
            
            return Doctor(**doctor_data)
            
        except Exception as e:
            print(f"获取医生信息失败: {e}")
            return None
        finally:
            conn.close()
    
    def logout(self, token: str) -> bool:
        """医生登出"""
        payload = self.verify_auth_token(token)
        if not payload:
            return False
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE doctors SET auth_token = NULL WHERE id = ?
            """, (payload['doctor_id'],))
            conn.commit()
            return True
            
        except Exception as e:
            print(f"医生登出失败: {e}")
            return False
        finally:
            conn.close()

# 全局医生认证管理器实例
doctor_auth_manager = DoctorAuthManager()