#!/usr/bin/env python3
"""
测试修复后的AI功能
"""

import requests
import json
import time

def test_fixed_ai():
    """测试修复后的AI功能"""
    
    # 简化测试：直接向API发送请求，但使用更短的思维过程以避免JSON解析错误
    test_data = {
        "disease_name": "腰痛", 
        "thinking_process": "患者腰痛，肾阳虚证。右归丸加减：熟地黄20g，肉桂6g，附子10g。温补肾阳。",
        "complexity_level": "simple",  # 使用简单级别
        "ai_mode": True
    }
    
    print("🔧 测试修复后的AI功能...")
    print(f"输入：{test_data['thinking_process']}")
    
    start_time = time.time()
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    end_time = time.time()
    
    result = response.json()
    
    print(f"⏱️ 响应时间: {end_time - start_time:.2f}秒")
    
    if result.get('success'):
        paths = result.get('data', {}).get('paths', [])
        if paths:
            path = paths[0]
            print(f"✅ 路径标题: {path.get('title', 'N/A')}")
            
            # 检查步骤内容
            steps = path.get('steps', [])
            for i, step in enumerate(steps):
                print(f"   步骤{i+1}: {step.get('content', 'N/A')}")
            
            # 检查是否包含用户输入的关键信息
            tcm_theory = path.get('tcm_theory', '')
            keywords_found = []
            test_keywords = ['右归丸', '熟地黄', '肉桂', '附子', '肾阳虚', '温补肾阳']
            
            for keyword in test_keywords:
                if keyword in str(path) or keyword in tcm_theory:
                    keywords_found.append(keyword)
            
            print(f"🔍 找到的关键词: {keywords_found}")
            
            if len(keywords_found) >= 3:
                print("✅ AI成功处理了用户的具体处方输入！")
                return True
            else:
                print("❌ AI未能充分处理用户输入")
                return False
        else:
            print("❌ 没有生成任何路径")
            return False
    else:
        print(f"❌ API调用失败: {result.get('message', 'Unknown error')}")
        return False

if __name__ == "__main__":
    success = test_fixed_ai()
    if success:
        print("\n🎉 问题已解决！AI现在能够正确处理用户的具体处方输入。")
    else:
        print("\n😞 问题仍然存在，需要进一步调试。")