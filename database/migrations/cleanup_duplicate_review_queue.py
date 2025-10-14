#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理doctor_review_queue表中的重复记录

问题: 每个处方在队列中有多条重复记录，导致医生端显示重复
解决: 保留每个prescription_id的最早记录，删除其他重复记录
"""

import sys
sys.path.append('/opt/tcm-ai')

import sqlite3
from datetime import datetime

DB_PATH = "/opt/tcm-ai/data/user_history.sqlite"

def cleanup_duplicate_queue_entries():
    """清理重复的审核队列记录"""

    print("=" * 60)
    print("清理doctor_review_queue重复记录")
    print("=" * 60)
    print(f"开始时间: {datetime.now().isoformat()}\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. 统计重复记录
        cursor.execute("""
            SELECT prescription_id, doctor_id, COUNT(*) as count
            FROM doctor_review_queue
            WHERE status = 'pending'
            GROUP BY prescription_id, doctor_id
            HAVING count > 1
            ORDER BY count DESC
        """)

        duplicates = cursor.fetchall()

        if not duplicates:
            print("✅ 没有发现重复记录")
            return

        print(f"发现 {len(duplicates)} 组重复记录:\n")

        total_removed = 0

        for prescription_id, doctor_id, count in duplicates:
            print(f"处方 #{prescription_id} (医生ID: {doctor_id}): {count} 条记录")

            # 2. 查找该处方+医生组合的所有记录
            cursor.execute("""
                SELECT id, submitted_at, priority
                FROM doctor_review_queue
                WHERE prescription_id = ? AND doctor_id = ? AND status = 'pending'
                ORDER BY submitted_at ASC, id ASC
            """, (prescription_id, doctor_id))

            records = cursor.fetchall()

            if len(records) > 1:
                # 保留第一条（最早的），删除其他
                keep_id = records[0][0]
                keep_time = records[0][1]

                delete_ids = [r[0] for r in records[1:]]

                print(f"  保留: ID={keep_id}, 提交时间={keep_time}")
                print(f"  删除: {len(delete_ids)} 条重复记录 (IDs: {delete_ids})")

                # 执行删除
                cursor.execute(f"""
                    DELETE FROM doctor_review_queue
                    WHERE id IN ({','.join('?' * len(delete_ids))})
                """, delete_ids)

                total_removed += len(delete_ids)
                print(f"  ✅ 已删除\n")

        # 3. 提交更改
        conn.commit()

        # 4. 验证结果
        print("=" * 60)
        print("清理结果验证")
        print("=" * 60)

        cursor.execute("""
            SELECT prescription_id, doctor_id, COUNT(*) as count
            FROM doctor_review_queue
            WHERE status = 'pending'
            GROUP BY prescription_id, doctor_id
            HAVING count > 1
        """)

        remaining_duplicates = cursor.fetchall()

        if remaining_duplicates:
            print(f"⚠️ 仍有 {len(remaining_duplicates)} 组重复记录")
            for pid, did, cnt in remaining_duplicates:
                print(f"  处方 #{pid} (医生 {did}): {cnt} 条")
        else:
            print("✅ 所有重复记录已清理")

        # 5. 统计最终数量
        cursor.execute("SELECT COUNT(*) FROM doctor_review_queue WHERE status = 'pending'")
        final_count = cursor.fetchone()[0]

        print(f"\n总计删除: {total_removed} 条重复记录")
        print(f"剩余待审核记录: {final_count} 条")

        print(f"\n完成时间: {datetime.now().isoformat()}")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()

    return True

if __name__ == "__main__":
    success = cleanup_duplicate_queue_entries()
    sys.exit(0 if success else 1)
