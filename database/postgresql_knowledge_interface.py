#!/usr/bin/env python3
# postgresql_knowledge_interface.py - PostgreSQL医生专用知识库接口

import psycopg2
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class PostgreSQLKnowledgeInterface:
    """PostgreSQL医生专用知识库接口"""
    

    def _handle_transaction_error(self, cursor, error):
        """处理PostgreSQL事务错误"""
        try:
            cursor.execute("ROLLBACK")
            logger.warning(f"事务回滚成功: {error}")
        except:
            pass
        
        # 重新开始事务
        try:
            cursor.execute("BEGIN")
        except:
            pass

    def __init__(self):
        try:
            self.pg_conn = psycopg2.connect(
                host="localhost",
                database="tcm_db",
                user="tcm_user",
                password="gE#5U&HBK6SC81DX"
            )
            self.cursor = self.pg_conn.cursor()
            
            # 医生映射
            self.doctor_mapping = {
                "zhang_zhongjing": 1,
                "li_dongyuan": 2,
                "ye_tianshi": 3,
                "liu_duzhou": 4,
                "zheng_qin_an": 5,
                "经方医生": 1,
                "脾胃医生": 2,
                "温病医生": 3,
                "经方派医生": 4,
                "扶阳派医生": 5
            }
            
            logger.info("PostgreSQL医生专用知识库接口初始化成功")
            
        except Exception as e:
            logger.error(f"PostgreSQL连接失败: {e}")
            self.pg_conn = None
            self.cursor = None
    
    def is_available(self) -> bool:
        """检查PostgreSQL接口是否可用"""
        return self.pg_conn is not None and self.cursor is not None
    
    async def search_doctor_specific_knowledge(self, query: str, selected_doctor: str, query_embedding: List[float] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """在指定医生的专用知识库中搜索（支持向量和全文搜索）"""
        
        if not self.is_available():
            return []
        
        try:
            doctor_id = self.doctor_mapping.get(selected_doctor, 1)
            knowledge_results = []
            
            # 优先使用向量搜索（如果有嵌入向量）
            if query_embedding:
                try:
                    # 向量相似度搜索
                    # 尝试使用向量相似度搜索，如果失败则降级到全文搜索
                    try:
                        self.cursor.execute("""
                            SELECT 
                                dkd.document_name,
                                dkd.content,
                                dkd.document_type,
                                dkd.source_book,
                                dkd.keywords,
                                1 - (dkd.content_embedding <-> %s::vector) as similarity
                            FROM doctor_knowledge_documents dkd
                            WHERE dkd.doctor_id = %s 
                              AND dkd.content_embedding IS NOT NULL
                            ORDER BY similarity DESC
                            LIMIT %s
                        """, (str(query_embedding), doctor_id, limit))
                    except Exception as vector_error:
                        logger.warning(f"向量搜索失败，使用全文搜索: {vector_error}")
                        # 开始新事务
                        self._handle_transaction_error(self.cursor, vector_error)
                        
                        # 降级到全文搜索
                        self.cursor.execute("""
                            SELECT 
                                dkd.document_name,
                                dkd.content,
                                dkd.document_type,
                                dkd.source_book,
                                dkd.keywords,
                                0.8 as similarity
                            FROM doctor_knowledge_documents dkd
                            WHERE dkd.doctor_id = %s 
                              AND (dkd.content ILIKE %s OR dkd.keywords ILIKE %s)
                            ORDER BY 
                                CASE 
                                    WHEN dkd.content ILIKE %s THEN 1
                                    WHEN dkd.keywords ILIKE %s THEN 2
                                    ELSE 3
                                END,
                                dkd.document_name
                            LIMIT %s
                        """, (doctor_id, f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))
                    
                    for row in self.cursor.fetchall():
                        doc_name, content, doc_type, source_book, keywords, similarity = row
                        if similarity > 0.3:  # 相似度阈值
                            knowledge_results.append({
                                "title": doc_name,
                                "content": content,
                                "type": doc_type,
                                "source": source_book,
                                "keywords": keywords,
                                "relevance_score": float(similarity),
                                "doctor_specific": True,
                                "search_method": "vector"
                            })
                    
                    logger.info(f"向量搜索找到 {len(knowledge_results)} 条结果")
                    
                except Exception as ve:
                    logger.warning(f"向量搜索失败，使用全文搜索: {ve}")
            
            # 如果向量搜索结果不足，补充全文搜索
            if len(knowledge_results) < limit:
                try:
                    # 提取关键词
                    keywords = self._extract_keywords(query)
                    search_terms = ' | '.join(keywords) if keywords else query.replace(' ', ' | ')
                    
                    remaining_limit = limit - len(knowledge_results)
                    
                    # 全文搜索 - 添加事务错误处理
                    try:
                        self.cursor.execute("""
                            SELECT 
                                dkd.document_name,
                                dkd.content,
                                dkd.document_type,
                                dkd.source_book,
                                dkd.keywords,
                                ts_rank(to_tsvector('simple', dkd.content), to_tsquery('simple', %s)) as rank
                            FROM doctor_knowledge_documents dkd
                            WHERE dkd.doctor_id = %s
                              AND to_tsvector('simple', dkd.content) @@ to_tsquery('simple', %s)
                            ORDER BY rank DESC, dkd.created_at DESC
                            LIMIT %s
                        """, (search_terms, doctor_id, search_terms, remaining_limit))
                    except Exception as fulltext_error:
                        logger.warning(f"全文搜索失败，使用简单LIKE搜索: {fulltext_error}")
                        # 处理事务错误
                        self._handle_transaction_error(self.cursor, fulltext_error)
                        
                        # 降级到简单LIKE搜索
                        self.cursor.execute("""
                            SELECT 
                                dkd.document_name,
                                dkd.content,
                                dkd.document_type,
                                dkd.source_book,
                                dkd.keywords,
                                0.6 as rank
                            FROM doctor_knowledge_documents dkd
                            WHERE dkd.doctor_id = %s
                              AND (dkd.content ILIKE %s OR dkd.keywords ILIKE %s OR dkd.document_name ILIKE %s)
                            ORDER BY 
                                CASE 
                                    WHEN dkd.document_name ILIKE %s THEN 1
                                    WHEN dkd.keywords ILIKE %s THEN 2
                                    WHEN dkd.content ILIKE %s THEN 3
                                    ELSE 4
                                END,
                                dkd.created_at DESC
                            LIMIT %s
                        """, (doctor_id, f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', remaining_limit))
                    
                    # 避免重复结果
                    existing_titles = {result["title"] for result in knowledge_results}
                    
                    for row in self.cursor.fetchall():
                        doc_name, content, doc_type, source_book, keywords, rank = row
                        if doc_name not in existing_titles:
                            knowledge_results.append({
                                "title": doc_name,
                                "content": content,
                                "type": doc_type,
                                "source": source_book,
                                "keywords": keywords,
                                "relevance_score": float(rank),
                                "doctor_specific": True,
                                "search_method": "fulltext"
                            })
                    
                    logger.info(f"全文搜索补充 {len(knowledge_results)} 条结果")
                    
                except Exception as fe:
                    logger.error(f"全文搜索也失败: {fe}")
            
            # 按相关性排序
            knowledge_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            logger.info(f"医生专用知识库搜索完成: {selected_doctor}, 总共找到 {len(knowledge_results)} 条结果")
            return knowledge_results[:limit]
            
        except Exception as e:
            logger.error(f"医生专用知识库搜索失败: {e}")
            return []
    
    def recommend_formula_by_symptoms(self, symptoms: str, selected_doctor: str) -> Optional[Dict[str, Any]]:
        """根据症状推荐该医生流派的方剂"""
        
        if not self.is_available():
            return None
        
        try:
            doctor_id = self.doctor_mapping.get(selected_doctor, 1)
            
            # 提取症状关键词
            symptom_keywords = self._extract_keywords(symptoms)
            
            # 搜索症状-方剂映射 (使用模糊匹配)
            self.cursor.execute("""
                SELECT 
                    sfm.symptom_pattern,
                    sfm.confidence_score,
                    df.formula_name,
                    df.composition,
                    df.indications,
                    df.dosage,
                    df.clinical_notes,
                    df.source_classic
                FROM symptom_formula_mapping sfm
                JOIN doctor_formulas df ON sfm.formula_id = df.id
                WHERE sfm.doctor_id = %s
                  AND (
                    %s ILIKE '%%' || REPLACE(sfm.symptom_pattern, ',', '%%') || '%%'
                    OR sfm.symptom_pattern ILIKE ANY(%s)
                  )
                ORDER BY sfm.confidence_score DESC
                LIMIT 1
            """, (doctor_id, symptoms, ['%' + kw + '%' for kw in symptom_keywords[:3]]))
            
            result = self.cursor.fetchone()
            if result:
                pattern, confidence, name, composition, indications, dosage, notes, source = result
                
                return {
                    "formula_name": name,
                    "composition": composition,
                    "indications": indications,
                    "dosage": dosage,
                    "clinical_notes": notes,
                    "source_classic": source,
                    "matched_pattern": pattern,
                    "confidence_score": float(confidence),
                    "doctor_recommendation": True
                }
            
            return None
            
        except Exception as e:
            logger.error(f"方剂推荐失败: {e}")
            return None
    
    def get_doctor_expertise_summary(self, selected_doctor: str) -> Dict[str, Any]:
        """获取医生专长总结"""
        
        if not self.is_available():
            return {}
        
        try:
            doctor_id = self.doctor_mapping.get(selected_doctor, 1)
            
            # 获取医生基本信息
            self.cursor.execute("""
                SELECT name, school, specialty, description
                FROM doctors WHERE id = %s
            """, (doctor_id,))
            
            doctor_info = self.cursor.fetchone()
            if not doctor_info:
                return {}
            
            name, school, specialty, description = doctor_info
            
            # 统计知识库内容
            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT dkd.id) as knowledge_count,
                    COUNT(DISTINCT df.id) as formula_count,
                    COUNT(DISTINCT sfm.id) as mapping_count,
                    array_agg(DISTINCT df.source_classic) as source_classics
                FROM doctors d
                LEFT JOIN doctor_knowledge_documents dkd ON d.id = dkd.doctor_id
                LEFT JOIN doctor_formulas df ON d.id = df.doctor_id
                LEFT JOIN symptom_formula_mapping sfm ON d.id = sfm.doctor_id
                WHERE d.id = %s
                GROUP BY d.id
            """, (doctor_id,))
            
            stats = self.cursor.fetchone()
            if stats:
                knowledge_count, formula_count, mapping_count, source_classics = stats
                
                return {
                    "doctor_name": name,
                    "school": school,
                    "specialty": specialty,
                    "description": description,
                    "knowledge_stats": {
                        "medical_cases": knowledge_count or 0,
                        "formulas": formula_count or 0,
                        "symptom_mappings": mapping_count or 0,
                        "source_classics": [c for c in (source_classics or []) if c]
                    },
                    "data_source": "postgresql_specialized"
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"获取医生专长失败: {e}")
            return {}
    
    def save_consultation_to_postgresql(self, conversation_id: str, user_message: str, ai_response: str, selected_doctor: str) -> bool:
        """保存新的咨询记录到PostgreSQL"""
        
        if not self.is_available():
            return False
        
        try:
            doctor_id = self.doctor_mapping.get(selected_doctor, 1)
            
            # 获取或创建用户
            user_id = self._get_or_create_user()
            
            # 创建会话记录
            self.cursor.execute("""
                INSERT INTO consultations (conversation_id, user_id, doctor_id, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (conversation_id) DO UPDATE SET updated_at = EXCLUDED.updated_at
                RETURNING id
            """, (conversation_id, user_id, doctor_id, 'active', datetime.now(), datetime.now()))
            
            consultation_id = self.cursor.fetchone()[0]
            
            # 保存用户消息
            self.cursor.execute("""
                INSERT INTO consultation_messages (consultation_id, sender, content, message_type, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (consultation_id, 'user', user_message, 'text', datetime.now()))
            
            # 保存AI回复
            self.cursor.execute("""
                INSERT INTO consultation_messages (consultation_id, sender, content, message_type, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (consultation_id, 'ai', ai_response, 'text', datetime.now()))
            
            self.pg_conn.commit()
            logger.info(f"咨询记录已保存到PostgreSQL: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存咨询记录失败: {e}")
            try:
                self.pg_conn.rollback()
            except Exception as rollback_error:
                logger.warning(f"回滚失败: {rollback_error}")
                # 重新创建连接
                try:
                    self.pg_conn.close()
                except:
                    pass
                try:
                    self.__init__()
                except:
                    pass
            return False
    
    def get_consultation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取会话历史记录"""
        
        if not self.is_available():
            return []
        
        try:
            self.cursor.execute("""
                SELECT cm.sender, cm.content, cm.created_at
                FROM consultations c
                JOIN consultation_messages cm ON c.id = cm.consultation_id
                WHERE c.conversation_id = %s
                ORDER BY cm.created_at ASC
            """, (conversation_id,))
            
            history = []
            for row in self.cursor.fetchall():
                sender, content, created_at = row
                history.append({
                    "role": "assistant" if sender == "ai" else "user",
                    "content": content,
                    "timestamp": created_at.isoformat() if created_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取中医相关关键词"""
        
        # 中医术语关键词
        tcm_keywords = [
            # 症状
            "头痛", "发热", "恶寒", "恶风", "汗出", "无汗", "咳嗽", "喘急", "胸胁苦满", 
            "往来寒热", "心烦", "口苦", "咽干", "目眩", "神疲", "乏力", "少气", "懒言",
            "食少", "便溏", "腹泻", "便秘", "失眠", "多梦", "心悸", "怔忡",
            
            # 舌脉
            "脉浮", "脉沉", "脉缓", "脉紧", "脉弦", "脉数", "脉迟", "舌淡", "舌红", "舌绛",
            "苔薄", "苔厚", "苔白", "苔黄", "苔腻",
            
            # 方剂
            "桂枝汤", "麻黄汤", "小柴胡汤", "补中益气汤", "升阳散火汤", "银翘散", "清营汤",
            
            # 证候
            "营卫不和", "卫分证", "营分证", "血分证", "脾胃气虚", "清阳不升", "阴火上炎"
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in tcm_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:5]  # 限制关键词数量
    
    def _get_or_create_user(self) -> int:
        """获取或创建匿名用户"""
        import uuid
        
        user_id = f"anonymous_{uuid.uuid4().hex[:8]}"
        
        self.cursor.execute("""
            INSERT INTO users (user_id, created_at, last_active)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, datetime.now(), datetime.now()))
        
        return self.cursor.fetchone()[0]
    
    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.pg_conn:
            self.pg_conn.close()

class HybridKnowledgeSystem:
    """混合知识库系统 - 整合PostgreSQL和原有FAISS系统"""
    
    def __init__(self, faiss_knowledge_retrieval=None):
        self.postgresql_interface = PostgreSQLKnowledgeInterface()
        self.faiss_retrieval = faiss_knowledge_retrieval
        self.use_postgresql = self.postgresql_interface.is_available()
        
        logger.info(f"混合知识库系统初始化: PostgreSQL={'可用' if self.use_postgresql else '不可用'}, FAISS={'可用' if self.faiss_retrieval else '不可用'}")
    
    async def search_knowledge(self, query: str, selected_doctor: str, query_embedding: List[float] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """混合知识库搜索（支持向量搜索）"""
        
        results = []
        
        # 优先使用PostgreSQL医生专用知识库（支持向量搜索）
        if self.use_postgresql:
            pg_results = await self.postgresql_interface.search_doctor_specific_knowledge(
                query, selected_doctor, query_embedding=query_embedding, limit=top_k//2 + 1
            )
            results.extend(pg_results)
            
            logger.info(f"PostgreSQL搜索结果: {len(pg_results)}条")
        
        # 如果PostgreSQL结果不足，补充FAISS结果
        if len(results) < top_k and self.faiss_retrieval:
            try:
                remaining_count = top_k - len(results)
                faiss_results = self.faiss_retrieval.hybrid_search(
                    query=query,
                    query_embedding=query_embedding or [],  
                    total_results=remaining_count
                )
                
                # 转换FAISS结果格式
                for result in faiss_results:
                    results.append({
                        "title": f"传统知识库-{result.get('chunk_id', 'Unknown')}",
                        "content": result.get('content', ''),
                        "type": "traditional",
                        "source": "综合知识库",
                        "relevance_score": result.get('score', 0.5),
                        "doctor_specific": False,
                        "search_method": "faiss"
                    })
                
                logger.info(f"FAISS补充结果: {len(faiss_results)}条")
                
            except Exception as e:
                logger.error(f"FAISS搜索失败: {e}")
        
        # 按相关性评分排序
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return results[:top_k]
    
    def get_formula_recommendation(self, symptoms: str, selected_doctor: str) -> Optional[Dict[str, Any]]:
        """获取方剂推荐"""
        
        if self.use_postgresql:
            return self.postgresql_interface.recommend_formula_by_symptoms(symptoms, selected_doctor)
        return None
    
    def get_doctor_info(self, selected_doctor: str) -> Dict[str, Any]:
        """获取医生信息"""
        
        if self.use_postgresql:
            return self.postgresql_interface.get_doctor_expertise_summary(selected_doctor)
        return {}
    
    def save_consultation(self, conversation_id: str, user_message: str, ai_response: str, selected_doctor: str) -> bool:
        """保存咨询记录"""
        
        if self.use_postgresql:
            return self.postgresql_interface.save_consultation_to_postgresql(
                conversation_id, user_message, ai_response, selected_doctor
            )
        return False
    
    def close(self):
        """关闭连接"""
        if self.postgresql_interface:
            self.postgresql_interface.close()

# 全局实例
_hybrid_knowledge_system = None

def get_hybrid_knowledge_system(faiss_retrieval=None):
    """获取混合知识库系统实例"""
    global _hybrid_knowledge_system
    if _hybrid_knowledge_system is None:
        _hybrid_knowledge_system = HybridKnowledgeSystem(faiss_retrieval)
    return _hybrid_knowledge_system