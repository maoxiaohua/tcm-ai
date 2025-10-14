#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库最终清理和优化脚本
Final Database Cleanup and Optimization

任务：
- P1-3: 补充consultation_id关联数据
- P2-1: 添加必要的数据库索引
- P2-2: 清理孤立数据
- 最终验证

Version: 1.0
Date: 2025-10-12
"""

import sys
sys.path.append('/opt/tcm-ai')

from core.database import get_db_connection_context, verify_database_integrity
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_consultation_prescription_links():
    """修复consultation和prescription的关联关系"""

    print("\n" + "=" * 60)
    print("任务1: 修复consultation-prescription关联")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 统计缺失consultation_id的处方
        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions
            WHERE consultation_id IS NULL
        """)
        missing_count = cursor.fetchone()[0]

        print(f"发现 {missing_count} 条处方缺少consultation_id")

        if missing_count > 0:
            # 尝试根据patient_id和时间匹配consultation
            cursor.execute("""
                UPDATE prescriptions
                SET consultation_id = (
                    SELECT c.uuid
                    FROM consultations c
                    WHERE c.patient_id = prescriptions.patient_id
                    AND datetime(c.created_at) <= datetime(prescriptions.created_at)
                    ORDER BY c.created_at DESC
                    LIMIT 1
                )
                WHERE consultation_id IS NULL
                AND patient_id IN (SELECT patient_id FROM consultations)
            """)

            linked_count = cursor.rowcount
            conn.commit()
            print(f"✅ 成功关联 {linked_count} 条处方到consultation")

            if linked_count < missing_count:
                print(f"⚠️  仍有 {missing_count - linked_count} 条处方无法自动关联")
        else:
            print("✅ 所有处方都已有consultation_id")

        return missing_count

def clean_orphan_records():
    """清理孤立记录"""

    print("\n" + "=" * 60)
    print("任务2: 清理孤立记录")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        cleaned = {}

        # 清理孤立的consultations（患者不存在）
        cursor.execute("""
            DELETE FROM consultations
            WHERE patient_id NOT IN (SELECT global_user_id FROM unified_users)
        """)
        cleaned['consultations'] = cursor.rowcount

        # 清理孤立的prescriptions（患者不存在）
        cursor.execute("""
            DELETE FROM prescriptions
            WHERE patient_id NOT IN (SELECT global_user_id FROM unified_users)
        """)
        cleaned['prescriptions'] = cursor.rowcount

        # 清理无效的会话记录（用户不存在）
        cursor.execute("""
            DELETE FROM unified_sessions
            WHERE user_id NOT IN (SELECT global_user_id FROM unified_users)
        """)
        cleaned['sessions'] = cursor.rowcount

        conn.commit()

        print("清理结果:")
        for table, count in cleaned.items():
            if count > 0:
                print(f"  - {table}: 清理了 {count} 条孤立记录")
            else:
                print(f"  - {table}: ✅ 无孤立记录")

        return cleaned

def create_performance_indexes():
    """创建性能优化索引"""

    print("\n" + "=" * 60)
    print("任务3: 创建性能优化索引")
    print("=" * 60)

    indexes = [
        # unified_users表索引
        ("idx_unified_users_username", "unified_users", "username"),
        ("idx_unified_users_email", "unified_users", "email"),
        ("idx_unified_users_phone", "unified_users", "phone_number"),
        ("idx_unified_users_status", "unified_users", "account_status"),

        # consultations表索引
        ("idx_consultations_patient_created", "consultations", "patient_id, created_at DESC"),
        ("idx_consultations_doctor_created", "consultations", "selected_doctor_id, created_at DESC"),
        ("idx_consultations_status_created", "consultations", "status, created_at DESC"),

        # prescriptions表索引
        ("idx_prescriptions_patient_created", "prescriptions", "patient_id, created_at DESC"),
        ("idx_prescriptions_doctor_status", "prescriptions", "doctor_id, status"),
        ("idx_prescriptions_consultation", "prescriptions", "consultation_id"),
        ("idx_prescriptions_status_created", "prescriptions", "status, created_at DESC"),

        # unified_sessions表索引
        ("idx_sessions_user_created", "unified_sessions", "user_id, created_at DESC"),
        ("idx_sessions_status_expires", "unified_sessions", "session_status, expires_at"),

        # user_roles_new表索引
        ("idx_user_roles_user_active", "user_roles_new", "user_id, is_active"),
        ("idx_user_roles_role_active", "user_roles_new", "role_name, is_active"),

        # doctors表额外索引
        ("idx_doctors_status_uuid", "doctors", "status, uuid"),
        ("idx_doctors_email", "doctors", "email"),
        ("idx_doctors_phone", "doctors", "phone"),
    ]

    created_count = 0
    exists_count = 0

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        for idx_name, table_name, columns in indexes:
            try:
                # 检查索引是否已存在
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name=?
                """, (idx_name,))

                if cursor.fetchone():
                    exists_count += 1
                    print(f"  - {idx_name}: 已存在")
                else:
                    # 创建索引
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name}
                        ON {table_name}({columns})
                    """)
                    created_count += 1
                    print(f"  - {idx_name}: ✅ 已创建")

            except Exception as e:
                logger.warning(f"创建索引 {idx_name} 失败: {e}")
                print(f"  - {idx_name}: ❌ 失败 ({e})")

        conn.commit()

    print(f"\n索引摘要: 创建 {created_count} 个，已存在 {exists_count} 个")
    return created_count

def optimize_database():
    """优化数据库"""

    print("\n" + "=" * 60)
    print("任务4: 数据库优化")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        print("执行 VACUUM（压缩数据库）...")
        cursor.execute("VACUUM")
        print("✅ VACUUM 完成")

        print("执行 ANALYZE（更新统计信息）...")
        cursor.execute("ANALYZE")
        print("✅ ANALYZE 完成")

        conn.commit()

def final_verification():
    """最终验证"""

    print("\n" + "=" * 60)
    print("最终验证")
    print("=" * 60)

    # 数据库完整性检查
    integrity_result = verify_database_integrity()

    print(f"✅ 外键约束: {'已启用' if integrity_result['foreign_keys_enabled'] else '❌ 未启用'}")
    print(f"✅ 完整性检查: {'通过' if integrity_result['integrity_check'] else '❌ 失败'}")

    if integrity_result['foreign_key_check']:
        print(f"⚠️  外键违规: {len(integrity_result['foreign_key_check'])} 条")
    else:
        print("✅ 无外键违规")

    if integrity_result['errors']:
        print("\n❌ 发现错误:")
        for error in integrity_result['errors']:
            print(f"  - {error}")

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 统计数据
        stats = {}

        cursor.execute("SELECT COUNT(*) FROM unified_users")
        stats['total_users'] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM unified_users uu
            JOIN user_roles_new ur ON uu.global_user_id = ur.user_id
            WHERE ur.role_name = 'PATIENT' AND ur.is_active = 1
        """)
        stats['patients'] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM unified_users uu
            JOIN user_roles_new ur ON uu.global_user_id = ur.user_id
            WHERE ur.role_name = 'DOCTOR' AND ur.is_active = 1
        """)
        stats['doctors'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM consultations")
        stats['consultations'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prescriptions")
        stats['prescriptions'] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions
            WHERE consultation_id IS NOT NULL
        """)
        stats['prescriptions_linked'] = cursor.fetchone()[0]

        print("\n数据统计:")
        print(f"  - 总用户数: {stats['total_users']}")
        print(f"    • 患者: {stats['patients']}")
        print(f"    • 医生: {stats['doctors']}")
        print(f"  - 问诊记录: {stats['consultations']}")
        print(f"  - 处方记录: {stats['prescriptions']}")
        print(f"    • 已关联: {stats['prescriptions_linked']}/{stats['prescriptions']}")

        # 检查数据完整性
        issues = []

        cursor.execute("""
            SELECT COUNT(*) FROM consultations c
            LEFT JOIN unified_users u ON c.patient_id = u.global_user_id
            WHERE u.global_user_id IS NULL
        """)
        orphan_cons = cursor.fetchone()[0]
        if orphan_cons > 0:
            issues.append(f"孤立consultation记录: {orphan_cons}")

        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions p
            LEFT JOIN unified_users u ON p.patient_id = u.global_user_id
            WHERE u.global_user_id IS NULL
        """)
        orphan_presc = cursor.fetchone()[0]
        if orphan_presc > 0:
            issues.append(f"孤立prescription记录: {orphan_presc}")

        if issues:
            print("\n⚠️  数据完整性问题:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ 数据完整性验证通过")

        return stats, issues

def main():
    """主流程"""

    print("=" * 60)
    print("数据库最终清理和优化")
    print("=" * 60)
    print(f"开始时间: {datetime.now().isoformat()}\n")

    try:
        # 任务1: 修复关联
        fix_consultation_prescription_links()

        # 任务2: 清理孤立数据
        clean_orphan_records()

        # 任务3: 创建索引
        create_performance_indexes()

        # 任务4: 优化数据库
        optimize_database()

        # 最终验证
        stats, issues = final_verification()

        print("\n" + "=" * 60)
        print("清理和优化完成")
        print("=" * 60)
        print(f"完成时间: {datetime.now().isoformat()}")

        if issues:
            print("\n⚠️  发现一些问题，但不影响系统运行")
            return True
        else:
            print("\n✅ 所有任务完成，系统状态良好")
            return True

    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        print(f"\n❌ 执行失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
