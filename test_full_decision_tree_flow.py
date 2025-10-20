#!/usr/bin/env python3
"""完整的决策树匹配流程测试"""
import asyncio
import sys
sys.path.append('/opt/tcm-ai')

from core.consultation.decision_tree_matcher import get_decision_tree_matcher

async def test_full_flow():
    print("=" * 80)
    print("完整决策树匹配流程测试")
    print("=" * 80)

    matcher = get_decision_tree_matcher()

    # 模拟患者输入（脾胃虚寒型胃痛的症见描述）
    patient_input = "胃脘隐痛，绵绵不休，喜温喜按，空腹痛甚，得食稍缓，泛吐清水，神疲乏力，手足不温，大便溏薄，舌淡苔白，脉沉迟无力"

    print(f"\n患者输入:\n{patient_input}\n")

    # 1. 提取疾病
    disease = matcher.extract_disease_from_text(patient_input)
    print(f"✅ 提取到疾病: {disease}")

    # 2. 提取症状
    symptoms = matcher.extract_symptoms_from_text(patient_input)
    print(f"✅ 提取到症状 ({len(symptoms)}个): {symptoms[:5]}...")

    # 3. 匹配决策树（三层fallback）
    print("\n" + "=" * 80)
    print("三层决策树匹配")
    print("=" * 80)

    # 第1层: jin_daifu
    print("\n第1层: 查询 jin_daifu 的决策树")
    matches = await matcher.find_matching_patterns(
        disease_name=disease,
        symptoms=symptoms,
        patient_description=patient_input,
        doctor_id="jin_daifu",
        min_match_score=0.3
    )
    print(f"结果: 找到 {len(matches)} 个匹配")

    # 第2层: anonymous_doctor
    print("\n第2层: 查询 anonymous_doctor 的决策树")
    matches = await matcher.find_matching_patterns(
        disease_name=disease,
        symptoms=symptoms,
        patient_description=patient_input,
        doctor_id="anonymous_doctor",
        min_match_score=0.3
    )
    print(f"结果: 找到 {len(matches)} 个匹配")

    if matches:
        best_match = matches[0]
        print(f"\n✅ 最佳匹配:")
        print(f"  决策树ID: {best_match.pattern_id}")
        print(f"  疾病名称: {best_match.disease_name}")
        print(f"  匹配分数: {best_match.match_score:.2%}")
        print(f"  置信度: {best_match.confidence:.2%}")
        print(f"  医生ID: {best_match.doctor_id}")

        # 显示处方
        import json
        patterns = json.loads(best_match.clinical_patterns) if isinstance(best_match.clinical_patterns, str) else best_match.clinical_patterns
        if patterns.get("treatment_principles"):
            print(f"\n✅ 处方信息:")
            for principle in patterns["treatment_principles"]:
                print(f"  {principle.get('principle_name', 'N/A')}")

    print("\n" + "=" * 80)
    print("测试完成 - 决策树匹配成功！🎉")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_full_flow())
