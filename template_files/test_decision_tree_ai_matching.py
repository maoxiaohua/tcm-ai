#!/usr/bin/env python3
"""
测试决策树AI语义匹配功能

测试场景：
1. 风热感冒症状 → 应该匹配到"风热感冒"决策树
2. 脾胃虚寒症状 → 应该匹配到"脾胃虚寒型胃痛"决策树
"""

import asyncio
import sys
sys.path.insert(0, '/opt/tcm-ai')

from core.consultation.decision_tree_matcher import DecisionTreeMatcher

async def test_wind_heat_cold():
    """测试风热感冒匹配"""
    print("\n" + "="*60)
    print("测试场景1: 风热感冒")
    print("="*60)

    matcher = DecisionTreeMatcher()

    # 模拟患者描述（风热感冒的典型症状）
    patient_description = """
    患者主诉：发热两天，体温38.5℃，伴有头痛、鼻塞、咽喉肿痛。
    现症：发热恶风，汗出不畅，咽痛口渴，咳嗽痰黄，舌边尖红，苔薄黄。
    既往史：平素体健。
    """

    disease_name = "发热"  # AI可能提取的疾病名
    symptoms = ["发热", "头痛", "鼻塞", "咽痛", "口渴", "咳嗽"]

    print(f"\n患者描述: {patient_description.strip()}")
    print(f"AI提取疾病: {disease_name}")
    print(f"AI提取症状: {symptoms}")

    # 查找匹配的决策树（指定金大夫）
    matches = await matcher.find_matching_patterns(
        disease_name=disease_name,
        symptoms=symptoms,
        patient_description=patient_description,
        doctor_id="jin_daifu",
        min_match_score=0.5  # 降低阈值以便测试
    )

    print(f"\n匹配结果: 找到 {len(matches)} 个决策树")
    for i, match in enumerate(matches, 1):
        print(f"\n【匹配 {i}】")
        print(f"  疾病名称: {match.disease_name}")
        print(f"  匹配分数: {match.match_score:.2f}")
        print(f"  匹配原因: {match.match_reason}")
        print(f"  证候描述: {match.syndrome_description[:100]}...")
        print(f"  历史使用: {match.usage_count}次, 成功{match.success_count}次")

    # 验证是否匹配到风热感冒
    wind_heat_match = any("风热感冒" in m.disease_name for m in matches)
    print(f"\n✅ 测试结果: {'成功 - 匹配到风热感冒' if wind_heat_match else '失败 - 未匹配到风热感冒'}")

    return wind_heat_match

async def test_spleen_stomach_cold():
    """测试脾胃虚寒匹配"""
    print("\n" + "="*60)
    print("测试场景2: 脾胃虚寒型胃痛")
    print("="*60)

    matcher = DecisionTreeMatcher()

    # 模拟患者描述（脾胃虚寒的典型症状）
    patient_description = """
    患者主诉：胃脘隐痛半年，喜温喜按，进食后稍缓解。
    现症：胃脘隐痛，得温痛减，神疲乏力，大便溏薄，舌淡苔白，脉沉细无力。
    既往史：脾胃素弱。
    """

    disease_name = "胃痛"
    symptoms = ["胃痛", "乏力", "便溏"]

    print(f"\n患者描述: {patient_description.strip()}")
    print(f"AI提取疾病: {disease_name}")
    print(f"AI提取症状: {symptoms}")

    matches = await matcher.find_matching_patterns(
        disease_name=disease_name,
        symptoms=symptoms,
        patient_description=patient_description,
        doctor_id="jin_daifu",
        min_match_score=0.5
    )

    print(f"\n匹配结果: 找到 {len(matches)} 个决策树")
    for i, match in enumerate(matches, 1):
        print(f"\n【匹配 {i}】")
        print(f"  疾病名称: {match.disease_name}")
        print(f"  匹配分数: {match.match_score:.2f}")
        print(f"  匹配原因: {match.match_reason}")
        if match.syndrome_description:
            print(f"  证候描述: {match.syndrome_description[:100]}...")

    spleen_match = any("脾胃虚寒" in m.disease_name for m in matches)
    print(f"\n✅ 测试结果: {'成功 - 匹配到脾胃虚寒' if spleen_match else '失败 - 未匹配到脾胃虚寒'}")

    return spleen_match

async def main():
    """运行所有测试"""
    print("\n🧪 决策树AI语义匹配功能测试")
    print("="*60)

    test1 = await test_wind_heat_cold()
    test2 = await test_spleen_stomach_cold()

    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    print(f"风热感冒测试: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"脾胃虚寒测试: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"\n总体结果: {'🎉 全部通过' if test1 and test2 else '⚠️ 部分失败'}")

if __name__ == "__main__":
    asyncio.run(main())
