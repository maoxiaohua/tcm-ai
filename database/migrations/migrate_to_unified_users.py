#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整用户数据迁移脚本
Complete User Data Migration Script

目标：
1. 将users表中的患者迁移到unified_users
2. 将doctors表中的医生迁移到unified_users
3. 更新所有关联表的外键引用
4. 保持数据完整性和一致性

Version: 1.0
Date: 2025-10-12
"""

import sys
sys.path.append('/opt/tcm-ai')

from core.database import get_db_connection_context
import hashlib
import secrets
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_patients_to_unified():
    """将patients从users表迁移到unified_users"""

    print("\n" + "=" * 60)
    print("步骤1: 迁移患者数据到unified_users")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 查询需要迁移的患者
        cursor.execute("""
            SELECT user_id, username, email, phone_number, nickname,
                   password_hash, created_at, last_active
            FROM users
            WHERE user_id NOT IN (SELECT global_user_id FROM unified_users)
        """)

        patients_to_migrate = cursor.fetchall()
        print(f"找到 {len(patients_to_migrate)} 个患者需要迁移")

        migrated_count = 0
        skipped_count = 0

        for patient in patients_to_migrate:
            user_id = patient[0]
            username = patient[1] or f"patient_{user_id[:8]}"
            email = patient[2]
            phone = patient[3]
            display_name = patient[4] or username
            password_hash = patient[5] or ""
            created_at = patient[6] or datetime.now().isoformat()

            try:
                # 生成salt和hash（如果原密码是明文或简单hash）
                if password_hash and ':' not in password_hash:
                    # 简单的迁移策略：保留原hash作为password_hash
                    salt = secrets.token_hex(16)
                    final_hash = password_hash
                elif password_hash and ':' in password_hash:
                    # 已经是salt:hash格式
                    salt, final_hash = password_hash.split(':', 1)
                else:
                    # 无密码，生成随机密码
                    salt = secrets.token_hex(16)
                    temp_password = secrets.token_hex(8)
                    final_hash = hashlib.pbkdf2_hmac(
                        'sha256',
                        temp_password.encode(),
                        salt.encode(),
                        100000
                    ).hex()

                #插入unified_users
                cursor.execute("""
                    INSERT OR IGNORE INTO unified_users
                    (global_user_id, username, email, phone_number, display_name,
                     password_hash, salt, account_status, security_level,
                     auth_methods, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 'basic',
                            '["password"]', ?, ?)
                """, (user_id, username, email, phone, display_name,
                      final_hash, salt, created_at, datetime.now().isoformat()))

                # 分配患者角色
                cursor.execute("""
                    INSERT OR IGNORE INTO user_roles_new
                    (user_id, role_name, is_active, assigned_at)
                    VALUES (?, 'PATIENT', 1, ?)
                """, (user_id, datetime.now().isoformat()))

                migrated_count += 1

            except Exception as e:
                logger.warning(f"迁移患者 {user_id} 失败: {e}")
                skipped_count += 1
                continue

        conn.commit()
        print(f"✅ 成功迁移 {migrated_count} 个患者")
        if skipped_count > 0:
            print(f"⚠️  跳过 {skipped_count} 个患者（可能已存在）")

        return migrated_count

def migrate_doctors_to_unified():
    """将doctors迁移到unified_users"""

    print("\n" + "=" * 60)
    print("步骤2: 迁移医生数据到unified_users")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 查询需要迁移的医生
        cursor.execute("""
            SELECT uuid, name, email, phone, password_hash, license_no,
                   specialties, hospital, created_at
            FROM doctors
            WHERE uuid NOT IN (SELECT global_user_id FROM unified_users)
        """)

        doctors_to_migrate = cursor.fetchall()
        print(f"找到 {len(doctors_to_migrate)} 个医生需要迁移")

        migrated_count = 0
        skipped_count = 0

        for doctor in doctors_to_migrate:
            doctor_uuid = doctor[0]
            name = doctor[1]
            email = doctor[2]
            phone = doctor[3]
            password_hash = doctor[4] or ""
            license_no = doctor[5]
            specialties = doctor[6]
            hospital = doctor[7]
            created_at = doctor[8] or datetime.now().isoformat()

            # 生成username（使用license_no或名字）
            username = f"dr_{license_no}" if license_no else f"dr_{name}"

            try:
                # 处理密码hash
                if password_hash:
                    salt = secrets.token_hex(16)
                    final_hash = password_hash
                else:
                    # 无密码，生成临时密码
                    salt = secrets.token_hex(16)
                    temp_password = secrets.token_hex(12)
                    final_hash = hashlib.pbkdf2_hmac(
                        'sha256',
                        temp_password.encode(),
                        salt.encode(),
                        100000
                    ).hex()

                # 插入unified_users
                cursor.execute("""
                    INSERT OR IGNORE INTO unified_users
                    (global_user_id, username, email, phone_number, display_name,
                     password_hash, salt, account_status, security_level,
                     auth_methods, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 'enhanced',
                            '["password"]', ?, ?)
                """, (doctor_uuid, username, email, phone, name,
                      final_hash, salt, created_at, datetime.now().isoformat()))

                # 分配医生角色
                cursor.execute("""
                    INSERT OR IGNORE INTO user_roles_new
                    (user_id, role_name, is_active, assigned_at)
                    VALUES (?, 'DOCTOR', 1, ?)
                """, (doctor_uuid, datetime.now().isoformat()))

                migrated_count += 1

            except Exception as e:
                logger.warning(f"迁移医生 {doctor_uuid} ({name}) 失败: {e}")
                skipped_count += 1
                continue

        conn.commit()
        print(f"✅ 成功迁移 {migrated_count} 个医生")
        if skipped_count > 0:
            print(f"⚠️  跳过 {skipped_count} 个医生（可能已存在）")

        return migrated_count

def update_consultations_foreign_keys():
    """更新consultations表的外键引用"""

    print("\n" + "=" * 60)
    print("步骤3: 更新consultations表外键引用")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 统计需要更新的记录
        cursor.execute("""
            SELECT COUNT(*) FROM consultations c
            INNER JOIN doctors d ON CAST(d.id AS TEXT) = c.selected_doctor_id
            WHERE c.selected_doctor_id NOT LIKE 'D%'
        """)
        update_needed = cursor.fetchone()[0]

        print(f"找到 {update_needed} 条记录需要更新医生ID格式")

        if update_needed > 0:
            # 更新医生ID引用（从整数ID转为UUID格式）
            cursor.execute("""
                UPDATE consultations
                SET selected_doctor_id = (
                    SELECT d.uuid
                    FROM doctors d
                    WHERE CAST(d.id AS TEXT) = consultations.selected_doctor_id
                )
                WHERE selected_doctor_id NOT LIKE 'D%'
                AND selected_doctor_id IN (SELECT CAST(id AS TEXT) FROM doctors)
            """)

            updated_count = cursor.rowcount
            conn.commit()
            print(f"✅ 成功更新 {updated_count} 条记录的医生ID")
        else:
            print("✅ 无需更新，所有医生ID已是正确格式")

        return update_needed

def update_prescriptions_foreign_keys():
    """更新prescriptions表的外键引用"""

    print("\n" + "=" * 60)
    print("步骤4: 更新prescriptions表外键引用")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 更新医生ID引用
        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions
            WHERE doctor_id IS NOT NULL
            AND CAST(doctor_id AS TEXT) NOT LIKE 'D%'
        """)
        update_needed = cursor.fetchone()[0]

        print(f"找到 {update_needed} 条处方需要更新医生ID格式")

        if update_needed > 0:
            cursor.execute("""
                UPDATE prescriptions
                SET doctor_id = (
                    SELECT d.uuid
                    FROM doctors d
                    WHERE d.id = CAST(prescriptions.doctor_id AS INTEGER)
                )
                WHERE doctor_id IS NOT NULL
                AND CAST(doctor_id AS TEXT) NOT LIKE 'D%'
            """)

            updated_count = cursor.rowcount
            conn.commit()
            print(f"✅ 成功更新 {updated_count} 条处方的医生ID")
        else:
            print("✅ 无需更新，所有医生ID已是正确格式")

        return update_needed

def verify_migration():
    """验证迁移结果"""

    print("\n" + "=" * 60)
    print("迁移结果验证")
    print("=" * 60)

    with get_db_connection_context() as conn:
        cursor = conn.cursor()

        # 统计unified_users数据
        cursor.execute("SELECT COUNT(*) FROM unified_users")
        total_unified = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM unified_users uu
            INNER JOIN user_roles_new ur ON uu.global_user_id = ur.user_id
            WHERE ur.role_name = 'PATIENT'
        """)
        patient_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM unified_users uu
            INNER JOIN user_roles_new ur ON uu.global_user_id = ur.user_id
            WHERE ur.role_name = 'DOCTOR'
        """)
        doctor_count = cursor.fetchone()[0]

        print(f"unified_users总数: {total_unified}")
        print(f"  - 患者: {patient_count}")
        print(f"  - 医生: {doctor_count}")
        print(f"  - 其他: {total_unified - patient_count - doctor_count}")

        # 检查数据一致性
        cursor.execute("SELECT COUNT(*) FROM users")
        old_users_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM doctors")
        old_doctors_count = cursor.fetchone()[0]

        print(f"\n原始数据:")
        print(f"  - users表: {old_users_count} 条记录")
        print(f"  - doctors表: {old_doctors_count} 条记录")

        if total_unified >= (old_users_count + old_doctors_count):
            print("\n✅ 数据迁移完整")
        else:
            missing = (old_users_count + old_doctors_count) - total_unified
            print(f"\n⚠️  可能有 {missing} 条记录未迁移")

        # 检查外键引用
        cursor.execute("""
            SELECT COUNT(*) FROM consultations c
            LEFT JOIN unified_users u ON c.patient_id = u.global_user_id
            WHERE u.global_user_id IS NULL
        """)
        orphan_consultations = cursor.fetchone()[0]

        if orphan_consultations > 0:
            print(f"\n⚠️  发现 {orphan_consultations} 条孤立的consultation记录")
        else:
            print("\n✅ 所有consultation记录都有有效的患者引用")

        return {
            "total_unified": total_unified,
            "patient_count": patient_count,
            "doctor_count": doctor_count,
            "orphan_consultations": orphan_consultations
        }

def main():
    """主迁移流程"""

    print("=" * 60)
    print("TCM-AI 统一用户系统数据迁移")
    print("=" * 60)
    print(f"开始时间: {datetime.now().isoformat()}")

    try:
        # 步骤1: 迁移患者
        patients_migrated = migrate_patients_to_unified()

        # 步骤2: 迁移医生
        doctors_migrated = migrate_doctors_to_unified()

        # 步骤3: 更新consultations外键
        consultations_updated = update_consultations_foreign_keys()

        # 步骤4: 更新prescriptions外键
        prescriptions_updated = update_prescriptions_foreign_keys()

        # 步骤5: 验证迁移结果
        results = verify_migration()

        print("\n" + "=" * 60)
        print("迁移完成摘要")
        print("=" * 60)
        print(f"✅ 迁移患者数: {patients_migrated}")
        print(f"✅ 迁移医生数: {doctors_migrated}")
        print(f"✅ 更新问诊记录: {consultations_updated}")
        print(f"✅ 更新处方记录: {prescriptions_updated}")
        print(f"✅ unified_users总数: {results['total_unified']}")
        print(f"\n完成时间: {datetime.now().isoformat()}")
        print("=" * 60)

        return True

    except Exception as e:
        logger.error(f"迁移过程出错: {e}", exc_info=True)
        print(f"\n❌ 迁移失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
