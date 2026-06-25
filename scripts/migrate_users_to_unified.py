#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据迁移脚本
将现有用户数据迁移到统一账户管理系统

Usage:
    python scripts/migrate_users_to_unified.py

Author: TCM-AI开发团队
Date: 2025-09-20
"""

import sys
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目路径
sys.path.append('/home/ute/tcm-ai')

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/home/ute/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

def generate_user_id() -> str:
    """生成全局唯一用户ID"""
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = secrets.token_hex(6)
    return f"usr_{date_str}_{random_str}"

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
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

def migrate_hardcoded_users():
    """迁移硬编码用户"""
    print("🔄 开始迁移硬编码用户...")
    
    hardcoded_users = [
        {
            "username": "admin",
            "password": "admin123",
            "display_name": "系统管理员",
            "role": "ADMIN",
            "email": "admin@tcm-ai.com"
        },
        {
            "username": "superadmin", 
            "password": "super123",
            "display_name": "超级管理员",
            "role": "SUPERADMIN",
            "email": "superadmin@tcm-ai.com"
        },
        {
            "username": "doctor",
            "password": "doctor123",
            "display_name": "测试医生",
            "role": "DOCTOR",
            "email": "doctor@tcm-ai.com"
        },
        {
            "username": "patient",
            "password": "patient123", 
            "display_name": "测试患者",
            "role": "PATIENT",
            "email": "patient@tcm-ai.com"
        },
        {
            "username": "test_patient",
            "password": "test123",
            "display_name": "测试患者002", 
            "role": "PATIENT",
            "email": "test_patient@tcm-ai.com"
        }
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        success_count = 0
        for user_data in hardcoded_users:
            try:
                # 检查用户是否已存在
                cursor.execute(
                    "SELECT global_user_id FROM unified_users WHERE username = ?",
                    (user_data["username"],)
                )
                if cursor.fetchone():
                    print(f"⚠️  用户已存在，跳过: {user_data['username']}")
                    continue
                
                # 生成用户ID和密码哈希
                user_id = generate_user_id()
                password_hash, salt = hash_password(user_data["password"])
                
                # 插入用户记录
                cursor.execute("""
                    INSERT INTO unified_users 
                    (global_user_id, username, email, display_name, password_hash, salt,
                     account_status, security_level, auth_methods, created_at, password_changed_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'active', 'basic', '["password"]', ?, ?)
                """, (
                    user_id, user_data["username"], user_data["email"], 
                    user_data["display_name"], password_hash, salt,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                
                # 分配角色
                cursor.execute("""
                    INSERT INTO user_roles_new 
                    (user_id, role_name, is_primary, assigned_at, assigned_reason)
                    VALUES (?, ?, 1, ?, ?)
                """, (
                    user_id, user_data["role"], 
                    datetime.now().isoformat(),
                    "系统初始化硬编码用户迁移"
                ))
                
                # 创建扩展配置
                cursor.execute("""
                    INSERT INTO user_extended_profiles (user_id) VALUES (?)
                """, (user_id,))
                
                print(f"✅ 迁移用户成功: {user_data['username']} → {user_id}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ 迁移用户失败: {user_data['username']} - {e}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"🎉 硬编码用户迁移完成: {success_count} 个用户成功迁移")

def migrate_existing_database_users():
    """迁移现有数据库用户"""
    print("🔄 开始迁移现有数据库用户...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 查询现有用户
        cursor.execute("""
            SELECT user_id, username, email, phone_number, nickname, 
                   password_hash, role, is_active, created_at, last_active
            FROM users 
            WHERE user_id IS NOT NULL AND username IS NOT NULL
            ORDER BY created_at
        """)
        
        existing_users = cursor.fetchall()
        print(f"📊 发现 {len(existing_users)} 个现有用户需要迁移")
        
        success_count = 0
        for user in existing_users:
            try:
                # 生成新的用户ID
                new_user_id = generate_user_id()
                
                # 检查用户名是否已在新系统中存在
                cursor.execute(
                    "SELECT global_user_id FROM unified_users WHERE username = ?",
                    (user['username'],)
                )
                if cursor.fetchone():
                    print(f"⚠️  用户名已存在，跳过: {user['username']}")
                    continue
                
                # 处理密码哈希
                if user['password_hash']:
                    # 如果有现有密码哈希，创建新的盐和哈希
                    temp_password = f"temp_{secrets.token_hex(8)}"  # 临时密码
                    password_hash, salt = hash_password(temp_password)
                else:
                    # 为没有密码的用户生成临时密码
                    temp_password = f"temp_{secrets.token_hex(8)}"
                    password_hash, salt = hash_password(temp_password)
                
                # 确定显示名称
                display_name = (
                    user['nickname'] or 
                    user['username'] or 
                    f"用户{user['user_id'][-6:]}"
                )
                
                # 确定角色
                role = user['role'].upper() if user['role'] else 'PATIENT'
                if role not in ['PATIENT', 'DOCTOR', 'ADMIN', 'SUPERADMIN']:
                    role = 'PATIENT'
                
                # 插入新用户记录
                cursor.execute("""
                    INSERT INTO unified_users 
                    (global_user_id, username, email, phone_number, display_name,
                     password_hash, salt, account_status, security_level, auth_methods,
                     created_at, last_login_at, user_preferences, registration_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_user_id, user['username'], user['email'], user['phone_number'],
                    display_name, password_hash, salt,
                    'active' if user['is_active'] else 'suspended',
                    'basic', '["password"]',
                    user['created_at'] or datetime.now().isoformat(),
                    user['last_active'],
                    '{}',  # 空的用户偏好
                    'migration'  # 标记为迁移来源
                ))
                
                # 分配角色
                cursor.execute("""
                    INSERT INTO user_roles_new 
                    (user_id, role_name, is_primary, assigned_at, assigned_reason)
                    VALUES (?, ?, 1, ?, ?)
                """, (
                    new_user_id, role,
                    datetime.now().isoformat(),
                    f"从旧系统迁移，原用户ID: {user['user_id']}"
                ))
                
                # 创建扩展配置
                cursor.execute("""
                    INSERT INTO user_extended_profiles (user_id) VALUES (?)
                """, (new_user_id,))
                
                print(f"✅ 迁移用户成功: {user['username']} ({user['user_id']} → {new_user_id})")
                success_count += 1
                
            except Exception as e:
                print(f"❌ 迁移用户失败: {user['username']} - {e}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"🎉 数据库用户迁移完成: {success_count} 个用户成功迁移")

def create_user_mapping_table():
    """创建用户ID映射表（用于数据关联）"""
    print("🔄 创建用户ID映射表...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 创建映射表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_id_mapping (
                old_user_id VARCHAR(100),
                new_user_id VARCHAR(50),
                username VARCHAR(100),
                migration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                PRIMARY KEY (old_user_id, new_user_id)
            )
        """)
        
        # 填充映射数据 
        cursor.execute("""
            INSERT OR IGNORE INTO user_id_mapping (old_user_id, new_user_id, username, notes)
            SELECT 
                u.user_id as old_user_id,
                uu.global_user_id as new_user_id,
                uu.username,
                '数据库用户迁移映射'
            FROM users u
            JOIN unified_users uu ON u.username = uu.username
            WHERE u.username IS NOT NULL
        """)
        
        # 硬编码用户映射
        hardcoded_mappings = [
            ("patient_001", "patient"),
            ("patient_test_001", "test_patient"),
            ("admin_admin", "admin"),
            ("admin_superadmin", "superadmin"),
            ("doctor_doctor", "doctor")
        ]
        
        for old_id, username in hardcoded_mappings:
            cursor.execute("""
                INSERT OR IGNORE INTO user_id_mapping (old_user_id, new_user_id, username, notes)
                SELECT ?, global_user_id, username, '硬编码用户映射'
                FROM unified_users WHERE username = ?
            """, (old_id, username))
        
        conn.commit()
        
        # 显示映射统计
        cursor.execute("SELECT COUNT(*) FROM user_id_mapping")
        mapping_count = cursor.fetchone()[0]
        print(f"✅ 用户ID映射表创建完成: {mapping_count} 条映射记录")

def verify_migration():
    """验证迁移结果"""
    print("🔍 验证迁移结果...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 统计新系统用户数量
        cursor.execute("SELECT COUNT(*) FROM unified_users")
        unified_users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_roles_new")
        roles_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM permissions")
        permissions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM role_permissions")
        role_permissions_count = cursor.fetchone()[0]
        
        # 显示统计信息
        print(f"📊 迁移验证统计:")
        print(f"   - 统一用户: {unified_users_count}")
        print(f"   - 用户角色: {roles_count}")
        print(f"   - 权限定义: {permissions_count}")
        print(f"   - 角色权限: {role_permissions_count}")
        
        # 显示按角色统计
        cursor.execute("""
            SELECT role_name, COUNT(*) as count
            FROM user_roles_new 
            WHERE is_active = 1
            GROUP BY role_name
            ORDER BY count DESC
        """)
        
        print(f"📈 用户角色分布:")
        for row in cursor.fetchall():
            print(f"   - {row['role_name']}: {row['count']} 人")

def cleanup_old_sessions():
    """清理旧会话，强制用户重新登录"""
    print("🧹 清理旧会话...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 标记所有旧会话为非活跃
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE is_active = 1")
        affected_sessions = cursor.rowcount
        
        # 记录清理事件
        cursor.execute("""
            INSERT INTO security_audit_logs 
            (log_id, event_type, event_category, event_result, event_details, risk_level, event_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f'migration_{int(datetime.now().timestamp())}',
            'system_migration',
            'admin',
            'success',
            json.dumps({
                "action": "cleanup_old_sessions",
                "sessions_affected": affected_sessions,
                "reason": "unified_account_migration"
            }),
            'medium',
            datetime.now().isoformat()
        ))
        
        conn.commit()
        print(f"✅ 已清理 {affected_sessions} 个旧会话，用户需要重新登录")

def main():
    """主函数"""
    print("🚀 开始统一账户系统用户迁移")
    print("=" * 50)
    
    try:
        # Step 1: 迁移硬编码用户
        migrate_hardcoded_users()
        print()
        
        # Step 2: 迁移现有数据库用户
        migrate_existing_database_users()
        print()
        
        # Step 3: 创建用户ID映射表
        create_user_mapping_table()
        print()
        
        # Step 4: 验证迁移结果
        verify_migration()
        print()
        
        # Step 5: 清理旧会话
        cleanup_old_sessions()
        print()
        
        print("🎉 用户迁移完成！")
        print("📝 重要提醒:")
        print("   1. 所有用户需要重新登录")
        print("   2. 硬编码用户密码保持不变")
        print("   3. 原数据库用户需要重置密码")
        print("   4. 请及时测试新系统功能")
        
    except Exception as e:
        print(f"❌ 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())