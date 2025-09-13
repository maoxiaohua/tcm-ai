#!/usr/bin/env python3
"""
数据库结构分析工具
分析TCM-AI数据库的结构问题和约束缺失
"""

import sqlite3
import os
from typing import Dict, List, Tuple
from datetime import datetime

def analyze_database_structure(db_path: str) -> Dict:
    """分析数据库结构"""
    if not os.path.exists(db_path):
        return {"error": f"数据库文件不存在: {db_path}"}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    analysis = {
        "database_path": db_path,
        "file_size": f"{os.path.getsize(db_path) / 1024:.1f} KB",
        "analyzed_at": datetime.now().isoformat(),
        "tables": {},
        "issues": [],
        "recommendations": []
    }
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"🔍 分析数据库: {os.path.basename(db_path)}")
    print(f"📊 发现 {len(tables)} 个数据表")
    print("-" * 60)
    
    for table in tables:
        print(f"\n📋 分析表: {table}")
        
        # 获取表信息
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = cursor.fetchall()
        
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        record_count = cursor.fetchone()[0]
        
        # 分析表结构
        table_info = {
            "columns": len(columns),
            "record_count": record_count,
            "has_primary_key": any(col[5] for col in columns),
            "foreign_keys": len(foreign_keys),
            "indexes": len(indexes),
            "column_details": [
                {
                    "name": col[1],
                    "type": col[2], 
                    "not_null": bool(col[3]),
                    "default": col[4],
                    "primary_key": bool(col[5])
                } for col in columns
            ],
            "foreign_key_details": [
                {
                    "from_column": fk[3],
                    "to_table": fk[2],
                    "to_column": fk[4]
                } for fk in foreign_keys
            ],
            "issues": []
        }
        
        # 检查问题
        if not table_info["has_primary_key"]:
            issue = f"❌ 表 '{table}' 缺少主键"
            table_info["issues"].append(issue)
            analysis["issues"].append(issue)
        
        # 检查可能需要外键的字段
        potential_fk_fields = []
        for col in columns:
            col_name = col[1].lower()
            if (col_name.endswith('_id') and col_name != 'user_id') or \
               col_name in ['patient_id', 'doctor_id', 'conversation_id', 'prescription_id']:
                if col_name not in [fk[3] for fk in foreign_keys]:
                    potential_fk_fields.append(col[1])
        
        if potential_fk_fields:
            issue = f"⚠️ 表 '{table}' 可能缺少外键约束: {', '.join(potential_fk_fields)}"
            table_info["issues"].append(issue)
            analysis["issues"].append(issue)
        
        # 检查索引
        id_columns = [col[1] for col in columns if col[1].lower().endswith('_id')]
        if id_columns and len(indexes) == 0:
            issue = f"💡 表 '{table}' 建议为ID字段添加索引: {', '.join(id_columns)}"
            table_info["issues"].append(issue)
            analysis["recommendations"].append(issue)
        
        analysis["tables"][table] = table_info
        
        # 输出表分析结果
        print(f"   📊 {record_count} 条记录, {len(columns)} 个字段")
        print(f"   🔑 主键: {'✅' if table_info['has_primary_key'] else '❌'}")
        print(f"   🔗 外键: {len(foreign_keys)} 个")
        print(f"   📇 索引: {len(indexes)} 个")
        
        if table_info["issues"]:
            for issue in table_info["issues"]:
                print(f"   {issue}")
    
    conn.close()
    
    # 总结
    print("\n" + "="*60)
    print("📊 数据库分析总结")
    print("="*60)
    print(f"总表数: {len(tables)}")
    print(f"发现问题: {len(analysis['issues'])}")
    print(f"优化建议: {len(analysis['recommendations'])}")
    
    if analysis["issues"]:
        print(f"\n❌ 发现的问题:")
        for i, issue in enumerate(analysis["issues"], 1):
            print(f"  {i}. {issue}")
    
    if analysis["recommendations"]:
        print(f"\n💡 优化建议:")
        for i, rec in enumerate(analysis["recommendations"], 1):
            print(f"  {i}. {rec}")
    
    return analysis

def generate_fix_sql(analysis: Dict) -> List[str]:
    """根据分析结果生成修复SQL语句"""
    sql_commands = []
    
    print(f"\n🛠️ 生成修复SQL语句")
    print("-" * 40)
    
    # 启用外键约束
    sql_commands.append("PRAGMA foreign_keys = ON;")
    
    for table_name, table_info in analysis["tables"].items():
        # 为缺少主键的表添加主键（如果可能）
        if not table_info["has_primary_key"] and table_name != "sqlite_sequence":
            # 检查是否已经有id字段
            has_id = any(col["name"].lower() == "id" for col in table_info["column_details"])
            if not has_id:
                sql = f"ALTER TABLE {table_name} ADD COLUMN id INTEGER PRIMARY KEY AUTOINCREMENT;"
                sql_commands.append(sql)
                print(f"✅ 为表 {table_name} 添加主键")
        
        # 添加外键约束 - 这个比较复杂，需要重建表
        # 暂时跳过，手动处理更安全
    
    # 添加常用索引
    common_index_fields = {
        'users': ['email', 'username', 'phone_number'],
        'prescriptions': ['patient_id', 'conversation_id', 'status', 'created_at'],
        'consultations': ['patient_id', 'doctor_id', 'status'],
        'user_sessions': ['user_id', 'status', 'created_at'],
        'orders': ['user_id', 'status', 'created_at']
    }
    
    for table_name, fields in common_index_fields.items():
        if table_name in analysis["tables"]:
            table_columns = [col["name"] for col in analysis["tables"][table_name]["column_details"]]
            for field in fields:
                if field in table_columns:
                    sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{field} ON {table_name}({field});"
                    sql_commands.append(sql)
                    print(f"📇 为 {table_name}.{field} 创建索引")
    
    return sql_commands

def main():
    """主函数"""
    print("🗄️ TCM-AI 数据库结构分析工具")
    print("=" * 60)
    
    databases = [
        "/opt/tcm-ai/data/user_history.sqlite",
        "/opt/tcm-ai/data/famous_doctors.sqlite", 
        "/opt/tcm-ai/data/cache.sqlite",
        "/opt/tcm-ai/data/intelligent_cache.db"
    ]
    
    all_analyses = {}
    all_sql_fixes = []
    
    for db_path in databases:
        if os.path.exists(db_path):
            analysis = analyze_database_structure(db_path)
            all_analyses[db_path] = analysis
            
            # 生成修复SQL
            fix_sql = generate_fix_sql(analysis)
            if fix_sql:
                all_sql_fixes.extend([f"-- 修复 {os.path.basename(db_path)}"] + fix_sql + [""])
    
    # 保存分析结果和修复SQL
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存修复SQL文件
    if all_sql_fixes:
        sql_file = f"/opt/tcm-ai/database/migrations/007_fix_constraints_{timestamp}.sql"
        os.makedirs(os.path.dirname(sql_file), exist_ok=True)
        
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write("-- TCM-AI 数据库约束修复\n")
            f.write(f"-- 生成时间: {datetime.now().isoformat()}\n")
            f.write("-- 请在执行前备份数据库\n\n")
            f.write("\n".join(all_sql_fixes))
        
        print(f"\n📄 修复SQL已保存到: {sql_file}")
    
    print(f"\n✅ 数据库分析完成!")
    print(f"📊 共分析 {len([db for db in databases if os.path.exists(db)])} 个数据库")

if __name__ == "__main__":
    main()