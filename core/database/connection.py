#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据库连接管理模块
Unified Database Connection Manager

功能：
1. 确保所有数据库连接启用外键约束
2. 提供连接池管理
3. 统一错误处理
4. 性能监控

Version: 1.0
Date: 2025-10-12
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional
from functools import wraps
import time

logger = logging.getLogger(__name__)

# 数据库路径配置
DEFAULT_DB_PATH = "/opt/tcm-ai/data/user_history.sqlite"

class DatabaseConnectionManager:
    """数据库连接管理器"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._connection_count = 0

    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接

        重要：每个连接都会自动启用外键约束
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # ⚠️ 关键：启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")

            # 性能优化设置
            conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous = NORMAL")  # 平衡性能和安全
            conn.execute("PRAGMA cache_size = -64000")  # 64MB缓存
            conn.execute("PRAGMA temp_store = MEMORY")  # 临时表存储在内存

            self._connection_count += 1
            logger.debug(f"数据库连接已创建 (总计: {self._connection_count})")

            return conn

        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    @contextmanager
    def get_connection_context(self):
        """
        获取数据库连接上下文管理器

        使用方式:
        with db_manager.get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
        """
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()

    def verify_foreign_keys_enabled(self) -> bool:
        """验证外键约束是否已启用"""
        with self.get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()[0]
            return result == 1

    def get_database_stats(self) -> dict:
        """获取数据库统计信息"""
        with self.get_connection_context() as conn:
            cursor = conn.cursor()

            stats = {
                "foreign_keys_enabled": None,
                "journal_mode": None,
                "page_size": None,
                "page_count": None,
                "database_size_mb": None,
                "table_count": None
            }

            # 检查外键状态
            cursor.execute("PRAGMA foreign_keys")
            stats["foreign_keys_enabled"] = bool(cursor.fetchone()[0])

            # 检查日志模式
            cursor.execute("PRAGMA journal_mode")
            stats["journal_mode"] = cursor.fetchone()[0]

            # 获取页大小和数量
            cursor.execute("PRAGMA page_size")
            stats["page_size"] = cursor.fetchone()[0]

            cursor.execute("PRAGMA page_count")
            stats["page_count"] = cursor.fetchone()[0]

            # 计算数据库大小
            stats["database_size_mb"] = round(
                (stats["page_size"] * stats["page_count"]) / (1024 * 1024), 2
            )

            # 获取表数量
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            stats["table_count"] = cursor.fetchone()[0]

            return stats

# 全局数据库管理器实例
db_manager = DatabaseConnectionManager()

# 便捷函数
def get_db_connection() -> sqlite3.Connection:
    """
    获取数据库连接（便捷函数）

    ⚠️ 重要：此函数返回的连接已启用外键约束

    使用示例:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        conn.commit()
    finally:
        conn.close()
    """
    return db_manager.get_connection()

@contextmanager
def get_db_connection_context():
    """
    获取数据库连接上下文管理器（便捷函数）

    使用示例:
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        conn.commit()
    """
    with db_manager.get_connection_context() as conn:
        yield conn

def db_transaction(func):
    """
    数据库事务装饰器

    使用示例:
    @db_transaction
    def create_user(username, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users ...")
        return cursor.lastrowid
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = get_db_connection()
        try:
            result = func(*args, **kwargs, conn=conn)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            logger.error(f"事务回滚: {func.__name__} - {e}")
            raise
        finally:
            conn.close()

    return wrapper

def verify_database_integrity():
    """
    验证数据库完整性

    返回:
        dict: 包含检查结果的字典
    """
    results = {
        "foreign_keys_enabled": False,
        "integrity_check": False,
        "foreign_key_check": [],
        "errors": []
    }

    try:
        with get_db_connection_context() as conn:
            cursor = conn.cursor()

            # 检查外键是否启用
            cursor.execute("PRAGMA foreign_keys")
            results["foreign_keys_enabled"] = bool(cursor.fetchone()[0])

            # 数据库完整性检查
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            results["integrity_check"] = (integrity_result == "ok")

            if integrity_result != "ok":
                results["errors"].append(f"完整性检查失败: {integrity_result}")

            # 外键一致性检查
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()

            if fk_violations:
                for violation in fk_violations:
                    results["foreign_key_check"].append({
                        "table": violation[0],
                        "rowid": violation[1],
                        "parent": violation[2],
                        "fkid": violation[3]
                    })
                results["errors"].append(
                    f"发现 {len(fk_violations)} 个外键约束违规"
                )

    except Exception as e:
        results["errors"].append(f"检查过程出错: {e}")
        logger.error(f"数据库完整性检查失败: {e}")

    return results

# 导出主要接口
__all__ = [
    'DatabaseConnectionManager',
    'db_manager',
    'get_db_connection',
    'get_db_connection_context',
    'db_transaction',
    'verify_database_integrity'
]
