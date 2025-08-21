#!/usr/bin/env python3
# test_symptom_fabrication_fix.py - 测试症状编造安全检查

import sys
sys.path.append('/opt/tcm')
from main import check_medical_safety, check_symptom_fabrication

def test_symptom_fabrication():
    """测试症状编造检查功能"""
    print("🔍 测试症状编造安全检查修复...")
    print("=" * 60)
    
    # 测试用例 1: 您报告的问题 - 从简单描述编造详细症状 (应该被阻止)
    patient_input_1 = "便秘，女孩，8岁，挑食，怎么调理下？"
    ai_response_1 = """
症状表现：
- 食欲不佳，挑食偏食；
- 大便干结，数日一行；
- 腹胀不舒，嗳气频频；
- 面色苍白，精神疲倦；
- 舌淡苔薄白，脉细弱。
"""
    
    result_1 = check_medical_safety(
        ai_response=ai_response_1,
        has_tongue_image=False,
        patient_described_tongue="",
        image_analysis_successful=False,
        original_patient_message=patient_input_1
    )
    print(f"测试1 - 您报告的症状编造问题:")
    print(f"  患者输入: {patient_input_1}")
    print(f"  AI编造内容: 大便干结数日一行、腹胀嗳气、面色苍白等")
    print(f"  结果: {'❌ 被阻止' if not result_1[0] else '⚠️ 未被阻止'}")
    print(f"  错误信息: {result_1[1]}")
    print()
    
    # 测试用例 2: 单独的symptoms检查功能验证
    fabrication_result = check_symptom_fabrication(ai_response_1, patient_input_1)
    print(f"测试2 - 症状编造检测功能:")
    print(f"  检测到的编造: {fabrication_result}")
    print(f"  状态: {'✅ 检测成功' if fabrication_result else '❌ 检测失败'}")
    print()
    
    # 测试用例 3: 合理的症状重述 (应该被允许)
    ai_response_3 = """
根据您描述的情况：
- 主诉：便秘
- 年龄：8岁女孩  
- 伴随情况：挑食
- 需要调理建议

建议从健脾开胃的角度进行调理...
"""
    result_3 = check_medical_safety(
        ai_response=ai_response_3,
        has_tongue_image=False,
        patient_described_tongue="",
        image_analysis_successful=False,
        original_patient_message=patient_input_1
    )
    print(f"测试3 - 合理的症状重述:")
    print(f"  结果: {'✅ 被允许' if result_3[0] else '❌ 被错误阻止'}")
    print()
    
    # 测试用例 4: 各种编造模式检测
    fabrication_patterns = [
        ("大便干结如栗", "便秘"),
        ("数日一行", "便秘"),
        ("腹胀嗳气", "挑食"),
        ("面色苍白", "女孩"),
        ("精神疲倦", "8岁"),
        ("食欲不佳", "挑食")
    ]
    
    print("测试4 - 各种编造模式检测:")
    all_detected = True
    
    for fabricated_desc, original_symptom in fabrication_patterns:
        test_response = f"患者症状表现为{fabricated_desc}，建议治疗。"
        fabrication = check_symptom_fabrication(test_response, f"{original_symptom}")
        detected = bool(fabrication)
        status = "✅ 检测到" if detected else "❌ 未检测"
        print(f"  '{fabricated_desc}' (原症状:'{original_symptom}'): {status}")
        if not detected:
            all_detected = False
    
    print()
    
    # 测试用例 5: XML格式中的症状编造
    xml_response = """
<诊疗方案>
    <主诉>便秘</主诉>
    <现病史>患儿便秘，大便干结如栗，数日一行，伴腹胀嗳气</现病史>
    <病机分析>脾胃虚弱</病机分析>
</诊疗方案>
"""
    result_5 = check_medical_safety(
        ai_response=xml_response,
        has_tongue_image=False,
        patient_described_tongue="",
        image_analysis_successful=False,
        original_patient_message=patient_input_1
    )
    print(f"测试5 - XML格式中的症状编造:")
    print(f"  结果: {'❌ 被阻止' if not result_5[0] else '⚠️ 未被阻止'}")
    print(f"  错误信息: {result_5[1]}")
    print()
    
    # 总结
    print("🎯 测试总结:")
    print("-" * 40)
    test_results = [
        ("您报告的问题", not result_1[0]),
        ("症状编造检测", bool(fabrication_result)),
        ("合理症状重述", result_3[0]),
        ("编造模式检测", all_detected),
        ("XML格式编造", not result_5[0])
    ]
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, passed_test in test_results:
        status = "✅ 通过" if passed_test else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有症状编造检查测试通过！")
        print("现在AI不会再编造患者未描述的症状细节了！")
    else:
        print(f"\n⚠️ 有 {total-passed} 个测试失败，需要进一步调试。")

if __name__ == "__main__":
    test_symptom_fabrication()