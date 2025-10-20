#!/usr/bin/env python3
"""调试决策树匹配"""
import asyncio
import sys
import sqlite3
sys.path.append('/opt/tcm-ai')

from core.consultation.decision_tree_matcher import get_decision_tree_matcher

async def debug_matching():
    matcher = get_decision_tree_matcher()
    
    # 先查看数据库中有什么决策树
    print("=" * 80)
    print("数据库中的决策树:")
    print("=" * 80)
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, doctor_id, disease_name, usage_count, success_count FROM doctor_clinical_patterns")
    patterns = cursor.fetchall()
    for p in patterns:
        print(f"ID: {p['id']}")
        print(f"  医生: {p['doctor_id']}")
        print(f"  疾病: {p['disease_name']}")
        print(f"  使用: {p['usage_count']}, 成功: {p['success_count']}")
        print()
    conn.close()
    
    # 测试疾病提取
    print("=" * 80)
    print("测试疾病提取:")
    print("=" * 80)
    test_texts = [
        "我最近胃痛",
        "脾胃虚寒型胃痛",
        "胃部不适"
    ]
    for text in test_texts:
        disease = matcher.extract_disease_from_text(text)
        print(f"文本: {text}")
        print(f"提取到的疾病: {disease}")
        print()
    
    # 测试别名匹配
    print("=" * 80)
    print("测试疾病别名匹配:")
    print("=" * 80)
    print("是否为别名 '胃痛' vs '脾胃虚寒型胃痛':", matcher._is_disease_alias("胃痛", "脾胃虚寒型胃痛"))
    print("是否为别名 '胃痛' vs '胃痛':", matcher._is_disease_alias("胃痛", "胃痛"))
    print()
    
    # 测试匹配
    print("=" * 80)
    print("测试匹配 (疾病='脾胃虚寒型胃痛'):")
    print("=" * 80)
    matches = await matcher.find_matching_patterns(
        disease_name="脾胃虚寒型胃痛",  # 使用完整的疾病名称
        symptoms=["胃痛", "手足不温"],
        patient_description="胃痛",
        doctor_id="anonymous_doctor",
        min_match_score=0.1  # 降低阈值
    )
    print(f"找到 {len(matches)} 个匹配")
    for m in matches:
        print(f"  - {m.disease_name}: 匹配度={m.match_score:.2%}")
    
if __name__ == "__main__":
    asyncio.run(debug_matching())
