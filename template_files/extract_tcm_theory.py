#!/usr/bin/env python3
"""
提取完整的tcm_theory内容
"""

import requests
import json
import re

def extract_full_tcm_theory():
    """提取完整的中医理论内容"""
    
    test_data = {
        "disease_name": "腰痛", 
        "thinking_process": "患者腰痛，肾阳虚证。右归丸加减：熟地黄20g，肉桂6g，附子10g。温补肾阳。",
        "complexity_level": "simple",
        "ai_mode": True
    }
    
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    result = response.json()
    
    paths = result.get('data', {}).get('paths', [])
    if paths:
        tcm_theory = paths[0].get('tcm_theory', '')
        
        print("="*80)
        print("完整的 tcm_theory 内容:")
        print("="*80)
        print(tcm_theory)
        print("="*80)
        
        # 尝试从中提取JSON
        json_matches = re.findall(r'```json\s*(.*?)\s*```', tcm_theory, re.DOTALL | re.IGNORECASE)
        
        if json_matches:
            json_content = json_matches[0].strip()
            print("\n提取的JSON内容:")
            print(json_content)
            
            try:
                ai_result = json.loads(json_content)
                print("\n✅ JSON解析成功！")
                
                # 检查是否包含用户输入的关键信息
                ai_paths = ai_result.get("paths", [])
                if ai_paths:
                    ai_path = ai_paths[0]
                    print(f"AI路径标题: {ai_path.get('title', 'N/A')}")
                    
                    steps = ai_path.get('steps', [])
                    for i, step in enumerate(steps):
                        print(f"步骤{i+1}: {step.get('content', 'N/A')}")
                    
                    # 检查关键词
                    full_content = json.dumps(ai_result, ensure_ascii=False)
                    keywords_found = []
                    test_keywords = ['右归丸', '熟地黄', '肉桂', '附子', '肾阳虚', '温补肾阳']
                    
                    for keyword in test_keywords:
                        if keyword in full_content:
                            keywords_found.append(keyword)
                    
                    print(f"\n🔍 在AI JSON中找到的关键词: {keywords_found}")
                    
                    if len(keywords_found) >= 4:
                        print("✅ AI JSON包含了用户的具体处方信息！")
                        print("🔧 问题在于：系统没有使用这个正确的AI JSON，而是用了通用模板")
                    else:
                        print("❌ AI JSON未包含足够的用户输入信息")
                        
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
        else:
            print("❌ 未找到JSON代码块")

if __name__ == "__main__":
    extract_full_tcm_theory()