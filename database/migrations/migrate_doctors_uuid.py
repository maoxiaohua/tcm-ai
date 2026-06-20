#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移脚本: 为doctors表添加uuid字段
Migration Script: Add UUID field to doctors table

Version: 1.0
Date: 2025-10-12
"""

import sys
sys.path.append('/opt/tcm-ai')

from core.database import get_db_connection_context
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_doctors_uuid():
    """为doctors表添加uuid字段"""

    print("=" * 60)
    print("开始迁移: 为doctors表添加uuid字段")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        try:
            # 步骤1: 检查uuid列是否已存在
            cursor.execute("PRAGMA table_info(doctors)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'uuid' in columns:
                print("⚠️  uuid字段已存在，检查数据...")
                cursor.execute("SELECT COUNT(*) FROM doctors WHERE uuid IS NULL")
                null_count = cursor.fetchone()[0]

                if null_count == 0:
                    print("✅ 所有医生都已有uuid，迁移完成")
                    return True
                else:
                    print(f"发现 {null_count} 个医生缺少uuid，开始补充...")
            else:
                print("步骤1: 创建临时表...")

                # 步骤2: 创建新表结构（包含uuid字段）
                cursor.execute("""
                    CREATE TABLE doctors_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(50) UNIQUE,
                        name TEXT NOT NULL,
                        license_no TEXT UNIQUE NOT NULL,
                        phone TEXT UNIQUE,
                        email TEXT UNIQUE,
                        speciality TEXT,
                        hospital TEXT,
                        auth_token TEXT,
                        password_hash TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now')),
                        last_login TEXT,
                        specialties TEXT,
                        average_rating DECIMAL(3,2) DEFAULT 0.00,
                        total_reviews INTEGER DEFAULT 0,
                        consultation_count INTEGER DEFAULT 0,
                        commission_rate DECIMAL(5,2) DEFAULT 0.00,
                        available_hours TEXT,
                        introduction TEXT,
                        avatar_url VARCHAR(255)
                    )
                """)
                print("✅ 新表结构创建成功")

                # 步骤3: 复制数据并生成uuid
                print("步骤2: 复制数据并生成uuid...")
                cursor.execute("""
                    INSERT INTO doctors_new
                    SELECT
                        id,
                        'D' || printf('%08d', id) AS uuid,
                        name,
                        license_no,
                        phone,
                        email,
                        speciality,
                        hospital,
                        auth_token,
                        password_hash,
                        status,
                        created_at,
                        updated_at,
                        last_login,
                        specialties,
                        average_rating,
                        total_reviews,
                        consultation_count,
                        commission_rate,
                        available_hours,
                        introduction,
                        avatar_url
                    FROM doctors
                """)

                rows_copied = cursor.rowcount
                print(f"✅ 已复制 {rows_copied} 条医生记录")

                # 步骤4: 删除旧表
                print("步骤3: 删除旧表...")
                cursor.execute("DROP TABLE doctors")
                print("✅ 旧表已删除")

                # 步骤5: 重命名新表
                print("步骤4: 重命名新表...")
                cursor.execute("ALTER TABLE doctors_new RENAME TO doctors")
                print("✅ 新表重命名完成")

            # 步骤6: 创建索引
            print("步骤5: 创建索引...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_doctors_uuid ON doctors(uuid)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_doctors_status ON doctors(status)")
            print("✅ 索引创建完成")

            # 步骤7: 验证数据
            print("\n" + "=" * 60)
            print("数据验证")
            print("=" * 60)

            cursor.execute("SELECT COUNT(*) FROM doctors")
            total_doctors = cursor.fetchone()[0]
            print(f"总医生数: {total_doctors}")

            cursor.execute("SELECT COUNT(DISTINCT uuid) FROM doctors WHERE uuid IS NOT NULL")
            uuid_count = cursor.fetchone()[0]
            print(f"已分配UUID: {uuid_count}")

            if total_doctors == uuid_count:
                print("✅ 所有医生都已分配唯一UUID")
            else:
                print(f"❌ 警告: 有 {total_doctors - uuid_count} 个医生未分配UUID")

            # 步骤8: 显示医生UUID映射
            print("\n医生UUID映射表:")
            print("-" * 60)
            cursor.execute("""
                SELECT id, uuid, name, email
                FROM doctors
                ORDER BY id
                LIMIT 10
            """)

            for row in cursor.fetchall():
                print(f"ID: {row[0]:2d} | UUID: {row[1]:15s} | {row[2]:20s} | {row[3] or 'N/A'}")

            if total_doctors > 10:
                print(f"... 还有 {total_doctors - 10} 条记录")

            conn.commit()
            print("\n✅ 迁移成功完成！")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"迁移失败: {e}")
            print(f"\n❌ 迁移失败: {e}")
            return False

if __name__ == "__main__":
    success = migrate_doctors_uuid()
    sys.exit(0 if success else 1)
