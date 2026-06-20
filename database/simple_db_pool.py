#!/usr/bin/env python3
# simple_db_pool.py - 简化的数据库连接池
"""
轻量级PostgreSQL连接池，用于TCM系统
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import time
from contextlib import contextmanager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SimpleDBPool:
    """简化的数据库连接池"""
    
    def __init__(self, max_connections=5):
        self.max_connections = max_connections
        self.connections = []
        self.used_connections = set()
        self.lock = threading.Lock()
        
        self.db_config = {
            'database': 'tcm_db',
            'user': 'tcm_user',
            'password': 'tcm_secure_2024', 
            'host': 'localhost',
            'port': 5432,
            'cursor_factory': RealDictCursor
        }
        
        # 统计信息
        self.stats = {
            'total_queries': 0,
            'active_connections': 0,
            'created_at': datetime.now()
        }
        
        # 预创建一个连接测试
        self._create_connection()
        logger.info(f"Simple DB pool initialized with max {max_connections} connections")
    
    def _create_connection(self):
        """创建新的数据库连接"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise
    
    def get_connection(self):
        """获取数据库连接"""
        with self.lock:
            # 尝试复用现有连接
            for conn in self.connections:
                if conn not in self.used_connections:
                    # 测试连接是否有效
                    try:
                        conn.cursor().execute("SELECT 1")
                        self.used_connections.add(conn)
                        self.stats['active_connections'] += 1
                        return conn
                    except:
                        # 连接无效，移除
                        self.connections.remove(conn)
            
            # 创建新连接
            if len(self.connections) < self.max_connections:
                conn = self._create_connection()
                self.connections.append(conn)
                self.used_connections.add(conn)
                self.stats['active_connections'] += 1
                return conn
            
            # 连接池已满，等待
            raise Exception("Connection pool exhausted")
    
    def return_connection(self, conn):
        """归还数据库连接"""
        with self.lock:
            if conn in self.used_connections:
                self.used_connections.remove(conn)
                self.stats['active_connections'] -= 1
                
                # 检查连接健康状态
                try:
                    conn.rollback()  # 确保事务状态清理
                except:
                    # 连接有问题，移除
                    if conn in self.connections:
                        self.connections.remove(conn)
    
    @contextmanager
    def connection(self):
        """连接上下文管理器"""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn:
                self.return_connection(conn)
    
    @contextmanager
    def cursor(self, commit=True):
        """游标上下文管理器"""
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
                self.stats['total_queries'] += 1
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute(self, query, params=None, fetch=None):
        """执行查询"""
        with self.cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch == 'one':
                return cursor.fetchone()
            elif fetch == 'all':
                return cursor.fetchall()
            else:
                return cursor.rowcount
    
    def get_stats(self):
        """获取连接池统计"""
        uptime = datetime.now() - self.stats['created_at']
        return {
            'total_connections': len(self.connections),
            'active_connections': self.stats['active_connections'],
            'max_connections': self.max_connections,
            'total_queries': self.stats['total_queries'],
            'uptime_minutes': round(uptime.total_seconds() / 60, 1)
        }

# 全局连接池实例
_db_pool = None

def init_db_pool(max_connections=5):
    """初始化数据库连接池"""
    global _db_pool
    _db_pool = SimpleDBPool(max_connections)
    return _db_pool

def get_db_pool():
    """获取数据库连接池"""
    global _db_pool
    if _db_pool is None:
        _db_pool = SimpleDBPool()
    return _db_pool

# 便捷函数
def db_execute(query, params=None, fetch=None):
    """执行数据库查询"""
    pool = get_db_pool()
    return pool.execute(query, params, fetch)

def db_get_stats():
    """获取数据库连接池统计"""
    pool = get_db_pool()
    return pool.get_stats()

# 测试函数
if __name__ == "__main__":
    print("Testing simple database pool...")
    
    # 初始化连接池
    pool = init_db_pool(max_connections=3)
    
    # 测试查询
    try:
        result = db_execute("SELECT COUNT(*) as count FROM doctors", fetch='one')
        print(f"Doctors count: {result['count']}")
        
        result = db_execute("SELECT COUNT(*) as count FROM doctor_knowledge_documents", fetch='one') 
        print(f"Documents count: {result['count']}")
        
        # 显示统计信息
        stats = db_get_stats()
        print("Pool stats:", stats)
        
        print("✅ Simple database pool test successful!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")