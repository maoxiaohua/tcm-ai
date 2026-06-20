#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCM系统高并发压力测试工具
用于验证系统在比赛期间的高并发性能表现
"""

import asyncio
import aiohttp
import time
import json
from concurrent.futures import ThreadPoolExecutor
import requests
from datetime import datetime

# 测试配置
BASE_URL = "http://127.0.0.1:8000"
TEST_SCENARIOS = [
    {
        "name": "基础测试",
        "concurrent_users": 2,
        "total_requests": 4,
        "description": "验证基本功能"
    },
    {
        "name": "轻度并发测试",
        "concurrent_users": 5,
        "total_requests": 10,
        "description": "模拟正常使用场景"
    },
    {
        "name": "中度并发测试", 
        "concurrent_users": 10,
        "total_requests": 20,
        "description": "模拟评委同时测试"
    }
]

def test_basic_endpoints():
    """测试基础端点响应"""
    print("🔍 测试基础端点...")
    
    endpoints = [
        "/debug_status",
        "/static/index_v2.html",
        "/doctor/thinking-v2"
    ]
    
    results = {}
    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            response_time = time.time() - start_time
            
            results[endpoint] = {
                "status": response.status_code,
                "response_time": f"{response_time:.3f}s",
                "size": len(response.content)
            }
            
            status_icon = "✅" if response.status_code == 200 else "❌"
            print(f"  {status_icon} {endpoint}: {response.status_code} ({response_time:.3f}s)")
            
        except Exception as e:
            results[endpoint] = {"error": str(e)}
            print(f"  ❌ {endpoint}: {str(e)}")
    
    return results

async def send_chat_request(session, user_id, test_query="头痛，睡眠不好"):
    """发送聊天请求"""
    
    payload = {
        "message": test_query,
        "conversation_id": f"test_concurrent_{user_id}_{int(time.time())}",
        "selected_doctor": "zhang_zhongjing"
    }
    
    try:
        start_time = time.time()
        async with session.post(
            f"{BASE_URL}/chat_with_ai",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            response_time = time.time() - start_time
            
            if response.status == 200:
                data = await response.json()
                return {
                    "success": True,
                    "user_id": user_id,
                    "response_time": response_time,
                    "response_length": len(data.get("response", "")),
                    "has_cache_hit": "cache" in data.get("response", "").lower()
                }
            else:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": f"HTTP {response.status}",
                    "response_time": response_time
                }
                
    except asyncio.TimeoutError:
        return {
            "success": False,
            "user_id": user_id,
            "error": "Timeout",
            "response_time": 60.0
        }
    except Exception as e:
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e),
            "response_time": time.time() - start_time
        }

async def run_concurrent_test(concurrent_users, total_requests):
    """运行并发测试"""
    
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 创建任务列表
        tasks = []
        for i in range(total_requests):
            user_id = i % concurrent_users
            task = send_chat_request(session, user_id)
            tasks.append(task)
        
        # 分批执行，避免过多并发
        batch_size = concurrent_users
        results = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            print(f"  执行批次 {i//batch_size + 1}/{(len(tasks)-1)//batch_size + 1}...")
            
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
            
            # 短暂休息，避免压垮系统
            await asyncio.sleep(1)
    
    return results

def analyze_results(results, test_name):
    """分析测试结果"""
    
    print(f"\n📊 {test_name} - 结果分析:")
    
    successful = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
    exceptions = [r for r in results if not isinstance(r, dict)]
    
    total = len(results)
    success_rate = len(successful) / total * 100 if total > 0 else 0
    
    print(f"  📈 成功率: {success_rate:.1f}% ({len(successful)}/{total})")
    print(f"  ❌ 失败数: {len(failed)}")
    print(f"  💥 异常数: {len(exceptions)}")
    
    if successful:
        response_times = [r["response_time"] for r in successful]
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        print(f"  ⏱️  平均响应时间: {avg_time:.2f}s")
        print(f"  🚀 最快响应: {min_time:.2f}s")
        print(f"  🐌 最慢响应: {max_time:.2f}s")
        
        # 缓存命中分析
        cache_hits = len([r for r in successful if r.get("has_cache_hit")])
        cache_rate = cache_hits / len(successful) * 100
        print(f"  💾 缓存命中率: {cache_rate:.1f}%")
    
    if failed:
        error_types = {}
        for r in failed:
            error = r.get("error", "Unknown")
            error_types[error] = error_types.get(error, 0) + 1
        
        print(f"  🔍 错误类型:")
        for error, count in error_types.items():
            print(f"    - {error}: {count}次")
    
    # 性能评级
    if success_rate >= 95 and successful:
        avg_time = sum(r["response_time"] for r in successful) / len(successful)
        if avg_time <= 10:
            grade = "🏆 优秀"
        elif avg_time <= 20:
            grade = "👍 良好"
        else:
            grade = "⚠️ 需优化"
    else:
        grade = "❌ 需修复"
    
    print(f"  📝 性能评级: {grade}")
    
    return {
        "success_rate": success_rate,
        "total_requests": total,
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "avg_response_time": sum(r["response_time"] for r in successful) / len(successful) if successful else 0,
        "grade": grade
    }

def main():
    """主测试函数"""
    
    print("🏥 TCM系统高并发性能测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标地址: {BASE_URL}")
    print()
    
    # 1. 基础端点测试
    basic_results = test_basic_endpoints()
    print()
    
    # 2. 高并发测试
    all_results = {}
    
    for scenario in TEST_SCENARIOS:
        print(f"🚀 开始 {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   并发用户: {scenario['concurrent_users']}")
        print(f"   总请求数: {scenario['total_requests']}")
        
        try:
            start_time = time.time()
            results = asyncio.run(run_concurrent_test(
                scenario['concurrent_users'], 
                scenario['total_requests']
            ))
            total_time = time.time() - start_time
            
            analysis = analyze_results(results, scenario['name'])
            analysis['total_test_time'] = total_time
            analysis['qps'] = scenario['total_requests'] / total_time
            
            all_results[scenario['name']] = analysis
            
            print(f"  🕐 总测试时间: {total_time:.2f}s")
            print(f"  📊 平均QPS: {analysis['qps']:.2f} req/s")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {str(e)}")
            all_results[scenario['name']] = {"error": str(e)}
        
        print("-" * 40)
    
    # 3. 总结报告
    print("\n🎯 高并发测试总结报告")
    print("=" * 50)
    
    for test_name, result in all_results.items():
        if "error" not in result:
            print(f"{test_name}:")
            print(f"  成功率: {result['success_rate']:.1f}%")
            print(f"  平均响应时间: {result['avg_response_time']:.2f}s")
            print(f"  QPS: {result['qps']:.2f}")
            print(f"  评级: {result['grade']}")
        else:
            print(f"{test_name}: ❌ {result['error']}")
        print()
    
    # 4. 比赛准备建议
    print("📋 比赛准备建议:")
    
    high_test = all_results.get("高并发压力测试", {})
    if high_test.get("success_rate", 0) >= 90:
        print("  ✅ 系统高并发性能良好，可以应对比赛现场访问")
    else:
        print("  ⚠️ 建议优化高并发性能")
    
    if any(r.get("avg_response_time", 0) > 15 for r in all_results.values() if "error" not in r):
        print("  💡 建议启用更多缓存或增加服务器资源")
    
    print("  🔧 建议比赛前:")
    print("    - 重启服务清理内存")
    print("    - 预热缓存系统")
    print("    - 监控服务器资源使用")
    
    # 保存结果
    with open('/opt/tcm/concurrency_test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'basic_endpoints': basic_results,
            'concurrency_tests': all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细结果已保存到: /opt/tcm/concurrency_test_results.json")

if __name__ == "__main__":
    main()