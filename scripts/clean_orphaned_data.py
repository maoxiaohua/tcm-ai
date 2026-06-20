#!/usr/bin/env python3
"""
数据库孤立数据清理工具
安全地处理外键关系不一致的数据
"""

import sqlite3
import os
from datetime import datetime
import json

def backup_orphaned_data(db_path: str) -> str:
    """备份孤立数据到JSON文件"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    backup_data = {
        "backup_time": datetime.now().isoformat(),
        "database": db_path,
        "orphaned_records": {}
    }
    
    # 备份孤立的处方记录
    cursor.execute("""
        SELECT id, patient_id, conversation_id, symptoms, diagnosis, 
               ai_prescription, status, created_at
        FROM prescriptions 
        WHERE patient_id NOT IN (SELECT user_id FROM users)
    """)
    
    orphaned_prescriptions = []
    for row in cursor.fetchall():
        orphaned_prescriptions.append({
            "id": row[0],
            "patient_id": row[1], 
            "conversation_id": row[2],
            "symptoms": row[3],
            "diagnosis": row[4],
            "ai_prescription": row[5],
            "status": row[6],
            "created_at": row[7]
        })
    
    backup_data["orphaned_records"]["prescriptions"] = orphaned_prescriptions
    
    # 备份孤立的订单记录
    cursor.execute("""
        SELECT id, prescription_id, patient_id, status, created_at
        FROM orders 
        WHERE prescription_id IS NOT NULL 
        AND prescription_id NOT IN (SELECT id FROM prescriptions)
    """)
    
    orphaned_orders = []
    for row in cursor.fetchall():
        orphaned_orders.append({
            "id": row[0],
            "prescription_id": row[1],
            "patient_id": row[2], 
            "status": row[3],
            "created_at": row[4]
        })
    
    backup_data["orphaned_records"]["orders"] = orphaned_orders
    
    conn.close()
    
    # 保存备份文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"/opt/tcm-ai/backups/orphaned_data_backup_{timestamp}.json"
    
    os.makedirs(os.path.dirname(backup_file), exist_ok=True)
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    return backup_file

def analyze_orphaned_data(db_path: str):
    """分析孤立数据的类型和重要性"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"📊 分析数据库孤立数据: {os.path.basename(db_path)}")
    print("-" * 60)
    
    # 分析孤立处方
    cursor.execute("""
        SELECT patient_id, COUNT(*) as count,
               MIN(created_at) as earliest,
               MAX(created_at) as latest,
               status
        FROM prescriptions 
        WHERE patient_id NOT IN (SELECT user_id FROM users)
        GROUP BY patient_id, status
        ORDER BY count DESC
    """)
    
    print("🔍 孤立的处方记录:")
    orphaned_prescriptions = cursor.fetchall()
    
    test_data_count = 0
    real_data_count = 0
    
    for row in orphaned_prescriptions:
        patient_id, count, earliest, latest, status = row
        is_test_data = any(keyword in patient_id.lower() for keyword in ['test', 'demo', 'patient_001'])
        
        print(f"  Patient ID: {patient_id}")
        print(f"  处方数量: {count}, 状态: {status}")
        print(f"  时间范围: {earliest} ~ {latest}")
        print(f"  数据类型: {'🧪 测试数据' if is_test_data else '📋 业务数据'}")
        print()
        
        if is_test_data:
            test_data_count += count
        else:
            real_data_count += count
    
    print(f"📈 总结:")
    print(f"  测试数据处方: {test_data_count} 条")
    print(f"  业务数据处方: {real_data_count} 条") 
    print(f"  总计孤立处方: {test_data_count + real_data_count} 条")
    
    # 分析孤立订单
    cursor.execute("""
        SELECT COUNT(*) FROM orders 
        WHERE prescription_id IS NOT NULL 
        AND prescription_id NOT IN (SELECT id FROM prescriptions)
    """)
    
    orphaned_orders_count = cursor.fetchone()[0]
    print(f"  孤立订单记录: {orphaned_orders_count} 条")
    
    conn.close()
    
    return {
        "test_data_prescriptions": test_data_count,
        "real_data_prescriptions": real_data_count,
        "orphaned_orders": orphaned_orders_count
    }

def clean_orphaned_data(db_path: str, clean_test_data: bool = True, clean_real_data: bool = False):
    """清理孤立数据"""
    print(f"🧹 开始清理孤立数据...")
    print(f"清理测试数据: {'✅' if clean_test_data else '❌'}")
    print(f"清理业务数据: {'✅' if clean_real_data else '❌'}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cleaned_count = 0
    
    if clean_test_data:
        # 清理明显的测试数据
        test_patterns = ['test%', 'demo%', 'patient_001']
        
        for pattern in test_patterns:
            cursor.execute("""
                DELETE FROM prescriptions 
                WHERE patient_id LIKE ? 
                AND patient_id NOT IN (SELECT user_id FROM users)
            """, (pattern,))
            
            deleted = cursor.rowcount
            cleaned_count += deleted
            print(f"清理测试处方 ({pattern}): {deleted} 条")
    
    if clean_real_data:
        # 清理所有孤立数据（危险操作）
        cursor.execute("""
            DELETE FROM prescriptions 
            WHERE patient_id NOT IN (SELECT user_id FROM users)
        """)
        
        deleted = cursor.rowcount
        cleaned_count += deleted
        print(f"清理所有孤立处方: {deleted} 条")
    
    # 清理孤立订单
    cursor.execute("""
        DELETE FROM orders 
        WHERE prescription_id IS NOT NULL 
        AND prescription_id NOT IN (SELECT id FROM prescriptions)
    """)
    
    deleted_orders = cursor.rowcount
    print(f"清理孤立订单: {deleted_orders} 条")
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据清理完成！共清理 {cleaned_count} 条处方记录，{deleted_orders} 条订单记录")
    
    return cleaned_count + deleted_orders

def main():
    """主函数"""
    db_path = "/opt/tcm-ai/data/user_history.sqlite"
    
    print("🗄️ TCM-AI 数据库孤立数据清理工具")
    print("=" * 60)
    
    # 1. 分析孤立数据
    stats = analyze_orphaned_data(db_path)
    
    # 2. 备份孤立数据
    print(f"\n💾 备份孤立数据...")
    backup_file = backup_orphaned_data(db_path)
    print(f"备份文件: {backup_file}")
    
    # 3. 清理策略
    if stats["test_data_prescriptions"] > 0:
        print(f"\n🧪 发现 {stats['test_data_prescriptions']} 条测试数据，建议清理")
        clean_orphaned_data(db_path, clean_test_data=True, clean_real_data=False)
    
    if stats["real_data_prescriptions"] > 0:
        print(f"\n⚠️ 发现 {stats['real_data_prescriptions']} 条业务数据孤立")
        print("建议手动检查这些数据的重要性后再决定是否清理")
        print("如需清理，请运行: clean_orphaned_data(db_path, clean_real_data=True)")
    
    # 4. 验证清理结果
    print(f"\n✅ 验证清理结果...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE patient_id NOT IN (SELECT user_id FROM users)")
    remaining_orphaned = cursor.fetchone()[0]
    
    print(f"剩余孤立处方: {remaining_orphaned} 条")
    
    if remaining_orphaned == 0:
        print("🎉 所有处方数据完整性问题已解决！")
    else:
        print("💡 仍有孤立数据，请检查是否需要进一步处理")
    
    conn.close()

if __name__ == "__main__":
    main()