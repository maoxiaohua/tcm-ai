#!/usr/bin/env python3
"""
决策树匹配功能测试脚本
验证三层fallback策略是否正常工作
"""
import asyncio
import sys
sys.path.append('/opt/tcm-ai')

from core.consultation.decision_tree_matcher import get_decision_tree_matcher

async def test_matching():
    print("=" * 80)
    print("决策树匹配功能测试")
    print("=" * 80)

    matcher = get_decision_tree_matcher()

    # 测试数据
    symptoms = ["胃痛", "手足不温", "大便溏薄", "神疲乏力", "泛吐清水"]
    patient_desc = "我最近半年胃痛反复发作,喝温水会舒服一点,按压也能减轻疼痛。还经常吐清水,没什么胃口,整个人很疲劳。手脚也总是冰凉的,大便稀溏。"

    # 第1层：查询指定医生
    print("\n" + "=" * 80)
    print("第1层：查询 jin_daifu 的决策树")
    print("=" * 80)
    matches = await matcher.find_matching_patterns(
        disease_name="胃痛",
        symptoms=symptoms,
        patient_description=patient_desc,
        doctor_id="jin_daifu"
    )
    print(f"✅ 找到 {len(matches)} 个匹配")
    for i, m in enumerate(matches, 1):
        print(f"  {i}. {m.disease_name}: 匹配度={m.match_score:.2%}, 置信度={m.confidence:.2%}")

    # 第2层：查询通用决策树
    print("\n" + "=" * 80)
    print("第2层：查询 anonymous_doctor 的决策树")
    print("=" * 80)
    matches = await matcher.find_matching_patterns(
        disease_name="胃痛",
        symptoms=symptoms,
        patient_description=patient_desc,
        doctor_id="anonymous_doctor"
    )
    print(f"✅ 找到 {len(matches)} 个匹配")
    for i, m in enumerate(matches, 1):
        print(f"  {i}. {m.disease_name}: 匹配度={m.match_score:.2%}, 置信度={m.confidence:.2%}")
        print(f"     决策树ID: {m.pattern_id}")
        print(f"     使用次数: {m.usage_count}, 成功次数: {m.success_count}")
        if m.clinical_patterns:
            import json
            patterns = json.loads(m.clinical_patterns) if isinstance(m.clinical_patterns, str) else m.clinical_patterns
            if patterns.get("treatment_principles"):
                for principle in patterns["treatment_principles"][:1]:
                    print(f"     处方: {principle.get('principle_name', 'N/A')}")

    # 第3层：查询所有医生
    print("\n" + "=" * 80)
    print("第3层：查询所有医生的决策树")
    print("=" * 80)
    matches = await matcher.find_matching_patterns(
        disease_name="胃痛",
        symptoms=symptoms,
        patient_description=patient_desc,
        doctor_id=None
    )
    print(f"✅ 找到 {len(matches)} 个匹配")
    for i, m in enumerate(matches, 1):
        print(f"  {i}. {m.disease_name} (医生:{m.doctor_id}): 匹配度={m.match_score:.2%}")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_matching())
