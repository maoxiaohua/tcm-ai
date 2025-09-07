#!/usr/bin/env python3
"""
测试医生登录重定向循环问题
"""

import requests
import json
import time

def test_login_flow():
    """测试完整的登录流程"""
    base_url = "http://localhost:8000"
    
    print("🧪 测试医生登录流程...")
    
    # 1. 测试登录页面访问
    print("\n1️⃣ 测试登录页面访问...")
    try:
        response = requests.get(f"{base_url}/login", allow_redirects=False)
        print(f"   登录页面状态码: {response.status_code}")
        
        if response.status_code == 301 or response.status_code == 302:
            print(f"   重定向到: {response.headers.get('Location', '未知')}")
        
    except Exception as e:
        print(f"   登录页面访问失败: {e}")
    
    # 2. 测试登录API
    print("\n2️⃣ 测试医生登录API...")
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
        
        print(f"   登录API状态码: {response.status_code}")
        print(f"   响应内容: {response.text[:500]}")
        
        if response.status_code == 200:
            login_result = response.json()
            print(f"   登录成功: {login_result.get('success')}")
            print(f"   重定向URL: {login_result.get('redirect_url')}")
            print(f"   用户角色: {login_result.get('user', {}).get('role')}")
            print(f"   Token: {login_result.get('token', 'None')[:20] if login_result.get('token') else 'None'}...")
            
            return login_result.get('token'), login_result.get('redirect_url')
        
    except Exception as e:
        print(f"   登录API调用失败: {e}")
        return None, None
    
    return None, None

def test_doctor_portal_access(token=None):
    """测试医生门户访问"""
    base_url = "http://localhost:8000"
    
    print("\n3️⃣ 测试医生门户访问...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.get(f"{base_url}/doctor", headers=headers, allow_redirects=False)
        print(f"   医生门户状态码: {response.status_code}")
        
        if response.status_code == 301 or response.status_code == 302:
            print(f"   重定向到: {response.headers.get('Location', '未知')}")
        elif response.status_code == 200:
            print(f"   访问成功: 内容长度 {len(response.content)} 字节")
        
    except Exception as e:
        print(f"   医生门户访问失败: {e}")

def test_redirect_chain():
    """测试重定向链路"""
    base_url = "http://localhost:8000"
    
    print("\n4️⃣ 测试重定向链路...")
    
    # 创建session来跟踪cookies
    session = requests.Session()
    
    try:
        # 模拟从https://mxh0510.cn/login选择医生登录
        response = session.get(f"{base_url}/doctor", allow_redirects=True)
        
        print(f"   最终状态码: {response.status_code}")
        print(f"   最终URL: {response.url}")
        print(f"   重定向历史:")
        
        for i, resp in enumerate(response.history):
            print(f"     {i+1}. {resp.status_code} -> {resp.headers.get('Location', '未知')}")
        
        # 检查页面内容
        if "login" in response.text.lower():
            print("   ⚠️ 页面包含登录内容，可能存在重定向循环")
        
    except Exception as e:
        print(f"   重定向链路测试失败: {e}")

def main():
    print("=" * 60)
    print("🔍 TCM-AI 医生登录问题诊断")
    print("=" * 60)
    
    # 测试登录流程
    token, redirect_url = test_login_flow()
    
    # 测试门户访问
    test_doctor_portal_access(token)
    
    # 测试重定向链路
    test_redirect_chain()
    
    print("\n" + "=" * 60)
    print("📊 诊断报告:")
    print("1. 如果登录API返回正确的redirect_url但仍然重定向到登录页面，")
    print("   可能是前端JavaScript处理问题")
    print("2. 如果/doctor端点直接重定向到登录页面，")
    print("   可能是缺少认证检查或权限验证")
    print("3. 检查静态文件是否正确配置")
    print("=" * 60)

if __name__ == "__main__":
    main()