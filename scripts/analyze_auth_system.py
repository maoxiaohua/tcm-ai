#!/usr/bin/env python3
"""
认证系统分析工具
分析当前双重认证逻辑的问题并提供统一方案
"""

import sqlite3
import os
from datetime import datetime
import hashlib

def analyze_user_tables():
    """分析用户表结构和数据"""
    conn = sqlite3.connect("/home/ute/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    print("🔐 TCM-AI 认证系统分析")
    print("=" * 60)
    
    # 分析admin_accounts表
    print("\n📋 admin_accounts 表分析:")
    cursor.execute("PRAGMA table_info(admin_accounts)")
    admin_columns = cursor.fetchall()
    print(f"字段数量: {len(admin_columns)}")
    for col in admin_columns:
        print(f"  - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
    
    cursor.execute("SELECT COUNT(*) FROM admin_accounts")
    admin_count = cursor.fetchone()[0]
    print(f"记录数量: {admin_count}")
    
    cursor.execute("SELECT role, COUNT(*) FROM admin_accounts GROUP BY role")
    admin_roles = cursor.fetchall()
    print("角色分布:")
    for role, count in admin_roles:
        print(f"  - {role}: {count} 个")
    
    # 分析users表
    print("\n👥 users 表分析:")
    cursor.execute("PRAGMA table_info(users)")
    user_columns = cursor.fetchall()
    print(f"字段数量: {len(user_columns)}")
    for col in user_columns:
        if col[1] in ['user_id', 'username', 'email', 'password_hash', 'nickname', 'registration_type']:
            print(f"  - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE password_hash IS NOT NULL")
    users_with_password = cursor.fetchone()[0]
    
    print(f"总记录数量: {users_total}")
    print(f"有密码用户: {users_with_password}")
    
    cursor.execute("SELECT registration_type, COUNT(*) FROM users GROUP BY registration_type")
    registration_types = cursor.fetchall()
    print("注册类型分布:")
    for reg_type, count in registration_types:
        print(f"  - {reg_type}: {count} 个")
    
    # 检查重复用户
    print("\n🔍 重复用户检查:")
    cursor.execute("""
        SELECT a.username, a.email, u.username, u.email
        FROM admin_accounts a
        LEFT JOIN users u ON (a.username = u.username OR a.email = u.email)
        WHERE u.username IS NOT NULL OR u.email IS NOT NULL
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"发现 {len(duplicates)} 个潜在重复:")
        for dup in duplicates:
            print(f"  Admin: {dup[0]} ({dup[1]}) <-> User: {dup[2]} ({dup[3]})")
    else:
        print("✅ 未发现重复用户")
    
    # 分析认证复杂性
    print("\n⚡ 认证复杂性分析:")
    total_auth_users = admin_count + users_with_password
    print(f"需要认证的用户总数: {total_auth_users}")
    print(f"认证表数量: 2 个")
    print(f"认证逻辑复杂度: 高 (需要查询两个表)")
    
    conn.close()
    
    return {
        'admin_accounts': {
            'count': admin_count,
            'roles': dict(admin_roles),
            'columns': len(admin_columns)
        },
        'users': {
            'total': users_total,
            'with_password': users_with_password,
            'registration_types': dict(registration_types),
            'columns': len(user_columns)
        },
        'duplicates': len(duplicates),
        'total_auth_users': total_auth_users
    }

def propose_unification_strategy(analysis):
    """提出统一策略"""
    print("\n🎯 统一认证策略建议")
    print("-" * 40)
    
    print("📊 现状问题:")
    print("  1. 双表认证增加复杂性")
    print("  2. 用户数据分散存储")
    print("  3. 角色管理不统一")
    print("  4. 认证逻辑冗余")
    
    print("\n💡 推荐方案: 表合并统一")
    print("策略: 将admin_accounts迁移到users表")
    
    print("\n✅ 实施步骤:")
    print("  1. 扩展users表字段 (添加role、is_active等)")
    print("  2. 迁移admin_accounts数据到users表")  
    print("  3. 更新认证逻辑为单表查询")
    print("  4. 删除admin_accounts表")
    print("  5. 测试验证统一认证")
    
    print("\n⚠️ 风险评估:")
    print("  - 风险级别: 中等")
    print("  - 影响范围: 认证系统、用户管理")
    print("  - 建议: 先备份，分步执行")
    
    return "table_merge_strategy"

def generate_migration_sql(analysis):
    """生成迁移SQL"""
    print("\n🛠️ 生成迁移SQL")
    print("-" * 30)
    
    sql_commands = []
    
    # 1. 扩展users表
    sql_commands.extend([
        "-- 第一步: 扩展users表结构",
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'patient';",
        "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;",
        "ALTER TABLE users ADD COLUMN updated_at TEXT;",
        ""
    ])
    
    # 2. 迁移数据
    sql_commands.extend([
        "-- 第二步: 迁移admin_accounts数据到users表",
        """INSERT INTO users (
            user_id, username, email, password_hash, nickname,
            registration_type, role, is_active, created_at, updated_at, is_verified
        )
        SELECT 
            user_id, username, email, password_hash, username as nickname,
            'authenticated' as registration_type, role, is_active, 
            created_at, updated_at, 1 as is_verified
        FROM admin_accounts
        WHERE user_id NOT IN (SELECT user_id FROM users);""",
        ""
    ])
    
    # 3. 更新角色
    sql_commands.extend([
        "-- 第三步: 更新现有users表用户角色",
        "UPDATE users SET role = 'patient' WHERE role IS NULL OR role = '';",
        ""
    ])
    
    # 4. 创建索引
    sql_commands.extend([
        "-- 第四步: 优化索引",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
        "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);",
        ""
    ])
    
    # 5. 验证和清理
    sql_commands.extend([
        "-- 第五步: 数据验证",
        "-- SELECT COUNT(*) as total_users FROM users;",
        "-- SELECT role, COUNT(*) FROM users GROUP BY role;",
        "",
        "-- 第六步: 备份admin_accounts表后删除 (谨慎执行)",
        "-- DROP TABLE admin_accounts;",
        ""
    ])
    
    return sql_commands

def main():
    """主函数"""
    if not os.path.exists("/home/ute/tcm-ai/data/user_history.sqlite"):
        print("❌ 数据库文件不存在")
        return
    
    # 分析现状
    analysis = analyze_user_tables()
    
    # 提出策略
    strategy = propose_unification_strategy(analysis)
    
    # 生成SQL
    sql_commands = generate_migration_sql(analysis)
    
    # 保存迁移脚本
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    migration_file = f"/home/ute/tcm-ai/database/migrations/009_unify_auth_system_{timestamp}.sql"
    
    os.makedirs(os.path.dirname(migration_file), exist_ok=True)
    
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write("-- TCM-AI 认证系统统一迁移\n")
        f.write(f"-- 生成时间: {datetime.now().isoformat()}\n")
        f.write("-- 执行前请备份数据库!\n\n")
        f.write("\n".join(sql_commands))
    
    print(f"\n📄 迁移脚本已生成: {migration_file}")
    print("\n✅ 认证系统分析完成!")

if __name__ == "__main__":
    main()