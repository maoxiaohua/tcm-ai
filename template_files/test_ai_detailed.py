#!/usr/bin/env python3
"""
详细AI测试 - 查看完整响应内容
"""

import requests
import json
import time

def test_ai_detailed_response():
    """获取AI的完整响应内容"""
    test_data = {
        "disease_name": "腰痛", 
        "thinking_process": "患者腰痛，辨证为肾阳虚证。肾阳虚则温煦无力，腰府失养而痛。治法：温补肾阳，强腰止痛。方药：右归丸加减。熟地黄20g补肾填精，山药15g健脾补肾，山茱萸12g补肝肾，枸杞子15g滋补肝肾，鹿角胶10g（烊化）温补肾阳，菟丝子15g补肾固精，杜仲15g补肾强腰，当归12g补血活血，肉桂6g温肾助阳，附子10g（先煎）回阳救逆。",
        "complexity_level": "intermediate",
        "ai_mode": True
    }
    
    print("发送请求...")
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    result = response.json()
    
    # 打印完整的tcm_theory内容
    paths = result.get('data', {}).get('paths', [])
    if paths:
        tcm_theory = paths[0].get('tcm_theory', '')
        print("="*60)
        print("AI生成的中医理论内容:")
        print("="*60)
        print(tcm_theory)
        print("="*60)
        
        # 检查具体药物
        herbs = ['右归丸', '熟地黄', '山药', '山茱萸', '枸杞子', '鹿角胶', '菟丝子', '杜仲', '当归', '肉桂', '附子']
        found_herbs = []
        for herb in herbs:
            if herb in tcm_theory:
                found_herbs.append(herb)
        
        print(f"\n找到的药物: {found_herbs}")
        print(f"药物覆盖率: {len(found_herbs)}/{len(herbs)} = {len(found_herbs)/len(herbs)*100:.1f}%")

if __name__ == "__main__":
    test_ai_detailed_response()