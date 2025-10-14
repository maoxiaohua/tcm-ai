#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建consultations表以修复外键引用
Rebuild consultations table to fix foreign key references

Version: 1.0
Date: 2025-10-12
"""

import sys
sys.path.append('/opt/tcm-ai')

import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "/opt/tcm-ai/data/user_history.sqlite"

def rebuild_consultations_table():
    """重建consultations表，修复外键引用"""

    print("=" * 60)
    print("重建consultations表")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 暂时禁用外键约束以进行表重建
    conn.execute("PRAGMA foreign_keys = OFF")

    cursor = conn.cursor()

    try:
        # 步骤1: 备份现有数据
        print("\n步骤1: 备份现有数据...")
        cursor.execute("SELECT * FROM consultations")
        consultations_data = cursor.fetchall()
        print(f"✅ 备份了 {len(consultations_data)} 条consultation记录")

        # 步骤2: 删除旧表
        print("\n步骤2: 删除旧表...")
        cursor.execute("DROP TABLE IF EXISTS consultations")
        print("✅ 旧表已删除")

        # 步骤3: 创建新表（正确的外键引用）
        print("\n步骤3: 创建新表结构...")
        cursor.execute("""
            CREATE TABLE consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid VARCHAR(50) UNIQUE NOT NULL,
                patient_id VARCHAR(50) NOT NULL,
                selected_doctor_id VARCHAR(50),
                doctor_selection_method VARCHAR(20) DEFAULT 'recommended',
                service_type VARCHAR(20) DEFAULT 'prescription_only',
                guide_doctor_id VARCHAR(50),
                symptoms_analysis TEXT,
                tcm_syndrome VARCHAR(200),
                conversation_log TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                patient_rating INTEGER,
                patient_review TEXT,
                review_created_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES unified_users(global_user_id) ON DELETE CASCADE,
                FOREIGN KEY (selected_doctor_id) REFERENCES unified_users(global_user_id) ON DELETE SET NULL,
                FOREIGN KEY (guide_doctor_id) REFERENCES unified_users(global_user_id) ON DELETE SET NULL
            )
        """)
        print("✅ 新表结构创建成功")

        # 步骤4: 恢复数据
        print("\n步骤4: 恢复数据...")
        restored_count = 0
        skipped_count = 0

        for row in consultations_data:
            try:
                # 验证patient_id是否在unified_users中
                cursor.execute("""
                    SELECT global_user_id FROM unified_users
                    WHERE global_user_id = ?
                """, (row['patient_id'],))

                if not cursor.fetchone():
                    print(f"  跳过: patient_id {row['patient_id']} 不存在于unified_users")
                    skipped_count += 1
                    continue

                # 插入数据
                cursor.execute("""
                    INSERT INTO consultations
                    (id, uuid, patient_id, selected_doctor_id, doctor_selection_method,
                     service_type, guide_doctor_id, symptoms_analysis, tcm_syndrome,
                     conversation_log, status, patient_rating, patient_review,
                     review_created_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['id'], row['uuid'], row['patient_id'],
                    row['selected_doctor_id'], row['doctor_selection_method'],
                    row['service_type'], row['guide_doctor_id'],
                    row['symptoms_analysis'], row['tcm_syndrome'],
                    row['conversation_log'], row['status'],
                    row['patient_rating'], row['patient_review'],
                    row['review_created_at'], row['created_at'], row['updated_at']
                ))
                restored_count += 1

            except Exception as e:
                logger.warning(f"恢复记录 {row['id']} 失败: {e}")
                skipped_count += 1

        print(f"✅ 成功恢复 {restored_count} 条记录")
        if skipped_count > 0:
            print(f"⚠️  跳过 {skipped_count} 条记录（数据不一致）")

        # 步骤5: 重建索引
        print("\n步骤5: 重建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultations_patient ON consultations(patient_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultations_doctor ON consultations(selected_doctor_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultations_uuid ON consultations(uuid)")
        print("✅ 索引创建完成")

        # 步骤6: 提交并重新启用外键
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        print("\n✅ 表重建完成，外键约束已重新启用")

        # 验证
        cursor.execute("SELECT COUNT(*) FROM consultations")
        final_count = cursor.fetchone()[0]
        print(f"\n最终记录数: {final_count}")

        conn.close()
        return True

    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"重建失败: {e}", exc_info=True)
        print(f"\n❌ 重建失败: {e}")
        return False

if __name__ == "__main__":
    success = rebuild_consultations_table()
    sys.exit(0 if success else 1)
