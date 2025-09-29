#!/usr/bin/env python3
"""
测试处方审核流程
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_payment_confirm():
    """测试支付确认和审核提交"""
    url = f"{BASE_URL}/api/prescription-review/payment-confirm"
    
    data = {
        "prescription_id": 101,  # 使用我们创建的测试处方ID
        "payment_amount": 80.00,
        "payment_method": "alipay"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"支付确认API响应状态: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"支付确认API调用失败: {e}")
        return None

def test_doctor_queue():
    """测试医生审核队列"""
    url = f"{BASE_URL}/api/prescription-review/doctor-queue/1"  # 金大夫ID为1
    
    try:
        response = requests.get(url)
        print(f"\n医生队列API响应状态: {response.status_code}")
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result
    except Exception as e:
        print(f"医生队列API调用失败: {e}")
        return None

def test_prescription_status():
    """测试处方状态查询"""
    url = f"{BASE_URL}/api/prescription-review/status/101"
    
    try:
        response = requests.get(url)
        print(f"\n处方状态API响应状态: {response.status_code}")
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result
    except Exception as e:
        print(f"处方状态API调用失败: {e}")
        return None

if __name__ == "__main__":
    print("=== 测试处方审核流程 ===\n")
    
    print("1. 测试支付确认和审核提交...")
    payment_result = test_payment_confirm()
    
    print("\n2. 测试医生审核队列...")
    queue_result = test_doctor_queue()
    
    print("\n3. 测试处方状态查询...")
    status_result = test_prescription_status()
    
    print("\n=== 测试完成 ===")