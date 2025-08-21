#!/usr/bin/env python3
# database_connection_pool.py - PostgreSQL连接池配置
"""
功能：
1. 实现PostgreSQL连接池管理
2. 提供高性能数据库连接
3. 自动连接重试和错误处理
4. 连接池监控和统计
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import threading

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnectionPool:
    """PostgreSQL连接池管理器"""
    
    def __init__(self, 
                 database: str = "tcm_db",
                 user: str = "tcm_user", 
                 password: str = "tcm_secure_2024",
                 host: str = "localhost",
                 port: int = 5432,
                 minconn: int = 2,
                 maxconn: int = 10):
        
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.minconn = minconn
        self.maxconn = maxconn
        
        # 连接池统计
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'created_at': datetime.now(),
            'total_queries': 0,
            'failed_queries': 0,
            'avg_query_time': 0.0
        }
        
        # 线程锁
        self._lock = threading.Lock()
        self._pool = None
        
        # 初始化连接池
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """初始化PostgreSQL连接池"""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.minconn,
                maxconn=self.maxconn,
                database=self.database,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                cursor_factory=RealDictCursor
            )
            
            self.stats['total_connections'] = self.maxconn
            logger.info(f"Database connection pool initialized: {self.minconn}-{self.maxconn} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            with self._lock:
                if self._pool is None:
                    raise Exception("Connection pool not initialized")
                
                conn = self._pool.getconn()
                self.stats['active_connections'] += 1
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
            
        finally:
            if conn:
                try:
                    with self._lock:
                        self._pool.putconn(conn)
                        self.stats['active_connections'] -= 1
                except Exception as e:
                    logger.warning(f"Failed to return connection to pool: {e}")
    
    @contextmanager  
    def get_cursor(self, commit: bool = True):
        """获取数据库游标的上下文管理器"""
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                yield cursor
                
                if commit:
                    conn.commit()
                    
                # 更新查询统计
                query_time = time.time() - start_time
                self._update_query_stats(query_time, success=True)
                
        except Exception as e:
            self._update_query_stats(time.time() - start_time, success=False)
            raise
    
    def _update_query_stats(self, query_time: float, success: bool):
        """更新查询统计信息"""
        with self._lock:
            if success:
                self.stats['total_queries'] += 1
                # 计算移动平均查询时间
                total_time = self.stats['avg_query_time'] * (self.stats['total_queries'] - 1)
                self.stats['avg_query_time'] = (total_time + query_time) / self.stats['total_queries']
            else:
                self.stats['failed_queries'] += 1
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = 'none') -> Any:
        """执行数据库查询"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                
                if fetch == 'one':
                    return cursor.fetchone()
                elif fetch == 'all':
                    return cursor.fetchall()
                elif fetch == 'many':
                    return cursor.fetchmany()
                else:
                    return cursor.rowcount
                    
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_many(self, query: str, params_list: list) -> int:
        """批量执行查询"""
        try:
            with self.get_cursor() as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount
                
        except Exception as e:
            logger.error(f"Batch query execution failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """测试连接池状态"""
        try:
            result = self.execute_query("SELECT 1 as test", fetch='one')
            return result and result['test'] == 1
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        with self._lock:
            uptime = datetime.now() - self.stats['created_at']
            
            pool_info = {
                'pool_size': f"{self.minconn}-{self.maxconn}",
                'active_connections': self.stats['active_connections'],
                'total_queries': self.stats['total_queries'],
                'failed_queries': self.stats['failed_queries'],
                'success_rate': f"{((self.stats['total_queries'] - self.stats['failed_queries']) / max(self.stats['total_queries'], 1) * 100):.1f}%",
                'avg_query_time_ms': f"{self.stats['avg_query_time'] * 1000:.2f}",
                'uptime_hours': f"{uptime.total_seconds() / 3600:.1f}",
                'queries_per_hour': f"{self.stats['total_queries'] / max(uptime.total_seconds() / 3600, 0.01):.1f}",
                'connection_health': 'healthy' if self.test_connection() else 'unhealthy'
            }
            
            return pool_info
    
    def close_pool(self):
        """关闭连接池"""
        try:
            if self._pool:
                with self._lock:
                    self._pool.closeall()
                    self._pool = None
                logger.info("Database connection pool closed")
                
        except Exception as e:
            logger.error(f"Failed to close connection pool: {e}")
    
    def __del__(self):
        """析构函数，确保连接池关闭"""
        self.close_pool()

# 全局连接池实例
_connection_pool = None

def get_database_pool() -> DatabaseConnectionPool:
    """获取全局数据库连接池实例"""
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = DatabaseConnectionPool()
    
    return _connection_pool

def init_database_pool(**kwargs) -> DatabaseConnectionPool:
    """初始化数据库连接池"""
    global _connection_pool
    
    _connection_pool = DatabaseConnectionPool(**kwargs)
    return _connection_pool

# 便捷函数
@contextmanager
def db_connection():
    """获取数据库连接"""
    pool = get_database_pool()
    with pool.get_connection() as conn:
        yield conn

@contextmanager  
def db_cursor(commit: bool = True):
    """获取数据库游标"""
    pool = get_database_pool()
    with pool.get_cursor(commit=commit) as cursor:
        yield cursor

def db_execute(query: str, params: tuple = None, fetch: str = 'none') -> Any:
    """执行数据库查询"""
    pool = get_database_pool()
    return pool.execute_query(query, params, fetch)

def db_execute_many(query: str, params_list: list) -> int:
    """批量执行查询"""
    pool = get_database_pool()
    return pool.execute_many(query, params_list)

def get_db_stats() -> Dict[str, Any]:
    """获取数据库连接池统计"""
    pool = get_database_pool()
    return pool.get_pool_stats()

# 测试函数
def test_database_pool():
    """测试数据库连接池功能"""
    print("=== 数据库连接池测试 ===")
    
    # 初始化连接池
    pool = init_database_pool(minconn=2, maxconn=5)
    
    # 测试基本连接
    print("1. 测试基本连接...")
    if pool.test_connection():
        print("   ✅ 连接测试通过")
    else:
        print("   ❌ 连接测试失败")
        return
    
    # 测试查询操作
    print("2. 测试查询操作...")
    try:
        doctors = db_execute("SELECT COUNT(*) as count FROM doctors", fetch='one')
        print(f"   ✅ 查询成功，医生数量: {doctors['count']}")
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")
    
    # 测试批量操作
    print("3. 测试连接池统计...")
    stats = get_db_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 测试并发连接
    print("4. 测试并发连接...")
    import concurrent.futures
    
    def test_concurrent_query(i):
        try:
            result = db_execute("SELECT COUNT(*) as count FROM doctor_knowledge_documents", fetch='one')
            return f"Query {i}: {result['count']} documents"
        except Exception as e:
            return f"Query {i} failed: {e}"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(test_concurrent_query, i) for i in range(10)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    for result in results:
        print(f"   {result}")
    
    # 最终统计
    print("5. 最终连接池状态:")
    final_stats = get_db_stats()
    for key, value in final_stats.items():
        print(f"   {key}: {value}")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_database_pool()