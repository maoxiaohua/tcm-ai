#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复表 - user_roles合并
Cleanup Duplicate Tables - Merge user_roles

Version: 1.0
Date: 2025-10-12
"""

import sys
sys.path.append('/opt/tcm-ai')

from core.database import get_db_connection_context
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_duplicate_user_roles():
    """合并user_roles和user_roles_new表"""

    print("=" * 60)
    print("清理重复表: user_roles")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 检查两个表是否都存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('user_roles', 'user_roles_new')
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if 'user_roles' not in tables:
            print("✅ user_roles表不存在，无需清理")
            return True

        if 'user_roles_new' not in tables:
            print("⚠️  只有user_roles表存在，重命名为user_roles_new")
            cursor.execute("ALTER TABLE user_roles RENAME TO user_roles_new")
            conn.commit()
            return True

        print(f"发现两个表: {', '.join(tables)}")

        # 统计数据
        cursor.execute("SELECT COUNT(*) FROM user_roles")
        old_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_roles_new")
        new_count = cursor.fetchone()[0]

        print(f"\n数据统计:")
        print(f"  user_roles (旧表): {old_count} 条记录")
        print(f"  user_roles_new (新表): {new_count} 条记录")

        # 检查user_roles_new是否有活跃使用
        cursor.execute("""
            SELECT COUNT(*) FROM user_roles_new
            WHERE is_active = 1 AND assigned_at > datetime('now', '-30 days')
        """)
        recent_new = cursor.fetchone()[0]

        print(f"  user_roles_new 最近30天活跃: {recent_new} 条")

        if recent_new > 0 or new_count > old_count:
            print(f"\n✅ 使用user_roles_new作为主表")

            # 迁移user_roles中不存在于user_roles_new的数据
            print("\n步骤1: 迁移旧表独有数据...")

            cursor.execute("""
                INSERT OR IGNORE INTO user_roles_new
                    (user_id, role_name, is_active, assigned_at, assigned_by, expires_at)
                SELECT
                    user_id,
                    role as role_name,
                    1 as is_active,
                    assigned_at,
                    assigned_by,
                    NULL as expires_at
                FROM user_roles
                WHERE user_id NOT IN (SELECT user_id FROM user_roles_new)
            """)

            migrated = cursor.rowcount
            print(f"✅ 迁移了 {migrated} 条独有记录")

            # 备份旧表
            print("\n步骤2: 备份旧表...")
            cursor.execute("DROP TABLE IF EXISTS user_roles_backup")
            cursor.execute("CREATE TABLE user_roles_backup AS SELECT * FROM user_roles")
            print(f"✅ 已备份到 user_roles_backup")

            # 删除旧表
            print("\n步骤3: 删除旧表...")
            cursor.execute("DROP TABLE user_roles")
            print(f"✅ 已删除 user_roles")

        else:
            print(f"\n⚠️  user_roles_new数据较少，保留两个表")
            print("建议手动检查后再删除")
            return False

        conn.commit()

        # 验证结果
        print("\n" + "=" * 60)
        print("清理结果验证")
        print("=" * 60)

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%user_roles%'
        """)
        remaining = [row[0] for row in cursor.fetchall()]

        print(f"剩余表: {', '.join(remaining)}")

        cursor.execute("SELECT COUNT(*) FROM user_roles_new")
        final_count = cursor.fetchone()[0]
        print(f"user_roles_new 最终记录数: {final_count}")

        print("\n✅ 清理完成！")
        return True

def cleanup_other_duplicates():
    """检查并清理其他可能的重复表"""

    print("\n" + "=" * 60)
    print("检查其他重复表")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 查找可能的重复表（后缀_new, _old, _backup）
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            AND (name LIKE '%_new' OR name LIKE '%_old' OR name LIKE '%_backup')
            AND name NOT IN ('user_roles_new', 'user_roles_backup')
        """)

        duplicates = [row[0] for row in cursor.fetchall()]

        if duplicates:
            print(f"发现可能的重复表: {', '.join(duplicates)}")
            print("建议手动检查是否需要清理")
        else:
            print("✅ 未发现其他重复表")

        return duplicates

def main():
    """主清理流程"""

    print("=" * 60)
    print("数据库表清理工具")
    print("=" * 60)
    print(f"开始时间: {__import__('datetime').datetime.now().isoformat()}\n")

    try:
        # 清理user_roles
        success = cleanup_duplicate_user_roles()

        # 检查其他重复表
        other_dups = cleanup_other_duplicates()

        print("\n" + "=" * 60)
        print("清理完成")
        print("=" * 60)

        if success:
            print("✅ user_roles表清理成功")

        if other_dups:
            print(f"⚠️  发现 {len(other_dups)} 个其他重复表，建议手动检查")

        return True

    except Exception as e:
        logger.error(f"清理失败: {e}", exc_info=True)
        print(f"\n❌ 清理失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
