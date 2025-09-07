#!/usr/bin/env python3
"""
测试中间件Cookie认证
"""

import requests

def test_middleware_cookie_auth():
    """测试中间件Cookie认证"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试中间件Cookie认证...")
    
    # 创建session
    session = requests.Session()
    
    # 1. 登录获取Cookie
    print("\n1️⃣ 登录获取Cookie...")
    login_response = session.post(f"{base_url}/api/auth/login", 
                                 json={"username": "doctor", "password": "doctor123"})
    
    if login_response.status_code == 200:
        print(f"   登录成功，Cookie: {session.cookies}")
        
        # 提取session_token
        session_token = None
        for cookie in session.cookies:
            if cookie.name == 'session_token':
                session_token = cookie.value
                break
        
        if session_token:
            print(f"   Session Token: {session_token[:20]}...")
            
            # 2. 测试直接访问/doctor（通过中间件）
            print("\n2️⃣ 通过中间件访问/doctor...")
            doctor_response = session.get(f"{base_url}/doctor", allow_redirects=False)
            print(f"   状态码: {doctor_response.status_code}")
            print(f"   Headers: {dict(doctor_response.headers)}")
            
            # 3. 手动设置Cookie头测试
            print("\n3️⃣ 手动设置Cookie测试...")
            headers = {"Cookie": f"session_token={session_token}"}
            manual_response = requests.get(f"{base_url}/doctor", headers=headers, allow_redirects=False)
            print(f"   状态码: {manual_response.status_code}")
            print(f"   重定向: {manual_response.headers.get('Location', '无')}")
            
            # 4. 测试API端点 (不通过中间件)
            print("\n4️⃣ 直接API调用测试...")
            api_headers = {"Authorization": f"Bearer {session_token}"}
            api_response = requests.get(f"{base_url}/api/auth/profile", headers=api_headers)
            print(f"   API状态码: {api_response.status_code}")
            if api_response.status_code == 200:
                print(f"   用户信息: {api_response.json()}")

def main():
    test_middleware_cookie_auth()

if __name__ == "__main__":
    main()