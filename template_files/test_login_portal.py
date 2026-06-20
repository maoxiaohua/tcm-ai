#!/usr/bin/env python3
"""
测试登录门户功能
验证统一认证API和页面跳转
"""
import requests
import json
import time

def test_auth_api():
    """测试统一认证API"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试统一认证API...")
    
    # 测试医生登录
    print("\n1. 测试医生登录...")
    doctor_login = {
        "username": "doctor",
        "password": "doctor123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=doctor_login)
        print(f"医生登录响应: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 登录成功: {data.get('message')}")
            print(f"  👤 用户角色: {data.get('user', {}).get('role')}")
            print(f"  🔗 跳转URL: {data.get('redirect_url')}")
        else:
            print(f"  ❌ 登录失败: {response.text}")
    except Exception as e:
        print(f"  ❌ 医生登录测试失败: {e}")
    
    # 测试管理员登录
    print("\n2. 测试管理员登录...")
    admin_login = {
        "username": "admin", 
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
        print(f"管理员登录响应: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 登录成功: {data.get('message')}")
            print(f"  👤 用户角色: {data.get('user', {}).get('role')}")
            print(f"  🔗 跳转URL: {data.get('redirect_url')}")
        else:
            print(f"  ❌ 登录失败: {response.text}")
    except Exception as e:
        print(f"  ❌ 管理员登录测试失败: {e}")
    
    # 测试患者登录
    print("\n3. 测试患者登录...")
    patient_login = {
        "username": "patient",
        "password": "patient123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=patient_login)
        print(f"患者登录响应: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 登录成功: {data.get('message')}")
            print(f"  👤 用户角色: {data.get('user', {}).get('role')}")
            print(f"  🔗 跳转URL: {data.get('redirect_url')}")
        else:
            print(f"  ❌ 登录失败: {response.text}")
    except Exception as e:
        print(f"  ❌ 患者登录测试失败: {e}")
    
    # 测试错误凭据
    print("\n4. 测试错误凭据...")
    wrong_login = {
        "username": "wrong",
        "password": "wrong"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=wrong_login)
        print(f"错误凭据响应: {response.status_code}")
        if response.status_code == 401:
            print(f"  ✅ 正确拒绝错误凭据")
        else:
            print(f"  ❌ 应该返回401，实际返回: {response.status_code}")
    except Exception as e:
        print(f"  ❌ 错误凭据测试失败: {e}")

def test_page_routes():
    """测试页面路由"""
    base_url = "http://localhost:8000"
    
    print("\n🌐 测试页面路由...")
    
    routes_to_test = [
        ("/login", "登录门户"),
        ("/patient", "患者端"),
        ("/doctor", "医生端"), 
        ("/admin", "管理端"),
        ("/", "主页")
    ]
    
    for route, name in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", timeout=10)
            if response.status_code == 200:
                print(f"  ✅ {name} ({route}): 正常访问")
            else:
                print(f"  ❌ {name} ({route}): 状态码 {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name} ({route}): 访问失败 - {e}")

def main():
    """主测试函数"""
    print("🧪 开始测试登录门户系统...\n")
    
    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:8000/debug_status", timeout=5)
        if response.status_code != 200:
            print("❌ 服务未运行，请先启动API服务")
            return
        print("✅ API服务正在运行\n")
    except:
        print("❌ 无法连接到API服务，请确认服务已启动")
        return
    
    # 运行测试
    test_auth_api()
    test_page_routes()
    
    print("\n🎉 登录门户测试完成！")

if __name__ == "__main__":
    main()