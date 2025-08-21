#!/usr/bin/env python3
# database_index_optimizer.py - PostgreSQL数据库索引优化系统
"""
功能：
1. 分析数据库表结构和查询模式
2. 识别缺失的索引机会
3. 创建优化的复合索引
4. 监控索引使用率和性能
5. 清理无用索引
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseIndexOptimizer:
    """数据库索引优化器"""
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'tcm_db',
            'user': 'tcm_user',
            'password': 'tcm_secure_2024'
        }
        
        # TCM系统查询模式分析
        self.tcm_query_patterns = {
            'doctors': {
                'frequent_queries': [
                    'SELECT * FROM doctors WHERE doctor_key = ?',
                    'SELECT * FROM doctors WHERE id = ?'
                ],
                'recommended_indexes': [
                    ('doctor_key', 'UNIQUE'),
                    ('id', 'PRIMARY KEY')  # 已存在
                ]
            },
            'doctor_knowledge_documents': {
                'frequent_queries': [
                    'SELECT * FROM doctor_knowledge_documents WHERE doctor_id = ?',
                    'SELECT * FROM doctor_knowledge_documents WHERE doctor_id = ? AND document_type = ?',
                    'SELECT * FROM doctor_knowledge_documents WHERE keywords LIKE ?',
                    'SELECT * FROM doctor_knowledge_documents WHERE content LIKE ?'
                ],
                'recommended_indexes': [
                    ('doctor_id', 'INDEX'),  # 已存在
                    ('doctor_id, document_type', 'COMPOSITE'),
                    ('keywords', 'GIN'),  # 全文搜索
                    ('content', 'GIN')     # 全文搜索
                ]
            },
            'consultations': {
                'frequent_queries': [
                    'SELECT * FROM consultations WHERE conversation_id = ?',
                    'SELECT * FROM consultations WHERE user_id = ? ORDER BY created_at DESC',
                    'SELECT * FROM consultations WHERE doctor_id = ? AND status = ?',
                    'SELECT * FROM consultations WHERE created_at >= ?'
                ],
                'recommended_indexes': [
                    ('conversation_id', 'UNIQUE'),  # 已存在
                    ('user_id, created_at', 'COMPOSITE'),
                    ('doctor_id, status', 'COMPOSITE'),
                    ('created_at', 'INDEX')
                ]
            },
            'consultation_messages': {
                'frequent_queries': [
                    'SELECT * FROM consultation_messages WHERE consultation_id = ? ORDER BY created_at',
                    'SELECT * FROM consultation_messages WHERE consultation_id = ? AND sender = ?',
                    'SELECT COUNT(*) FROM consultation_messages WHERE consultation_id = ?'
                ],
                'recommended_indexes': [
                    ('consultation_id', 'INDEX'),  # 已存在
                    ('consultation_id, created_at', 'COMPOSITE'),
                    ('consultation_id, sender', 'COMPOSITE')
                ]
            },
            'user_feedback': {
                'frequent_queries': [
                    'SELECT * FROM user_feedback WHERE consultation_id = ?',
                    'SELECT AVG(rating) FROM user_feedback WHERE consultation_id IN (?)',
                    'SELECT * FROM user_feedback WHERE rating >= ? ORDER BY created_at DESC'
                ],
                'recommended_indexes': [
                    ('consultation_id', 'INDEX'),  # 已存在
                    ('rating', 'INDEX'),  # 已存在
                    ('rating, created_at', 'COMPOSITE')
                ]
            }
        }
        
        logger.info("Database Index Optimizer initialized")
    
    def connect_database(self):
        """连接数据库"""
        return psycopg2.connect(**self.db_config)
    
    def analyze_current_indexes(self) -> Dict:
        """分析当前数据库索引状态"""
        try:
            with self.connect_database() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # 获取所有索引信息
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef,
                        pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
                
                current_indexes = cursor.fetchall()
                
                # 获取索引使用统计
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
                
                index_stats = cursor.fetchall()
                
                # 获取表大小信息
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """)
                
                table_sizes = cursor.fetchall()
                
                analysis_result = {
                    "current_indexes": [dict(row) for row in current_indexes],
                    "index_usage_stats": [dict(row) for row in index_stats],
                    "table_sizes": [dict(row) for row in table_sizes],
                    "analysis_timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Found {len(current_indexes)} indexes across {len(table_sizes)} tables")
                return analysis_result
                
        except Exception as e:
            logger.error(f"Failed to analyze current indexes: {e}")
            return {"error": str(e)}
    
    def identify_missing_indexes(self) -> List[Dict]:
        """识别缺失的索引"""
        try:
            current_analysis = self.analyze_current_indexes()
            if "error" in current_analysis:
                return [{"error": current_analysis["error"]}]
            
            existing_indexes = {}
            for index in current_analysis["current_indexes"]:
                table_name = index["tablename"]
                index_name = index["indexname"]
                if table_name not in existing_indexes:
                    existing_indexes[table_name] = []
                existing_indexes[table_name].append(index_name)
            
            missing_indexes = []
            
            # 分析每个表的推荐索引
            for table_name, patterns in self.tcm_query_patterns.items():
                for index_def, index_type in patterns["recommended_indexes"]:
                    # 生成建议的索引名
                    index_columns = index_def.replace(', ', '_').replace(' ', '_')
                    suggested_index_name = f"idx_{table_name}_{index_columns}"
                    
                    # 检查是否已存在类似索引
                    exists = False
                    if table_name in existing_indexes:
                        for existing_index in existing_indexes[table_name]:
                            if index_columns.lower() in existing_index.lower():
                                exists = True
                                break
                    
                    if not exists and index_type not in ['PRIMARY KEY', 'UNIQUE']:
                        missing_indexes.append({
                            "table_name": table_name,
                            "index_name": suggested_index_name,
                            "columns": index_def,
                            "index_type": index_type,
                            "priority": self._calculate_index_priority(table_name, index_def),
                            "estimated_benefit": self._estimate_index_benefit(table_name, index_def)
                        })
            
            # 按优先级排序
            missing_indexes.sort(key=lambda x: x["priority"], reverse=True)
            
            logger.info(f"Identified {len(missing_indexes)} missing indexes")
            return missing_indexes
            
        except Exception as e:
            logger.error(f"Failed to identify missing indexes: {e}")
            return [{"error": str(e)}]
    
    def _calculate_index_priority(self, table_name: str, columns: str) -> int:
        """计算索引优先级"""
        priority = 0
        
        # 基于表的重要性
        table_priorities = {
            'doctor_knowledge_documents': 10,
            'consultations': 9,
            'consultation_messages': 8,
            'user_feedback': 7,
            'doctors': 6
        }
        
        priority += table_priorities.get(table_name, 5)
        
        # 基于列的重要性
        if 'id' in columns:
            priority += 5
        if 'created_at' in columns:
            priority += 3
        if any(col in columns for col in ['doctor_id', 'consultation_id', 'user_id']):
            priority += 4
        if any(col in columns for col in ['content', 'keywords']):
            priority += 2
        
        return priority
    
    def _estimate_index_benefit(self, table_name: str, columns: str) -> str:
        """估计索引收益"""
        if 'content' in columns or 'keywords' in columns:
            return "High - Full text search optimization"
        elif any(col in columns for col in ['doctor_id', 'consultation_id', 'user_id']):
            return "High - Foreign key join optimization"
        elif 'created_at' in columns:
            return "Medium - Time range query optimization"
        else:
            return "Medium - General query optimization"
    
    def create_recommended_indexes(self, dry_run: bool = True) -> List[Dict]:
        """创建推荐的索引"""
        missing_indexes = self.identify_missing_indexes()
        if not missing_indexes or "error" in missing_indexes[0]:
            return missing_indexes
        
        results = []
        
        try:
            with self.connect_database() as conn:
                cursor = conn.cursor()
                
                for index_info in missing_indexes:
                    if index_info["priority"] < 8:  # 只创建高优先级索引
                        continue
                        
                    table_name = index_info["table_name"]
                    index_name = index_info["index_name"]
                    columns = index_info["columns"]
                    index_type = index_info["index_type"]
                    
                    # 构建CREATE INDEX语句
                    if index_type == 'GIN':
                        # 全文搜索索引
                        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING GIN (to_tsvector('english', {columns}))"
                    elif index_type == 'COMPOSITE':
                        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})"
                    else:
                        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})"
                    
                    result = {
                        "index_name": index_name,
                        "table_name": table_name,
                        "sql": sql,
                        "dry_run": dry_run,
                        "success": False,
                        "error": None,
                        "execution_time": None
                    }
                    
                    if dry_run:
                        result["success"] = True
                        result["message"] = "Dry run - SQL prepared but not executed"
                    else:
                        try:
                            start_time = datetime.now()
                            cursor.execute(sql)
                            conn.commit()
                            end_time = datetime.now()
                            
                            result["success"] = True
                            result["execution_time"] = (end_time - start_time).total_seconds()
                            result["message"] = "Index created successfully"
                            
                            logger.info(f"Created index: {index_name}")
                            
                        except Exception as e:
                            result["error"] = str(e)
                            logger.error(f"Failed to create index {index_name}: {e}")
                            conn.rollback()
                    
                    results.append(result)
                
                logger.info(f"Index creation {'simulation' if dry_run else 'execution'} completed")
                return results
                
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            return [{"error": str(e)}]
    
    def analyze_slow_queries(self) -> List[Dict]:
        """分析慢查询（需要开启query logging）"""
        try:
            with self.connect_database() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # 检查是否启用了查询统计
                cursor.execute("SELECT name, setting FROM pg_settings WHERE name IN ('log_statement', 'log_min_duration_statement')")
                settings = cursor.fetchall()
                
                # 查看当前活跃查询
                cursor.execute("""
                    SELECT 
                        pid,
                        now() - pg_stat_activity.query_start AS duration,
                        query,
                        state
                    FROM pg_stat_activity 
                    WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
                    AND state != 'idle'
                """)
                
                long_running_queries = cursor.fetchall()
                
                # 获取表访问统计
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        idx_tup_fetch,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY seq_scan DESC
                """)
                
                table_access_stats = cursor.fetchall()
                
                analysis = {
                    "pg_settings": [dict(row) for row in settings],
                    "long_running_queries": [dict(row) for row in long_running_queries],
                    "table_access_stats": [dict(row) for row in table_access_stats],
                    "recommendations": []
                }
                
                # 分析建议
                for table_stat in table_access_stats:
                    if table_stat['seq_scan'] > 1000:  # 顺序扫描过多
                        analysis["recommendations"].append({
                            "type": "high_sequential_scan",
                            "table": table_stat['tablename'],
                            "seq_scans": table_stat['seq_scan'],
                            "recommendation": f"Consider adding indexes to {table_stat['tablename']} to reduce sequential scans"
                        })
                
                return analysis
                
        except Exception as e:
            logger.error(f"Failed to analyze slow queries: {e}")
            return {"error": str(e)}
    
    def generate_optimization_report(self) -> Dict:
        """生成完整的优化报告"""
        try:
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "database_info": self.db_config["database"],
                "current_indexes_analysis": self.analyze_current_indexes(),
                "missing_indexes": self.identify_missing_indexes(),
                "slow_query_analysis": self.analyze_slow_queries(),
                "optimization_recommendations": []
            }
            
            # 生成优化建议
            if report["missing_indexes"] and "error" not in report["missing_indexes"][0]:
                high_priority_indexes = [idx for idx in report["missing_indexes"] if idx["priority"] >= 8]
                if high_priority_indexes:
                    report["optimization_recommendations"].append({
                        "type": "create_indexes",
                        "priority": "high",
                        "description": f"Create {len(high_priority_indexes)} high-priority indexes",
                        "indexes": high_priority_indexes
                    })
            
            # 保存报告到文件
            report_file = f"/opt/tcm/database_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Optimization report saved to {report_file}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate optimization report: {e}")
            return {"error": str(e)}

# 命令行工具
if __name__ == "__main__":
    import sys
    
    optimizer = DatabaseIndexOptimizer()
    
    if len(sys.argv) == 1:
        print("TCM Database Index Optimizer")
        print("Commands:")
        print("  python3 database_index_optimizer.py analyze     - Analyze current indexes")
        print("  python3 database_index_optimizer.py missing     - Identify missing indexes")
        print("  python3 database_index_optimizer.py create      - Create recommended indexes")
        print("  python3 database_index_optimizer.py dry-run     - Simulate index creation")
        print("  python3 database_index_optimizer.py report      - Generate full optimization report")
        print("  python3 database_index_optimizer.py slow        - Analyze slow queries")
        
    elif sys.argv[1] == "analyze":
        result = optimizer.analyze_current_indexes()
        print(json.dumps(result, indent=2))
        
    elif sys.argv[1] == "missing":
        missing = optimizer.identify_missing_indexes()
        print(f"Missing indexes: {len(missing)}")
        for idx in missing:
            if "error" not in idx:
                print(f"  {idx['table_name']}.{idx['index_name']} (Priority: {idx['priority']}) - {idx['estimated_benefit']}")
            
    elif sys.argv[1] == "dry-run":
        results = optimizer.create_recommended_indexes(dry_run=True)
        print("Index creation simulation:")
        for result in results:
            if "error" not in result:
                print(f"  ✅ {result['index_name']}: {result['message']}")
                print(f"     SQL: {result['sql']}")
            
    elif sys.argv[1] == "create":
        print("Creating recommended indexes...")
        results = optimizer.create_recommended_indexes(dry_run=False)
        for result in results:
            if result.get("success"):
                print(f"  ✅ {result['index_name']}: Created in {result.get('execution_time', 0):.2f}s")
            else:
                print(f"  ❌ {result['index_name']}: {result.get('error', 'Unknown error')}")
                
    elif sys.argv[1] == "slow":
        analysis = optimizer.analyze_slow_queries()
        print(json.dumps(analysis, indent=2))
        
    elif sys.argv[1] == "report":
        print("Generating optimization report...")
        report = optimizer.generate_optimization_report()
        if "error" not in report:
            print(f"✅ Report generated successfully")
            print(f"Current indexes: {len(report['current_indexes_analysis']['current_indexes'])}")
            print(f"Missing indexes: {len(report['missing_indexes'])}")
            print(f"Recommendations: {len(report['optimization_recommendations'])}")
        else:
            print(f"❌ Report generation failed: {report['error']}")
    
    else:
        print(f"Unknown command: {sys.argv[1]}")\nimport os