#!/usr/bin/env python3
"""
详细测试登录API响应
"""

import requests
import json

def test_detailed_login():
    """详细测试登录API"""
    base_url = "http://localhost:8000"
    
    print("🔍 详细测试登录API...")
    
    login_data = {
        "username": "doctor",
        "password": "doctor123"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"原始响应: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"解析后数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if 'token' in data:
                    print(f"Token 存在: {data['token']}")
                else:
                    print("⚠️ Token 不存在于响应中")
                
            except Exception as e:
                print(f"JSON解析失败: {e}")
        
    except Exception as e:
        print(f"请求失败: {e}")

def test_auth_verification():
    """测试认证验证"""
    base_url = "http://localhost:8000"
    
    # 先登录获取token
    login_data = {
        "username": "doctor", 
        "password": "doctor123"
    }
    
    try:
        login_response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        if login_response.status_code == 200:
            login_data = login_response.json()
            token = login_data.get('token')
            
            if token:
                print(f"\n✅ 获取到Token: {token[:20]}...")
                
                # 测试使用token访问
                headers = {"Authorization": f"Bearer {token}"}
                profile_response = requests.get(f"{base_url}/api/auth/profile", headers=headers)
                
                print(f"Profile API状态码: {profile_response.status_code}")
                print(f"Profile响应: {profile_response.text}")
            else:
                print("\n❌ 未获取到Token")
    
    except Exception as e:
        print(f"认证测试失败: {e}")

if __name__ == "__main__":
    test_detailed_login()
    test_auth_verification()