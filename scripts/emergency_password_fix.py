#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急密码安全修复脚本
Emergency Password Security Fix

修复问题：
1. 将明文密码转换为PBKDF2哈希
2. 将SHA256密码升级为PBKDF2哈希  
3. 统一密码存储格式
4. 清理过期会话

使用方法：
python /opt/tcm-ai/scripts/emergency_password_fix.py

Author: TCM-AI Security Team
Date: 2025-09-22
"""

import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/tcm-ai/logs/password_fix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PasswordSecurityFixer:
    def __init__(self, db_path="/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self.fixes_applied = 0
        self.backup_file = f"/opt/tcm-ai/data/backup_before_password_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    def create_backup(self):
        """创建数据库备份"""
        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_file)
            logger.info(f"数据库备份已创建: {self.backup_file}")
            return True
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return False
    
    def hash_password_pbkdf2(self, password: str, salt: str = None) -> tuple:
        """使用PBKDF2哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000  # 100K 迭代
        ).hex()
        
        return password_hash, salt
    
    def fix_doctors_passwords(self):
        """修复医生表的密码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找需要修复的密码
            cursor.execute("""
                SELECT id, name, password_hash 
                FROM doctors 
                WHERE LENGTH(password_hash) < 20 OR password_hash NOT LIKE '%:%'
            """)
            
            weak_passwords = cursor.fetchall()
            
            for doctor_id, name, current_password in weak_passwords:
                logger.info(f"修复医生密码: {name} (ID: {doctor_id})")
                
                # 如果是明文密码，直接哈希
                if len(current_password) < 20:
                    logger.warning(f"发现明文密码: {name}")
                    password_hash, salt = self.hash_password_pbkdf2(current_password)
                    new_password_hash = f"{salt}:{password_hash}"
                    
                # 如果是SHA256格式，生成临时密码并通知
                else:
                    logger.warning(f"发现SHA256密码: {name}, 生成临时密码")
                    temp_password = f"temp_{secrets.token_hex(4)}"
                    password_hash, salt = self.hash_password_pbkdf2(temp_password)
                    new_password_hash = f"{salt}:{password_hash}"
                    logger.info(f"临时密码 {name}: {temp_password}")
                
                # 更新密码
                cursor.execute("""
                    UPDATE doctors 
                    SET password_hash = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (new_password_hash, doctor_id))
                
                self.fixes_applied += 1
                logger.info(f"密码已更新: {name}")
            
            conn.commit()
            logger.info(f"医生密码修复完成，共修复 {len(weak_passwords)} 个")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"修复医生密码失败: {e}")
            raise
        finally:
            conn.close()
    
    def fix_users_passwords(self):
        """修复用户表的SHA256密码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找SHA256密码
            cursor.execute("""
                SELECT user_id, username, password_hash 
                FROM users 
                WHERE LENGTH(password_hash) = 64 AND password_hash NOT LIKE '%:%'
                AND password_hash IS NOT NULL
            """)
            
            sha256_passwords = cursor.fetchall()
            
            for user_id, username, sha256_hash in sha256_passwords:
                logger.info(f"修复用户密码: {username} (ID: {user_id})")
                
                # 生成临时密码（因为SHA256不可逆）
                temp_password = f"temp_{secrets.token_hex(4)}"
                password_hash, salt = self.hash_password_pbkdf2(temp_password)
                new_password_hash = f"{salt}:{password_hash}"
                
                # 更新密码
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = ?, updated_at = datetime('now')
                    WHERE user_id = ?
                """, (new_password_hash, user_id))
                
                self.fixes_applied += 1
                logger.info(f"用户临时密码 {username}: {temp_password}")
            
            conn.commit()
            logger.info(f"用户密码修复完成，共修复 {len(sha256_passwords)} 个")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"修复用户密码失败: {e}")
            raise
        finally:
            conn.close()
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找过期会话
            cursor.execute("""
                SELECT COUNT(*) FROM unified_sessions 
                WHERE expires_at < datetime('now') AND session_status = 'active'
            """)
            expired_count = cursor.fetchone()[0]
            
            if expired_count > 0:
                # 更新过期会话状态
                cursor.execute("""
                    UPDATE unified_sessions 
                    SET session_status = 'expired'
                    WHERE expires_at < datetime('now') AND session_status = 'active'
                """)
                
                conn.commit()
                logger.info(f"清理了 {expired_count} 个过期会话")
            else:
                logger.info("没有找到过期会话")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"清理过期会话失败: {e}")
            raise
        finally:
            conn.close()
    
    def verify_fixes(self):
        """验证修复效果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查医生表
            cursor.execute("""
                SELECT COUNT(*) FROM doctors 
                WHERE LENGTH(password_hash) < 20 OR password_hash NOT LIKE '%:%'
            """)
            remaining_doctor_issues = cursor.fetchone()[0]
            
            # 检查用户表
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE LENGTH(password_hash) = 64 AND password_hash NOT LIKE '%:%'
                AND password_hash IS NOT NULL
            """)
            remaining_user_issues = cursor.fetchone()[0]
            
            # 检查过期会话
            cursor.execute("""
                SELECT COUNT(*) FROM unified_sessions 
                WHERE expires_at < datetime('now') AND session_status = 'active'
            """)
            remaining_expired_sessions = cursor.fetchone()[0]
            
            logger.info("=== 修复验证结果 ===")
            logger.info(f"剩余医生密码问题: {remaining_doctor_issues}")
            logger.info(f"剩余用户密码问题: {remaining_user_issues}")
            logger.info(f"剩余过期会话: {remaining_expired_sessions}")
            logger.info(f"总共修复项目: {self.fixes_applied}")
            
            if remaining_doctor_issues == 0 and remaining_user_issues == 0:
                logger.info("✅ 密码安全修复成功！")
                return True
            else:
                logger.error("❌ 仍有密码安全问题未解决")
                return False
                
        except Exception as e:
            logger.error(f"验证修复效果失败: {e}")
            return False
        finally:
            conn.close()
    
    def run_emergency_fix(self):
        """执行紧急修复"""
        logger.info("🚨 开始紧急密码安全修复")
        logger.info("=" * 50)
        
        # 1. 创建备份
        if not self.create_backup():
            logger.error("❌ 备份失败，停止修复")
            return False
        
        try:
            # 2. 修复医生密码
            logger.info("修复医生密码...")
            self.fix_doctors_passwords()
            
            # 3. 修复用户密码
            logger.info("修复用户密码...")
            self.fix_users_passwords()
            
            # 4. 清理过期会话
            logger.info("清理过期会话...")
            self.cleanup_expired_sessions()
            
            # 5. 验证修复
            logger.info("验证修复效果...")
            success = self.verify_fixes()
            
            if success:
                logger.info("🎉 紧急密码安全修复完成！")
                logger.info(f"备份文件: {self.backup_file}")
                return True
            else:
                logger.error("❌ 修复未完全成功")
                return False
                
        except Exception as e:
            logger.error(f"紧急修复过程出错: {e}")
            logger.info(f"可以从备份恢复: {self.backup_file}")
            return False

def main():
    """主函数"""
    fixer = PasswordSecurityFixer()
    success = fixer.run_emergency_fix()
    
    if success:
        print("\n✅ 紧急密码安全修复成功完成！")
        print("🔐 所有密码已标准化为PBKDF2格式")
        print("🧹 过期会话已清理")
        print("\n⚠️  重要提醒：")
        print("1. 受影响用户需要使用新的临时密码登录")
        print("2. 建议用户登录后立即修改密码")
        print("3. 系统已更安全，密码破解难度大幅提升")
    else:
        print("\n❌ 修复过程中出现问题")
        print("请检查日志文件获取详细信息")
    
    return success

if __name__ == "__main__":
    main()