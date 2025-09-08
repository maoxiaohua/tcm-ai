#!/usr/bin/env python3
"""
对比API调用和直接调用的差异
"""

import sys
sys.path.insert(0, '/opt/tcm-ai')

from services.famous_doctor_learning_system import FamousDoctorLearningSystem
import requests
import json
import asyncio

async def compare_api_vs_direct():
    """对比API调用和直接调用"""
    
    # 测试参数
    test_params = {
        "disease_name": "腰痛",
        "thinking_process": "患者腰痛，肾阳虚证。右归丸加减：熟地黄20g，肉桂6g，附子10g。温补肾阳。",
        "use_ai": True,
        "include_tcm_analysis": True,
        "complexity_level": "standard"
    }
    
    print("🔍 对比API调用 vs 直接调用")
    print("="*50)
    
    # 1. 直接调用
    print("1️⃣ 直接调用 FamousDoctorLearningSystem:")
    system = FamousDoctorLearningSystem()
    
    try:
        direct_result = await system.generate_decision_paths(
            disease_name=test_params["disease_name"],
            thinking_process=test_params["thinking_process"],
            use_ai=test_params["use_ai"],
            include_tcm_analysis=test_params["include_tcm_analysis"],
            complexity_level=test_params["complexity_level"]
        )
        
        print(f"✅ 直接调用成功")
        print(f"   source: {direct_result.get('source')}")
        print(f"   ai_generated: {direct_result.get('ai_generated')}")
        print(f"   paths数量: {len(direct_result.get('paths', []))}")
        
        if direct_result.get('paths'):
            first_path = direct_result['paths'][0]
            print(f"   第一个路径标题: {first_path.get('title', 'N/A')}")
            print(f"   步骤数: {len(first_path.get('steps', []))}")
            
            # 检查内容是否包含医生思路
            path_content = json.dumps(first_path, ensure_ascii=False)
            keywords = ['肾阳虚', '右归丸', '熟地黄', '肉桂', '附子']
            found = [k for k in keywords if k in path_content]
            print(f"   包含的医生思路: {found}")
            
    except Exception as e:
        print(f"❌ 直接调用失败: {e}")
    
    print("\n" + "-"*50)
    
    # 2. API调用
    print("2️⃣ API调用:")
    try:
        response = requests.post(
            "http://localhost:8000/api/generate_visual_decision_tree",
            json=test_params,
            headers={"Content-Type": "application/json"}
        )
        
        api_result = response.json()
        
        print(f"✅ API调用成功")
        print(f"   success: {api_result.get('success')}")
        print(f"   message: {api_result.get('message')}")
        
        data = api_result.get('data', {})
        print(f"   source: {data.get('source')}")
        print(f"   ai_generated: {data.get('ai_generated')}")
        print(f"   paths数量: {len(data.get('paths', []))}")
        
        if data.get('paths'):
            first_path = data['paths'][0]
            print(f"   第一个路径标题: {first_path.get('title', 'N/A')}")
            print(f"   步骤数: {len(first_path.get('steps', []))}")
            
            # 检查内容是否包含医生思路
            path_content = json.dumps(first_path, ensure_ascii=False)
            keywords = ['肾阳虚', '右归丸', '熟地黄', '肉桂', '附子']
            found = [k for k in keywords if k in path_content]
            print(f"   包含的医生思路: {found}")
            
    except Exception as e:
        print(f"❌ API调用失败: {e}")
    
    print("\n🎯 结论:")
    print("如果直接调用成功但API调用失败，说明问题在API路由层面")

if __name__ == "__main__":
    asyncio.run(compare_api_vs_direct())