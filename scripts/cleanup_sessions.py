#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话清理脚本
定期清理过期的匿名会话和过期会话，避免数据库膨胀
"""

import sys
import sqlite3
from datetime import datetime, timedelta
import logging

# 添加项目路径
sys.path.insert(0, '/home/ute/tcm-ai')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = '/home/ute/tcm-ai/data/user_history.sqlite'

def cleanup_anonymous_sessions(days_to_keep=3):
    """清理超过指定天数的匿名会话"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 计算cutoff时间
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        # 删除旧的匿名会话
        cursor.execute("""
            DELETE FROM user_sessions
            WHERE user_id = 'anonymous'
            AND created_at < ?
        """, (cutoff_time.isoformat(),))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"✅ 清理了 {deleted_count} 个超过 {days_to_keep} 天的匿名会话")
        return deleted_count

    except Exception as e:
        logger.error(f"❌ 清理匿名会话失败: {e}")
        return 0

def cleanup_expired_sessions():
    """清理所有已过期的会话"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        now = datetime.now()

        # 将过期会话标记为非活跃
        cursor.execute("""
            UPDATE user_sessions
            SET is_active = 0
            WHERE expires_at < ?
            AND is_active = 1
        """, (now.isoformat(),))

        updated_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"✅ 标记了 {updated_count} 个过期会话为非活跃")
        return updated_count

    except Exception as e:
        logger.error(f"❌ 清理过期会话失败: {e}")
        return 0

def cleanup_old_security_events(days_to_keep=30):
    """清理旧的安全事件日志（保留30天）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        # 删除旧的低风险安全事件
        cursor.execute("""
            DELETE FROM security_events
            WHERE timestamp < ?
            AND risk_level IN ('LOW', 'MEDIUM')
        """, (cutoff_time.isoformat(),))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"✅ 清理了 {deleted_count} 个超过 {days_to_keep} 天的低风险安全事件")
        return deleted_count

    except Exception as e:
        logger.error(f"❌ 清理安全事件失败: {e}")
        return 0

def get_database_stats():
    """获取数据库统计信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        stats = {}

        # 总会话数
        cursor.execute("SELECT COUNT(*) FROM user_sessions")
        stats['total_sessions'] = cursor.fetchone()[0]

        # 活跃会话数
        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 1")
        stats['active_sessions'] = cursor.fetchone()[0]

        # 匿名会话数
        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE user_id = 'anonymous'")
        stats['anonymous_sessions'] = cursor.fetchone()[0]

        # 安全事件数
        cursor.execute("SELECT COUNT(*) FROM security_events")
        stats['security_events'] = cursor.fetchone()[0]

        conn.close()
        return stats

    except Exception as e:
        logger.error(f"❌ 获取数据库统计失败: {e}")
        return {}

def main():
    """主清理流程"""
    logger.info("=" * 60)
    logger.info("开始执行会话清理任务")
    logger.info("=" * 60)

    # 清理前统计
    logger.info("\n📊 清理前数据库统计:")
    before_stats = get_database_stats()
    for key, value in before_stats.items():
        logger.info(f"  - {key}: {value}")

    # 执行清理
    logger.info("\n🧹 开始清理...")

    # 1. 清理旧的匿名会话（保留3天）
    cleanup_anonymous_sessions(days_to_keep=3)

    # 2. 清理过期会话
    cleanup_expired_sessions()

    # 3. 清理旧的安全事件（保留30天）
    cleanup_old_security_events(days_to_keep=30)

    # 清理后统计
    logger.info("\n📊 清理后数据库统计:")
    after_stats = get_database_stats()
    for key, value in after_stats.items():
        logger.info(f"  - {key}: {value}")

    # 计算清理效果
    logger.info("\n📈 清理效果:")
    total_before = before_stats.get('total_sessions', 0)
    total_after = after_stats.get('total_sessions', 0)
    reduced = total_before - total_after

    if reduced > 0:
        percentage = (reduced / total_before * 100) if total_before > 0 else 0
        logger.info(f"  - 总会话减少: {reduced} 条 ({percentage:.1f}%)")
    else:
        logger.info("  - 无需清理，数据库状态良好")

    logger.info("\n" + "=" * 60)
    logger.info("会话清理任务完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
