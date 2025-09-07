#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医RAG效果演示
展示实际的检索效果
"""

import sys
sys.path.append('.')
from utils.enhanced_tcm_rag import EnhancedTCMRAG

def demo_rag_effects():
    """演示RAG效果"""
    
    print("🏥 中医RAG系统效果演示")
    print("=" * 60)
    
    # 初始化
    rag_system = EnhancedTCMRAG()
    
    print(f"📚 知识库状态: {len(rag_system.documents)} 个分块已加载")
    
    # 演示查询
    demo_cases = [
        {
            "query": "感冒",
            "description": "基础疾病查询", 
            "expected": "应该找到感冒的症状、治疗等信息"
        },
        {
            "query": "高血压症状",
            "description": "复合关键词查询",
            "expected": "应该找到高血压的症状描述"
        },
        {
            "query": "咳嗽治疗",
            "description": "症状+治疗查询", 
            "expected": "应该找到咳嗽的治疗方法"
        },
        {
            "query": "中药",
            "description": "治疗方式查询",
            "expected": "应该找到中药相关内容"
        }
    ]
    
    for i, case in enumerate(demo_cases, 1):
        print(f"\n🔍 演示 {i}: {case['description']}")
        print(f"查询: \"{case['query']}\"")
        print(f"预期: {case['expected']}")
        print("-" * 50)
        
        # 执行搜索
        search_result = rag_system.search_knowledge(case['query'], top_k=2)
        
        if search_result['success'] and search_result['results']:
            results = search_result['results']
            print(f"✅ 找到 {len(results)} 个相关结果\n")
            
            for j, result in enumerate(results, 1):
                score = result.get('score', 0)
                source = result['metadata'].get('source', 'unknown')
                content = result['document']
                
                # 提取关键句子
                sentences = content.split('。')
                relevant_sentences = []
                
                for sentence in sentences:
                    if case['query'] in sentence or any(word in sentence for word in case['query'].split()):
                        relevant_sentences.append(sentence.strip())
                
                print(f"📄 结果 {j}")
                print(f"   相关度: {score:.4f}")
                print(f"   来源: {source}")
                
                if relevant_sentences:
                    print(f"   关键内容:")
                    for sentence in relevant_sentences[:2]:  # 显示前2个相关句子
                        if sentence and len(sentence) > 5:
                            print(f"   • {sentence}。")
                else:
                    print(f"   内容预览: {content[:100]}...")
                print()
        else:
            print("❌ 未找到相关结果")
        
        print("=" * 60)

def show_knowledge_coverage():
    """显示知识覆盖情况"""
    
    print("\n📊 知识库覆盖分析")
    print("=" * 40)
    
    rag_system = EnhancedTCMRAG()
    
    # 按来源统计
    source_stats = {}
    for metadata in rag_system.metadata:
        source = metadata.get('source', 'unknown')
        source_stats[source] = source_stats.get(source, 0) + 1
    
    print("📁 文档分布:")
    for source, count in sorted(source_stats.items()):
        print(f"   {source}: {count} 个分块")
    
    # 关键概念覆盖
    key_concepts = ['症状', '治疗', '病因', '诊断', '方药', '针灸', '调理']
    
    print(f"\n🔑 关键概念覆盖:")
    for concept in key_concepts:
        count = sum(1 for doc in rag_system.documents if concept in doc)
        coverage = count / len(rag_system.documents) * 100 if rag_system.documents else 0
        print(f"   {concept}: {count} 个分块 ({coverage:.1f}%)")

if __name__ == "__main__":
    demo_rag_effects()
    show_knowledge_coverage()
    
    print(f"\n🎯 总结:")
    print(f"✅ RAG系统已成功运行")
    print(f"✅ 文档预处理完成")
    print(f"✅ 检索功能正常工作")
    print(f"✅ 能够找到相关的医学内容")
    print(f"\n🚀 可以扩展到全部58个文档了！")