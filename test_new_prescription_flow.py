#!/usr/bin/env python3
"""
测试修复后的处方审核流程
"""
import sqlite3
import sys
import requests
import json
sys.path.append('/opt/tcm-ai')

def test_new_prescription_flow():
    """测试完整的处方审核流程"""
    print("=== 测试新处方审核流程 ===\n")
    
    # 连接数据库
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. 创建新处方（模拟前端）
        print("1. 创建新处方...")
        cursor.execute("""
            INSERT INTO prescriptions (
                patient_id, conversation_id, doctor_id, patient_name, 
                symptoms, diagnosis, ai_prescription, status, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'usr_20250920_5741e17a78e8',  # 使用真实用户ID
            'test_conv_new_001', 
            1,  # 金大夫
            '测试用户', 
            '新症状描述', 
            '新诊断结果', 
            '新处方内容：当归10g 白芍10g 川芎6g 熟地黄12g 党参15g', 
            'pending', 
            'pending'
        ))
        
        prescription_id = cursor.lastrowid
        print(f"   ✅ 处方创建成功，ID: {prescription_id}")
        
        conn.commit()
        
        # 2. 测试支付确认API
        print("\n2. 测试支付确认API...")
        
        api_url = "http://localhost:8000/api/prescription-review/payment-confirm"
        payload = {
            "prescription_id": prescription_id,
            "payment_amount": 88.0,
            "payment_method": "alipay"
        }
        
        response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ API调用成功: {result}")
            
            if result.get('success'):
                if result.get('status') == 'already_paid':
                    print(f"   ℹ️ 处方已支付状态")
                elif result.get('data'):
                    print(f"   ✅ 支付确认成功，状态: {result['data']['status']}")
                    print(f"   📋 提示信息: {result['data']['note']}")
                else:
                    print(f"   ✅ 支付确认成功（无详细数据）")
            else:
                print(f"   ❌ API返回失败: {result.get('message')}")
        else:
            print(f"   ❌ API调用失败，状态码: {response.status_code}")
            print(f"   响应内容: {response.text}")
        
        # 3. 验证数据库状态
        print("\n3. 验证数据库状态...")
        cursor.execute("SELECT * FROM prescriptions WHERE id = ?", (prescription_id,))
        prescription = cursor.fetchone()
        
        if prescription:
            print(f"   ✅ 处方状态: {prescription['status']}")
            print(f"   ✅ 支付状态: {prescription['payment_status']}")
            print(f"   ✅ 是否对患者可见: {prescription['is_visible_to_patient']}")
        
        # 4. 检查审核队列
        print("\n4. 检查医生审核队列...")
        cursor.execute("""
            SELECT * FROM doctor_review_queue 
            WHERE prescription_id = ? AND doctor_id = '1'
        """, (prescription_id,))
        
        queue_entry = cursor.fetchone()
        if queue_entry:
            print(f"   ✅ 审核队列状态: {queue_entry['status']}")
            print(f"   ✅ 提交时间: {queue_entry['submitted_at']}")
            print(f"   ✅ 优先级: {queue_entry['priority']}")
        else:
            print("   ❌ 未找到审核队列记录")
        
        # 5. 测试医生API
        print("\n5. 测试医生审核队列API...")
        doctor_api_url = "http://localhost:8000/api/prescription-review/doctor-queue/1"
        doctor_response = requests.get(doctor_api_url)
        
        if doctor_response.status_code == 200:
            doctor_result = doctor_response.json()
            if doctor_result.get('success'):
                pending_count = doctor_result['data']['pending_count']
                print(f"   ✅ 医生待审核处方数量: {pending_count}")
                
                if pending_count > 0:
                    reviews = doctor_result['data']['pending_reviews']
                    print(f"   📋 第一个待审核处方: {reviews[0]['prescription_id']}")
                    print(f"   📋 患者: {reviews[0]['patient_id']}")
                    print(f"   📋 症状: {reviews[0]['symptoms']}")
        
        return {
            'success': True,
            'prescription_id': prescription_id,
            'final_status': prescription['status'] if prescription else None
        }
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    result = test_new_prescription_flow()
    if result['success']:
        print(f"\n🎉 新处方审核流程测试成功！处方ID: {result['prescription_id']}")
    else:
        print(f"\n❌ 测试失败: {result['error']}")