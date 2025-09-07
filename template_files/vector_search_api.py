#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCM向量搜索API包装器
用于集成到现有问诊系统中
"""

import os
import pickle
import json
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jieba
import logging

logger = logging.getLogger(__name__)

class TCMVectorSearchAPI:
    """TCM向量搜索API"""
    
    def __init__(self, db_path: str = '/opt/tcm-ai/template_files/lightweight_vector_db'):
        """
        初始化向量搜索API
        
        Args:
            db_path: 向量数据库路径
        """
        self.db_path = db_path
        self.vectors = None
        self.vectorizer = None
        self.prescriptions = None
        self.metadata = None
        self._loaded = False
        
    def _load_database(self) -> bool:
        """加载向量数据库"""
        if self._loaded:
            return True
            
        try:
            # 加载向量
            with open(os.path.join(self.db_path, 'tfidf_vectors.pkl'), 'rb') as f:
                self.vectors = pickle.load(f)
            
            # 加载处方数据
            with open(os.path.join(self.db_path, 'prescriptions.json'), 'r', encoding='utf-8') as f:
                self.prescriptions = json.load(f)
            
            # 加载元数据
            with open(os.path.join(self.db_path, 'metadata.json'), 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            # 重新创建vectorizer
            self.vectorizer = TfidfVectorizer(
                tokenizer=self._jieba_tokenizer,
                lowercase=False,
                max_features=5000,
                min_df=2,
                max_df=0.8,
                ngram_range=(1, 2)
            )
            
            # 重新训练vectorizer
            search_texts = [p['search_text'] for p in self.prescriptions]
            self.vectorizer.fit(search_texts)
            
            self._loaded = True
            logger.info(f"向量数据库加载成功: {len(self.prescriptions)}个处方")
            return True
            
        except Exception as e:
            logger.error(f"加载向量数据库失败: {e}")
            return False
    
    def _jieba_tokenizer(self, text: str) -> List[str]:
        """jieba分词器"""
        words = jieba.lcut(text)
        filtered_words = []
        for word in words:
            word = word.strip()
            if len(word) >= 2 and not self._is_punctuation(word):
                filtered_words.append(word)
        return filtered_words
    
    def _is_punctuation(self, word: str) -> bool:
        """判断是否为标点符号"""
        punctuations = set('，。！？；：""''（）【】《》、·～@#￥%……&*+-={}[]|\\/')
        return all(c in punctuations or c.isspace() or c.isdigit() for c in word)
    
    def search_prescriptions(self, 
                           query: str, 
                           top_k: int = 5, 
                           min_similarity: float = 0.1,
                           disease_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索相似处方
        
        Args:
            query: 搜索查询（症状描述、病症名称等）
            top_k: 返回前k个结果
            min_similarity: 最小相似度阈值
            disease_filter: 病症过滤器（可选）
            
        Returns:
            相似处方列表
        """
        if not self._load_database():
            return []
        
        try:
            # 将查询转换为向量
            query_vector = self.vectorizer.transform([query])
            
            # 计算相似度
            similarities = cosine_similarity(query_vector, self.vectors)[0]
            
            # 获取排序索引
            sorted_indices = np.argsort(similarities)[::-1]
            
            results = []
            for idx in sorted_indices:
                similarity = similarities[idx]
                
                # 过滤低相似度结果
                if similarity < min_similarity:
                    break
                
                prescription = self.prescriptions[idx]
                
                # 病症过滤
                if disease_filter and disease_filter not in prescription['disease_name']:
                    continue
                
                result = {
                    'similarity': float(similarity),
                    'prescription_id': prescription['id'],
                    'disease_name': prescription['disease_name'],
                    'syndrome': prescription['syndrome'],
                    'treatment_method': prescription['treatment_method'],
                    'formula_name': prescription['formula_name'],
                    'herbs': prescription['herbs'],
                    'herb_count': prescription['herb_count'],
                    'usage': prescription['usage'],
                    'source_document': prescription['source_document'],
                    'display_text': prescription['display_text']
                }
                
                results.append(result)
                
                if len(results) >= top_k:
                    break
            
            logger.info(f"搜索查询: {query}, 返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"处方搜索失败: {e}")
            return []
    
    def search_by_symptoms(self, symptoms: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        基于症状列表搜索处方
        
        Args:
            symptoms: 症状列表
            top_k: 返回前k个结果
            
        Returns:
            相似处方列表
        """
        query = ' '.join(symptoms)
        return self.search_prescriptions(query, top_k)
    
    def search_by_disease(self, disease_name: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        基于病症名称搜索处方
        
        Args:
            disease_name: 病症名称
            top_k: 返回前k个结果
            
        Returns:
            相似处方列表
        """
        return self.search_prescriptions(disease_name, top_k, disease_filter=disease_name)
    
    def get_prescription_by_id(self, prescription_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取处方详情
        
        Args:
            prescription_id: 处方ID
            
        Returns:
            处方详情或None
        """
        if not self._load_database():
            return None
            
        for prescription in self.prescriptions:
            if prescription['id'] == prescription_id:
                return prescription
        return None
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            数据库统计信息
        """
        if not self._load_database():
            return {}
        
        return {
            'total_prescriptions': len(self.prescriptions),
            'total_diseases': len(set(p['disease_name'] for p in self.prescriptions)),
            'total_herbs': len(set(herb['name'] for p in self.prescriptions for herb in p['herbs'])),
            'vector_dimension': self.metadata['vector_dimension'],
            'creation_time': self.metadata['creation_time'],
            'model_type': self.metadata['model_type']
        }
    
    def recommend_similar_prescriptions(self, 
                                      current_prescription_id: int, 
                                      top_k: int = 5) -> List[Dict[str, Any]]:
        """
        基于当前处方推荐相似处方
        
        Args:
            current_prescription_id: 当前处方ID
            top_k: 推荐数量
            
        Returns:
            相似处方列表
        """
        if not self._load_database():
            return []
        
        # 找到当前处方
        current_prescription = None
        current_index = None
        
        for i, prescription in enumerate(self.prescriptions):
            if prescription['id'] == current_prescription_id:
                current_prescription = prescription
                current_index = i
                break
        
        if current_prescription is None:
            return []
        
        # 计算与其他处方的相似度
        current_vector = self.vectors[current_index:current_index+1]
        similarities = cosine_similarity(current_vector, self.vectors)[0]
        
        # 排除自己
        similarities[current_index] = -1
        
        # 获取最相似的处方
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # 最小相似度阈值
                prescription = self.prescriptions[idx]
                result = {
                    'similarity': float(similarities[idx]),
                    'prescription_id': prescription['id'],
                    'disease_name': prescription['disease_name'],
                    'formula_name': prescription['formula_name'],
                    'display_text': prescription['display_text']
                }
                results.append(result)
        
        return results

# 创建全局实例
tcm_vector_search = TCMVectorSearchAPI()

def search_tcm_prescriptions(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    便捷函数：搜索TCM处方
    
    Args:
        query: 搜索查询
        top_k: 返回结果数量
        
    Returns:
        处方列表
    """
    return tcm_vector_search.search_prescriptions(query, top_k)

def get_tcm_database_stats() -> Dict[str, Any]:
    """
    便捷函数：获取数据库统计信息
    
    Returns:
        统计信息
    """
    return tcm_vector_search.get_database_stats()

if __name__ == "__main__":
    # 测试API
    api = TCMVectorSearchAPI()
    
    print("TCM向量搜索API测试")
    print("=" * 50)
    
    # 测试数据库统计
    stats = api.get_database_stats()
    print("数据库统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "-" * 50)
    
    # 测试搜索功能
    test_queries = [
        "咳嗽痰多",
        "风寒感冒",
        "失眠心悸",
        "高血压头晕"
    ]
    
    for query in test_queries:
        print(f"\n搜索: {query}")
        results = api.search_prescriptions(query, top_k=3)
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['formula_name']} (相似度: {result['similarity']:.3f})")
            print(f"     病症: {result['disease_name']}")
            if result['syndrome']:
                print(f"     证型: {result['syndrome']}")