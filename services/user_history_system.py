# user_history_system.py - 用户历史记录系统核心模块
# TCM中医智能诊断系统 - 用户历史记录功能
# 版本: v1.0 MVP
# 创建时间: 2025-08-04

import sqlite3
import hashlib
import uuid
import json
import time
import random
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserHistorySystem:
    """用户历史记录系统 - MVP版本"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self.init_database()
        logger.info("用户历史系统初始化完成")
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户表 - 支持渐进式注册
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                device_fingerprint TEXT UNIQUE,
                phone_number TEXT UNIQUE,
                nickname TEXT,
                registration_type TEXT DEFAULT 'device',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified INTEGER DEFAULT 0,
                user_preferences TEXT DEFAULT '{}',
                health_profile TEXT DEFAULT '{}'
            )
        """)
        
        # 医生会话表 - 按医生分组管理
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctor_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                session_count INTEGER DEFAULT 1,
                chief_complaint TEXT,
                session_status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_conversations INTEGER DEFAULT 0,
                conversation_file_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # 对话记录元数据表（实际对话存储在JSON文件中）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_metadata (
                conversation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                diagnosis_summary TEXT,
                prescription_given TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES doctor_sessions(session_id)
            )
        """)
        
        # 复诊关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followup_relations (
                relation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                previous_session_id TEXT,
                current_session_id TEXT NOT NULL,
                interval_days INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # 手机验证码表 (新增)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phone_verification (
                verification_id TEXT PRIMARY KEY,
                phone_number TEXT NOT NULL,
                verification_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_used INTEGER DEFAULT 0,
                attempt_count INTEGER DEFAULT 0
            )
        """)
        
        # 设备绑定记录表 (新增)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_devices (
                binding_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                device_fingerprint TEXT NOT NULL,
                device_name TEXT,
                first_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # 创建索引优化查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_doctor 
            ON doctor_sessions(user_id, doctor_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_fingerprint 
            ON users(device_fingerprint)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_phone_verification 
            ON phone_verification(phone_number, expires_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_devices 
            ON user_devices(user_id, device_fingerprint)
        """)
        
        conn.commit()
        conn.close()
        logger.info("数据库表结构初始化完成（包含手机验证支持）")
    
    def generate_device_fingerprint(self, request_info: Dict[str, str]) -> str:
        """生成设备指纹"""
        try:
            # 收集设备特征信息
            user_agent = request_info.get('user_agent', '')
            client_ip = request_info.get('client_ip', '')
            accept_language = request_info.get('accept_language', '')
            
            # 添加时间戳（小时级别，增加唯一性但保持一定稳定性）
            hour_timestamp = str(int(time.time() / 3600))
            
            # 组合特征字符串
            fingerprint_data = f"{user_agent}|{client_ip}|{accept_language}|{hour_timestamp}"
            
            # 生成32位哈希值
            fingerprint = hashlib.md5(fingerprint_data.encode('utf-8')).hexdigest()[:32]
            
            logger.info(f"生成设备指纹: {fingerprint[:8]}...")
            return fingerprint
            
        except Exception as e:
            logger.error(f"生成设备指纹失败: {e}")
            # 备用方案：使用时间戳
            return hashlib.md5(str(time.time()).encode()).hexdigest()[:32]
    
    def register_or_get_user(self, device_fingerprint: str, phone: Optional[str] = None) -> str:
        """注册或获取用户ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if phone:
                # 手机号登录/注册
                cursor.execute("SELECT user_id FROM users WHERE phone_number=?", (phone,))
                result = cursor.fetchone()
                
                if result:
                    user_id = result[0]
                    # 绑定设备指纹
                    cursor.execute("""
                        UPDATE users SET device_fingerprint=?, last_active=CURRENT_TIMESTAMP 
                        WHERE user_id=?
                    """, (device_fingerprint, user_id))
                    logger.info(f"手机号用户登录: {user_id}")
                else:
                    # 新注册手机号用户
                    user_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO users (user_id, device_fingerprint, phone_number, 
                                         registration_type, is_verified) 
                        VALUES (?, ?, ?, 'phone', 1)
                    """, (user_id, device_fingerprint, phone))
                    logger.info(f"新手机号用户注册: {user_id}")
            else:
                # 设备注册
                cursor.execute("SELECT user_id FROM users WHERE device_fingerprint=?", (device_fingerprint,))
                result = cursor.fetchone()
                
                if result:
                    user_id = result[0]
                    # 更新最后活跃时间
                    cursor.execute("""
                        UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE user_id=?
                    """, (user_id,))
                    logger.info(f"设备用户返回: {user_id}")
                else:
                    # 新注册设备用户
                    user_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO users (user_id, device_fingerprint, registration_type) 
                        VALUES (?, ?, 'device')
                    """, (user_id, device_fingerprint))
                    logger.info(f"新设备用户注册: {user_id}")
            
            conn.commit()
            return user_id
            
        except Exception as e:
            logger.error(f"用户注册/登录失败: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def start_session(self, user_id: str, doctor_name: str, chief_complaint: str = "") -> str:
        """开始新的医生会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查该医生的历史会话数量
            cursor.execute("""
                SELECT COUNT(*) FROM doctor_sessions 
                WHERE user_id=? AND doctor_name=?
            """, (user_id, doctor_name))
            
            session_count = cursor.fetchone()[0] + 1
            session_id = str(uuid.uuid4())
            
            # 创建新会话
            cursor.execute("""
                INSERT INTO doctor_sessions 
                (session_id, user_id, doctor_name, session_count, chief_complaint) 
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, user_id, doctor_name, session_count, chief_complaint))
            
            # 如果是复诊，创建关联关系
            if session_count > 1:
                cursor.execute("""
                    SELECT session_id FROM doctor_sessions 
                    WHERE user_id=? AND doctor_name=? AND session_count=?
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id, doctor_name, session_count - 1))
                
                previous_session = cursor.fetchone()
                if previous_session:
                    relation_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO followup_relations 
                        (relation_id, user_id, previous_session_id, current_session_id) 
                        VALUES (?, ?, ?, ?)
                    """, (relation_id, user_id, previous_session[0], session_id))
            
            conn.commit()
            logger.info(f"开始会话: {session_id}, 医生: {doctor_name}, 第{session_count}次")
            return session_id
            
        except Exception as e:
            logger.error(f"开始会话失败: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_conversation_metadata(self, session_id: str, conversation_file: str, 
                                 message_count: int, diagnosis: str = "", prescription: str = ""):
        """保存对话元数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            conversation_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO conversation_metadata 
                (conversation_id, session_id, message_count, diagnosis_summary, prescription_given) 
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, session_id, message_count, diagnosis, prescription))
            
            # 更新会话的对话文件路径和计数
            cursor.execute("""
                UPDATE doctor_sessions 
                SET conversation_file_path=?, total_conversations=?, last_updated=CURRENT_TIMESTAMP
                WHERE session_id=?
            """, (conversation_file, message_count, session_id))
            
            conn.commit()
            logger.info(f"保存对话元数据: {conversation_id}")
            
        except Exception as e:
            logger.error(f"保存对话元数据失败: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
            
    def update_session_status(self, session_id: str, status: str):
        """更新会话状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE doctor_sessions 
                SET session_status=?, last_updated=CURRENT_TIMESTAMP
                WHERE session_id=?
            """, (status, session_id))
            
            conn.commit()
            logger.info(f"更新会话状态: {session_id} -> {status}")
            
        except Exception as e:
            logger.error(f"更新会话状态失败: {e}")
            conn.rollback()
        finally:
            conn.close()
            
    def detect_session_completion(self, user_message: str) -> bool:
        """检测会话是否应该标记为完成"""
        completion_keywords = [
            # 直接告别类
            "谢谢", "再见", "拜拜", "感谢", "多谢", "辛苦了",
            "thank", "bye", "goodbye", "farewell",
            
            # 结束类
            "完了", "结束", "就这样", "就这些", "没了", "没问题了",
            "end", "finish", "done", "complete",
            
            # 满意确认类  
            "好的", "明白了", "知道了", "清楚了", "懂了", "了解了",
            "明白", "清楚", "好", "行", "可以", "收到", "好的谢谢",
            "ok", "okay", "got it", "understand", "clear",
            
            # 不再需要类
            "不用了", "够了", "不需要了", "不用问了", "已经可以了"
        ]
        
        user_message_lower = user_message.lower().strip()
        
        # 增强检测逻辑：检查是否包含完成意图
        has_completion_keyword = any(keyword in user_message_lower for keyword in completion_keywords)
        
        # 特殊模式检测：短消息且是确认类
        is_short_confirmation = len(user_message_lower) <= 10 and any(word in user_message_lower for word in ["好", "行", "嗯", "是", "对"])
        
        return has_completion_keyword or is_short_confirmation
    
    def map_device_to_user(self, real_user_id: str, device_user_id: str, device_fingerprint: str = None):
        """建立设备用户ID到真实用户ID的映射"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO user_device_mapping 
                (real_user_id, device_user_id, device_fingerprint)
                VALUES (?, ?, ?)
            """, (real_user_id, device_user_id, device_fingerprint))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ 建立设备映射: {real_user_id} -> {device_user_id}")
            
        except Exception as e:
            logger.error(f"❌ 建立设备映射失败: {e}")
        finally:
            conn.close()
    
    def get_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取用户的会话历史 - 支持跨设备同步"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 🔑 查找所有与此用户关联的设备user_id
            related_user_ids = [user_id]  # 包含当前user_id
            
            # 1. 如果这是认证用户ID，查找所有映射的设备user_id
            cursor.execute("""
                SELECT device_user_id 
                FROM user_device_mapping 
                WHERE real_user_id = ?
            """, (user_id,))
            device_ids = cursor.fetchall()
            related_user_ids.extend([row[0] for row in device_ids])
            
            # 2. 如果这是设备user_id，查找对应的认证user_id及其他设备
            cursor.execute("""
                SELECT real_user_id 
                FROM user_device_mapping 
                WHERE device_user_id = ?
            """, (user_id,))
            real_user_result = cursor.fetchone()
            if real_user_result:
                real_user_id = real_user_result[0]
                related_user_ids.append(real_user_id)
                
                # 查找该真实用户的所有其他设备
                cursor.execute("""
                    SELECT device_user_id 
                    FROM user_device_mapping 
                    WHERE real_user_id = ? AND device_user_id != ?
                """, (real_user_id, user_id))
                other_devices = cursor.fetchall()
                related_user_ids.extend([row[0] for row in other_devices])
            
            # 去重
            related_user_ids = list(set(related_user_ids))
            
            # 构建查询条件
            placeholders = ','.join(['?' for _ in related_user_ids])
            cursor.execute(f"""
                SELECT session_id, doctor_name, session_count, chief_complaint, 
                       session_status, created_at, total_conversations, user_id
                FROM doctor_sessions 
                WHERE user_id IN ({placeholders})
                ORDER BY last_updated DESC 
                LIMIT ?
            """, related_user_ids + [limit])
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'doctor_name': row[1],
                    'session_count': row[2],
                    'chief_complaint': row[3],
                    'session_status': row[4],
                    'created_at': row[5],
                    'total_conversations': row[6]
                })
            
            logger.info(f"获取用户会话: {user_id}, 数量: {len(sessions)}")
            return sessions
            
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_sessions_by_doctor(self, user_id: str, doctor_name: str) -> List[Dict[str, Any]]:
        """获取用户与特定医生的会话历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT session_id, session_count, chief_complaint, session_status, 
                       created_at, total_conversations, conversation_file_path
                FROM doctor_sessions 
                WHERE user_id=? AND doctor_name=? 
                ORDER BY session_count DESC
            """, (user_id, doctor_name))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'session_count': row[1],
                    'chief_complaint': row[2],
                    'session_status': row[3],
                    'created_at': row[4],
                    'total_conversations': row[5],
                    'conversation_file_path': row[6]
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"获取医生会话失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT user_id, device_fingerprint, phone_number, nickname, 
                       registration_type, created_at, is_verified
                FROM users WHERE user_id=?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'device_fingerprint': row[1],
                    'phone_number': row[2],
                    'nickname': row[3],
                    'registration_type': row[4],
                    'created_at': row[5],
                    'is_verified': bool(row[6])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
        finally:
            conn.close()
    
    def update_user_profile(self, user_id: str, nickname: str = "", preferences: Dict = None):
        """更新用户资料"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if nickname:
                updates.append("nickname=?")
                params.append(nickname)
                
            if preferences:
                updates.append("user_preferences=?")
                params.append(json.dumps(preferences, ensure_ascii=False))
            
            if updates:
                params.append(user_id)
                sql = f"UPDATE users SET {', '.join(updates)} WHERE user_id=?"
                cursor.execute(sql, params)
                conn.commit()
                logger.info(f"更新用户资料: {user_id}")
                
        except Exception as e:
            logger.error(f"更新用户资料失败: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 用户统计
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE registration_type='phone'")
            verified_users = cursor.fetchone()[0]
            
            # 会话统计
            cursor.execute("SELECT COUNT(*) FROM doctor_sessions")
            total_sessions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM conversation_metadata")
            total_conversations = cursor.fetchone()[0]
            
            return {
                'total_users': total_users,
                'verified_users': verified_users,
                'device_users': total_users - verified_users,
                'total_sessions': total_sessions,
                'total_conversations': total_conversations
            }
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}
        finally:
            conn.close()
    
    # ========== 手机号验证相关方法 (第二阶段新增) ==========
    
    def validate_phone_number(self, phone: str) -> bool:
        """验证手机号格式"""
        phone_pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(phone_pattern, phone))
    
    def generate_verification_code(self) -> str:
        """生成6位验证码"""
        return str(random.randint(100000, 999999))
    
    def send_verification_code(self, phone: str) -> Dict[str, Any]:
        """发送验证码（模拟发送，实际需要集成阿里云短信服务）"""
        # 验证手机号格式
        if not self.validate_phone_number(phone):
            return {"success": False, "error": "手机号格式不正确"}
        
        # 检查发送频率限制（1分钟内只能发送一次）
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查最近1分钟内是否已发送
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            cursor.execute("""
                SELECT COUNT(*) FROM phone_verification 
                WHERE phone_number=? AND created_at > ?
            """, (phone, one_minute_ago.isoformat()))
            
            recent_count = cursor.fetchone()[0]
            if recent_count > 0:
                return {"success": False, "error": "验证码发送过于频繁，请稍后再试"}
            
            # 生成验证码
            verification_code = self.generate_verification_code()
            verification_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(minutes=5)  # 5分钟有效期
            
            # 保存验证码
            cursor.execute("""
                INSERT INTO phone_verification 
                (verification_id, phone_number, verification_code, expires_at) 
                VALUES (?, ?, ?, ?)
            """, (verification_id, phone, verification_code, expires_at.isoformat()))
            
            conn.commit()
            
            # 这里应该调用阿里云短信API发送验证码
            # 目前为模拟发送，实际项目中需要集成真实短信服务
            logger.info(f"发送验证码到 {phone}: {verification_code} (模拟发送)")
            
            return {
                "success": True, 
                "verification_id": verification_id,
                "expires_in": 300,  # 5分钟
                "message": f"验证码已发送到 {phone[:3]}****{phone[-4:]}"
            }
            
        except Exception as e:
            logger.error(f"发送验证码失败: {e}")
            conn.rollback()
            return {"success": False, "error": "验证码发送失败"}
        finally:
            conn.close()
    
    def verify_phone_code(self, phone: str, code: str) -> Dict[str, Any]:
        """验证手机验证码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找有效的验证码
            cursor.execute("""
                SELECT verification_id, verification_code, expires_at, is_used, attempt_count
                FROM phone_verification 
                WHERE phone_number=? AND is_used=0 AND expires_at > ?
                ORDER BY created_at DESC LIMIT 1
            """, (phone, datetime.now().isoformat()))
            
            result = cursor.fetchone()
            if not result:
                return {"success": False, "error": "验证码不存在或已过期"}
            
            verification_id, stored_code, expires_at, is_used, attempt_count = result
            
            # 增加尝试次数
            new_attempt_count = attempt_count + 1
            cursor.execute("""
                UPDATE phone_verification 
                SET attempt_count=? WHERE verification_id=?
            """, (new_attempt_count, verification_id))
            
            # 检查尝试次数限制
            if new_attempt_count > 3:
                cursor.execute("""
                    UPDATE phone_verification 
                    SET is_used=1 WHERE verification_id=?
                """, (verification_id,))
                conn.commit()
                return {"success": False, "error": "验证码错误次数过多，请重新获取"}
            
            # 验证码码匹配
            if code != stored_code:
                conn.commit()
                return {"success": False, "error": f"验证码错误，还可尝试{3-new_attempt_count}次"}
            
            # 验证成功，标记为已使用
            cursor.execute("""
                UPDATE phone_verification 
                SET is_used=1 WHERE verification_id=?
            """, (verification_id,))
            
            conn.commit()
            logger.info(f"手机号验证成功: {phone}")
            
            return {"success": True, "message": "验证码验证成功"}
            
        except Exception as e:
            logger.error(f"验证码验证失败: {e}")
            conn.rollback()
            return {"success": False, "error": "验证失败"}
        finally:
            conn.close()
    
    def bind_phone_to_user(self, device_fingerprint: str, phone: str, nickname: str = "") -> Dict[str, Any]:
        """将手机号绑定到设备用户（升级账户）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查设备用户是否存在
            cursor.execute("SELECT user_id FROM users WHERE device_fingerprint=?", (device_fingerprint,))
            device_user = cursor.fetchone()
            
            if not device_user:
                return {"success": False, "error": "设备用户不存在"}
            
            device_user_id = device_user[0]
            
            # 检查手机号是否已被其他用户绑定
            cursor.execute("SELECT user_id FROM users WHERE phone_number=?", (phone,))
            existing_phone_user = cursor.fetchone()
            
            if existing_phone_user:
                existing_user_id = existing_phone_user[0]
                
                if existing_user_id == device_user_id:
                    return {"success": False, "error": "该手机号已绑定到当前账户"}
                else:
                    # 合并账户数据
                    return self._merge_user_accounts(device_user_id, existing_user_id, device_fingerprint)
            
            # 升级设备用户为手机用户
            update_fields = [
                "phone_number=?", 
                "registration_type='phone'", 
                "is_verified=1",
                "last_active=CURRENT_TIMESTAMP"
            ]
            params = [phone]
            
            if nickname:
                update_fields.append("nickname=?")
                params.append(nickname)
            
            params.append(device_user_id)
            
            cursor.execute(f"""
                UPDATE users SET {', '.join(update_fields)} WHERE user_id=?
            """, params)
            
            # 记录设备绑定
            binding_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user_devices 
                (binding_id, user_id, device_fingerprint, device_name, is_current) 
                VALUES (?, ?, ?, ?, 1)
            """, (binding_id, device_user_id, device_fingerprint, "主设备"))
            
            conn.commit()
            logger.info(f"账户升级成功: {device_user_id} -> {phone}")
            
            return {
                "success": True, 
                "user_id": device_user_id,
                "message": "手机号绑定成功，账户已升级"
            }
            
        except Exception as e:
            logger.error(f"手机号绑定失败: {e}")
            conn.rollback()
            return {"success": False, "error": "绑定失败"}
        finally:
            conn.close()
    
    def _merge_user_accounts(self, device_user_id: str, phone_user_id: str, device_fingerprint: str) -> Dict[str, Any]:
        """合并设备用户和手机用户的数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 将设备用户的会话转移到手机用户
            cursor.execute("""
                UPDATE doctor_sessions SET user_id=? WHERE user_id=?
            """, (phone_user_id, device_user_id))
            
            # 将设备用户的复诊关系转移到手机用户
            cursor.execute("""
                UPDATE followup_relations SET user_id=? WHERE user_id=?
            """, (phone_user_id, device_user_id))
            
            # 添加设备绑定记录
            binding_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user_devices 
                (binding_id, user_id, device_fingerprint, device_name, is_current) 
                VALUES (?, ?, ?, ?, 1)
            """, (binding_id, phone_user_id, device_fingerprint, "新设备"))
            
            # 删除设备用户记录
            cursor.execute("DELETE FROM users WHERE user_id=?", (device_user_id,))
            
            # 更新手机用户最后活跃时间
            cursor.execute("""
                UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE user_id=?
            """, (phone_user_id,))
            
            conn.commit()
            logger.info(f"账户合并成功: {device_user_id} -> {phone_user_id}")
            
            return {
                "success": True,
                "user_id": phone_user_id,
                "message": "账户数据已合并，新设备绑定成功"
            }
            
        except Exception as e:
            logger.error(f"账户合并失败: {e}")
            conn.rollback()
            return {"success": False, "error": "账户合并失败"}
        finally:
            conn.close()
    
    def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户绑定的设备列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT binding_id, device_fingerprint, device_name, 
                       first_login, last_active, is_current
                FROM user_devices 
                WHERE user_id=? 
                ORDER BY last_active DESC
            """, (user_id,))
            
            devices = []
            for row in cursor.fetchall():
                devices.append({
                    'binding_id': row[0],
                    'device_fingerprint': row[1][:16] + '...',  # 部分显示
                    'device_name': row[2],
                    'first_login': row[3],
                    'last_active': row[4],
                    'is_current': bool(row[5])
                })
            
            return devices
            
        except Exception as e:
            logger.error(f"获取用户设备失败: {e}")
            return []
        finally:
            conn.close()
    
    def login_with_phone(self, phone: str, device_fingerprint: str) -> Dict[str, Any]:
        """手机号登录（多设备支持）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找手机用户
            cursor.execute("SELECT user_id FROM users WHERE phone_number=?", (phone,))
            result = cursor.fetchone()
            
            if not result:
                return {"success": False, "error": "手机号未注册"}
            
            user_id = result[0]
            
            # 检查设备是否已绑定
            cursor.execute("""
                SELECT binding_id FROM user_devices 
                WHERE user_id=? AND device_fingerprint=?
            """, (user_id, device_fingerprint))
            
            existing_binding = cursor.fetchone()
            
            if not existing_binding:
                # 新设备，创建绑定记录
                binding_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO user_devices 
                    (binding_id, user_id, device_fingerprint, device_name, is_current) 
                    VALUES (?, ?, ?, ?, 1)
                """, (binding_id, user_id, device_fingerprint, "新设备"))
                
                logger.info(f"新设备绑定: {user_id}")
            
            # 更新最后活跃时间
            cursor.execute("""
                UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE user_id=?
            """, (user_id,))
            
            cursor.execute("""
                UPDATE user_devices 
                SET last_active=CURRENT_TIMESTAMP, is_current=1 
                WHERE user_id=? AND device_fingerprint=?
            """, (user_id, device_fingerprint))
            
            conn.commit()
            
            return {
                "success": True,
                "user_id": user_id,
                "message": "登录成功"
            }
            
        except Exception as e:
            logger.error(f"手机号登录失败: {e}")
            conn.rollback()
            return {"success": False, "error": "登录失败"}
        finally:
            conn.close()
    
    def get_conversation_detail(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取对话详情（用于详细查看和导出）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取会话基本信息
            cursor.execute("""
                SELECT ds.session_id, ds.doctor_name, ds.session_count, ds.chief_complaint,
                       ds.session_status, ds.created_at, ds.conversation_file_path,
                       cm.message_count, cm.diagnosis_summary, cm.prescription_given
                FROM doctor_sessions ds
                LEFT JOIN conversation_metadata cm ON ds.session_id = cm.session_id
                WHERE ds.user_id = ? AND (ds.session_id = ? OR cm.conversation_id = ?)
                ORDER BY ds.last_updated DESC
                LIMIT 1
            """, (user_id, conversation_id, conversation_id))
            
            session_row = cursor.fetchone()
            if not session_row:
                logger.warning(f"未找到对话详情: {conversation_id}")
                return None
            
            # 获取用户信息
            user_info = self.get_user_info(user_id)
            if not user_info:
                logger.warning(f"未找到用户信息: {user_id}")
                return None
            
            # 构建对话详情
            conversation_detail = {
                'conversation_id': conversation_id,
                'session_id': session_row[0],
                'doctor_name': session_row[1],
                'session_count': session_row[2],
                'chief_complaint': session_row[3] or '未记录',
                'session_status': session_row[4],
                'created_at': session_row[5],
                'conversation_file_path': session_row[6],
                'message_count': session_row[7] or 0,
                'diagnosis_summary': session_row[8] or '未记录',
                'prescription_given': session_row[9] or '未开方',
                'user_info': {
                    'user_id': user_info['user_id'],
                    'nickname': user_info['nickname'] or f'用户_{user_info["user_id"][-4:]}',
                    'phone_number': user_info['phone_number'],
                    'registration_type': user_info['registration_type'],
                    'is_verified': user_info['is_verified']
                }
            }
            
            # 尝试读取对话文件内容
            if session_row[6]:  # conversation_file_path
                try:
                    import os
                    file_path = f"/opt/tcm/{session_row[6]}"
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            conversation_data = json.load(f)
                            # 处理不同的对话文件格式
                            if isinstance(conversation_data, list):
                                # 对话文件是消息列表格式
                                conversation_detail['conversation_messages'] = conversation_data
                                conversation_detail['session_metadata'] = {}
                            elif isinstance(conversation_data, dict):
                                # 对话文件是包含metadata的字典格式
                                conversation_detail['conversation_messages'] = conversation_data.get('messages', [])
                                conversation_detail['session_metadata'] = conversation_data.get('metadata', {})
                            else:
                                # 未知格式，设为空
                                conversation_detail['conversation_messages'] = []
                                conversation_detail['session_metadata'] = {}
                    else:
                        conversation_detail['conversation_messages'] = []
                        logger.warning(f"对话文件不存在: {file_path}")
                except Exception as e:
                    logger.error(f"读取对话文件失败: {e}")
                    conversation_detail['conversation_messages'] = []
            else:
                conversation_detail['conversation_messages'] = []
            
            logger.info(f"获取对话详情成功: {conversation_id}")
            return conversation_detail
            
        except Exception as e:
            logger.error(f"获取对话详情失败: {e}")
            return None
        finally:
            conn.close()
    
    def export_as_medical_record(self, conversation_detail: Dict[str, Any]) -> str:
        """导出为三甲医院风格的专业门诊病历"""
        try:
            # 医生信息映射
            doctor_info_map = {
                'zhang_zhongjing': {'name': '张仲景', 'title': '主任中医师', 'specialty': '经方派', 'department': '中医内科'},
                'ye_tianshi': {'name': '叶天士', 'title': '主任中医师', 'specialty': '温病派', 'department': '中医内科'},
                'li_dongyuan': {'name': '李东垣', 'title': '主任中医师', 'specialty': '脾胃派', 'department': '脾胃科'},
                'zhu_danxi': {'name': '朱丹溪', 'title': '主任中医师', 'specialty': '滋阴派', 'department': '中医妇科'},
                'liu_duzhou': {'name': '刘渡舟', 'title': '主任中医师', 'specialty': '伤寒派', 'department': '中医内科'}
            }
            
            doctor_info = doctor_info_map.get(conversation_detail['doctor_name'], {
                'name': conversation_detail['doctor_name'],
                'title': '主治中医师',
                'specialty': '中医综合',
                'department': '中医科'
            })
            
            # 格式化日期
            visit_date = datetime.fromisoformat(conversation_detail['created_at']).strftime('%Y年%m月%d日')
            visit_time = datetime.fromisoformat(conversation_detail['created_at']).strftime('%H:%M')
            
            # 提取对话内容中的关键信息
            messages = conversation_detail.get('conversation_messages', [])
            patient_messages = [msg for msg in messages if msg.get('role') == 'user']
            doctor_messages = [msg for msg in messages if msg.get('role') == 'assistant']
            
            # 主诉和现病史
            chief_complaint = conversation_detail['chief_complaint']
            present_illness = self.extract_present_illness_improved(patient_messages)
            
            # 提取四诊信息
            four_exam_info = self.extract_four_examinations_info(patient_messages)
            
            # 中医诊断和处方
            diagnosis = conversation_detail['diagnosis_summary'] or '待完善'
            prescription = conversation_detail['prescription_given'] or '未开方'
            
            # 清理处方内容中的不必要信息
            prescription, extracted_info = self._clean_prescription_content(prescription)
            follow_up_text = extracted_info['follow_up']
            lifestyle_text = extracted_info['lifestyle'] 
            usage_text = extracted_info['usage']
            modification_text = extracted_info['modification']
            
            # 生成HTML格式的专业病历
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中医门诊病历 - {doctor_info['name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'SimSun', serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            background: white;
            padding: 30px;
        }}
        
        .medical-record {{
            max-width: 800px;
            margin: 0 auto;
            border: 2px solid #000;
            padding: 30px;
            background: white;
        }}
        
        .header {{
            text-align: center;
            border-bottom: 2px solid #000;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        .hospital-name {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .record-title {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        
        .patient-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 18px;
            padding: 12px;
            border: 1px solid #ccc;
            background: #f9f9f9;
        }}
        
        .info-row {{
            display: flex;
            align-items: center;
        }}
        
        .info-label {{
            font-weight: bold;
            min-width: 80px;
            margin-right: 10px;
        }}
        
        .info-value {{
            border-bottom: 1px solid #000;
            flex: 1;
            padding: 2px 5px;
        }}
        
        .section {{
            margin-bottom: 15px;
            border: 1px solid #ddd;
            padding: 12px;
        }}
        
        .section-title {{
            font-weight: bold;
            font-size: 15px;
            margin-bottom: 8px;
            color: #d32f2f;
            border-bottom: 1px solid #d32f2f;
            padding-bottom: 3px;
        }}
        
        .section-content {{
            line-height: 1.6;
            text-align: justify;
        }}
        
        .diagnosis-box {{
            background: #f0f8ff;
            border: 2px solid #4a90e2;
            padding: 12px;
            margin: 12px 0;
        }}
        
        .prescription-box {{
            background: #f0fff0;
            border: 2px solid #4caf50;
            padding: 12px;
            margin: 12px 0;
        }}
        
        .footer {{
            margin-top: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid #000;
            padding-top: 15px;
        }}
        
        .doctor-signature {{
            text-align: right;
        }}
        
        .signature-line {{
            border-bottom: 1px solid #000;
            width: 150px;
            margin: 10px 0;
            text-align: center;
            padding: 5px;
        }}
        
        .stamp-area {{
            width: 100px;
            height: 100px;
            border: 2px dashed #ccc;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 12px;
        }}
        
        .print-info {{
            font-size: 12px;
            color: #666;
            text-align: center;
            margin-top: 20px;
            border-top: 1px solid #eee;
            padding-top: 10px;
        }}
        
        @media print {{
            body {{
                padding: 0;
            }}
            .print-info {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="medical-record">
        <!-- 病历头部 -->
        <div class="header">
            <div class="hospital-name">🏥 TCM AI中医智能诊疗中心</div>
            <div class="record-title">中医门诊病历</div>
            <div style="font-size: 12px; color: #666;">Medical Record No: {conversation_detail['session_id'][:8].upper()}</div>
        </div>
        
        <!-- 患者基本信息 -->
        <div class="patient-info">
            <div class="info-row">
                <span class="info-label">姓名：</span>
                <span class="info-value">{conversation_detail['user_info']['nickname']}</span>
            </div>
            <div class="info-row">
                <span class="info-label">性别：</span>
                <span class="info-value">未填写</span>
            </div>
            <div class="info-row">
                <span class="info-label">年龄：</span>
                <span class="info-value">未填写</span>
            </div>
            <div class="info-row">
                <span class="info-label">就诊日期：</span>
                <span class="info-value">{visit_date} {visit_time}</span>
            </div>
            <div class="info-row">
                <span class="info-label">科室：</span>
                <span class="info-value">{doctor_info['department']}</span>
            </div>
            <div class="info-row">
                <span class="info-label">医师：</span>
                <span class="info-value">{doctor_info['name']} {doctor_info['title']}</span>
            </div>
        </div>
        
        <!-- 主诉 -->
        <div class="section">
            <div class="section-title">主诉</div>
            <div class="section-content">{chief_complaint}</div>
        </div>
        
        <!-- 现病史 -->
        <div class="section">
            <div class="section-title">现病史</div>
            <div class="section-content">{present_illness}</div>
        </div>
        
        <!-- 中医四诊 -->
        <div class="section">
            <div class="section-title">中医四诊</div>
            <div class="section-content">
                <strong>问诊：</strong>AI智能问诊收集详细症状信息<br>
                <strong>望诊：</strong>舌象：{four_exam_info['tongue']}；面色神态：{four_exam_info['appearance']}<br>
                <strong>切诊：</strong>脉象：{four_exam_info['pulse']}
            </div>
        </div>
        
        <!-- 中医诊断 -->
        <div class="diagnosis-box">
            <div class="section-title">中医诊断</div>
            <div class="section-content">{diagnosis}</div>
        </div>
        
        <!-- 治疗方案 -->
        <div class="prescription-box">
            <div class="section-title">治疗方案</div>
            <div class="section-content">{prescription}</div>
        </div>
        
        <!-- 服用方法与辨证加减 -->
        <div class="section">
            <div class="section-title">服用方法与辨证加减</div>
            <div class="section-content">
                <strong>服用方法：</strong><br>
                {usage_text}<br><br>
                
                <strong>辨证加减：</strong><br>
                {modification_text}
            </div>
        </div>
        
        <!-- 医嘱与复诊 -->
        <div class="section">
            <div class="section-title">医嘱与复诊</div>
            <div class="section-content">
                <strong>用药指导：</strong><br>
                • 按方服药，注意饮食调理<br>
                • 避免辛辣刺激性食物<br><br>
                
                <strong>生活调护：</strong><br>
                {lifestyle_text}<br><br>
                
                <strong>复诊安排：</strong><br>
                {follow_up_text}<br>
                • 复诊要点：观察症状改善情况，调整治疗方案
            </div>
        </div>
        
        <!-- 免责声明 -->
        <div class="section" style="background: #fff3cd; border-color: #ffeaa7;">
            <div class="section-title" style="color: #856404;">⚠️ 重要提醒</div>
            <div class="section-content" style="color: #856404;">
                <strong>注意事项：</strong><br>
                • 本方案为AI辅助中医建议，仅供参考<br>
                • 必须在执业中医师指导下使用<br>
                • 如有疑问或不适，请及时就医<br>
                • 中药使用需遵医嘱，不可自行增减剂量
            </div>
        </div>
        
        <!-- 病历结尾 -->
        <div class="footer">
            <div class="doctor-signature">
                <div>接诊医师：{doctor_info['name']}</div>
                <div class="signature-line">医师签名</div>
                <div style="font-size: 12px;">{doctor_info['title']} | {doctor_info['specialty']}</div>
            </div>
            <div class="stamp-area">
                医院公章
            </div>
        </div>
        
        <!-- 打印信息 -->
        <div class="print-info">
            <p>🤖 本病历由TCM AI中医智能诊疗系统生成</p>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 病历编号: {conversation_detail['session_id'][:12].upper()}</p>
            <p>⚠️ 此为AI辅助诊疗记录，仅供参考，如需正式医疗服务请咨询专业医师</p>
        </div>
    </div>
</body>
</html>
            """
            
            logger.info(f"生成专业病历成功: {conversation_detail['conversation_id']}")
            return html_content
            
        except Exception as e:
            logger.error(f"生成专业病历失败: {e}")
            return f"<html><body><h1>病历生成失败</h1><p>错误信息: {str(e)}</p></body></html>"
    
    def export_as_text(self, conversation_detail: Dict[str, Any]) -> str:
        """导出为纯文本格式"""
        try:
            visit_date = datetime.fromisoformat(conversation_detail['created_at']).strftime('%Y-%m-%d %H:%M')
            
            text_content = f"""
════════════════════════════════════════
           TCM AI中医智能诊疗记录
════════════════════════════════════════

【基本信息】
患者昵称: {conversation_detail['user_info']['nickname']}
就诊日期: {visit_date}
接诊医师: {conversation_detail['doctor_name']}
就诊次数: 第{conversation_detail['session_count']}次

【主诉】
{conversation_detail['chief_complaint']}

【现病史】
{conversation_detail.get('diagnosis_summary', '未记录')}

【诊疗建议】
{conversation_detail['prescription_given']}

【对话轮数】
共{conversation_detail['message_count']}轮对话

【会话状态】
{conversation_detail['session_status']}

════════════════════════════════════════
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
病历编号: {conversation_detail['session_id'][:12].upper()}
⚠️ 此为AI辅助诊疗记录，仅供参考
════════════════════════════════════════
            """
            
            return text_content
            
        except Exception as e:
            logger.error(f"生成文本病历失败: {e}")
            return f"病历生成失败: {str(e)}"
    
    def extract_four_examinations_info(self, messages) -> dict:
        """
        提取患者描述的四诊信息（望、闻、问、切）
        """
        four_exam_info = {
            'tongue': '未描述',
            'pulse': '未描述', 
            'appearance': '未描述',
            'symptoms': []
        }
        
        if not messages:
            return four_exam_info
        
        # 提取用户消息
        user_messages = [msg.get('content', '') for msg in messages if msg.get('content')]
        
        for msg in user_messages:
            msg_lower = msg.lower()
            
            # 提取舌象描述
            tongue_patterns = [
                r'舌.*?([红白黄厚薄腻干润裂纹边尖淡暗紫]+)',
                r'舌苔.*?([白黄厚薄腻干润滑]+)',
                r'舌质.*?([红淡暗紫]+)'
            ]
            
            for pattern in tongue_patterns:
                match = re.search(pattern, msg)
                if match:
                    tongue_desc = match.group(0)
                    if four_exam_info['tongue'] == '未描述':
                        four_exam_info['tongue'] = tongue_desc
                    else:
                        four_exam_info['tongue'] += f'，{tongue_desc}'
            
            # 提取脉象描述  
            pulse_patterns = [
                r'脉.*?([浮沉迟数滑涩弦细洪缓紧弱虚实]+)',
                r'脉象.*?([浮沉迟数滑涩弦细洪缓紧弱虚实]+)'
            ]
            
            for pattern in pulse_patterns:
                match = re.search(pattern, msg)
                if match:
                    pulse_desc = match.group(0)
                    if four_exam_info['pulse'] == '未描述':
                        four_exam_info['pulse'] = pulse_desc
                    else:
                        four_exam_info['pulse'] += f'，{pulse_desc}'
            
            # 提取面色等望诊信息
            appearance_keywords = ['面色', '神态', '精神', '面红', '面白', '面黄', '憔悴', '疲倦']
            for keyword in appearance_keywords:
                if keyword in msg:
                    four_exam_info['appearance'] = f"患者自述：{msg[:50]}..."
                    break
        
        return four_exam_info

    def _clean_prescription_content(self, prescription: str) -> tuple[str, str]:
        """清理处方内容中的不必要信息，返回清理后的处方和复诊信息"""
        if not prescription or prescription == '未开方':
            return '未开方', '根据病情变化，建议7-14天后复诊'
        
        original_prescription = prescription
        
        # 1. 提取各种信息（在清理前）
        follow_up_info = []
        follow_up_patterns = [
            r'## 📞.*?复诊安排.*?(?=\n##|$)',
            r'## 复诊安排.*?(?=\n##|$)',
            r'复诊时间：.*?(?=\n##|\n\n|$)', 
            r'复诊要点：.*?(?=\n##|\n\n|$)',
            r'\d+\..*?建议.*?复诊.*?(?=\n\d+\.|\n##|\n\n|$)',
            r'建议\d+.*?天.*?后.*?复诊.*?(?=\n##|\n\n|$)',
            r'建议.*?复查.*?(?=\n##|\n\n|$)',
        ]
        
        # 提取生活调护信息
        lifestyle_info = []
        lifestyle_patterns = [
            r'## 🍃.*?生活调护.*?\n(.*?)(?=\n##|$)',  # 只提取内容部分
        ]
        
        # 提取服用方法信息  
        usage_info = []
        usage_patterns = [
            r'## 💊.*?服用方法.*?\n(.*?)(?=\n##|$)',  # 只匹配服用方法部分的内容
            r'水煎服[^#]*?(?=\n##|\n\n|$)',  # 独立的水煎服说明
        ]
        
        # 提取辨证加减信息
        modification_info = []
        modification_patterns = [
            r'## 🔄.*?辨证加减.*?\n(.*?)(?=\n##|$)',  # 只提取内容部分
            r'\*\*随证加减：\*\*([^#]*?)(?=\n##|\n\n|$)',  # 只提取随证加减的内容
        ]
        
        # 提取复诊信息
        for pattern in follow_up_patterns:
            matches = re.findall(pattern, original_prescription, re.DOTALL | re.IGNORECASE)
            for match in matches:
                clean_match = re.sub(r'^## 📞.*?复诊安排\s*', '', match).strip()
                clean_match = re.sub(r'^## 复诊安排\s*', '', clean_match).strip()
                clean_match = re.sub(r'^\d+\.\s*', '', clean_match).strip()
                if clean_match and clean_match not in follow_up_info:
                    follow_up_info.append(clean_match)
        
        # 提取生活调护信息
        for pattern in lifestyle_patterns:
            matches = re.findall(pattern, original_prescription, re.DOTALL | re.IGNORECASE)
            for match in matches:
                clean_match = re.sub(r'^## 🍃.*?生活调护\s*', '', match).strip()
                if clean_match and clean_match not in lifestyle_info:
                    lifestyle_info.append(clean_match)
        
        # 提取服用方法信息
        for pattern in usage_patterns:
            matches = re.findall(pattern, original_prescription, re.DOTALL | re.IGNORECASE)
            for match in matches:
                clean_match = re.sub(r'^## 💊.*?服用方法\s*', '', match).strip()
                if clean_match and clean_match not in usage_info:
                    usage_info.append(clean_match)
        
        # 提取辨证加减信息
        for pattern in modification_patterns:
            matches = re.findall(pattern, original_prescription, re.DOTALL | re.IGNORECASE)
            for match in matches:
                clean_match = re.sub(r'^## 🔄.*?辨证加减\s*', '', match).strip()
                clean_match = re.sub(r'^\*\*随证加减：\*\*', '', clean_match).strip()
                if clean_match and clean_match not in modification_info:
                    modification_info.append(clean_match)
        
        # 2. 清理医疗安全原则
        cleaned_content = original_prescription
        
        safety_patterns = [
            r'\*\*【医疗安全原则】：严格基于患者明确描述的症状进行分析。\*\*\s*\n*',
            r'【医疗安全原则】：.*?(?=\n##|\n\n|$)',
            r'\*\*严格基于患者明确描述的症状进行分析[。．]*\*\*\s*\n*',
            r'严格基于患者明确描述的症状进行分析[。．]*\s*\n*',
            r'## ⚠️.*?重要提醒.*?(?=\n##|$)',
            r'> \*\*注意事项：\*\*\s*\n*> - 本方案为AI辅助中医建议.*?(?=\n##|$)',
            r'> - 本方案为AI辅助中医建议，仅供参考\s*\n*',
            r'> - 必须在执业中医师指导下使用\s*\n*',
        ]
        
        for pattern in safety_patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 3. 清理重复内容（精确匹配，保留处方建议部分）
        follow_up_clean_patterns = [
            r'## 📞\s*\*\*复诊安排\*\*.*?(?=\n##|$)',  # 精确匹配复诊安排
            r'## 复诊安排.*?(?=\n##|$)',
            r'\d+\..*?建议.*?复诊.*?(?=\n\d+\.|\n##|\n\n|$)',
            r'## 🍃\s*\*\*生活调护\*\*.*?(?=\n##|$)',  # 精确匹配生活调护部分
            r'## 💊\s*\*\*服用方法\*\*.*?(?=\n##|$)',  # 精确匹配服用方法部分
            r'## 🔄\s*\*\*辨证加减\*\*.*?(?=\n##|$)',  # 精确匹配辨证加减部分
        ]
        
        for pattern in follow_up_clean_patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 4. 清理格式问题
        cleaned_content = re.sub(r'\n\n\n+', '\n\n', cleaned_content)  # 多个空行合并
        cleaned_content = re.sub(r'^\s*\n', '', cleaned_content, flags=re.MULTILINE)  # 移除空白行
        cleaned_content = cleaned_content.strip()
        
        # 5. 处理所有提取的信息
        def clean_info_list(info_list):
            """清理信息列表的通用函数"""
            cleaned = []
            for info in info_list:
                # 清理格式问题
                clean_info = re.sub(r'^\*\*\s*', '', info)  # 移除开头的**
                clean_info = re.sub(r'\s*\*\*$', '', clean_info)  # 移除结尾的**
                clean_info = re.sub(r'^-\s*', '', clean_info)  # 移除开头的-
                clean_info = clean_info.strip()
                
                # 只保留非空且不重复的信息
                if clean_info and clean_info not in cleaned:
                    cleaned.append(clean_info)
            return cleaned
        
        # 清理各类信息
        cleaned_follow_up = clean_info_list(follow_up_info)
        cleaned_lifestyle = clean_info_list(lifestyle_info)
        cleaned_usage = clean_info_list(usage_info)
        cleaned_modification = clean_info_list(modification_info)
        
        # 格式化复诊信息
        if cleaned_follow_up:
            follow_up_text = '\n'.join(f"• {info}" for info in cleaned_follow_up)
        else:
            follow_up_text = '• 根据病情变化，建议7-14天后复诊'
        
        # 格式化生活调护信息
        if cleaned_lifestyle:
            lifestyle_text = '\n'.join(f"• {info}" for info in cleaned_lifestyle)
        else:
            lifestyle_text = '• 保持良好作息，适量运动'
        
        # 格式化服用方法信息
        if cleaned_usage:
            usage_text = '\n'.join(f"• {info}" for info in cleaned_usage)
        else:
            usage_text = '• 按医嘱服用，注意观察反应'
        
        # 格式化辨证加减信息
        if cleaned_modification:
            modification_text = '\n'.join(f"• {info}" for info in cleaned_modification)
        else:
            modification_text = '• 根据症状变化调整用药'
        
        # 返回清理后的内容和所有提取的信息
        return cleaned_content, {
            'follow_up': follow_up_text,
            'lifestyle': lifestyle_text, 
            'usage': usage_text,
            'modification': modification_text
        }

    def extract_present_illness_improved(self, messages, max_length: int = 300) -> str:
        """
        改进的现病史提取
        整合更多用户消息，生成更完整的现病史
        """
        if not messages:
            return "无明显症状描述"
        
        # 提取用户消息内容
        user_messages = [msg.get('content', '') for msg in messages if msg.get('content')]
        
        if not user_messages:
            return "无明显症状描述"
        
        # 按时间顺序整理症状
        symptoms_mentioned = []
        
        for msg in user_messages[:5]:  # 取前5条消息
            msg = msg.strip()
            if len(msg) < 5 or len(msg) > 200:  # 过滤过短或过长的消息
                continue
                
            # 去掉一些无用的开头
            for prefix in ['你好', '医生', '请问', '我想咨询', '帮我看看']:
                if msg.startswith(prefix):
                    msg = msg[len(prefix):].strip()
            
            if msg:
                symptoms_mentioned.append(msg)
        
        if not symptoms_mentioned:
            return user_messages[0][:max_length] + ("..." if len(user_messages[0]) > max_length else "")
        
        # 组合成现病史
        present_illness = '患者主要表现：' + '；'.join(symptoms_mentioned)
        
        # 控制长度
        if len(present_illness) > max_length:
            present_illness = present_illness[:max_length] + "..."
        
        return present_illness

# 全局实例
user_history = UserHistorySystem()

if __name__ == "__main__":
    # 测试代码
    print("用户历史系统测试")
    
    # 模拟请求信息
    request_info = {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'client_ip': '192.168.1.100',
        'accept_language': 'zh-CN,zh;q=0.9'
    }
    
    # 生成设备指纹
    fingerprint = user_history.generate_device_fingerprint(request_info)
    print(f"设备指纹: {fingerprint}")
    
    # 注册用户
    user_id = user_history.register_or_get_user(fingerprint)
    print(f"用户ID: {user_id}")
    
    # 开始会话
    session_id = user_history.start_session(user_id, "zhang_zhongjing", "感冒症状")
    print(f"会话ID: {session_id}")
    
    # 获取用户信息
    user_info = user_history.get_user_info(user_id)
    print(f"用户信息: {user_info}")
    
    # 获取系统统计
    stats = user_history.get_system_stats()
    print(f"系统统计: {stats}")