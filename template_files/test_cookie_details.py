#!/usr/bin/env python3
"""
详细对比Cookie发送方式
"""

import requests

def detailed_cookie_test():
    """详细测试Cookie发送"""
    base_url = "http://localhost:8000"
    
    # 登录获取session_token
    session = requests.Session()
    login_response = session.post(f"{base_url}/api/auth/login", 
                                 json={"username": "doctor", "password": "doctor123"})
    
    session_token = None
    for cookie in session.cookies:
        if cookie.name == 'session_token':
            session_token = cookie.value
            break
    
    if not session_token:
        print("无法获取session_token")
        return
    
    print(f"Session Token: {session_token[:20]}...")
    
    # 测试1: 使用requests.Session (自动Cookie管理)
    print("\n🔸 测试1: requests.Session自动Cookie管理")
    print(f"   Session cookies: {session.cookies}")
    
    # 打印实际发送的头信息
    from requests_toolbelt.utils import dump
    
    resp1 = session.get(f"{base_url}/doctor", allow_redirects=False)
    print(f"   状态码: {resp1.status_code}")
    
    # 测试2: 手动设置Cookie头
    print("\n🔸 测试2: 手动Cookie头")
    headers = {"Cookie": f"session_token={session_token}"}
    resp2 = requests.get(f"{base_url}/doctor", headers=headers, allow_redirects=False)
    print(f"   状态码: {resp2.status_code}")
    
    # 测试3: 新的session with explicit cookie
    print("\n🔸 测试3: 显式设置Cookie到新session")
    new_session = requests.Session()
    new_session.cookies.set('session_token', session_token, domain='localhost', path='/')
    resp3 = new_session.get(f"{base_url}/doctor", allow_redirects=False)
    print(f"   状态码: {resp3.status_code}")
    
    # 检查服务器日志中的认证信息
    print(f"\n📋 如果手动Cookie成功但Session失败，可能是:")
    print("   1. Session发送的Cookie域名或路径不匹配")
    print("   2. 其他HTTP头信息的差异")
    print("   3. requests库的Cookie处理bug")

if __name__ == "__main__":
    detailed_cookie_test()