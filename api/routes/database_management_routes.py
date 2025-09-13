#!/usr/bin/env python3
"""
数据库管理API路由
为数据库管理界面提供后端支持
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import sqlite3
import os
import logging
from datetime import datetime

# 导入统一响应格式
from api.utils.api_response import APIResponse

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/database", tags=["database-management"])

# 数据库文件路径映射
DATABASE_PATHS = {
    'user_history': '/opt/tcm-ai/data/user_history.sqlite',
    'famous_doctors': '/opt/tcm-ai/data/famous_doctors.sqlite', 
    'cache': '/opt/tcm-ai/data/cache.sqlite',
    'intelligent_cache': '/opt/tcm-ai/data/intelligent_cache.db'
}

# Pydantic模型
class DatabaseQueryRequest(BaseModel):
    database: str
    query: str

class DatabaseOverviewRequest(BaseModel):
    database: str

class QueryResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str = ""

def get_database_connection(db_name: str) -> sqlite3.Connection:
    """获取数据库连接"""
    if db_name not in DATABASE_PATHS:
        raise HTTPException(status_code=400, detail=f"不支持的数据库: {db_name}")
    
    db_path = DATABASE_PATHS[db_name]
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail=f"数据库文件不存在: {db_path}")
    
    return sqlite3.connect(db_path)

def get_file_size(file_path: str) -> str:
    """获取文件大小的友好显示"""
    try:
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except:
        return "未知"

def get_table_count(conn: sqlite3.Connection, table_name: str) -> int:
    """获取表记录数"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except:
        return 0

@router.post("/overview", response_model=QueryResult)
async def get_database_overview(request: DatabaseOverviewRequest):
    """获取数据库概览信息"""
    try:
        db_path = DATABASE_PATHS.get(request.database)
        if not db_path or not os.path.exists(db_path):
            return QueryResult(
                success=False, 
                message=f"数据库 {request.database} 不存在"
            )
        
        conn = get_database_connection(request.database)
        cursor = conn.cursor()
        
        # 获取基本信息
        file_size = get_file_size(db_path)
        last_modified = datetime.fromtimestamp(os.path.getmtime(db_path)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row[0] for row in cursor.fetchall()]
        
        # 获取每个表的记录数
        tables = []
        for table_name in table_names:
            count = get_table_count(conn, table_name)
            tables.append({
                'name': table_name,
                'count': count
            })
        
        conn.close()
        
        overview_data = {
            'database_name': request.database,
            'file_size': file_size,
            'table_count': len(tables),
            'last_modified': last_modified,
            'tables': tables
        }
        
        return QueryResult(
            success=True,
            data=overview_data,
            message="数据库概览加载成功"
        )
        
    except Exception as e:
        logger.error(f"获取数据库概览失败: {e}")
        return QueryResult(
            success=False,
            message=f"获取数据库概览失败: {str(e)}"
        )

@router.post("/query", response_model=QueryResult)
async def execute_database_query(request: DatabaseQueryRequest):
    """执行数据库查询"""
    try:
        # 安全检查 - 只允许SELECT和PRAGMA查询
        query_upper = request.query.upper().strip()
        if not (query_upper.startswith('SELECT') or 
                query_upper.startswith('PRAGMA') or 
                query_upper.startswith('EXPLAIN')):
            return QueryResult(
                success=False,
                message="出于安全考虑，只允许执行SELECT、PRAGMA和EXPLAIN查询"
            )
        
        conn = get_database_connection(request.database)
        cursor = conn.cursor()
        
        # 执行查询
        cursor.execute(request.query)
        
        # 获取结果
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        
        conn.close()
        
        query_data = {
            'columns': columns,
            'rows': rows,
            'row_count': len(rows)
        }
        
        return QueryResult(
            success=True,
            data=query_data,
            message=f"查询成功，返回 {len(rows)} 条记录"
        )
        
    except sqlite3.Error as e:
        logger.error(f"SQL查询错误: {e}")
        return QueryResult(
            success=False,
            message=f"SQL错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"查询执行失败: {e}")
        return QueryResult(
            success=False,
            message=f"查询执行失败: {str(e)}"
        )

@router.get("/tables/{database}")
async def get_database_tables(database: str):
    """获取数据库所有表名"""
    try:
        conn = get_database_connection(database)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "success": True,
            "data": {"tables": tables},
            "message": f"获取到 {len(tables)} 个表"
        }
        
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        return {
            "success": False,
            "message": f"获取表列表失败: {str(e)}"
        }

@router.get("/schema/{database}/{table}")
async def get_table_schema(database: str, table: str):
    """获取表结构信息"""
    try:
        conn = get_database_connection(database)
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        # 获取外键信息
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = cursor.fetchall()
        
        # 获取索引信息
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        
        conn.close()
        
        schema_data = {
            'table_name': table,
            'columns': [
                {
                    'cid': col[0],
                    'name': col[1], 
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default_value': col[4],
                    'primary_key': bool(col[5])
                } for col in columns
            ],
            'foreign_keys': [
                {
                    'id': fk[0],
                    'seq': fk[1],
                    'table': fk[2],
                    'from_column': fk[3],
                    'to_column': fk[4]
                } for fk in foreign_keys
            ],
            'indexes': [
                {
                    'seq': idx[0],
                    'name': idx[1],
                    'unique': bool(idx[2])
                } for idx in indexes
            ]
        }
        
        return {
            "success": True,
            "data": schema_data,
            "message": f"获取表 {table} 结构成功"
        }
        
    except Exception as e:
        logger.error(f"获取表结构失败: {e}")
        return {
            "success": False,
            "message": f"获取表结构失败: {str(e)}"
        }

@router.get("/analyze/{database}")
async def analyze_database_issues(database: str):
    """分析数据库潜在问题"""
    try:
        conn = get_database_connection(database)
        cursor = conn.cursor()
        
        issues = []
        recommendations = []
        
        # 检查外键约束
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()
        if fk_violations:
            issues.append(f"发现 {len(fk_violations)} 个外键约束违规")
            recommendations.append("建议修复外键约束违规")
        
        # 检查表是否有主键
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        tables_without_pk = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            has_pk = any(col[5] for col in columns)  # col[5] is pk flag
            if not has_pk:
                tables_without_pk.append(table)
        
        if tables_without_pk:
            issues.append(f"以下表缺少主键: {', '.join(tables_without_pk)}")
            recommendations.append("建议为所有表添加主键")
        
        # 检查索引使用情况
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        custom_indexes = cursor.fetchall()
        
        if len(custom_indexes) < len(tables):
            recommendations.append("考虑为常用查询字段添加索引以提升性能")
        
        conn.close()
        
        analysis_data = {
            'database': database,
            'issues_found': len(issues),
            'issues': issues,
            'recommendations': recommendations,
            'health_score': max(0, 100 - len(issues) * 20)  # 简单的健康评分
        }
        
        return {
            "success": True,
            "data": analysis_data,
            "message": f"数据库分析完成，发现 {len(issues)} 个问题"
        }
        
    except Exception as e:
        logger.error(f"数据库分析失败: {e}")
        return {
            "success": False,
            "message": f"数据库分析失败: {str(e)}"
        }