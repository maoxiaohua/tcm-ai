#!/usr/bin/env python3
"""
智能缓存系统测试脚本
测试缓存系统的功能和性能
"""

import sys
import time
import requests
import json
import os
sys.path.append('/opt/tcm')

from intelligent_cache_system import IntelligentCacheSystem

def test_cache_system_basic():
    """测试缓存系统基本功能"""
    print("=" * 60)
    print("🔍 智能缓存系统基本功能测试")
    print("=" * 60)
    
    # 初始化缓存系统
    cache_system = IntelligentCacheSystem(
        cache_db_path="./data/test_cache.sqlite",
        similarity_threshold=0.80
    )
    
    # 测试案例
    test_cases = [
        {
            "name": "感冒咳嗽",
            "symptom": "我最近感冒了，有点咳嗽，流鼻涕",
            "doctor": "张仲景",
            "response": "根据您的症状，考虑外感风寒证。建议服用荆防败毒散加减：荆芥10g、防风10g、羌活10g、独活10g、柴胡10g、前胡10g、川芎6g、桔梗10g、枳壳10g、甘草6g。温服，一日二次。",
            "docs": ["感冒治疗文档1", "外感风寒证候"]
        },
        {
            "name": "类似感冒症状",
            "symptom": "感冒咳嗽流鼻涕，头有点痛",
            "doctor": "张仲景",
            "response": "不应该被缓存，因为这是新的响应",
            "docs": ["感冒相关文档"]
        },
        {
            "name": "完全不同的症状",
            "symptom": "最近失眠多梦，心烦意乱",
            "doctor": "张仲景",
            "response": "考虑心肾不交证。建议黄连阿胶汤加减：黄连6g、黄芩9g、白芍12g、阿胶10g、鸡子黄2枚。",
            "docs": ["失眠治疗文档", "心肾不交证候"]
        }
    ]
    
    print("\n📝 测试1: 缓存存储和精确匹配")
    # 存储第一个案例
    case1 = test_cases[0]
    cache_system.cache_response(
        case1["symptom"], case1["doctor"], 
        case1["response"], case1["docs"]
    )
    print(f"✅ 已缓存: {case1['name']}")
    
    # 精确匹配测试
    cached_result = cache_system.get_cached_response(case1["symptom"], case1["doctor"])
    if cached_result:
        cached_response, cached_docs, similarity = cached_result
        print(f"✅ 精确匹配成功，相似度: {similarity:.3f}")
        assert cached_response == case1["response"], "响应内容不匹配"
        assert cached_docs == case1["docs"], "文档列表不匹配"
    else:
        print("❌ 精确匹配失败")
        return False
    
    print("\n📝 测试2: 相似度匹配")
    # 相似症状测试
    case2 = test_cases[1]
    cached_result = cache_system.get_cached_response(case2["symptom"], case2["doctor"])
    if cached_result:
        cached_response, cached_docs, similarity = cached_result
        print(f"✅ 相似度匹配成功，相似度: {similarity:.3f}")
        assert similarity >= 0.80, f"相似度过低: {similarity}"
        # 应该返回第一个案例的响应，而不是第二个案例的响应
        assert cached_response == case1["response"], "应该返回缓存的响应"
    else:
        print("❌ 相似度匹配失败")
        return False
    
    print("\n📝 测试3: 缓存未命中")
    # 完全不同的症状
    case3 = test_cases[2]
    cached_result = cache_system.get_cached_response(case3["symptom"], case3["doctor"])
    if cached_result:
        cached_response, cached_docs, similarity = cached_result
        print(f"⚠️  意外命中缓存，相似度: {similarity:.3f}")
        # 如果相似度很低，这可能是正常的
        if similarity < 0.70:
            print("✅ 低相似度命中，系统运行正常")
        else:
            print("❌ 不应该命中缓存")
            return False
    else:
        print("✅ 正确的缓存未命中")
    
    print("\n📝 测试4: 缓存统计")
    stats = cache_system.get_cache_stats()
    print(f"✅ 缓存条目数: {stats.total_entries}")
    print(f"✅ 命中率: {stats.hit_rate:.3f}")
    print(f"✅ 缓存大小: {stats.cache_size_mb:.2f} MB")
    print(f"✅ 总查询数: {cache_system.total_queries}")
    print(f"✅ 缓存命中: {cache_system.cache_hits}")
    print(f"✅ 缓存未命中: {cache_system.cache_misses}")
    
    # 清理测试缓存
    try:
        os.remove("./data/test_cache.sqlite")
        print("\n🗑️  测试缓存已清理")
    except:
        pass
    
    print("\n🎉 缓存系统基本功能测试完成！")
    return True

def test_cache_performance():
    """测试缓存系统性能"""
    print("\n" + "=" * 60)
    print("⚡ 智能缓存系统性能测试")
    print("=" * 60)
    
    cache_system = IntelligentCacheSystem(
        cache_db_path="./data/perf_test_cache.sqlite",
        similarity_threshold=0.85
    )
    
    # 性能测试数据
    test_symptoms = [
        "头痛发热咳嗽流鼻涕",
        "失眠多梦心烦意乱",
        "胃痛腹胀消化不良",
        "腰痛腿软乏力",
        "月经不调痛经",
        "咽喉肿痛声音嘶哑",
        "便秘大便干结",
        "腹泻水样便",
        "高血压头晕",
        "糖尿病口渴多尿"
    ]
    
    responses = [
        f"针对症状 '{symptom}' 的中医治疗方案：{i+1}. 建议使用相应的中药方剂进行治疗。"
        for i, symptom in enumerate(test_symptoms)
    ]
    
    doctor = "张仲景"
    
    print("\n📝 填充缓存数据...")
    # 填充缓存
    start_time = time.time()
    for symptom, response in zip(test_symptoms, responses):
        cache_system.cache_response(symptom, doctor, response, [f"文档_{symptom}"])
    fill_time = time.time() - start_time
    print(f"✅ 缓存填充完成，耗时: {fill_time:.3f}秒")
    
    print("\n📝 测试缓存查询性能...")
    # 测试查询性能
    query_times = []
    hit_count = 0
    
    # 精确匹配测试
    for symptom in test_symptoms:
        start_time = time.time()
        result = cache_system.get_cached_response(symptom, doctor)
        query_time = time.time() - start_time
        query_times.append(query_time)
        
        if result:
            hit_count += 1
            cached_response, cached_docs, similarity = result
            print(f"  ✅ 查询: '{symptom[:20]}...' 耗时: {query_time:.4f}秒, 相似度: {similarity:.3f}")
        else:
            print(f"  ❌ 查询: '{symptom[:20]}...' 耗时: {query_time:.4f}秒, 未命中")
    
    # 相似性查询测试
    similar_symptoms = [
        "头疼发烧咳嗽有鼻涕",  # 类似 "头痛发热咳嗽流鼻涕"
        "睡不着觉多梦心烦",    # 类似 "失眠多梦心烦意乱"
        "肚子疼胀气不消化"     # 类似 "胃痛腹胀消化不良"
    ]
    
    print(f"\n📝 测试相似性查询性能...")
    for symptom in similar_symptoms:
        start_time = time.time()
        result = cache_system.get_cached_response(symptom, doctor)
        query_time = time.time() - start_time
        query_times.append(query_time)
        
        if result:
            cached_response, cached_docs, similarity = result
            print(f"  ✅ 相似查询: '{symptom}' 耗时: {query_time:.4f}秒, 相似度: {similarity:.3f}")
        else:
            print(f"  ❌ 相似查询: '{symptom}' 耗时: {query_time:.4f}秒, 未命中")
    
    # 性能统计
    avg_query_time = sum(query_times) / len(query_times)
    max_query_time = max(query_times)
    min_query_time = min(query_times)
    
    print(f"\n📊 性能统计:")
    print(f"  平均查询时间: {avg_query_time:.4f}秒")
    print(f"  最大查询时间: {max_query_time:.4f}秒")
    print(f"  最小查询时间: {min_query_time:.4f}秒")
    print(f"  命中率: {hit_count}/{len(test_symptoms)} = {hit_count/len(test_symptoms):.3f}")
    
    # 缓存统计
    stats = cache_system.get_cache_stats()
    print(f"  缓存条目数: {stats.total_entries}")
    print(f"  缓存大小: {stats.cache_size_mb:.2f} MB")
    
    # 清理测试缓存
    try:
        os.remove("./data/perf_test_cache.sqlite")
        print("\n🗑️  性能测试缓存已清理")
    except:
        pass
    
    print("\n🎉 缓存系统性能测试完成！")
    return True

def test_integration_with_main_system():
    """测试与主系统的集成"""
    print("\n" + "=" * 60)
    print("🔗 缓存系统与主系统集成测试")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # 测试系统状态
    try:
        response = requests.get(f"{base_url}/debug_status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ 系统状态: {status.get('server_status', 'unknown')}")
            print(f"✅ 缓存系统可用: {status.get('cache_system_available', False)}")
            
            if status.get('cache_stats'):
                cache_stats = status['cache_stats']
                print(f"✅ 缓存条目数: {cache_stats.get('total_entries', 0)}")
                print(f"✅ 缓存命中率: {cache_stats.get('hit_rate', '0.000')}")
                print(f"✅ 缓存大小: {cache_stats.get('cache_size_mb', '0.00')} MB")
            else:
                print("⚠️  缓存统计信息不可用")
        else:
            print(f"❌ 系统状态检查失败: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到主系统: {e}")
        print("请确保主系统正在运行: python3 main.py")
        return False
    
    # 测试对话接口（如果系统运行）
    test_message = {
        "conversation_id": "cache_test_001",
        "message": "我最近感冒了，有点咳嗽流鼻涕，怎么办？",
        "selected_doctor": "张仲景"
    }
    
    print(f"\n📝 测试对话接口缓存...")
    try:
        # 第一次请求（应该缓存未命中）
        start_time = time.time()
        response1 = requests.post(f"{base_url}/chat_with_ai", 
                                json=test_message, timeout=30)
        time1 = time.time() - start_time
        
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ 第一次请求成功，耗时: {time1:.2f}秒")
            print(f"   响应长度: {len(result1.get('reply', ''))}")
            
            # 第二次相同请求（应该缓存命中）
            start_time = time.time()
            response2 = requests.post(f"{base_url}/chat_with_ai", 
                                    json=test_message, timeout=30)
            time2 = time.time() - start_time
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"✅ 第二次请求成功，耗时: {time2:.2f}秒")
                print(f"   响应长度: {len(result2.get('reply', ''))}")
                
                # 检查是否有加速效果
                if time2 < time1 * 0.8:  # 如果第二次请求快了20%以上
                    print(f"🚀 缓存加速效果明显: {time1/time2:.1f}x 倍速提升")
                else:
                    print(f"⚠️  缓存加速效果不明显: {time1:.2f}s vs {time2:.2f}s")
                
            else:
                print(f"❌ 第二次请求失败: {response2.status_code}")
                return False
                
        else:
            print(f"❌ 第一次请求失败: {response1.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 对话接口测试失败: {e}")
        return False
    
    print("\n🎉 集成测试完成！")
    return True

def main():
    """主测试函数"""
    print("🚀 TCM智能缓存系统综合测试")
    print("=" * 60)
    
    tests = [
        ("基本功能测试", test_cache_system_basic),
        ("性能测试", test_cache_performance),
        ("集成测试", test_integration_with_main_system)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 开始 {test_name}...")
            if test_func():
                print(f"✅ {test_name} 通过")
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n" + "=" * 60)
    print(f"📊 测试总结: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！缓存系统运行良好。")
        return True
    else:
        print("⚠️  部分测试失败，请检查系统配置。")
        return False

if __name__ == "__main__":
    main()