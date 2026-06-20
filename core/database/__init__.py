"""
数据库核心模块
Database Core Module
"""

from .connection import (
    db_manager,
    get_db_connection,
    get_db_connection_context,
    db_transaction,
    verify_database_integrity
)

__all__ = [
    'db_manager',
    'get_db_connection',
    'get_db_connection_context',
    'db_transaction',
    'verify_database_integrity'
]
