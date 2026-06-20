#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试向量数据库搜索功能
"""

import os
import pickle
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jieba

def load_vector_database():
    """加载向量数据库"""
    db_path = '/opt/tcm-ai/template_files/lightweight_vector_db'
    
    # 加载向量
    with open(os.path.join(db_path, 'tfidf_vectors.pkl'), 'rb') as f:
        vectors = pickle.load(f)
    
    # 加载处方数据
    with open(os.path.join(db_path, 'prescriptions.json'), 'r', encoding='utf-8') as f:
        prescriptions = json.load(f)
    
    # 重新创建vectorizer（避免pickle问题）
    vectorizer = TfidfVectorizer(
        tokenizer=lambda text: [w for w in jieba.lcut(text) if len(w) >= 2 and not _is_punctuation(w)],
        lowercase=False,
        max_features=5000,
        min_df=2,
        max_df=0.8,
        ngram_range=(1, 2)
    )
    
    # 重新训练vectorizer
    search_texts = [p['search_text'] for p in prescriptions]
    vectorizer.fit(search_texts)
    
    return vectors, vectorizer, prescriptions

def _is_punctuation(word):
    """判断是否为标点符号"""
    punctuations = set('，。！？；：""''（）【】《》、·～@#￥%……&*+-={}[]|\\/')
    return all(c in punctuations or c.isspace() or c.isdigit() for c in word)

def search_similar_prescriptions(query, k=5):
    """搜索相似处方"""
    vectors, vectorizer, prescriptions = load_vector_database()
    
    # 将查询转换为向量
    query_vector = vectorizer.transform([query])
    
    # 计算余弦相似度
    similarities = cosine_similarity(query_vector, vectors)[0]
    
    # 获取top-k结果
    top_indices = np.argsort(similarities)[::-1][:k]
    
    results = []
    for i, idx in enumerate(top_indices):
        if similarities[idx] > 0:  # 只返回有相似度的结果
            result = {
                'rank': i + 1,
                'similarity': similarities[idx],
                'prescription_id': prescriptions[idx]['id'],
                'disease_name': prescriptions[idx]['disease_name'],
                'syndrome': prescriptions[idx]['syndrome'],
                'formula_name': prescriptions[idx]['formula_name'],
                'display_text': prescriptions[idx]['display_text'],
                'herbs': prescriptions[idx]['herbs'][:6],  # 前6味药
                'herb_count': prescriptions[idx]['herb_count']
            }
            results.append(result)
    
    return results

def test_search_functionality():
    """测试搜索功能"""
    print("🔍 TCM向量数据库搜索测试")
    print("=" * 80)
    
    # 测试查询
    test_queries = [
        "咳嗽痰多发热",
        "风寒感冒恶寒发热",
        "头痛失眠心烦",
        "腹泻腹痛脾虚",
        "月经不调痛经",
        "高血压头晕",
        "糖尿病口干多饮",
        "肾炎水肿",
        "失眠多梦心悸"
    ]
    
    for query in test_queries:
        print(f"\n🔎 查询: {query}")
        print("-" * 60)
        
        results = search_similar_prescriptions(query, k=3)
        
        if not results:
            print("   未找到相关处方")
        else:
            for result in results:
                print(f"  [{result['rank']}] 相似度: {result['similarity']:.3f}")
                print(f"      病症: {result['disease_name']}")
                if result['syndrome']:
                    print(f"      证型: {result['syndrome']}")
                print(f"      方剂: {result['formula_name']}")
                print(f"      药物: {', '.join([h['name'] for h in result['herbs']])} 等{result['herb_count']}味药")
                print()

def search_by_disease(disease_name):
    """按病症搜索"""
    print(f"\n🏥 搜索病症: {disease_name}")
    print("-" * 60)
    
    results = search_similar_prescriptions(disease_name, k=5)
    
    for result in results:
        print(f"相似度: {result['similarity']:.3f} | {result['formula_name']}")
        if result['syndrome']:
            print(f"  证型: {result['syndrome']}")
        print(f"  药物: {', '.join([h['name'] + h['dose'] + h['unit'] for h in result['herbs']])}...")
        print()

def interactive_search():
    """交互式搜索"""
    print("\n🎯 交互式搜索模式")
    print("输入症状描述或病症名称，输入'quit'退出")
    print("=" * 60)
    
    while True:
        query = input("\n请输入查询内容: ").strip()
        if query.lower() == 'quit':
            break
        
        if not query:
            continue
        
        results = search_similar_prescriptions(query, k=5)
        
        if not results:
            print("未找到相关处方，请尝试其他关键词")
        else:
            print(f"\n找到 {len(results)} 个相关处方:")
            for result in results:
                print(f"\n[{result['rank']}] {result['formula_name']} (相似度: {result['similarity']:.3f})")
                print(f"    病症: {result['disease_name']}")
                if result['syndrome']:
                    print(f"    证型: {result['syndrome']}")
                herbs_text = ', '.join([f"{h['name']}{h['dose']}{h['unit']}" for h in result['herbs']])
                print(f"    主要药物: {herbs_text}")

def main():
    """主函数"""
    print("TCM向量数据库功能测试")
    print("=" * 80)
    
    # 基础搜索测试
    test_search_functionality()
    
    # 特定病症搜索
    diseases = ["感冒", "咳嗽", "高血压", "糖尿病", "月经失调"]
    for disease in diseases:
        search_by_disease(disease)
    
    # 交互式搜索（可选）
    # interactive_search()

if __name__ == "__main__":
    main()