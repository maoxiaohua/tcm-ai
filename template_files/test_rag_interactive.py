#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医RAG系统交互式测试
让用户直接体验RAG检索效果
"""

import sys
import os
sys.path.append('.')

from utils.enhanced_tcm_rag import EnhancedTCMRAG

def display_search_results(search_result, show_full_content=False):
    """美化显示搜索结果"""
    if not search_result['success']:
        print(f"❌ 搜索失败: {search_result.get('error', 'unknown')}")
        return
    
    results = search_result['results']
    if not results:
        print("📭 未找到相关内容")
        return
    
    print(f"🎯 找到 {len(results)} 个相关结果")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        score = result.get('hybrid_score', result.get('score', 0))
        metadata = result['metadata']
        source = metadata.get('source', 'unknown')
        section = metadata.get('section_type', 'other')
        content = result['document']
        
        print(f"\n📄 结果 {i}")
        print(f"📊 相关度评分: {score:.4f}")
        print(f"📚 来源文档: {source}")
        print(f"📖 文档部分: {section}")
        print(f"📝 内容预览:")
        
        if show_full_content:
            print(f"    {content}")
        else:
            # 智能截取显示
            if len(content) > 200:
                print(f"    {content[:200]}...")
                print(f"    [显示前200字符，完整内容共{len(content)}字符]")
            else:
                print(f"    {content}")
        
        print("-" * 80)

def interactive_test():
    """交互式测试"""
    print("🏥 中医RAG系统交互式测试")
    print("=" * 60)
    
    # 初始化系统
    print("🔄 正在初始化RAG系统...")
    rag_system = EnhancedTCMRAG()
    
    if not rag_system.documents:
        print("❌ 知识库为空，请先运行文档处理")
        return
    
    print(f"✅ 知识库已加载: {len(rag_system.documents)} 个文档分块")
    
    # 预设测试查询
    preset_queries = [
        "感冒的症状有哪些",
        "高血压怎么治疗",
        "咳嗽吃什么药",
        "糖尿病的病因是什么",
        "月经失调如何调理",
        "头痛的中医治疗",
        "发热如何处理"
    ]
    
    print("\n🎯 你可以:")
    print("1. 输入自定义查询")
    print("2. 选择预设查询 (输入数字1-7)")
    print("3. 输入 'quit' 退出")
    
    print(f"\n📋 预设查询列表:")
    for i, query in enumerate(preset_queries, 1):
        print(f"   {i}. {query}")
    
    while True:
        print("\n" + "="*60)
        user_input = input("🔍 请输入查询内容或选择数字 (quit退出): ").strip()
        
        if user_input.lower() == 'quit':
            print("👋 再见！")
            break
        
        # 检查是否是数字选择
        if user_input.isdigit():
            num = int(user_input)
            if 1 <= num <= len(preset_queries):
                query = preset_queries[num - 1]
                print(f"📝 选择的查询: {query}")
            else:
                print("❌ 无效的数字选择")
                continue
        else:
            query = user_input
            if not query:
                print("❌ 请输入有效的查询内容")
                continue
        
        # 询问显示选项
        show_full = input("📄 是否显示完整内容? (y/n, 默认n): ").strip().lower() == 'y'
        top_k = input("🔢 返回结果数量 (1-10, 默认3): ").strip()
        
        try:
            top_k = int(top_k) if top_k.isdigit() and 1 <= int(top_k) <= 10 else 3
        except:
            top_k = 3
        
        print(f"\n🔍 正在搜索: '{query}'")
        print(f"⚙️ 参数: 返回{top_k}个结果, {'完整内容' if show_full else '预览模式'}")
        
        # 执行搜索
        search_result = rag_system.search_knowledge(query, top_k=top_k)
        
        # 显示结果
        display_search_results(search_result, show_full_content=show_full)
        
        # 询问是否继续
        continue_search = input("\n🔄 继续测试? (y/n, 默认y): ").strip().lower()
        if continue_search == 'n':
            print("👋 测试完成！")
            break

def quick_demo():
    """快速演示"""
    print("🚀 中医RAG系统快速演示")
    print("=" * 50)
    
    rag_system = EnhancedTCMRAG()
    
    if not rag_system.documents:
        print("❌ 知识库为空")
        return
    
    # 演示查询
    demo_queries = [
        "感冒的症状",
        "高血压治疗", 
        "咳嗽用药"
    ]
    
    for query in demo_queries:
        print(f"\n🔍 演示查询: {query}")
        search_result = rag_system.search_knowledge(query, top_k=2)
        display_search_results(search_result, show_full_content=False)
        input("按回车继续下一个演示...")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        quick_demo()
    else:
        interactive_test()