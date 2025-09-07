# personalized_learning.py - 个性化学习系统

import os
import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

@dataclass
class UserFeedback:
    """用户反馈数据结构"""
    session_id: str
    user_query: str
    selected_doctor: str
    ai_response: str
    user_rating: int  # 1-5分评分
    feedback_text: Optional[str]  # 用户文字反馈
    timestamp: datetime
    user_id: Optional[str] = None
    
@dataclass
class DoctorPerformance:
    """医生表现统计"""
    doctor_name: str
    total_sessions: int
    average_rating: float
    positive_feedback_count: int
    negative_feedback_count: int
    preferred_symptoms: List[str]  # 擅长处理的症状
    improvement_areas: List[str]  # 需要改进的领域

@dataclass
class LearningInsight:
    """学习洞察"""
    insight_type: str  # 洞察类型：symptom_preference, formula_effectiveness, etc.
    doctor_name: str
    content: Dict
    confidence_score: float
    sample_size: int
    last_updated: datetime

class PersonalizedLearningSystem:
    """个性化学习系统"""
    
    def __init__(self, db_path: str = "/home/tcm-app/learning_db.sqlite"):
        self.db_path = db_path
        self.init_database()
        
        # 学习参数
        self.min_feedback_for_learning = 5  # 最少反馈数量才开始学习
        self.rating_threshold = 3.5  # 好评阈值
        self.confidence_threshold = 0.7  # 置信度阈值
        
        # 症状-医生适配度缓存
        self.symptom_doctor_cache = {}
        self.cache_expiry = timedelta(hours=24)
        self.last_cache_update = None
        
    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 用户反馈表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_query TEXT NOT NULL,
                    selected_doctor TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    user_rating INTEGER NOT NULL,
                    feedback_text TEXT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT
                )
            ''')
            
            # 医生表现统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS doctor_performance (
                    doctor_name TEXT PRIMARY KEY,
                    total_sessions INTEGER DEFAULT 0,
                    total_rating_sum INTEGER DEFAULT 0,
                    positive_feedback_count INTEGER DEFAULT 0,
                    negative_feedback_count INTEGER DEFAULT 0,
                    last_updated TEXT
                )
            ''')
            
            # 学习洞察表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight_type TEXT NOT NULL,
                    doctor_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # 症状-医生匹配表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS symptom_doctor_match (
                    symptom TEXT NOT NULL,
                    doctor_name TEXT NOT NULL,
                    success_rate REAL NOT NULL,
                    total_cases INTEGER NOT NULL,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (symptom, doctor_name)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Learning database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize learning database: {e}")
            
    def record_feedback(self, feedback: UserFeedback):
        """记录用户反馈"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_feedback 
                (session_id, user_query, selected_doctor, ai_response, user_rating, feedback_text, timestamp, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                feedback.session_id,
                feedback.user_query,
                feedback.selected_doctor,
                feedback.ai_response,
                feedback.user_rating,
                feedback.feedback_text,
                feedback.timestamp.isoformat(),
                feedback.user_id
            ))
            
            conn.commit()
            conn.close()
            
            # 触发学习更新
            self._update_doctor_performance(feedback)
            self._update_symptom_doctor_matching(feedback)
            
            logger.info(f"Recorded feedback for session {feedback.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            
    def _update_doctor_performance(self, feedback: UserFeedback):
        """更新医生表现统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新或插入医生表现数据
            cursor.execute('''
                INSERT OR REPLACE INTO doctor_performance 
                (doctor_name, total_sessions, total_rating_sum, positive_feedback_count, negative_feedback_count, last_updated)
                VALUES (
                    ?,
                    COALESCE((SELECT total_sessions FROM doctor_performance WHERE doctor_name = ?), 0) + 1,
                    COALESCE((SELECT total_rating_sum FROM doctor_performance WHERE doctor_name = ?), 0) + ?,
                    COALESCE((SELECT positive_feedback_count FROM doctor_performance WHERE doctor_name = ?), 0) + ?,
                    COALESCE((SELECT negative_feedback_count FROM doctor_performance WHERE doctor_name = ?), 0) + ?,
                    ?
                )
            ''', (
                feedback.selected_doctor,
                feedback.selected_doctor,
                feedback.selected_doctor,
                feedback.user_rating,
                feedback.selected_doctor,
                1 if feedback.user_rating >= 4 else 0,
                feedback.selected_doctor,
                1 if feedback.user_rating <= 2 else 0,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update doctor performance: {e}")
            
    def _update_symptom_doctor_matching(self, feedback: UserFeedback):
        """更新症状-医生匹配度"""
        try:
            # 从用户查询中提取症状关键词
            symptoms = self._extract_symptoms(feedback.user_query)
            if not symptoms:
                return
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for symptom in symptoms:
                # 计算成功率（评分>=4算成功）
                is_success = 1 if feedback.user_rating >= 4 else 0
                
                # 更新症状-医生匹配数据
                cursor.execute('''
                    SELECT total_cases, success_rate FROM symptom_doctor_match 
                    WHERE symptom = ? AND doctor_name = ?
                ''', (symptom, feedback.selected_doctor))
                
                result = cursor.fetchone()
                if result:
                    total_cases, old_success_rate = result
                    new_total_cases = total_cases + 1
                    new_success_rate = (old_success_rate * total_cases + is_success) / new_total_cases
                    
                    cursor.execute('''
                        UPDATE symptom_doctor_match 
                        SET success_rate = ?, total_cases = ?, last_updated = ?
                        WHERE symptom = ? AND doctor_name = ?
                    ''', (new_success_rate, new_total_cases, datetime.now().isoformat(), symptom, feedback.selected_doctor))
                else:
                    cursor.execute('''
                        INSERT INTO symptom_doctor_match 
                        (symptom, doctor_name, success_rate, total_cases, last_updated)
                        VALUES (?, ?, ?, 1, ?)
                    ''', (symptom, feedback.selected_doctor, float(is_success), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update symptom-doctor matching: {e}")
            
    def _extract_symptoms(self, query: str) -> List[str]:
        """从查询中提取症状关键词"""
        # 中医常见症状词典
        symptom_keywords = [
            "头痛", "头晕", "发热", "咳嗽", "胸闷", "心悸", "失眠", "多梦",
            "便秘", "腹泻", "恶心", "呕吐", "食欲", "乏力", "疲劳", "出汗",
            "口干", "口苦", "舌苔", "脉象", "腰痛", "关节痛", "水肿",
            "月经", "白带", "小便", "大便", "咽痛", "鼻塞", "流涕"
        ]
        
        found_symptoms = []
        query_lower = query.lower()
        
        for symptom in symptom_keywords:
            if symptom in query_lower:
                found_symptoms.append(symptom)
                
        return found_symptoms
        
    def recommend_doctor(self, user_query: str, available_doctors: List[str] = None) -> Tuple[str, float]:
        """基于学习数据推荐医生"""
        try:
            symptoms = self._extract_symptoms(user_query)
            if not symptoms:
                # 如果没有识别到症状，返回默认推荐
                return "zhang_zhongjing", 0.5
                
            # 更新缓存
            self._update_symptom_cache()
            
            doctor_scores = defaultdict(list)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for symptom in symptoms:
                cursor.execute('''
                    SELECT doctor_name, success_rate, total_cases 
                    FROM symptom_doctor_match 
                    WHERE symptom = ? AND total_cases >= ?
                    ORDER BY success_rate DESC
                ''', (symptom, self.min_feedback_for_learning))
                
                results = cursor.fetchall()
                for doctor_name, success_rate, total_cases in results:
                    if not available_doctors or doctor_name in available_doctors:
                        # 加权评分：成功率 * 样本量权重
                        weight = min(total_cases / 20, 1.0)  # 样本量权重，最大1.0
                        weighted_score = success_rate * (0.7 + 0.3 * weight)
                        doctor_scores[doctor_name].append(weighted_score)
            
            conn.close()
            
            if not doctor_scores:
                return "zhang_zhongjing", 0.5
                
            # 计算每个医生的平均分数
            final_scores = {}
            for doctor, scores in doctor_scores.items():
                final_scores[doctor] = np.mean(scores)
                
            # 返回得分最高的医生
            best_doctor = max(final_scores, key=final_scores.get)
            confidence = final_scores[best_doctor]
            
            logger.info(f"Recommended doctor: {best_doctor} with confidence: {confidence:.3f}")
            return best_doctor, confidence
            
        except Exception as e:
            logger.error(f"Failed to recommend doctor: {e}")
            return "zhang_zhongjing", 0.5
            
    def _update_symptom_cache(self):
        """更新症状-医生缓存"""
        if (self.last_cache_update and 
            datetime.now() - self.last_cache_update < self.cache_expiry):
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT symptom, doctor_name, success_rate, total_cases 
                FROM symptom_doctor_match 
                WHERE total_cases >= ?
            ''', (self.min_feedback_for_learning,))
            
            self.symptom_doctor_cache = {}
            for symptom, doctor_name, success_rate, total_cases in cursor.fetchall():
                if symptom not in self.symptom_doctor_cache:
                    self.symptom_doctor_cache[symptom] = []
                self.symptom_doctor_cache[symptom].append({
                    'doctor': doctor_name,
                    'success_rate': success_rate,
                    'total_cases': total_cases
                })
            
            # 按成功率排序
            for symptom in self.symptom_doctor_cache:
                self.symptom_doctor_cache[symptom].sort(
                    key=lambda x: x['success_rate'], reverse=True
                )
            
            self.last_cache_update = datetime.now()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update symptom cache: {e}")
            
    def get_doctor_performance(self, doctor_name: str) -> Optional[DoctorPerformance]:
        """获取医生表现统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT total_sessions, total_rating_sum, positive_feedback_count, negative_feedback_count
                FROM doctor_performance 
                WHERE doctor_name = ?
            ''', (doctor_name,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            total_sessions, total_rating_sum, positive_count, negative_count = result
            average_rating = total_rating_sum / total_sessions if total_sessions > 0 else 0
            
            # 获取擅长的症状
            cursor.execute('''
                SELECT symptom, success_rate FROM symptom_doctor_match 
                WHERE doctor_name = ? AND success_rate >= ? AND total_cases >= ?
                ORDER BY success_rate DESC LIMIT 5
            ''', (doctor_name, 0.7, self.min_feedback_for_learning))
            
            preferred_symptoms = [row[0] for row in cursor.fetchall()]
            
            # 获取需要改进的领域
            cursor.execute('''
                SELECT symptom, success_rate FROM symptom_doctor_match 
                WHERE doctor_name = ? AND success_rate < ? AND total_cases >= ?
                ORDER BY success_rate ASC LIMIT 3
            ''', (doctor_name, 0.5, self.min_feedback_for_learning))
            
            improvement_areas = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            return DoctorPerformance(
                doctor_name=doctor_name,
                total_sessions=total_sessions,
                average_rating=average_rating,
                positive_feedback_count=positive_count,
                negative_feedback_count=negative_count,
                preferred_symptoms=preferred_symptoms,
                improvement_areas=improvement_areas
            )
            
        except Exception as e:
            logger.error(f"Failed to get doctor performance: {e}")
            return None
            
    def generate_learning_insights(self) -> List[LearningInsight]:
        """生成学习洞察"""
        insights = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 洞察1：最佳症状-医生匹配
            cursor.execute('''
                SELECT symptom, doctor_name, success_rate, total_cases
                FROM symptom_doctor_match 
                WHERE success_rate >= ? AND total_cases >= ?
                ORDER BY success_rate DESC, total_cases DESC
                LIMIT 10
            ''', (0.8, self.min_feedback_for_learning * 2))
            
            best_matches = cursor.fetchall()
            if best_matches:
                insights.append(LearningInsight(
                    insight_type="best_symptom_doctor_matches",
                    doctor_name="all",
                    content={"matches": best_matches},
                    confidence_score=0.9,
                    sample_size=len(best_matches),
                    last_updated=datetime.now()
                ))
            
            # 洞察2：需要关注的低表现组合
            cursor.execute('''
                SELECT symptom, doctor_name, success_rate, total_cases
                FROM symptom_doctor_match 
                WHERE success_rate < ? AND total_cases >= ?
                ORDER BY success_rate ASC, total_cases DESC
                LIMIT 5
            ''', (0.4, self.min_feedback_for_learning))
            
            poor_matches = cursor.fetchall()
            if poor_matches:
                insights.append(LearningInsight(
                    insight_type="poor_symptom_doctor_matches",
                    doctor_name="all",
                    content={"matches": poor_matches},
                    confidence_score=0.8,
                    sample_size=len(poor_matches),
                    last_updated=datetime.now()
                ))
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to generate learning insights: {e}")
            
        return insights
        
    def get_adaptive_weights(self, doctor_name: str) -> Dict[str, float]:
        """获取自适应权重"""
        performance = self.get_doctor_performance(doctor_name)
        if not performance or performance.total_sessions < self.min_feedback_for_learning:
            return {"semantic_weight": 0.6, "keyword_weight": 0.4}
            
        # 根据医生表现调整权重
        if performance.average_rating >= 4.0:
            # 高评分医生，更信任语义理解
            return {"semantic_weight": 0.7, "keyword_weight": 0.3}
        elif performance.average_rating <= 3.0:
            # 低评分医生，更依赖关键词匹配
            return {"semantic_weight": 0.5, "keyword_weight": 0.5}
        else:
            # 平均表现，平衡权重
            return {"semantic_weight": 0.6, "keyword_weight": 0.4}

# 使用示例
def demo_learning_system():
    """演示个性化学习系统"""
    learning_system = PersonalizedLearningSystem()
    
    # 模拟用户反馈
    feedback = UserFeedback(
        session_id="test_session_001",
        user_query="八岁女孩长期便秘怎么办",
        selected_doctor="li_dongyuan",
        ai_response="建议使用补中益气汤...",
        user_rating=5,
        feedback_text="回答很专业，很有帮助",
        timestamp=datetime.now()
    )
    
    # 记录反馈
    learning_system.record_feedback(feedback)
    
    # 推荐医生
    recommended_doctor, confidence = learning_system.recommend_doctor("小孩便秘问题")
    print(f"推荐医生: {recommended_doctor}, 置信度: {confidence:.3f}")
    
    # 获取医生表现
    performance = learning_system.get_doctor_performance("li_dongyuan")
    if performance:
        print(f"医生表现: 平均评分 {performance.average_rating:.2f}, 总会话 {performance.total_sessions}")
    
    # 生成学习洞察
    insights = learning_system.generate_learning_insights()
    for insight in insights:
        print(f"洞察类型: {insight.insight_type}, 置信度: {insight.confidence_score:.3f}")

if __name__ == "__main__":
    demo_learning_system()