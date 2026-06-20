#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账户信息修改脚本
Account Update Script

修改内容：
1. admin账户设置密码为admin123  
2. zhangzhongjing改为jingdaifu，密码改为jingdaifu123

Author: TCM-AI Security Team
Date: 2025-09-22
"""

import sqlite3
import hashlib
import secrets
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_password_pbkdf2(password: str, salt: str = None) -> tuple:
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

def update_accounts():
    """更新账户信息"""
    db_path = "/opt/tcm-ai/data/user_history.sqlite"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 更新admin账户密码为admin123
        logger.info("更新admin账户密码...")
        password_hash, salt = hash_password_pbkdf2("admin123")
        new_password_hash = f"{salt}:{password_hash}"
        
        cursor.execute("""
            UPDATE unified_users 
            SET password_hash = ?, salt = ?, password_changed_at = ?
            WHERE username = 'admin'
        """, (password_hash, salt, "2025-09-22T17:45:00"))
        
        logger.info("admin账户密码已更新为: admin123")
        
        # 2. 更新zhangzhongjing账户
        logger.info("查找zhangzhongjing账户...")
        
        # 在unified_users表中查找
        cursor.execute("SELECT global_user_id FROM unified_users WHERE username = 'zhangzhongjing'")
        unified_user = cursor.fetchone()
        
        if unified_user:
            user_id = unified_user[0]
            logger.info(f"找到统一用户: {user_id}")
            
            # 更新用户名和密码
            password_hash, salt = hash_password_pbkdf2("jingdaifu123")
            
            cursor.execute("""
                UPDATE unified_users 
                SET username = 'jingdaifu', password_hash = ?, salt = ?, 
                    display_name = '金大夫', password_changed_at = ?
                WHERE global_user_id = ?
            """, (password_hash, salt, "2025-09-22T17:45:00", user_id))
            
            logger.info("zhangzhongjing账户已更新为jingdaifu")
        
        # 3. 在旧users表中也查找并更新
        cursor.execute("SELECT user_id FROM users WHERE username = 'zhangzhongjing'")
        old_user = cursor.fetchone()
        
        if old_user:
            user_id = old_user[0]
            logger.info(f"找到旧用户: {user_id}")
            
            password_hash, salt = hash_password_pbkdf2("jingdaifu123")
            new_password_hash = f"{salt}:{password_hash}"
            
            cursor.execute("""
                UPDATE users 
                SET username = 'jingdaifu', password_hash = ?, 
                    nickname = '金大夫', updated_at = datetime('now')
                WHERE user_id = ?
            """, (new_password_hash, user_id))
            
            logger.info("旧users表中的zhangzhongjing也已更新")
        
        # 4. 更新doctors表中的相关信息
        cursor.execute("""
            UPDATE doctors 
            SET name = '金大夫', updated_at = datetime('now')
            WHERE name LIKE '%张仲景%' OR name LIKE '%zhangzhongjing%'
        """)
        
        conn.commit()
        logger.info("✅ 所有账户更新完成")
        
        # 验证更新
        cursor.execute("SELECT username, display_name FROM unified_users WHERE username = 'jingdaifu'")
        result = cursor.fetchone()
        if result:
            logger.info(f"验证: 新用户名={result[0]}, 显示名={result[1]}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"更新账户失败: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = update_accounts()
    if success:
        print("✅ 账户更新成功!")
        print("🔐 admin账户密码: admin123")
        print("🔐 jingdaifu账户密码: jingdaifu123")
    else:
        print("❌ 账户更新失败")