#!/usr/bin/env python3
"""
直接测试API调用，查看详细日志
"""

import requests
import json

def test_with_debug():
    """测试API并获取详细信息"""
    
    test_data = {
        "disease_name": "腰痛", 
        "thinking_process": "患者腰痛，肾阳虚证。右归丸加减：熟地黄20g，肉桂6g，附子10g。温补肾阳。",
        "complexity_level": "simple",
        "ai_mode": True
    }
    
    print("📤 发送API请求...")
    response = requests.post(
        "http://localhost:8000/api/generate_visual_decision_tree",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    result = response.json()
    
    print("📥 完整API响应:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 查看服务器日志的最后几行
    print("\n📋 检查服务器日志...")
    import subprocess
    try:
        logs = subprocess.run(['tail', '-20', 'server_new.log'], capture_output=True, text=True)
        if logs.stdout:
            print("服务器日志:")
            print(logs.stdout)
    except Exception as e:
        print(f"无法读取日志: {e}")

if __name__ == "__main__":
    test_with_debug()