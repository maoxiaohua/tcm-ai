#!/usr/bin/env python3
"""
测试完整的医生登录流程修复
"""

import requests
import time

def test_complete_doctor_login_flow():
    """测试完整的医生登录流程"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试完整医生登录流程...")
    
    # 创建session以保持cookies
    session = requests.Session()
    
    # 1. 登录API测试
    print("\n1️⃣ 测试登录API...")
    login_data = {"username": "doctor", "password": "doctor123"}
    
    try:
        login_response = session.post(f"{base_url}/api/auth/login", json=login_data)
        
        print(f"   登录状态码: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            print(f"   登录成功: {login_result.get('success')}")
            print(f"   重定向URL: {login_result.get('redirect_url')}")
            print(f"   用户角色: {login_result.get('user', {}).get('role')}")
            print(f"   Token字段: {'存在' if login_result.get('token') else '不存在'}")
            
            # 检查Cookies
            session_cookie = None
            for cookie in session.cookies:
                if cookie.name == 'session_token':
                    session_cookie = cookie.value
                    break
            
            print(f"   Session Cookie: {'存在' if session_cookie else '不存在'}")
            if session_cookie:
                print(f"   Cookie值: {session_cookie[:20]}...")
            
            # 2. 测试医生门户访问
            print("\n2️⃣ 测试医生门户访问...")
            doctor_response = session.get(f"{base_url}/doctor", allow_redirects=False)
            
            print(f"   门户状态码: {doctor_response.status_code}")
            
            if doctor_response.status_code == 302:
                print(f"   重定向到: {doctor_response.headers.get('Location')}")
                print("   ❌ 仍然重定向到登录页面")
            elif doctor_response.status_code == 200:
                print("   ✅ 成功访问医生门户")
                print(f"   页面大小: {len(doctor_response.content)} 字节")
            
            # 3. 测试使用session token的API调用
            print("\n3️⃣ 测试API权限...")
            if session_cookie:
                headers = {"Authorization": f"Bearer {session_cookie}"}
                profile_response = session.get(f"{base_url}/api/auth/profile", headers=headers)
                
                print(f"   Profile API状态码: {profile_response.status_code}")
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    print(f"   用户权限: {profile_data.get('user', {}).get('permissions', [])}")
                
        else:
            print(f"   登录失败: {login_response.text}")
    
    except Exception as e:
        print(f"   测试失败: {e}")

def main():
    print("=" * 70)
    print("🏥 TCM-AI 医生登录流程完整测试")
    print("=" * 70)
    
    test_complete_doctor_login_flow()
    
    print("\n" + "=" * 70)
    print("📋 解决方案总结:")
    print("1. 识别问题: 登录API使用Cookie认证，前端期望Token认证")
    print("2. 解决方案: 修改登录页面从Cookie中读取session_token")
    print("3. 保存到localStorage: 前端可以正常访问医生门户")
    print("=" * 70)

if __name__ == "__main__":
    main()