#!/usr/bin/env python3
"""
简单测试处方审核API的数据库操作
"""
import sqlite3
import sys
sys.path.append('/opt/tcm-ai')

def test_simple_database_operations():
    """直接测试数据库操作，不通过API"""
    print("=== 直接测试数据库操作 ===\n")
    
    # 连接数据库
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        prescription_id = 104
        
        # 1. 检查处方是否存在
        print("1. 检查处方是否存在...")
        cursor.execute("""
            SELECT id, consultation_id, doctor_id, status, payment_status
            FROM prescriptions 
            WHERE id = ?
        """, (prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            print(f"   ❌ 处方 {prescription_id} 不存在")
            return False
        
        print(f"   ✅ 处方存在: ID={prescription['id']}, 状态={prescription['status']}, 支付状态={prescription['payment_status']}")
        
        # 2. 更新支付状态和处方状态
        print("\n2. 更新支付状态...")
        cursor.execute("""
            UPDATE prescriptions 
            SET payment_status = 'paid',
                status = 'pending_review',
                is_visible_to_patient = 1,
                visibility_unlock_time = datetime('now'),
                confirmed_at = datetime('now')
            WHERE id = ?
        """, (prescription_id,))
        
        print(f"   ✅ 更新了 {cursor.rowcount} 行")
        
        # 3. 插入支付日志
        print("\n3. 插入支付日志...")
        cursor.execute("""
            INSERT OR REPLACE INTO prescription_payment_logs (
                prescription_id, amount, payment_method, payment_time, status
            ) VALUES (?, ?, ?, datetime('now'), 'completed')
        """, (prescription_id, 88.0, 'alipay'))
        
        print(f"   ✅ 支付日志插入成功")
        
        # 4. 插入审核队列
        print("\n4. 插入审核队列...")
        doctor_id_str = str(prescription['doctor_id']) if prescription['doctor_id'] else '1'
        cursor.execute("""
            INSERT OR REPLACE INTO doctor_review_queue (
                prescription_id, doctor_id, consultation_id, 
                submitted_at, status, priority
            ) VALUES (?, ?, ?, datetime('now'), 'pending', 'normal')
        """, (prescription_id, doctor_id_str, prescription['consultation_id']))
        
        print(f"   ✅ 审核队列插入成功，医生ID: {doctor_id_str}")
        
        # 5. 验证最终状态
        print("\n5. 验证最终状态...")
        cursor.execute("SELECT * FROM prescriptions WHERE id = ?", (prescription_id,))
        final_prescription = cursor.fetchone()
        
        if final_prescription:
            print(f"   ✅ 处方状态: {final_prescription['status']}")
            print(f"   ✅ 支付状态: {final_prescription['payment_status']}")
            print(f"   ✅ 患者可见: {final_prescription['is_visible_to_patient']}")
        
        # 6. 检查审核队列
        print("\n6. 检查审核队列...")
        cursor.execute("""
            SELECT * FROM doctor_review_queue 
            WHERE prescription_id = ? AND doctor_id = ?
        """, (prescription_id, doctor_id_str))
        
        queue_entry = cursor.fetchone()
        if queue_entry:
            print(f"   ✅ 队列状态: {queue_entry['status']}")
            print(f"   ✅ 提交时间: {queue_entry['submitted_at']}")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = test_simple_database_operations()
    if success:
        print("\n🎉 数据库操作测试成功！")
    else:
        print("\n❌ 数据库操作测试失败！")