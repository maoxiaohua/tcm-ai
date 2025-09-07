#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试doctor portal页面中的链接是否可访问
"""

import requests
import re

def test_portal_links():
    """测试portal页面中的所有链接"""
    base_url = "http://localhost:8000"
    
    print("测试Doctor Portal链接可访问性")
    print("=" * 50)
    
    # 测试主portal页面
    try:
        response = requests.get(f"{base_url}/doctor/portal", timeout=5)
        print(f"✅ Portal主页: {response.status_code}")
        portal_content = response.text
    except Exception as e:
        print(f"❌ Portal主页访问失败: {e}")
        return
    
    # 提取页面中的链接
    links = re.findall(r'href="([^"]*)"', portal_content)
    
    print(f"\n发现 {len(links)} 个链接:")
    print("-" * 30)
    
    for link in links:
        if link.startswith('/'):
            test_url = f"{base_url}{link}"
        elif link.startswith('http'):
            test_url = link
        else:
            continue
            
        try:
            response = requests.get(test_url, timeout=5)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {link} -> {response.status_code}")
        except Exception as e:
            print(f"❌ {link} -> 连接错误: {e}")
    
    # 测试具体的doctor相关端点
    print(f"\n测试Doctor相关端点:")
    print("-" * 30)
    
    doctor_endpoints = [
        "/doctor/portal",
        "/doctor_portal", 
        "/static/doctor_thinking_input.html",
        "/static/doctor_management.html",
        "/static/doctor_thinking_style.css",
        "/doctor_portal_info"
    ]
    
    for endpoint in doctor_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {endpoint} -> {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} -> 连接错误: {e}")

if __name__ == "__main__":
    test_portal_links()