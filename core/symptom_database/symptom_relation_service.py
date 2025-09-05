#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医症状关系数据库服务
提供症状关联查询、AI分析集成、智能缓存等功能
"""

import sqlite3
import json
import time
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SymptomRelation:
    """症状关系数据结构"""
    main_symptom: str
    related_symptom: str
    relationship_type: str  # direct/accompanying/concurrent/conditional
    confidence_score: float
    frequency: str  # common/frequent/occasional/rare
    source: str

@dataclass 
class SymptomCluster:
    """症状聚类结果"""
    cluster_name: str
    main_symptom: str
    related_symptoms: List[str]
    confidence_score: float

class SymptomRelationService:
    """症状关系服务 - 三层智能架构"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        self.db_path = db_path
        self.cache = {}  # 内存缓存
        self.cache_expiry = 300  # 5分钟缓存
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 执行建表SQL
                with open('database/migrations/003_create_symptom_database.sql', 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
                
                # 插入初始数据 (只在首次运行时)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tcm_diseases")
                if cursor.fetchone()[0] == 0:
                    with open('database/data/initial_symptom_data.sql', 'r', encoding='utf-8') as f:
                        conn.executescript(f.read())
                    logger.info("已初始化症状关系数据库")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    async def find_symptom_relations(self, main_symptom: str, context_symptoms: List[str] = None) -> List[SymptomRelation]:
        """
        智能症状关系查询 - 三层架构
        1. 内存缓存 (毫秒级)
        2. 数据库查询 (100ms级) 
        3. AI实时分析 (2-3s级)
        """
        cache_key = f"{main_symptom}_{','.join(sorted(context_symptoms or []))}"
        
        # 第一层：检查内存缓存
        if cache_key in self.cache:
            cache_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_expiry:
                logger.info(f"缓存命中: {main_symptom}")
                return cache_data
        
        # 第二层：数据库查询
        db_relations = await self._query_database_relations(main_symptom)
        if db_relations:
            logger.info(f"数据库命中: {main_symptom}, 找到 {len(db_relations)} 个关系")
            self.cache[cache_key] = (db_relations, time.time())
            return db_relations
        
        # 第三层：AI智能分析
        logger.info(f"启动AI分析: {main_symptom}")
        ai_relations = await self._ai_analyze_symptom_relations(main_symptom, context_symptoms)
        
        # 将AI结果存入数据库以供下次使用
        if ai_relations:
            await self._save_ai_relations_to_db(main_symptom, ai_relations)
            self.cache[cache_key] = (ai_relations, time.time())
        
        return ai_relations or []
    
    async def _query_database_relations(self, main_symptom: str) -> List[SymptomRelation]:
        """从数据库查询症状关系"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询直接关系和伴随关系
                query = """
                SELECT 
                    ms.name as main_symptom,
                    rs.name as related_symptom,
                    sr.relationship_type,
                    sr.confidence_score,
                    sr.frequency,
                    sr.source
                FROM symptom_relationships sr
                JOIN tcm_symptoms ms ON sr.main_symptom_id = ms.id
                JOIN tcm_symptoms rs ON sr.related_symptom_id = rs.id
                WHERE ms.name = ? 
                ORDER BY sr.confidence_score DESC, sr.frequency DESC
                """
                
                cursor.execute(query, (main_symptom,))
                results = cursor.fetchall()
                
                relations = []
                for row in results:
                    relations.append(SymptomRelation(
                        main_symptom=row[0],
                        related_symptom=row[1], 
                        relationship_type=row[2],
                        confidence_score=row[3],
                        frequency=row[4],
                        source=row[5]
                    ))
                
                return relations
                
        except Exception as e:
            logger.error(f"数据库查询失败: {e}")
            return []
    
    async def _ai_analyze_symptom_relations(self, main_symptom: str, context_symptoms: List[str] = None) -> List[SymptomRelation]:
        """AI智能分析症状关系"""
        try:
            # 临时简化实现 - 返回空结果，避免导入错误  
            logger.info(f"AI分析暂时禁用，主症状: {main_symptom}")
            return []
            
            # TODO: 后续集成真正的AI分析功能
            # from services.medical_diagnosis_controller import MedicalDiagnosisController
            # controller = MedicalDiagnosisController()
            
            # 构建AI分析提示
            context = f"主要症状: {main_symptom}"
            if context_symptoms:
                context += f"\n已有症状: {', '.join(context_symptoms)}"
            
            analysis_prompt = f"""
            请分析中医症状"{main_symptom}"的相关症状和伴随症状。

            {context}

            请返回JSON格式的分析结果:
            {{
                "direct_symptoms": ["直接相关症状1", "直接相关症状2"],
                "accompanying_symptoms": ["伴随症状1", "伴随症状2"],
                "confidence_score": 0.8
            }}

            要求:
            1. 基于中医理论分析
            2. 只返回临床常见的症状
            3. 每类症状不超过6个
            4. 置信度基于临床出现频率
            """
            
            # 暂时返回空结果
            return []
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return []
    
    def _parse_ai_response(self, main_symptom: str, ai_response: str) -> List[SymptomRelation]:
        """解析AI返回的症状关系"""
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_response)
            if not json_match:
                return []
            
            data = json.loads(json_match.group())
            relations = []
            
            # 处理直接相关症状
            for symptom in data.get('direct_symptoms', []):
                relations.append(SymptomRelation(
                    main_symptom=main_symptom,
                    related_symptom=symptom,
                    relationship_type='direct',
                    confidence_score=data.get('confidence_score', 0.7),
                    frequency='common',
                    source='ai'
                ))
            
            # 处理伴随症状
            for symptom in data.get('accompanying_symptoms', []):
                relations.append(SymptomRelation(
                    main_symptom=main_symptom,
                    related_symptom=symptom,
                    relationship_type='accompanying',
                    confidence_score=data.get('confidence_score', 0.7) * 0.8,
                    frequency='common',
                    source='ai'
                ))
            
            return relations
            
        except Exception as e:
            logger.error(f"AI响应解析失败: {e}")
            return []
    
    async def _save_ai_relations_to_db(self, main_symptom: str, relations: List[SymptomRelation]):
        """将AI分析结果保存到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for relation in relations:
                    # 首先确保症状存在于症状表中
                    cursor.execute(
                        "INSERT OR IGNORE INTO tcm_symptoms (name, category) VALUES (?, ?)",
                        (relation.main_symptom, '主症')
                    )
                    cursor.execute(
                        "INSERT OR IGNORE INTO tcm_symptoms (name, category) VALUES (?, ?)", 
                        (relation.related_symptom, '兼症')
                    )
                    
                    # 获取症状ID
                    cursor.execute("SELECT id FROM tcm_symptoms WHERE name = ?", (relation.main_symptom,))
                    main_id = cursor.fetchone()[0]
                    cursor.execute("SELECT id FROM tcm_symptoms WHERE name = ?", (relation.related_symptom,))
                    related_id = cursor.fetchone()[0]
                    
                    # 插入关系记录
                    cursor.execute("""
                        INSERT OR IGNORE INTO symptom_relationships 
                        (main_symptom_id, related_symptom_id, relationship_type, confidence_score, frequency, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (main_id, related_id, relation.relationship_type, 
                         relation.confidence_score, relation.frequency, relation.source))
                
                conn.commit()
                logger.info(f"AI关系已保存: {main_symptom}, {len(relations)}条记录")
                
        except Exception as e:
            logger.error(f"保存AI关系失败: {e}")
    
    async def _log_ai_analysis(self, main_symptom: str, context_symptoms: List[str], ai_response: str, response_time: int):
        """记录AI分析日志"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_symptom_analysis_log 
                    (query_symptom, context_symptoms, ai_response, response_time_ms)
                    VALUES (?, ?, ?, ?)
                """, (
                    main_symptom,
                    json.dumps(context_symptoms or [], ensure_ascii=False),
                    ai_response,
                    response_time
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"AI日志记录失败: {e}")
    
    def get_symptom_cluster(self, main_symptom: str) -> Optional[SymptomCluster]:
        """获取症状聚类信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT sc.cluster_name, ms.name, sc.related_symptoms, sc.confidence_score
                    FROM symptom_clusters sc
                    JOIN tcm_symptoms ms ON sc.main_symptom_id = ms.id  
                    WHERE ms.name = ?
                """, (main_symptom,))
                
                row = cursor.fetchone()
                if row:
                    related_symptoms = json.loads(row[2]) if row[2] else []
                    return SymptomCluster(
                        cluster_name=row[0],
                        main_symptom=row[1], 
                        related_symptoms=related_symptoms,
                        confidence_score=row[3]
                    )
        except Exception as e:
            logger.error(f"获取症状聚类失败: {e}")
        
        return None
    
    def get_database_stats(self) -> Dict:
        """获取数据库统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                cursor.execute("SELECT COUNT(*) FROM tcm_diseases")
                stats['diseases_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tcm_symptoms")
                stats['symptoms_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM symptom_relationships")
                stats['relationships_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM ai_symptom_analysis_log")
                stats['ai_queries_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT source, COUNT(*) FROM symptom_relationships GROUP BY source")
                stats['sources'] = dict(cursor.fetchall())
                
                return stats
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

# 全局服务实例
symptom_service = SymptomRelationService()