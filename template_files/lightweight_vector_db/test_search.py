#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCM向量数据库测试脚本
"""
import pickle
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import jieba

def load_database():
    """加载数据库"""
    # 加载向量
    with open('tfidf_vectors.pkl', 'rb') as f:
        vectors = pickle.load(f)
    
    # 加载向量化器
    with open('tfidf_vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
    
    # 加载处方数据
    with open('prescriptions.json', 'r', encoding='utf-8') as f:
        prescriptions = json.load(f)
    
    return vectors, vectorizer, prescriptions

def search_prescriptions(query, k=5):
    """搜索相似处方"""
    vectors, vectorizer, prescriptions = load_database()
    
    # 将查询转换为向量
    query_vector = vectorizer.transform([query])
    
    # 计算余弦相似度
    similarities = cosine_similarity(query_vector, vectors)[0]
    
    # 获取top-k结果
    top_indices = np.argsort(similarities)[::-1][:k]
    
    results = []
    for i, idx in enumerate(top_indices):
        result = {
            'rank': i + 1,
            'similarity': similarities[idx],
            'prescription': prescriptions[idx]
        }
        results.append(result)
    
    return results

if __name__ == "__main__":
    # 测试查询
    test_queries = [
        "咳嗽痰多发热",
        "风寒感冒恶寒",
        "头痛失眠心烦",
        "腹泻腹痛"
    ]
    
    print("🔍 TCM向量数据库测试")
    print("=" * 60)
    
    for test_query in test_queries:
        print(f"\n查询: {test_query}")
        results = search_prescriptions(test_query, k=3)
        
        for result in results:
            print(f"  [{result['rank']}] 相似度: {result['similarity']:.3f}")
            print(f"      {result['prescription']['display_text'][:100]}...")
