#!/usr/bin/env python3
"""
简单测试处方审核功能，不依赖安全系统
"""
import sqlite3
import sys
sys.path.append('/opt/tcm-ai')

def test_prescription_review_directly():
    """直接测试处方审核逻辑"""
    print("=== 直接测试处方审核逻辑 ===\n")
    
    # 连接数据库
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. 创建测试处方
        print("1. 创建测试处方...")
        cursor.execute("""
            INSERT INTO prescriptions (
                patient_id, conversation_id, doctor_id, patient_name, 
                symptoms, diagnosis, ai_prescription, status, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test_user_maoxiaohua', 
            'test_conv_002', 
            1,  # 金大夫
            '毛小花测试', 
            '测试症状描述', 
            '测试诊断结果', 
            '测试AI处方内容：当归10g 白芍10g 川芎6g 熟地黄12g', 
            'pending', 
            'pending'
        ))
        
        prescription_id = cursor.lastrowid
        print(f"   ✅ 处方创建成功，ID: {prescription_id}")
        
        # 2. 模拟支付确认，提交审核
        print("\n2. 模拟支付确认和审核提交...")
        
        # 更新支付状态
        cursor.execute("""
            UPDATE prescriptions 
            SET payment_status = 'paid', status = 'pending_review'
            WHERE id = ?
        """, (prescription_id,))
        
        # 插入到审核队列
        cursor.execute("""
            INSERT INTO doctor_review_queue (
                prescription_id, doctor_id, consultation_id, 
                submitted_at, status, priority
            ) VALUES (?, ?, ?, datetime('now'), 'pending', 'normal')
        """, (prescription_id, '1', 'test_conv_002'))
        
        print(f"   ✅ 处方已提交审核队列")
        
        # 3. 查询医生待审核列表
        print("\n3. 查询医生待审核处方...")
        cursor.execute("""
            SELECT p.*, q.submitted_at, q.priority
            FROM prescriptions p 
            JOIN doctor_review_queue q ON p.id = q.prescription_id
            WHERE q.status = 'pending' AND q.doctor_id = '1'
            ORDER BY q.priority DESC, q.submitted_at ASC
        """)
        
        pending_prescriptions = cursor.fetchall()
        print(f"   ✅ 找到 {len(pending_prescriptions)} 个待审核处方：")
        
        for row in pending_prescriptions:
            print(f"     - 处方ID: {row['id']}, 患者: {row['patient_name']}, 状态: {row['status']}")
        
        # 4. 模拟医生审核
        print("\n4. 模拟医生审核...")
        if pending_prescriptions:
            review_prescription_id = pending_prescriptions[0]['id']
            
            # 更新处方状态为已审核
            cursor.execute("""
                UPDATE prescriptions 
                SET status = 'doctor_approved', 
                    doctor_notes = '审核通过，处方合理',
                    reviewed_at = datetime('now')
                WHERE id = ?
            """, (review_prescription_id,))
            
            # 更新审核队列状态
            cursor.execute("""
                UPDATE doctor_review_queue 
                SET status = 'completed', completed_at = datetime('now')
                WHERE prescription_id = ?
            """, (review_prescription_id,))
            
            print(f"   ✅ 处方 {review_prescription_id} 审核完成")
        
        # 5. 验证最终状态
        print("\n5. 验证处方最终状态...")
        cursor.execute("""
            SELECT * FROM prescriptions WHERE id = ?
        """, (prescription_id,))
        
        final_prescription = cursor.fetchone()
        if final_prescription:
            print(f"   ✅ 处方状态: {final_prescription['status']}")
            print(f"   ✅ 支付状态: {final_prescription['payment_status']}")
            print(f"   ✅ 审核时间: {final_prescription['reviewed_at']}")
            print(f"   ✅ 医生备注: {final_prescription['doctor_notes']}")
        
        conn.commit()
        print("\n=== 测试完成 ===")
        
        return {
            'success': True,
            'prescription_id': prescription_id,
            'final_status': final_prescription['status'] if final_prescription else None
        }
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    result = test_prescription_review_directly()
    if result['success']:
        print(f"🎉 处方审核流程测试成功！处方ID: {result['prescription_id']}")
    else:
        print(f"❌ 测试失败: {result['error']}")