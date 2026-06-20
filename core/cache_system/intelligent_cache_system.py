# intelligent_cache_system.py - 智能缓存系统
"""
TCM智能缓存系统 - 提升AI响应速度和用户体验
功能：
1. 症状模式相似度缓存
2. 处方推荐缓存
3. 知识检索结果缓存
4. 过期策略和缓存更新
"""

import os
import json
import hashlib
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """缓存条目数据结构"""
    cache_key: str
    symptom_pattern: str
    ai_response: str
    doctor_selected: str
    retrieval_docs: List[str]
    similarity_score: float
    created_at: datetime
    access_count: int
    last_accessed: datetime
    user_rating: Optional[float] = None

@dataclass
class CacheStats:
    """缓存统计信息"""
    total_entries: int
    hit_rate: float
    avg_response_time: float
    cache_size_mb: float
    last_cleanup: datetime

class IntelligentCacheSystem:
    """智能缓存系统"""
    
    def __init__(self, cache_db_path: str = "./data/cache.sqlite", 
                 similarity_threshold: float = 0.85,
                 max_cache_entries: int = 10000,
                 cache_expiry_days: int = 30):
        
        self.cache_db_path = cache_db_path
        self.similarity_threshold = similarity_threshold
        self.max_cache_entries = max_cache_entries
        self.cache_expiry_days = cache_expiry_days
        
        # 确保目录存在
        os.makedirs(os.path.dirname(cache_db_path), exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        # TF-IDF向量化器用于相似度计算 - 针对中文优化
        self.vectorizer = TfidfVectorizer(
            analyzer='char',
            ngram_range=(1, 2),  # 降低ngram范围，提升中文匹配
            max_features=3000
        )
        
        # 缓存统计
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_queries = 0
        
        logger.info("智能缓存系统初始化完成")
    
    def _init_database(self):
        """初始化缓存数据库"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 创建缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                symptom_pattern TEXT NOT NULL,
                symptom_vector TEXT,
                ai_response TEXT NOT NULL,
                doctor_selected TEXT NOT NULL,
                retrieval_docs TEXT,
                similarity_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_rating REAL DEFAULT NULL
            )
        """)
        
        # 创建索引优化查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symptom_pattern 
            ON cache_entries(symptom_pattern)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_accessed 
            ON cache_entries(last_accessed)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_similarity_score 
            ON cache_entries(similarity_score DESC)
        """)
        
        # 创建缓存统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_stats (
                date TEXT PRIMARY KEY,
                total_queries INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                cache_misses INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0.0
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("缓存数据库初始化完成")
    
    def _generate_cache_key(self, symptom_pattern: str, doctor_selected: str, conversation_stage: str = "initial") -> str:
        """生成缓存键"""
        # 标准化症状描述
        normalized_symptoms = self._normalize_symptoms(symptom_pattern)
        combined_key = f"{normalized_symptoms}:{doctor_selected}:{conversation_stage}"
        return hashlib.md5(combined_key.encode('utf-8')).hexdigest()
    
    def _normalize_symptoms(self, symptom_text: str) -> str:
        """标准化症状描述"""
        # 去除标点符号和多余空格
        text = ''.join(char for char in symptom_text if char.isalnum() or char.isspace())
        
        # 使用jieba分词
        words = jieba.lcut(text.lower().strip())
        
        # 去除停用词和单字符词
        stop_words = {'的', '了', '是', '有', '在', '和', '与', '或', '但', '也', '还', '就', '都', '很', '更', '最', '我', '你', '他', '她', '它'}
        filtered_words = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 症状关键词标准化
        symptom_mapping = {
            '头疼': '头痛', '脑袋疼': '头痛', '头晕痛': '头痛',
            '发烧': '发热', '高热': '发热', '低热': '发热',
            '拉肚子': '腹泻', '大便溏': '腹泻', '水样便': '腹泻',
            '睡不着': '失眠', '不寐': '失眠', '多梦': '失眠',
            '咳': '咳嗽', '干咳': '咳嗽', '湿咳': '咳嗽'
        }
        
        normalized_words = [symptom_mapping.get(word, word) for word in filtered_words]
        
        return ' '.join(sorted(normalized_words))
    
    def _calculate_symptom_similarity(self, symptoms1: str, symptoms2: str) -> float:
        """计算症状相似度"""
        if not symptoms1 or not symptoms2:
            return 0.0
        
        try:
            # 使用TF-IDF向量化
            texts = [symptoms1, symptoms2]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # 计算余弦相似度
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"相似度计算失败: {e}")
            # 回退到简单字符匹配
            set1 = set(symptoms1.split())
            set2 = set(symptoms2.split())
            if not set1 and not set2:
                return 0.0
            return len(set1.intersection(set2)) / len(set1.union(set2))
    
    def get_cached_response(self, symptom_pattern: str, doctor_selected: str, conversation_stage: str = "initial") -> Optional[Tuple[str, List[str], float]]:
        """获取缓存的响应"""
        self.total_queries += 1
        
        # 先尝试精确匹配
        cache_key = self._generate_cache_key(symptom_pattern, doctor_selected, conversation_stage)
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 精确匹配查询
        cursor.execute("""
            SELECT ai_response, retrieval_docs, similarity_score, cache_key
            FROM cache_entries 
            WHERE cache_key = ? AND doctor_selected = ?
        """, (cache_key, doctor_selected))
        
        result = cursor.fetchone()
        
        if result:
            ai_response, retrieval_docs_json, similarity_score, found_key = result
            retrieval_docs = json.loads(retrieval_docs_json) if retrieval_docs_json else []
            
            # 更新访问统计
            self._update_access_stats(found_key)
            self.cache_hits += 1
            
            conn.close()
            logger.info(f"缓存命中(精确匹配): {cache_key}")
            return ai_response, retrieval_docs, 1.0
        
        # 相似度匹配查询
        normalized_symptoms = self._normalize_symptoms(symptom_pattern)
        
        cursor.execute("""
            SELECT cache_key, symptom_pattern, ai_response, retrieval_docs, 
                   similarity_score, access_count, user_rating
            FROM cache_entries 
            WHERE doctor_selected = ?
            ORDER BY access_count DESC, user_rating DESC NULLS LAST
            LIMIT 50
        """, (doctor_selected,))
        
        candidates = cursor.fetchall()
        conn.close()
        
        # 计算相似度并找到最佳匹配
        best_match = None
        best_similarity = 0.0
        
        for candidate in candidates:
            cache_key_cand, symptom_pattern_cand, ai_response, retrieval_docs_json, stored_sim, access_count, user_rating = candidate
            
            # 计算相似度
            similarity = self._calculate_symptom_similarity(normalized_symptoms, 
                                                          self._normalize_symptoms(symptom_pattern_cand))
            
            # 综合评分：相似度 + 访问次数权重 + 用户评分权重
            score = similarity * 0.7 + min(access_count / 100, 0.2) * 0.2
            if user_rating:
                score += (user_rating / 5.0) * 0.1
            
            if score > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = score
                best_match = (ai_response, retrieval_docs_json, similarity, cache_key_cand)
        
        if best_match:
            ai_response, retrieval_docs_json, similarity, matched_key = best_match
            retrieval_docs = json.loads(retrieval_docs_json) if retrieval_docs_json else []
            
            # 更新访问统计
            self._update_access_stats(matched_key)
            self.cache_hits += 1
            
            logger.info(f"缓存命中(相似度匹配): 相似度={similarity:.3f}")
            return ai_response, retrieval_docs, similarity
        
        self.cache_misses += 1
        logger.info("缓存未命中")
        return None
    
    def cache_response(self, symptom_pattern: str, doctor_selected: str, 
                      ai_response: str, retrieval_docs: List[str], 
                      user_rating: Optional[float] = None, conversation_stage: str = "initial"):
        """缓存AI响应"""
        cache_key = self._generate_cache_key(symptom_pattern, doctor_selected, conversation_stage)
        normalized_symptoms = self._normalize_symptoms(symptom_pattern)
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("SELECT cache_key FROM cache_entries WHERE cache_key = ?", (cache_key,))
        exists = cursor.fetchone()
        
        if exists:
            # 更新现有条目
            cursor.execute("""
                UPDATE cache_entries 
                SET ai_response = ?, retrieval_docs = ?, access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP, user_rating = ?
                WHERE cache_key = ?
            """, (ai_response, json.dumps(retrieval_docs, ensure_ascii=False), user_rating, cache_key))
        else:
            # 插入新条目
            cursor.execute("""
                INSERT INTO cache_entries 
                (cache_key, symptom_pattern, ai_response, doctor_selected, 
                 retrieval_docs, created_at, last_accessed, user_rating)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
            """, (cache_key, normalized_symptoms, ai_response, doctor_selected, 
                  json.dumps(retrieval_docs, ensure_ascii=False), user_rating))
        
        conn.commit()
        conn.close()
        
        # 检查缓存大小并清理
        self._cleanup_cache_if_needed()
        
        logger.info(f"响应已缓存: {cache_key}")
    
    def _update_access_stats(self, cache_key: str):
        """更新访问统计"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE cache_entries 
            SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
            WHERE cache_key = ?
        """, (cache_key,))
        
        conn.commit()
        conn.close()
    
    def _cleanup_cache_if_needed(self):
        """根据需要清理缓存"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 检查条目数量
        cursor.execute("SELECT COUNT(*) FROM cache_entries")
        count = cursor.fetchone()[0]
        
        if count > self.max_cache_entries:
            # 删除最老的20%条目（按访问时间和访问次数）
            delete_count = int(count * 0.2)
            cursor.execute("""
                DELETE FROM cache_entries 
                WHERE cache_key IN (
                    SELECT cache_key FROM cache_entries 
                    ORDER BY access_count ASC, last_accessed ASC 
                    LIMIT ?
                )
            """, (delete_count,))
            
            logger.info(f"清理了 {delete_count} 个旧缓存条目")
        
        # 删除过期条目
        expiry_date = datetime.now() - timedelta(days=self.cache_expiry_days)
        cursor.execute("""
            DELETE FROM cache_entries 
            WHERE created_at < ?
        """, (expiry_date,))
        
        expired_count = cursor.rowcount
        if expired_count > 0:
            logger.info(f"清理了 {expired_count} 个过期缓存条目")
        
        conn.commit()
        conn.close()
    
    def get_cache_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # 获取基本统计
        cursor.execute("SELECT COUNT(*) FROM cache_entries")
        total_entries = cursor.fetchone()[0]
        
        # 计算命中率
        hit_rate = 0.0
        if self.total_queries > 0:
            hit_rate = self.cache_hits / self.total_queries
        
        # 获取数据库文件大小
        try:
            cache_size_mb = os.path.getsize(self.cache_db_path) / (1024 * 1024)
        except:
            cache_size_mb = 0.0
        
        conn.close()
        
        return CacheStats(
            total_entries=total_entries,
            hit_rate=hit_rate,
            avg_response_time=0.0,  # 可以后续添加响应时间统计
            cache_size_mb=cache_size_mb,
            last_cleanup=datetime.now()
        )
    
    def update_user_rating(self, symptom_pattern: str, doctor_selected: str, rating: float):
        """更新用户评分"""
        cache_key = self._generate_cache_key(symptom_pattern, doctor_selected)
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE cache_entries 
            SET user_rating = ?
            WHERE cache_key = ?
        """, (rating, cache_key))
        
        conn.commit()
        conn.close()
        
        logger.info(f"更新用户评分: {cache_key} = {rating}")
    
    def get_popular_symptoms(self, limit: int = 20) -> List[Tuple[str, int]]:
        """获取热门症状模式"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symptom_pattern, SUM(access_count) as total_access
            FROM cache_entries 
            GROUP BY symptom_pattern
            ORDER BY total_access DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def clear_cache(self, older_than_days: Optional[int] = None):
        """清空缓存"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        if older_than_days:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            cursor.execute("DELETE FROM cache_entries WHERE created_at < ?", (cutoff_date,))
            logger.info(f"清除了 {older_than_days} 天前的缓存")
        else:
            cursor.execute("DELETE FROM cache_entries")
            logger.info("清空了所有缓存")
        
        conn.commit()
        conn.close()
        
        # 重置统计
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_queries = 0

# 全局缓存实例
cache_system = None

def get_cache_system() -> IntelligentCacheSystem:
    """获取全局缓存系统实例"""
    global cache_system
    if cache_system is None:
        cache_system = IntelligentCacheSystem()
    return cache_system

def init_cache_system(cache_db_path: str = "./data/cache.sqlite", 
                     similarity_threshold: float = 0.85) -> IntelligentCacheSystem:
    """初始化缓存系统"""
    global cache_system
    cache_system = IntelligentCacheSystem(cache_db_path, similarity_threshold)
    return cache_system