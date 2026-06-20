#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识检索处理模块
从chat_with_ai_endpoint函数中提取的RAG知识检索相关功能
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..utils.common_utils import safe_execute, get_current_timestamp_iso
from ..utils.text_utils import extract_keywords_from_query, clean_medical_text

logger = logging.getLogger(__name__)

class KnowledgeRetrievalProcessor:
    """知识检索处理器"""
    
    def __init__(self, vector_store_service, faiss_service, db_manager):
        self.vector_store = vector_store_service
        self.faiss_service = faiss_service
        self.db_manager = db_manager
        
        # 检索参数配置
        self.default_top_k = 5
        self.similarity_threshold = 0.7
        self.max_context_length = 4000
        
        # 知识库类型权重
        self.knowledge_weights = {
            'clinical_cases': 1.0,      # 临床案例
            'prescriptions': 0.9,       # 处方数据
            'symptoms_mapping': 0.8,    # 症状映射
            'herb_database': 0.7,       # 药材数据库
            'medical_texts': 0.6        # 医学文献
        }
    
    def retrieve_relevant_knowledge(self, query: str, user_context: Dict[str, Any] = None, 
                                   top_k: int = None) -> Dict[str, Any]:
        """检索相关知识"""
        retrieval_result = {
            'success': False,
            'query': query,
            'retrieved_items': [],
            'context_summary': '',
            'retrieval_stats': {},
            'error_message': ''
        }
        
        try:
            # 参数设置
            top_k = top_k or self.default_top_k
            
            # 查询预处理
            processed_query = self._preprocess_query(query, user_context)
            
            # 多源检索
            retrieval_sources = [
                ('vector_search', self._vector_similarity_search),
                ('faiss_search', self._faiss_similarity_search),
                ('keyword_search', self._keyword_based_search),
                ('contextual_search', self._contextual_search)
            ]
            
            all_results = []
            retrieval_stats = {}
            
            for source_name, search_func in retrieval_sources:
                logger.info(f"执行{source_name}检索")
                
                source_results = safe_execute(
                    search_func,
                    processed_query,
                    top_k,
                    user_context,
                    default_return=[],
                    error_message=f"{source_name}检索失败"
                )
                
                retrieval_stats[source_name] = {
                    'count': len(source_results),
                    'avg_score': np.mean([r.get('score', 0) for r in source_results]) if source_results else 0
                }
                
                all_results.extend(source_results)
            
            # 结果融合和排序
            merged_results = self._merge_and_rank_results(all_results, query)
            
            # 过滤和优化
            filtered_results = self._filter_and_optimize_results(merged_results, top_k)
            
            # 生成上下文摘要
            context_summary = self._generate_context_summary(filtered_results, query)
            
            retrieval_result.update({
                'success': True,
                'retrieved_items': filtered_results,
                'context_summary': context_summary,
                'retrieval_stats': retrieval_stats
            })
            
        except Exception as e:
            logger.error(f"知识检索失败: {e}")
            retrieval_result['error_message'] = str(e)
        
        return retrieval_result
    
    def _preprocess_query(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """预处理查询"""
        processed = {
            'original_query': query,
            'cleaned_query': clean_medical_text(query),
            'keywords': extract_keywords_from_query(query),
            'query_type': self._classify_query_type(query),
            'context_keywords': []
        }
        
        # 从用户上下文提取额外关键词
        if user_context:
            recent_symptoms = user_context.get('relevant_symptoms', [])
            processed['context_keywords'] = recent_symptoms
        
        return processed
    
    def _classify_query_type(self, query: str) -> str:
        """分类查询类型"""
        query_patterns = {
            'symptom_inquiry': ['症状', '不舒服', '疼痛', '感觉'],
            'prescription_request': ['处方', '药方', '吃什么药', '如何治疗'],
            'diagnosis_question': ['什么病', '诊断', '是不是', '病因'],
            'lifestyle_advice': ['注意什么', '如何调理', '生活', '饮食'],
            'herb_inquiry': ['中药', '草药', '药材', '功效']
        }
        
        for query_type, keywords in query_patterns.items():
            if any(keyword in query for keyword in keywords):
                return query_type
        
        return 'general_inquiry'
    
    def _vector_similarity_search(self, processed_query: Dict[str, Any], 
                                 top_k: int, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """向量相似性搜索"""
        try:
            query_text = processed_query['cleaned_query']
            
            # PostgreSQL向量搜索
            search_result = self.vector_store.similarity_search(
                query_text,
                top_k=top_k * 2,  # 获取更多结果用于后续过滤
                threshold=self.similarity_threshold
            )
            
            results = []
            for item in search_result.get('results', []):
                results.append({
                    'source': 'vector_search',
                    'content': item.get('content', ''),
                    'metadata': item.get('metadata', {}),
                    'score': item.get('score', 0.0),
                    'knowledge_type': item.get('metadata', {}).get('type', 'unknown')
                })
            
            return results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    def _faiss_similarity_search(self, processed_query: Dict[str, Any], 
                                top_k: int, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """FAISS相似性搜索"""
        try:
            query_text = processed_query['cleaned_query']
            
            # FAISS搜索
            search_result = self.faiss_service.search_similar_texts(
                query_text,
                top_k=top_k
            )
            
            results = []
            if search_result.get('success') and search_result.get('results'):
                for item in search_result['results']:
                    results.append({
                        'source': 'faiss_search',
                        'content': item.get('text', ''),
                        'metadata': item.get('metadata', {}),
                        'score': item.get('similarity_score', 0.0),
                        'knowledge_type': 'faiss_indexed'
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS搜索失败: {e}")
            return []
    
    def _keyword_based_search(self, processed_query: Dict[str, Any], 
                             top_k: int, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """基于关键词的搜索"""
        try:
            keywords = processed_query['keywords']
            if not keywords:
                return []
            
            # 构建关键词查询
            keyword_query = ' OR '.join(keywords)
            
            # 数据库全文搜索
            query = """
            SELECT content, metadata, 
                   ts_rank(to_tsvector('chinese', content), to_tsquery('chinese', %s)) as rank
            FROM knowledge_base 
            WHERE to_tsvector('chinese', content) @@ to_tsquery('chinese', %s)
            ORDER BY rank DESC
            LIMIT %s
            """
            
            result = self.db_manager.execute_query(query, (keyword_query, keyword_query, top_k))
            
            results = []
            if result['success'] and result['data']:
                for row in result['data']:
                    results.append({
                        'source': 'keyword_search',
                        'content': row['content'],
                        'metadata': row.get('metadata', {}),
                        'score': float(row['rank']),
                        'knowledge_type': 'keyword_match'
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []
    
    def _contextual_search(self, processed_query: Dict[str, Any], 
                          top_k: int, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """基于上下文的搜索"""
        try:
            results = []
            
            if not user_context:
                return results
            
            # 基于用户历史模式的搜索
            most_common_type = user_context.get('user_pattern', {}).get('most_common_type', '')
            if most_common_type:
                type_query = f"SELECT * FROM knowledge_base WHERE metadata->>'diagnosis_type' = %s LIMIT %s"
                type_result = self.db_manager.execute_query(type_query, (most_common_type, top_k // 2))
                
                if type_result['success'] and type_result['data']:
                    for row in type_result['data']:
                        results.append({
                            'source': 'contextual_search',
                            'content': row['content'],
                            'metadata': row.get('metadata', {}),
                            'score': 0.8,  # 上下文相关性评分
                            'knowledge_type': 'contextual_match'
                        })
            
            # 基于症状上下文的搜索
            context_symptoms = user_context.get('relevant_symptoms', [])
            if context_symptoms:
                symptoms_query = ' OR '.join(context_symptoms)
                symptom_search = f"""
                SELECT content, metadata, 0.7 as context_score
                FROM knowledge_base 
                WHERE content ILIKE ANY(ARRAY[%s])
                LIMIT %s
                """
                
                like_patterns = [f'%{symptom}%' for symptom in context_symptoms]
                symptom_result = self.db_manager.execute_query(symptom_search, (like_patterns, top_k // 2))
                
                if symptom_result['success'] and symptom_result['data']:
                    for row in symptom_result['data']:
                        results.append({
                            'source': 'contextual_search',
                            'content': row['content'],
                            'metadata': row.get('metadata', {}),
                            'score': 0.7,
                            'knowledge_type': 'symptom_context'
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"上下文搜索失败: {e}")
            return []
    
    def _merge_and_rank_results(self, all_results: List[Dict[str, Any]], 
                               query: str) -> List[Dict[str, Any]]:
        """合并和排序结果"""
        # 去重（基于内容相似性）
        unique_results = []
        seen_contents = set()
        
        for result in all_results:
            content_hash = hash(result['content'][:100])  # 使用前100字符作为去重依据
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_results.append(result)
        
        # 重新计算综合评分
        for result in unique_results:
            result['final_score'] = self._calculate_final_score(result, query)
        
        # 按综合评分排序
        unique_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        return unique_results
    
    def _calculate_final_score(self, result: Dict[str, Any], query: str) -> float:
        """计算最终评分"""
        base_score = result.get('score', 0.0)
        
        # 知识类型权重
        knowledge_type = result.get('knowledge_type', 'unknown')
        type_weight = self.knowledge_weights.get(knowledge_type, 0.5)
        
        # 来源权重
        source_weights = {
            'vector_search': 1.0,
            'faiss_search': 0.9,
            'keyword_search': 0.8,
            'contextual_search': 1.1  # 上下文搜索给予更高权重
        }
        source_weight = source_weights.get(result.get('source', ''), 0.5)
        
        # 内容长度惩罚（避免过长或过短的内容）
        content_length = len(result.get('content', ''))
        if content_length < 50:
            length_penalty = 0.7
        elif content_length > 2000:
            length_penalty = 0.8
        else:
            length_penalty = 1.0
        
        # 查询关键词匹配加分
        query_keywords = extract_keywords_from_query(query)
        content_text = result.get('content', '').lower()
        keyword_matches = sum(1 for kw in query_keywords if kw.lower() in content_text)
        keyword_bonus = min(keyword_matches * 0.1, 0.5)  # 最多加0.5分
        
        final_score = base_score * type_weight * source_weight * length_penalty + keyword_bonus
        
        return min(final_score, 1.0)  # 限制在1.0以内
    
    def _filter_and_optimize_results(self, results: List[Dict[str, Any]], 
                                   top_k: int) -> List[Dict[str, Any]]:
        """过滤和优化结果"""
        # 过滤低分结果
        filtered_results = [r for r in results if r['final_score'] > 0.3]
        
        # 限制数量
        filtered_results = filtered_results[:top_k]
        
        # 优化内容（截断过长内容）
        for result in filtered_results:
            content = result.get('content', '')
            if len(content) > 800:
                result['content'] = content[:800] + '...'
                result['is_truncated'] = True
            else:
                result['is_truncated'] = False
        
        return filtered_results
    
    def _generate_context_summary(self, results: List[Dict[str, Any]], 
                                 query: str) -> str:
        """生成上下文摘要"""
        if not results:
            return "未找到相关知识内容"
        
        summary_parts = []
        
        # 统计信息
        total_items = len(results)
        avg_score = np.mean([r['final_score'] for r in results])
        
        summary_parts.append(f"检索到{total_items}条相关知识")
        summary_parts.append(f"平均相关度{avg_score:.2f}")
        
        # 知识类型分布
        type_counts = {}
        for result in results:
            knowledge_type = result.get('knowledge_type', 'unknown')
            type_counts[knowledge_type] = type_counts.get(knowledge_type, 0) + 1
        
        if type_counts:
            type_summary = '，'.join([f"{k}({v}条)" for k, v in type_counts.items()])
            summary_parts.append(f"包含：{type_summary}")
        
        # 主要内容概览
        if results:
            top_result = results[0]
            content_preview = top_result['content'][:100]
            summary_parts.append(f"主要内容：{content_preview}...")
        
        return '；'.join(summary_parts)
    
    def get_knowledge_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        stats = {
            'total_items': 0,
            'by_type': {},
            'by_source': {},
            'last_updated': '',
            'index_status': {}
        }
        
        try:
            # 总数统计
            count_query = "SELECT COUNT(*) as total FROM knowledge_base"
            count_result = self.db_manager.execute_query(count_query)
            
            if count_result['success'] and count_result['data']:
                stats['total_items'] = count_result['data'][0]['total']
            
            # 按类型统计
            type_query = """
            SELECT metadata->>'type' as knowledge_type, COUNT(*) as count
            FROM knowledge_base 
            WHERE metadata->>'type' IS NOT NULL
            GROUP BY metadata->>'type'
            """
            type_result = self.db_manager.execute_query(type_query)
            
            if type_result['success'] and type_result['data']:
                for row in type_result['data']:
                    stats['by_type'][row['knowledge_type']] = row['count']
            
            # 获取向量索引状态
            vector_stats = safe_execute(
                self.vector_store.get_collection_stats,
                default_return={'total_vectors': 0, 'dimension': 0},
                error_message="获取向量索引状态失败"
            )
            stats['index_status']['vector_store'] = vector_stats
            
            # 获取FAISS索引状态
            faiss_stats = safe_execute(
                self.faiss_service.get_index_stats,
                default_return={'total_vectors': 0, 'index_size': 0},
                error_message="获取FAISS索引状态失败"
            )
            stats['index_status']['faiss'] = faiss_stats
            
        except Exception as e:
            logger.error(f"获取知识库统计失败: {e}")
        
        return stats
    
    def update_knowledge_item(self, item_id: str, content: str, 
                            metadata: Dict[str, Any] = None) -> bool:
        """更新知识项目"""
        try:
            update_query = """
            UPDATE knowledge_base 
            SET content = %s, metadata = %s, updated_at = %s
            WHERE id = %s
            """
            
            result = self.db_manager.execute_query(
                update_query,
                (content, metadata or {}, get_current_timestamp_iso(), item_id)
            )
            
            if result['success']:
                # 同步更新向量索引
                self._update_vector_index(item_id, content, metadata)
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"更新知识项目失败: {e}")
            return False
    
    def _update_vector_index(self, item_id: str, content: str, 
                           metadata: Dict[str, Any] = None):
        """更新向量索引"""
        try:
            # 更新PostgreSQL向量索引
            self.vector_store.update_document(item_id, content, metadata)
            
            # 更新FAISS索引（可能需要重建）
            # 这里可以实现增量更新逻辑
            logger.info(f"向量索引更新完成: {item_id}")
            
        except Exception as e:
            logger.error(f"向量索引更新失败: {e}")