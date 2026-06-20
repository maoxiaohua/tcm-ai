#!/usr/bin/env python3
"""
舌象脉象幻觉修复验证测试
用于测试修复后的医疗安全检查和清理机制
"""

import sys
import os
sys.path.append('/opt/tcm')

from main import check_medical_safety, sanitize_ai_response

def test_hallucination_detection():
    """测试幻觉检测功能"""
    print("=" * 60)
    print("🔍 舌象脉象幻觉检测测试")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "用户反馈的问题案例",
            "patient_message": "小孩子，嗓子干，有点咳嗽",
            "ai_response": """### 一、辨证要点
- 舌象：舌边尖红，苔薄白或薄黄
- 脉象：脉浮数
- 症状：咽干、微咳、口渴、无发热或低热""",
            "should_detect": True
        },
        {
            "name": "正常症状描述（无幻觉）",
            "patient_message": "小孩子，嗓子干，有点咳嗽",
            "ai_response": """根据患者描述的嗓子干、咳嗽症状，考虑是外感风热。
建议清热润燥，可用银翘散加减。""",
            "should_detect": False
        },
        {
            "name": "其他格式的舌象编造",
            "patient_message": "头痛",
            "ai_response": """观察舌苔薄白，舌质淡红，脉象细弱，属于气血不足。""",
            "should_detect": True
        },
        {
            "name": "XML格式的望诊编造",
            "patient_message": "失眠",
            "ai_response": """<望诊所见>舌质红，苔薄黄，脉数</望诊所见>
属于心火亢盛。""",
            "should_detect": True
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n📋 测试案例 {i}: {case['name']}")
        print(f"患者输入: {case['patient_message']}")
        print(f"AI回复: {case['ai_response']}")
        
        is_safe, error_msg = check_medical_safety(
            case['ai_response'], 
            False, 
            '', 
            False, 
            case['patient_message']
        )
        
        detected = not is_safe
        expected = case['should_detect']
        
        if detected == expected:
            result = "✅ 通过"
        else:
            result = "❌ 失败"
        
        print(f"预期检测: {'是' if expected else '否'}")
        print(f"实际检测: {'是' if detected else '否'}")
        print(f"检测结果: {result}")
        
        if detected:
            print(f"错误信息: {error_msg}")

def test_hallucination_sanitization():
    """测试幻觉内容清理功能"""
    print("\n" + "=" * 60)
    print("🧹 舌象脉象幻觉清理测试")
    print("=" * 60)
    
    test_response = """### 一、辨证要点

- 舌象：舌边尖红，苔薄白或薄黄
- 脉象：脉浮数
- 症状：咽干、微咳、口渴、无发热或低热
- 病因：外感风热，肺热郁蒸，津液受损

### 二、治疗方案

根据患者舌边尖红、苔薄白的表现，脉浮数，考虑为外感风热证。

### 三、处方建议

银翘散加减：
- 金银花 15g
- 连翘 12g
- 薄荷 6g"""

    patient_message = "小孩子，嗓子干，有点咳嗽"
    
    print("🔍 原始AI回复:")
    print(test_response)
    print("\n" + "-" * 40)
    
    cleaned_response = sanitize_ai_response(
        test_response, 
        False, 
        '', 
        False, 
        patient_message
    )
    
    print("🧹 清理后的回复:")
    print(cleaned_response)
    print("\n" + "-" * 40)
    
    # 验证清理效果
    problematic_patterns = [
        "舌边尖红",
        "苔薄白或薄黄", 
        "脉浮数",
        "舌象：舌边尖红",
        "脉象：脉浮数"
    ]
    
    print("🔍 清理效果验证:")
    for pattern in problematic_patterns:
        if pattern in cleaned_response:
            print(f"❌ 仍包含: {pattern}")
        else:
            print(f"✅ 已清理: {pattern}")
    
    # 验证安全声明是否添加
    if "【重要医疗声明】" in cleaned_response:
        print("✅ 已添加医疗安全声明")
    else:
        print("❌ 未添加医疗安全声明")

def test_edge_cases():
    """测试边缘情况"""
    print("\n" + "=" * 60)
    print("⚠️  边缘情况测试")
    print("=" * 60)
    
    # 测试患者自己描述舌象的情况
    print("\n📋 测试: 患者自己描述舌象")
    patient_with_tongue = "我舌苔白厚，舌边有齿痕"
    ai_response_with_patient_tongue = "根据您描述的舌苔白厚、舌边齿痕，属于脾虚湿盛。"
    
    is_safe, error_msg = check_medical_safety(
        ai_response_with_patient_tongue,
        False,
        patient_with_tongue,
        False,
        patient_with_tongue
    )
    
    print(f"患者输入: {patient_with_tongue}")
    print(f"AI回复: {ai_response_with_patient_tongue}")
    print(f"安全检查: {'✅ 通过' if is_safe else '❌ 失败'}")
    if not is_safe:
        print(f"错误信息: {error_msg}")

if __name__ == "__main__":
    print("🛡️ 舌象脉象幻觉修复验证测试")
    print("测试目标: 验证AI不再编造患者未描述的舌象脉象信息")
    
    try:
        test_hallucination_detection()
        test_hallucination_sanitization() 
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()