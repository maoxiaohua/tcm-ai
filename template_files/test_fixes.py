#!/usr/bin/env python3
"""
中医AI系统修复验证测试脚本
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# 测试配置
BASE_URL = "http://localhost:8000"  # 根据实际端口调整
ENDPOINTS = {
    "doctor_list": "/api/doctors/list",
    "admin_dashboard": "/api/admin/dashboard",
    "admin_users": "/api/admin/users",
    "admin_doctors": "/api/admin/doctors",
    "admin_prescriptions": "/api/admin/prescriptions",
    "admin_orders": "/api/admin/orders",
    "admin_system": "/api/admin/system",
    "admin_logs": "/api/admin/logs"
}

class TestResults:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def add_result(self, test_name, status, message="", response_data=None):
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.results.append(result)
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
        
        # 实时输出结果
        status_symbol = "✅" if status == "PASS" else "❌"
        print(f"{status_symbol} {test_name}: {message}")

async def test_endpoint(session, endpoint_name, url, expected_fields=None):
    """测试API端点"""
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                
                if data.get('success') == True:
                    # 检查期望的字段
                    if expected_fields:
                        missing_fields = []
                        for field in expected_fields:
                            if field not in data:
                                missing_fields.append(field)
                        
                        if missing_fields:
                            return f"FAIL", f"缺少字段: {missing_fields}", data
                    
                    return "PASS", f"API正常响应，返回数据: {len(str(data))}字符", data
                else:
                    return "FAIL", f"API响应success=False: {data.get('message', '未知错误')}", data
            else:
                return "FAIL", f"HTTP状态码: {response.status}", None
                
    except asyncio.TimeoutError:
        return "FAIL", "请求超时", None
    except Exception as e:
        return "FAIL", f"请求异常: {str(e)}", None

async def run_tests():
    """运行所有测试"""
    print("🚀 开始进行中医AI系统修复验证测试...")
    print("=" * 60)
    
    results = TestResults()
    
    async with aiohttp.ClientSession() as session:
        
        # 测试1: 医生列表API
        print("\n📋 测试医生列表API...")
        status, message, data = await test_endpoint(
            session, 
            "医生列表API", 
            f"{BASE_URL}{ENDPOINTS['doctor_list']}", 
            ['doctors', 'pagination']
        )
        results.add_result("医生列表API", status, message, data)
        
        # 测试2: 管理员仪表板API
        print("\n📊 测试管理员仪表板API...")
        status, message, data = await test_endpoint(
            session,
            "管理员仪表板API",
            f"{BASE_URL}{ENDPOINTS['admin_dashboard']}",
            ['stats']
        )
        results.add_result("管理员仪表板API", status, message, data)
        
        # 测试3: 管理员用户管理API
        print("\n👥 测试用户管理API...")
        status, message, data = await test_endpoint(
            session,
            "用户管理API",
            f"{BASE_URL}{ENDPOINTS['admin_users']}",
            ['users', 'pagination']
        )
        results.add_result("用户管理API", status, message, data)
        
        # 测试4: 管理员医生管理API
        print("\n👨‍⚕️ 测试医生管理API...")
        status, message, data = await test_endpoint(
            session,
            "医生管理API", 
            f"{BASE_URL}{ENDPOINTS['admin_doctors']}",
            ['doctors', 'pagination']
        )
        results.add_result("医生管理API", status, message, data)
        
        # 测试5: 管理员处方管理API
        print("\n📋 测试处方管理API...")
        status, message, data = await test_endpoint(
            session,
            "处方管理API",
            f"{BASE_URL}{ENDPOINTS['admin_prescriptions']}",
            ['prescriptions', 'pagination']
        )
        results.add_result("处方管理API", status, message, data)
        
        # 测试6: 管理员订单管理API
        print("\n🛒 测试订单管理API...")
        status, message, data = await test_endpoint(
            session,
            "订单管理API",
            f"{BASE_URL}{ENDPOINTS['admin_orders']}",
            ['orders', 'pagination']
        )
        results.add_result("订单管理API", status, message, data)
        
        # 测试7: 系统监控API
        print("\n⚙️ 测试系统监控API...")
        status, message, data = await test_endpoint(
            session,
            "系统监控API",
            f"{BASE_URL}{ENDPOINTS['admin_system']}",
            ['system']
        )
        results.add_result("系统监控API", status, message, data)
        
        # 测试8: 系统日志API
        print("\n📜 测试系统日志API...")
        status, message, data = await test_endpoint(
            session,
            "系统日志API",
            f"{BASE_URL}{ENDPOINTS['admin_logs']}",
            ['logs', 'pagination']
        )
        results.add_result("系统日志API", status, message, data)

    # 输出测试总结
    print("\n" + "=" * 60)
    print("🏁 测试完成！")
    print(f"✅ 通过: {results.passed}")
    print(f"❌ 失败: {results.failed}")
    print(f"📊 总计: {len(results.results)}")
    
    success_rate = (results.passed / len(results.results)) * 100 if results.results else 0
    print(f"🎯 成功率: {success_rate:.1f}%")
    
    if results.failed > 0:
        print("\n❌ 失败的测试:")
        for result in results.results:
            if result["status"] == "FAIL":
                print(f"   - {result['test']}: {result['message']}")
    
    # 保存详细测试结果
    with open('/opt/tcm-ai/template_files/test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results.results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细测试结果已保存到: /opt/tcm-ai/template_files/test_results.json")
    
    return results.passed == len(results.results)

def main():
    """主函数"""
    print("中医AI系统修复验证测试")
    print("Author: Claude Code Assistant")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        success = asyncio.run(run_tests())
        if success:
            print("\n🎉 所有测试通过！修复成功！")
            return 0
        else:
            print("\n⚠️  部分测试失败，请检查问题。")
            return 1
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        return 1

if __name__ == "__main__":
    exit(main())