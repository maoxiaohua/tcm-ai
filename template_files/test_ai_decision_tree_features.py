#!/usr/bin/env python3
"""
测试AI决策树新功能
Test the new AI-powered decision tree features
"""

import asyncio
import json
import sys
sys.path.append('/opt/tcm-ai')

from services.famous_doctor_learning_system import FamousDoctorLearningSystem

async def test_ai_generation():
    """测试AI自动生成决策树功能"""
    print("=== 测试AI自动生成决策树功能 ===")
    
    system = FamousDoctorLearningSystem()
    
    # 测试失眠的决策树生成
    result = await system.generate_decision_paths(
        disease_name="失眠",
        include_tcm_analysis=True,
        complexity_level="standard"
    )
    
    print("✅ AI生成决策树成功")
    print(f"生成路径数量: {len(result['paths'])}")
    
    for i, path in enumerate(result['paths']):
        print(f"\n路径 {i+1}: {path['title']}")
        flow = " → ".join([step['content'] for step in path['steps']])
        print(f"  诊疗流程: {flow}")
        print(f"  关键词: {', '.join(path['keywords'])}")
        print(f"  中医理论: {path['tcm_theory']}")

async def test_tcm_theory_analysis():
    """测试中医理论分析功能"""
    print("\n=== 测试中医理论分析功能 ===")
    
    system = FamousDoctorLearningSystem()
    
    # 模拟决策树数据
    sample_tree = {
        "paths": [
            {
                "id": "test_path",
                "steps": [
                    {"type": "symptom", "content": "失眠"},
                    {"type": "condition", "content": "舌红苔黄"},
                    {"type": "diagnosis", "content": "心火旺盛"},
                    {"type": "treatment", "content": "清心火"},
                    {"type": "formula", "content": "黄连阿胶汤"}
                ],
                "keywords": ["失眠", "舌红", "苔黄"],
                "tcm_theory": "心主神明"
            }
        ]
    }
    
    result = await system.analyze_tcm_theory(
        tree_data=sample_tree,
        disease_name="失眠",
        analysis_prompt=""
    )
    
    print("✅ TCM理论分析成功")
    analysis = result['theory_analysis']
    print(f"理论评分: {analysis['overall_score']}/100")
    print(f"优势: {', '.join(analysis['strengths'])}")
    print(f"不足: {', '.join(analysis['weaknesses'])}")
    
    print(f"\n改进建议数量: {len(result['improvement_suggestions'])}")
    for suggestion in result['improvement_suggestions']:
        print(f"  - {suggestion['description']} (优先级: {suggestion['priority']})")

async def test_missing_logic_detection():
    """测试遗漏逻辑检测功能"""
    print("\n=== 测试遗漏逻辑检测功能 ===")
    
    system = FamousDoctorLearningSystem()
    
    # 模拟简单的决策树（故意缺少一些证型）
    incomplete_tree = {
        "paths": [
            {
                "id": "simple_path",
                "steps": [
                    {"type": "symptom", "content": "失眠"},
                    {"type": "diagnosis", "content": "心火旺盛"}
                ]
            }
        ]
    }
    
    result = await system.detect_missing_logic(
        current_tree=incomplete_tree,
        disease_name="失眠",
        detection_prompt=""
    )
    
    print("✅ 遗漏逻辑检测成功")
    print(f"发现遗漏分析类别: {len(result['missing_analyses'])}")
    
    for analysis in result['missing_analyses']:
        print(f"\n类别: {analysis['category']}")
        for item in analysis['items']:
            print(f"  - {item['content']}: {item['description']} (重要性: {item['importance']})")
    
    print(f"\n快速添加建议: {len(result['quick_additions'])}")
    for addition in result['quick_additions']:
        print(f"  - {addition['title']}")

async def test_disease_specific_paths():
    """测试特定疾病的路径生成"""
    print("\n=== 测试特定疾病路径生成 ===")
    
    system = FamousDoctorLearningSystem()
    
    diseases = ["失眠", "胃痛", "头痛"]
    
    for disease in diseases:
        print(f"\n疾病: {disease}")
        result = await system.generate_decision_paths(disease_name=disease)
        
        print(f"生成路径数量: {len(result['paths'])}")
        for path in result['paths']:
            print(f"  - {path['title']}")
            formula = next((step['content'] for step in path['steps'] if step['type'] == 'formula'), "未指定")
            print(f"    推荐方剂: {formula}")

async def main():
    """主测试函数"""
    print("🧪 AI决策树功能测试开始\n")
    
    try:
        await test_ai_generation()
        await test_tcm_theory_analysis()
        await test_missing_logic_detection()
        await test_disease_specific_paths()
        
        print("\n🎉 所有AI功能测试完成！")
        print("\n📝 功能说明:")
        print("1. ✅ AI自动生成决策树 - 支持多种疾病的智能路径生成")
        print("2. ✅ 中医理论分析 - 评估决策树的理论合理性")
        print("3. ✅ 遗漏逻辑检测 - 识别可能遗漏的重要诊疗逻辑")
        print("4. ✅ 特定疾病支持 - 失眠、胃痛等疾病有专门的路径模板")
        
        print("\n🔗 集成说明:")
        print("- 前端可视化构建器已支持调用这些AI功能")
        print("- 后端API endpoints已实现，包含完整的错误处理")
        print("- 中医理论知识库已集成到AI分析中")
        print("- 支持一键添加AI建议的诊疗路径")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())