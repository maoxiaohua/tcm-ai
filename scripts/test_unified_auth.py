#!/usr/bin/env python3
"""
统一认证系统测试工具
验证认证系统统一后的功能正常性
"""

import requests
import json
import sqlite3
from typing import Dict, List

def test_database_integrity():
    """测试数据库完整性"""
    print("🔍 测试数据库完整性")
    print("-" * 30)
    
    conn = sqlite3.connect("/home/ute/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    # 检查是否还有admin_accounts表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_accounts'")
    admin_table_exists = cursor.fetchone() is not None
    
    if admin_table_exists:
        print("❌ admin_accounts表仍然存在")
        return False
    else:
        print("✅ admin_accounts表已成功删除")
    
    # 检查users表结构
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    required_fields = ['role', 'is_active', 'updated_at']
    missing_fields = [field for field in required_fields if field not in columns]
    
    if missing_fields:
        print(f"❌ 缺少必需字段: {missing_fields}")
        return False
    else:
        print("✅ users表结构完整")
    
    # 检查用户数据
    cursor.execute("SELECT COUNT(*) FROM users WHERE password_hash IS NOT NULL")
    auth_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT role, COUNT(*) FROM users WHERE role IS NOT NULL GROUP BY role")
    role_distribution = cursor.fetchall()
    
    print(f"✅ 认证用户总数: {auth_users}")
    print("✅ 角色分布:")
    for role, count in role_distribution:
        print(f"   - {role}: {count} 个")
    
    conn.close()
    return True

def test_auth_api(username: str, password: str, expected_role: str = None):
    """测试认证API"""
    print(f"\n🔐 测试用户认证: {username}")
    print("-" * 30)
    
    try:
        # 测试登录
        response = requests.post("http://localhost:8000/api/auth/login", 
                               json={"username": username, "password": password},
                               timeout=10)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                user_info = data.get("user", {})
                print(f"✅ 登录成功")
                print(f"   用户ID: {user_info.get('user_id', 'N/A')}")
                print(f"   角色: {user_info.get('role', 'N/A')}")
                print(f"   用户名: {user_info.get('username', 'N/A')}")
                
                if expected_role and user_info.get('role') != expected_role:
                    print(f"❌ 角色不匹配，期望: {expected_role}, 实际: {user_info.get('role')}")
                    return False
                
                # 测试获取用户信息
                token = data.get("token")
                if token:
                    profile_response = requests.get("http://localhost:8000/api/auth/profile",
                                                  headers={"Authorization": f"Bearer {token}"},
                                                  timeout=10)
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        if profile_data.get("success"):
                            print("✅ 用户信息获取成功")
                            return True
                        else:
                            print(f"❌ 用户信息获取失败: {profile_data.get('message')}")
                    else:
                        print(f"❌ 用户信息API响应错误: {profile_response.status_code}")
                        
                return True
            else:
                print(f"❌ 登录失败: {data.get('message', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   错误详情: {error_data}")
            except:
                print(f"   响应内容: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def get_test_users():
    """获取测试用户列表"""
    conn = sqlite3.connect("/home/ute/tcm-ai/data/user_history.sqlite")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT username, role 
        FROM users 
        WHERE password_hash IS NOT NULL 
        AND username IS NOT NULL 
        AND username != ''
        LIMIT 5
    """)
    
    users = cursor.fetchall()
    conn.close()
    
    return users

def main():
    """主函数"""
    print("🚀 TCM-AI 统一认证系统测试")
    print("=" * 50)
    
    # 1. 测试数据库完整性
    if not test_database_integrity():
        print("❌ 数据库完整性测试失败，停止测试")
        return
    
    print(f"\n{'='*50}")
    print("📡 测试认证API")
    
    # 2. 获取测试用户
    test_users = get_test_users()
    
    if not test_users:
        print("❌ 没有找到可测试的用户")
        return
    
    print(f"找到 {len(test_users)} 个测试用户")
    
    # 3. 测试已知用户（使用通用密码）
    test_cases = [
        ("admin", "123456", "admin"),
        ("maoxiaohua", "123456", "patient"),
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for username, password, expected_role in test_cases:
        if test_auth_api(username, password, expected_role):
            success_count += 1
    
    # 4. 总结
    print(f"\n{'='*50}")
    print("📊 测试结果总结")
    print(f"成功: {success_count}/{total_tests}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！统一认证系统工作正常")
    else:
        print("⚠️ 部分测试失败，请检查系统状态")
        print("\n🔧 故障排查建议:")
        print("1. 检查服务器是否已重启以加载新代码")
        print("2. 验证用户密码哈希是否正确")
        print("3. 检查数据库表结构是否完整")

if __name__ == "__main__":
    main()