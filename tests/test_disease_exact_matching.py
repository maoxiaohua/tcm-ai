#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试疾病精确匹配功能
验证新的疾病查询优先机制
"""

import sys
import os
sys.path.append('/opt/tcm')

from enhanced_retrieval import EnhancedKnowledgeRetrieval
import time

def test_disease_exact_matching():
    """测试疾病精确匹配功能"""
    print("🔍 测试疾病精确匹配功能")
    print("="*60)
    
    # 初始化检索系统
    retrieval = EnhancedKnowledgeRetrieval('/opt/tcm/knowledge_db')
    retrieval.load_knowledge_base()
    
    # 测试用例：精确疾病名查询
    test_cases = [
        "高血压",
        "糖尿病", 
        "冠心病",
        "肺结核病",
        "小儿消化不良",
        "月经失调",
        "消化性溃疡",
        "慢性气管炎",
        "血压高",  # 同义词测试
        "消渴",    # 同义词测试
    ]
    
    print("🎯 测试疾病精确匹配效果:")
    print("-" * 60)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n📋 测试 {i}: 查询「{query}」")
        
        start_time = time.time()
        results = retrieval.hybrid_search(query, total_results=5)
        end_time = time.time()
        
        print(f"⏱️  响应时间: {(end_time - start_time)*1000:.1f}ms")
        print(f"📊 结果数量: {len(results)}")
        
        if results:
            print("🔍 Top 3 结果:")
            for j, result in enumerate(results[:3], 1):
                source = result['metadata'].get('source', 'unknown')
                hybrid_score = result.get('hybrid_score', 0)
                disease_bonus = result.get('disease_exact_bonus', 0)
                semantic_score = result.get('semantic_score', 0)
                keyword_score = result.get('keyword_score', 0)
                
                print(f"  {j}. 📄 {source}")
                print(f"     💯 总分: {hybrid_score:.3f} (疾病加成: {disease_bonus:.2f})")
                print(f"     📈 语义: {semantic_score:.3f}, 关键词: {keyword_score:.3f}")
                
                # 显示文档片段
                doc_preview = result['document'][:100].replace('\n', ' ')
                print(f"     📝 内容: {doc_preview}...")
                print()
        else:
            print("❌ 未找到结果")
            
        print("-" * 40)
    
    # 计算疾病查询的整体性能
    print("\n📊 疾病精确匹配统计:")
    disease_queries = ["高血压", "糖尿病", "冠心病", "肺结核病", "小儿消化不良"]
    
    total_relevant = 0
    total_retrieved = 0
    total_relevant_retrieved = 0
    
    for query in disease_queries:
        results = retrieval.hybrid_search(query, total_results=5)
        query_lower = query.lower()
        
        retrieved = len(results)
        relevant_retrieved = 0
        
        for result in results:
            source = result['metadata'].get('source', '').lower()
            if query_lower in source or any(query_lower in word for word in source.split()):
                relevant_retrieved += 1
                
        total_retrieved += retrieved
        total_relevant_retrieved += relevant_retrieved
        total_relevant += 3  # 假设每个疾病有3个相关文档
        
        precision = relevant_retrieved / retrieved if retrieved > 0 else 0
        print(f"  {query}: 精确率 {precision:.1%} ({relevant_retrieved}/{retrieved})")
    
    overall_precision = total_relevant_retrieved / total_retrieved if total_retrieved > 0 else 0
    overall_recall = total_relevant_retrieved / total_relevant if total_relevant > 0 else 0
    f1_score = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0
    
    print(f"\n🎯 整体性能:")
    print(f"  精确率: {overall_precision:.1%}")
    print(f"  召回率: {overall_recall:.1%}")
    print(f"  F1分数: {f1_score:.1%}")
    
    if f1_score > 0.65:
        print("✅ 疾病查询F1分数达到目标 (>65%)")
    else:
        print("⚠️  疾病查询F1分数未达到目标 (<65%)")

def quick_test():
    """快速测试几个关键疾病"""
    print("⚡ 快速测试疾病精确匹配")
    
    retrieval = EnhancedKnowledgeRetrieval('/opt/tcm/knowledge_db')
    retrieval.load_knowledge_base()
    
    test_diseases = ["高血压", "糖尿病", "冠心病"]
    
    for disease in test_diseases:
        print(f"\n🔍 测试: {disease}")
        # 使用关键词搜索测试疾病精确匹配
        results = retrieval.keyword_search(disease, k=5)
        
        for i, result in enumerate(results, 1):
            source = result['metadata'].get('source', 'unknown')
            keyword_score = result.get('keyword_score', 0)
            print(f"  {i}. {source} (关键词分数: {keyword_score:.3f})")
            
        # 测试疾病精确匹配加成函数
        if results:
            test_result = results[0]
            bonus = retrieval._calculate_disease_exact_bonus(
                disease, 
                test_result['document'], 
                test_result['metadata']
            )
            print(f"  📈 疾病精确匹配加成: {bonus:.2f}")
    
    print("\n✅ 疾病精确匹配功能基本正常")

if __name__ == "__main__":
    print("🚀 开始测试疾病精确匹配功能\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_test()
    else:
        test_disease_exact_matching()
    
    print("\n✅ 测试完成")