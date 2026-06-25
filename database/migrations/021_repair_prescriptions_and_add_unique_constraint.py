#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线修复 prescriptions 历史脏数据，并可选添加唯一约束索引。

目标：
1. 去重：同一 consultation_id 仅保留一条 prescriptions 记录
2. 清理孤儿：删除无法关联 consultations 的 prescriptions
3. 迁移引用：将相关表 prescription_id 引用迁移到保留记录
4. 约束收口：添加 consultation_id 唯一索引（非空生效）
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.append('/home/ute/tcm-ai')

from core.database import get_db_connection_context  # noqa: E402


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def get_tables_with_prescription_id(cursor) -> List[str]:
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
          AND name != 'prescriptions'
    """)
    tables = []
    for (table_name,) in cursor.fetchall():
        cursor.execute(f"PRAGMA table_info({quote_ident(table_name)})")
        columns = {row[1] for row in cursor.fetchall()}
        if 'prescription_id' in columns:
            tables.append(table_name)
    return tables


def calc_keep_score(row: Dict) -> Tuple:
    status_priority = {
        'completed': 90,
        'dispensed': 85,
        'patient_confirmed': 80,
        'approved': 75,
        'reviewed': 70,
        'paid': 65,
        'pending_review': 40,
        'pending': 30,
        'rejected': 10,
    }
    status = (row.get('status') or '').strip().lower()
    payment_status = (row.get('payment_status') or '').strip().lower()
    has_doctor_prescription = 1 if (row.get('doctor_prescription') or '').strip() else 0
    payment_done = 1 if payment_status in {'paid', 'completed', 'success'} else 0
    reviewed_at = row.get('reviewed_at') or ''
    confirmed_at = row.get('confirmed_at') or ''
    created_at = row.get('created_at') or ''

    return (
        payment_done,
        has_doctor_prescription,
        status_priority.get(status, 20),
        reviewed_at,
        confirmed_at,
        created_at,
        row.get('id', 0),
    )


def normalize_empty_consultation_id(cursor) -> int:
    cursor.execute("""
        UPDATE prescriptions
        SET consultation_id = NULL
        WHERE consultation_id IS NOT NULL
          AND TRIM(consultation_id) = ''
    """)
    return cursor.rowcount


def backfill_missing_consultation_id(cursor) -> int:
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
          AND EXISTS (
              SELECT 1
              FROM consultations c2
              WHERE c2.patient_id = prescriptions.patient_id
                AND datetime(c2.created_at) <= datetime(prescriptions.created_at)
          )
    """)
    return cursor.rowcount


def remap_prescription_refs(cursor, table_names: List[str], old_id: int, new_id: int) -> int:
    if old_id == new_id:
        return 0
    total = 0
    for table_name in table_names:
        cursor.execute(
            f"UPDATE {quote_ident(table_name)} SET prescription_id = ? WHERE prescription_id = ?",
            (new_id, old_id),
        )
        total += cursor.rowcount
    return total


def delete_refs_for_prescriptions(cursor, table_names: List[str], prescription_ids: List[int]) -> int:
    if not prescription_ids:
        return 0

    placeholders = ','.join('?' for _ in prescription_ids)
    total = 0
    for table_name in table_names:
        cursor.execute(
            f"DELETE FROM {quote_ident(table_name)} WHERE prescription_id IN ({placeholders})",
            prescription_ids,
        )
        total += cursor.rowcount
    return total


def cleanup_orphan_prescriptions(cursor, table_names: List[str]) -> Dict[str, int]:
    cursor.execute("""
        SELECT id
        FROM prescriptions p
        WHERE p.consultation_id IS NOT NULL
          AND TRIM(p.consultation_id) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM consultations c
              WHERE c.uuid = p.consultation_id
          )
    """)
    orphan_ids = [row[0] for row in cursor.fetchall()]

    if not orphan_ids:
        return {'orphan_prescriptions': 0, 'orphan_refs_deleted': 0}

    orphan_refs_deleted = delete_refs_for_prescriptions(cursor, table_names, orphan_ids)
    placeholders = ','.join('?' for _ in orphan_ids)
    cursor.execute(
        f"DELETE FROM prescriptions WHERE id IN ({placeholders})",
        orphan_ids,
    )

    return {
        'orphan_prescriptions': cursor.rowcount,
        'orphan_refs_deleted': orphan_refs_deleted,
    }


def deduplicate_prescriptions(cursor, table_names: List[str]) -> Dict[str, int]:
    cursor.execute("""
        SELECT consultation_id
        FROM prescriptions
        WHERE consultation_id IS NOT NULL
          AND TRIM(consultation_id) <> ''
        GROUP BY consultation_id
        HAVING COUNT(*) > 1
    """)
    duplicate_consultations = [row[0] for row in cursor.fetchall()]

    if not duplicate_consultations:
        return {
            'duplicate_groups': 0,
            'duplicate_rows_deleted': 0,
            'reference_rows_remapped': 0,
        }

    duplicate_rows_deleted = 0
    reference_rows_remapped = 0

    for consultation_id in duplicate_consultations:
        cursor.execute("""
            SELECT id, status, payment_status, doctor_prescription,
                   reviewed_at, confirmed_at, created_at
            FROM prescriptions
            WHERE consultation_id = ?
        """, (consultation_id,))
        rows = [dict(row) for row in cursor.fetchall()]

        keep_row = max(rows, key=calc_keep_score)
        keep_id = keep_row['id']
        delete_ids = [row['id'] for row in rows if row['id'] != keep_id]

        for old_id in delete_ids:
            reference_rows_remapped += remap_prescription_refs(cursor, table_names, old_id, keep_id)

        placeholders = ','.join('?' for _ in delete_ids)
        cursor.execute(
            f"DELETE FROM prescriptions WHERE id IN ({placeholders})",
            delete_ids,
        )
        duplicate_rows_deleted += cursor.rowcount

    return {
        'duplicate_groups': len(duplicate_consultations),
        'duplicate_rows_deleted': duplicate_rows_deleted,
        'reference_rows_remapped': reference_rows_remapped,
    }


def create_unique_index(cursor) -> bool:
    cursor.execute("DROP INDEX IF EXISTS idx_prescriptions_consultation")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_prescriptions_consultation_id
        ON prescriptions(consultation_id)
        WHERE consultation_id IS NOT NULL
          AND TRIM(consultation_id) <> ''
    """)
    return True


def collect_stats(cursor) -> Dict[str, int]:
    stats: Dict[str, int] = {}

    cursor.execute("SELECT COUNT(*) FROM prescriptions")
    stats['total_prescriptions'] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT consultation_id
            FROM prescriptions
            WHERE consultation_id IS NOT NULL
              AND TRIM(consultation_id) <> ''
            GROUP BY consultation_id
            HAVING COUNT(*) > 1
        )
    """)
    stats['duplicate_groups'] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM prescriptions p
        WHERE p.consultation_id IS NOT NULL
          AND TRIM(p.consultation_id) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM consultations c
              WHERE c.uuid = p.consultation_id
          )
    """)
    stats['orphan_prescriptions'] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM prescriptions
        WHERE consultation_id IS NULL
           OR TRIM(consultation_id) = ''
    """)
    stats['null_or_empty_consultation'] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type='index'
          AND name='ux_prescriptions_consultation_id'
    """)
    stats['unique_index_exists'] = cursor.fetchone()[0]

    return stats


def run_repair(apply_changes: bool, add_unique_constraint: bool) -> int:
    print("=" * 72)
    print("离线修复: prescriptions 去重 / 孤儿清理 / 唯一约束收口")
    print("=" * 72)
    print(f"开始时间: {datetime.now().isoformat()}")
    print(f"执行模式: {'APPLY(会写入数据库)' if apply_changes else 'DRY-RUN(仅预演，不提交)'}")
    print(f"添加唯一约束: {'是' if add_unique_constraint else '否'}\n")

    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        conn.execute("BEGIN IMMEDIATE")

        table_names = get_tables_with_prescription_id(cursor)

        before_stats = collect_stats(cursor)
        print("修复前统计:", before_stats)
        print(f"联动表(prescription_id): {', '.join(table_names) if table_names else '(无)'}")

        normalized = normalize_empty_consultation_id(cursor)
        backfilled = backfill_missing_consultation_id(cursor)
        orphan_result = cleanup_orphan_prescriptions(cursor, table_names)
        dedup_result = deduplicate_prescriptions(cursor, table_names)

        if add_unique_constraint:
            create_unique_index(cursor)

        after_stats = collect_stats(cursor)

        print("\n执行摘要:")
        print(f"- 标准化空 consultation_id -> NULL: {normalized}")
        print(f"- 回填 consultation_id: {backfilled}")
        print(f"- 删除孤儿处方: {orphan_result['orphan_prescriptions']}")
        print(f"- 删除孤儿引用记录: {orphan_result['orphan_refs_deleted']}")
        print(f"- 重复 consultation 组: {dedup_result['duplicate_groups']}")
        print(f"- 删除重复处方行: {dedup_result['duplicate_rows_deleted']}")
        print(f"- 迁移引用行数: {dedup_result['reference_rows_remapped']}")

        print("\n修复后统计:", after_stats)

        if apply_changes:
            conn.commit()
            print("\n✅ 已提交到数据库")
        else:
            conn.rollback()
            print("\nℹ️ DRY-RUN 已回滚，数据库未改动")

    print(f"结束时间: {datetime.now().isoformat()}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="离线修复处方历史数据，并可选添加唯一约束"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='实际写入数据库。默认仅 dry-run 预演。',
    )
    parser.add_argument(
        '--add-unique-constraint',
        action='store_true',
        help='修复完成后创建唯一索引 ux_prescriptions_consultation_id',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_repair(
        apply_changes=args.apply,
        add_unique_constraint=args.add_unique_constraint,
    )


if __name__ == '__main__':
    raise SystemExit(main())
