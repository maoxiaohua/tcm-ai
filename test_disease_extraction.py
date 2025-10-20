#!/usr/bin/env python3
"""测试疾病提取优化"""
import sys
sys.path.append('/opt/tcm-ai')

from core.consultation.decision_tree_matcher import get_decision_tree_matcher

def test_disease_extraction():
    matcher = get_decision_tree_matcher()

    test_cases = [
        {
            "text": "胃脘隐痛，绵绵不休，喜温喜按，空腹痛甚，得食稍缓，泛吐清水，神疲乏力，手足不温，大便溏薄，舌淡苔白，脉沉迟无力",
            "expected": "胃痛",
            "description": "脾胃虚寒型胃痛症见（主症在前，大便溏在后）"
        },
        {
            "text": "我最近胃痛，还有点拉肚子",
            "expected": "胃痛",
            "description": "胃痛在前，腹泻在后"
        },
        {
            "text": "我最近拉肚子，胃也有点痛",
            "expected": "腹泻",
            "description": "腹泻在前，胃痛在后"
        },
        {
            "text": "最近失眠多梦",
            "expected": "失眠",
            "description": "单一疾病"
        }
    ]

    print("=" * 80)
    print("疾病提取优化测试")
    print("=" * 80)

    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['description']}")
        print(f"文本: {case['text'][:60]}...")

        extracted = matcher.extract_disease_from_text(case['text'])

        print(f"预期疾病: {case['expected']}")
        print(f"提取结果: {extracted}")

        if extracted == case['expected']:
            print("✅ 通过")
        else:
            print("❌ 失败")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_disease_extraction()
