#!/usr/bin/env python3
"""
测试登录流程的调试版本
"""

import requests
import json

def test_login_with_curl():
    """使用curl测试登录"""
    print("🧪 使用curl测试登录...")
    
    import subprocess
    
    curl_cmd = [
        'curl', '-X', 'POST',
        'http://localhost:8000/api/auth/login',
        '-H', 'Content-Type: application/json',
        '-d', '{"username": "doctor", "password": "doctor123"}',
        '-v'
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"Curl test failed: {e}")

def test_login_debug():
    """调试版本的登录测试"""
    base_url = "http://localhost:8000"
    
    print("🔍 调试登录API...")
    
    login_data = {
        "username": "doctor",
        "password": "doctor123"
    }
    
    # 使用requests.Session来保持cookies
    session = requests.Session()
    
    try:
        response = session.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"Cookies: {session.cookies}")
        print(f"原始响应: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"解析后数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 检查各个字段
            print(f"\n字段检查:")
            print(f"- success: {data.get('success')}")
            print(f"- message: {data.get('message')}")
            print(f"- user: {data.get('user')}")
            print(f"- redirect_url: {data.get('redirect_url')}")
            print(f"- token: {data.get('token')}")
            
            if 'token' in data and data['token']:
                print(f"✅ Token存在: {data['token']}")
            else:
                print("❌ Token缺失")
        
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_login_debug()
    print("\n" + "="*50)
    test_login_with_curl()