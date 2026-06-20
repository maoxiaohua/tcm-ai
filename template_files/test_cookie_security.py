#!/usr/bin/env python3
"""
测试Cookie设置和HTTP vs HTTPS的问题
"""

import requests
from urllib.parse import urlparse

def test_cookie_security():
    """测试Cookie安全设置"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试Cookie安全设置问题...")
    
    session = requests.Session()
    
    # 登录并查看Cookie设置
    print("\n1️⃣ 登录并检查Cookie设置...")
    response = session.post(f"{base_url}/api/auth/login", 
                           json={"username": "doctor", "password": "doctor123"})
    
    print(f"登录状态: {response.status_code}")
    
    # 检查Set-Cookie响应头
    set_cookie_header = response.headers.get('Set-Cookie')
    print(f"Set-Cookie头: {set_cookie_header}")
    
    if set_cookie_header and 'Secure' in set_cookie_header:
        print("⚠️  发现问题: Cookie设置了Secure标志！")
        print("   在HTTP环境下，浏览器不会发送Secure Cookie")
        print("   这就是为什么PC端浏览器访问失败的原因")
        
        # 分析Cookie属性
        cookie_parts = set_cookie_header.split(';')
        cookie_attributes = {}
        for part in cookie_parts:
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookie_attributes[key] = value
            else:
                cookie_attributes[part] = True
        
        print(f"Cookie属性: {cookie_attributes}")
        
        return True
    else:
        print("✅ Cookie没有Secure标志，应该可以在HTTP下工作")
        return False

def main():
    has_secure_flag = test_cookie_security()
    
    print("\n" + "="*60)
    if has_secure_flag:
        print("🎯 解决方案:")
        print("1. 移除Cookie的Secure标志（开发环境）")
        print("2. 或者配置HTTPS（生产环境推荐）")
        print("3. 或者修改中间件在开发环境下不检查认证")
    else:
        print("需要进一步调试Cookie传输问题...")
    print("="*60)

if __name__ == "__main__":
    main()