#!/usr/bin/env python3
"""
测试决策树V3版本的功能
"""

import requests
import json

# 测试服务器地址
BASE_URL = "http://localhost:8000"

def test_generate_paths():
    """测试AI生成路径功能"""
    print("=== 测试AI生成路径功能 ===")
    
    test_data = {
        "disease_name": "失眠",
        "thinking_process": "对于失眠患者，我首先会询问失眠的类型。如果是心火旺盛，舌红苔黄，脉数，我会考虑黄连阿胶汤。如果是心脾两虚，面色萎黄，舌淡脉弱，则用归脾汤。"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/generate_paths_from_thinking",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功")
            print(f"生成路径数量: {len(result.get('data', {}).get('paths', []))}")
            
            for i, path in enumerate(result.get('data', {}).get('paths', [])):
                print(f"\n路径 {i+1}:")
                flow = " → ".join([step.get('content', '') for step in path.get('steps', [])])
                print(f"  流程: {flow}")
                print(f"  关键词: {', '.join(path.get('keywords', []))}")
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_symptom_matching():
    """测试症状匹配功能"""
    print("\n=== 测试症状匹配功能 ===")
    
    test_symptoms = ["失眠", "多梦", "心烦", "舌红", "苔黄"]
    
    test_data = {
        "symptoms": test_symptoms,
        "disease_context": "失眠"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/match_symptoms_to_paths",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 症状匹配成功")
            print(f"输入症状: {', '.join(test_symptoms)}")
            
            if result.get('data', {}).get('matched_path'):
                matched_path = result['data']['matched_path']
                formula = result['data'].get('recommended_formula')
                confidence = result['data'].get('match_confidence', 0) * 100
                
                print(f"匹配路径: {matched_path.get('id')}")
                print(f"推荐方剂: {formula}")
                print(f"匹配置信度: {confidence:.1f}%")
                print(f"匹配关键词: {', '.join(result['data'].get('matched_keywords', []))}")
            else:
                print("⚠️ 未找到高度匹配的路径")
                print(f"建议: {result.get('data', {}).get('suggestion', '无')}")
        else:
            print(f"❌ 症状匹配失败: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_save_paths():
    """测试保存决策树功能"""
    print("\n=== 测试保存决策树功能 ===")
    
    test_paths = [
        {
            "id": "test_path_1",
            "steps": [
                {"type": "symptom", "content": "失眠"},
                {"type": "condition", "content": "舌红苔黄", "result": True},
                {"type": "diagnosis", "content": "心火旺盛"},
                {"type": "treatment", "content": "清心火"},
                {"type": "formula", "content": "黄连阿胶汤"}
            ],
            "keywords": ["失眠", "多梦", "心烦", "口干", "舌红", "苔黄"],
            "created_by": "测试医生"
        }
    ]
    
    test_data = {
        "disease_name": "失眠",
        "paths": test_paths,
        "integration_enabled": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/save_decision_tree_v3",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 决策树保存成功")
            print(f"保存ID: {result.get('data', {}).get('saved_id')}")
            print(f"路径数量: {result.get('data', {}).get('paths_count')}")
        else:
            print(f"❌ 保存失败: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    print("🧪 决策树V3功能测试\n")
    
    # 检查服务器状态
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ 服务器运行正常\n")
        else:
            print("⚠️ 服务器可能有问题\n")
    except:
        print("❌ 无法连接到服务器，请确保API服务正在运行\n")
        print("启动命令: python api/main.py\n")
    
    # 运行测试
    test_generate_paths()
    test_symptom_matching()
    test_save_paths()
    
    print("\n🎉 测试完成！")
    print("\n📝 使用说明:")
    print("1. 访问 http://localhost:8000/static/decision_tree_v3.html 创建决策树")
    print("2. 访问 http://localhost:8000/static/decision_tree_integration_demo.html 测试集成效果")
    print("3. 在问诊系统中，症状将自动匹配决策路径推荐方剂")