#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
患者评价管理系统 - 智汇中医工作流核心模块
支持多维度评价、匿名评价、医生回复等功能
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import sqlite3
import json
from config.settings import PATHS

logger = logging.getLogger(__name__)

@dataclass
class PatientReview:
    """患者评价数据类"""
    uuid: str
    consultation_id: str
    patient_id: str
    doctor_id: str
    overall_rating: int
    professional_score: int = None
    service_score: int = None
    effect_score: int = None
    review_content: str = ""
    is_anonymous: bool = False
    is_visible: bool = True
    doctor_reply: str = ""
    doctor_reply_time: datetime = None
    helpful_count: int = 0
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class ReviewSummary:
    """评价汇总数据类"""
    doctor_id: str
    total_reviews: int
    average_rating: float
    rating_distribution: Dict[int, int]  # {5: 50, 4: 30, 3: 15, 2: 3, 1: 2}
    professional_avg: float
    service_avg: float
    effect_avg: float
    recent_reviews: List[PatientReview]

class ReviewManager:
    """评价管理服务类"""
    
    def __init__(self):
        self.db_path = PATHS['user_db']
    
    def create_review(self, consultation_id: str, patient_id: str, 
                     review_data: Dict[str, Any]) -> Optional[PatientReview]:
        """创建患者评价"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取医生ID
                doctor_id = conn.execute("""
                    SELECT selected_doctor_id FROM consultations 
                    WHERE uuid = ?
                """, (consultation_id,)).fetchone()
                
                if not doctor_id or not doctor_id[0]:
                    logger.error(f"未找到问诊记录或医生信息: {consultation_id}")
                    return None
                
                doctor_id = doctor_id[0]
                
                # 检查是否已存在评价
                existing = conn.execute("""
                    SELECT uuid FROM patient_reviews 
                    WHERE consultation_id = ? AND patient_id = ?
                """, (consultation_id, patient_id)).fetchone()
                
                if existing:
                    logger.warning(f"患者已对此次问诊进行过评价: {consultation_id}")
                    return None
                
                # 创建评价记录
                review_uuid = f"review-{datetime.now().strftime('%Y%m%d%H%M%S')}-{patient_id[:8]}"
                
                review = PatientReview(
                    uuid=review_uuid,
                    consultation_id=consultation_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    overall_rating=review_data.get('overall_rating', 5),
                    professional_score=review_data.get('professional_score'),
                    service_score=review_data.get('service_score'),
                    effect_score=review_data.get('effect_score'),
                    review_content=review_data.get('review_content', '').strip(),
                    is_anonymous=review_data.get('is_anonymous', False),
                    is_visible=True,
                    created_at=datetime.now()
                )
                
                # 插入数据库
                conn.execute("""
                    INSERT INTO patient_reviews (
                        uuid, consultation_id, patient_id, doctor_id,
                        overall_rating, professional_score, service_score, effect_score,
                        review_content, is_anonymous, is_visible, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    review.uuid, review.consultation_id, review.patient_id, review.doctor_id,
                    review.overall_rating, review.professional_score, review.service_score, 
                    review.effect_score, review.review_content, review.is_anonymous,
                    review.is_visible, review.created_at
                ))
                
                # 同时更新问诊记录中的评价信息
                conn.execute("""
                    UPDATE consultations SET
                        patient_rating = ?,
                        patient_review = ?,
                        review_created_at = ?
                    WHERE uuid = ?
                """, (review.overall_rating, review.review_content, review.created_at, consultation_id))
                
                conn.commit()
                
                logger.info(f"评价创建成功: {review_uuid} (医生: {doctor_id}, 评分: {review.overall_rating})")
                return review
                
        except Exception as e:
            logger.error(f"创建评价失败: {e}")
            return None
    
    def get_doctor_reviews(self, doctor_id: str, limit: int = 20, 
                          offset: int = 0, include_invisible: bool = False) -> List[PatientReview]:
        """获取医生的评价列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                where_clause = "WHERE doctor_id = ?"
                params = [doctor_id]
                
                if not include_invisible:
                    where_clause += " AND is_visible = 1"
                
                query = f"""
                    SELECT r.*
                    FROM patient_reviews r
                    {where_clause}
                    ORDER BY r.created_at DESC
                    LIMIT ? OFFSET ?
                """
                
                params.extend([limit, offset])
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                reviews = []
                for row in rows:
                    review = PatientReview(
                        uuid=row['uuid'],
                        consultation_id=row['consultation_id'],
                        patient_id=row['patient_id'],
                        doctor_id=row['doctor_id'],
                        overall_rating=row['overall_rating'],
                        professional_score=row['professional_score'],
                        service_score=row['service_score'],
                        effect_score=row['effect_score'],
                        review_content=row['review_content'] or '',
                        is_anonymous=bool(row['is_anonymous']),
                        is_visible=bool(row['is_visible']),
                        doctor_reply=row['doctor_reply'] or '',
                        doctor_reply_time=datetime.fromisoformat(row['doctor_reply_time']) if row['doctor_reply_time'] else None,
                        helpful_count=row['helpful_count'] or 0,
                        created_at=datetime.fromisoformat(row['created_at']),
                        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                    )
                    reviews.append(review)
                
                return reviews
                
        except Exception as e:
            logger.error(f"获取医生评价失败: {e}")
            return []
    
    def get_review_summary(self, doctor_id: str) -> Optional[ReviewSummary]:
        """获取医生评价汇总统计"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 获取基础统计数据
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_reviews,
                        AVG(overall_rating) as average_rating,
                        AVG(professional_score) as professional_avg,
                        AVG(service_score) as service_avg,
                        AVG(effect_score) as effect_avg
                    FROM patient_reviews
                    WHERE doctor_id = ? AND is_visible = 1
                """, (doctor_id,)).fetchone()
                
                if not stats or stats['total_reviews'] == 0:
                    return ReviewSummary(
                        doctor_id=doctor_id,
                        total_reviews=0,
                        average_rating=0.0,
                        rating_distribution={},
                        professional_avg=0.0,
                        service_avg=0.0,
                        effect_avg=0.0,
                        recent_reviews=[]
                    )
                
                # 获取评分分布
                rating_dist = conn.execute("""
                    SELECT overall_rating, COUNT(*) as count
                    FROM patient_reviews
                    WHERE doctor_id = ? AND is_visible = 1
                    GROUP BY overall_rating
                    ORDER BY overall_rating DESC
                """, (doctor_id,)).fetchall()
                
                rating_distribution = {row['overall_rating']: row['count'] for row in rating_dist}
                
                # 获取最近的评价
                recent_reviews = self.get_doctor_reviews(doctor_id, limit=5)
                
                summary = ReviewSummary(
                    doctor_id=doctor_id,
                    total_reviews=stats['total_reviews'],
                    average_rating=round(stats['average_rating'], 2) if stats['average_rating'] else 0.0,
                    rating_distribution=rating_distribution,
                    professional_avg=round(stats['professional_avg'], 2) if stats['professional_avg'] else 0.0,
                    service_avg=round(stats['service_avg'], 2) if stats['service_avg'] else 0.0,
                    effect_avg=round(stats['effect_avg'], 2) if stats['effect_avg'] else 0.0,
                    recent_reviews=recent_reviews
                )
                
                return summary
                
        except Exception as e:
            logger.error(f"获取评价汇总失败: {e}")
            return None
    
    def doctor_reply_to_review(self, review_id: str, doctor_id: str, reply_content: str) -> bool:
        """医生回复患者评价"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 验证评价是否属于该医生
                review = conn.execute("""
                    SELECT uuid FROM patient_reviews 
                    WHERE uuid = ? AND doctor_id = ?
                """, (review_id, doctor_id)).fetchone()
                
                if not review:
                    logger.error(f"评价不存在或不属于该医生: {review_id}")
                    return False
                
                # 更新回复
                conn.execute("""
                    UPDATE patient_reviews SET
                        doctor_reply = ?,
                        doctor_reply_time = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE uuid = ?
                """, (reply_content.strip(), review_id))
                
                conn.commit()
                
                logger.info(f"医生回复评价成功: {review_id}")
                return True
                
        except Exception as e:
            logger.error(f"医生回复评价失败: {e}")
            return False
    
    def get_patient_review_history(self, patient_id: str, limit: int = 10) -> List[PatientReview]:
        """获取患者的评价历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = """
                    SELECT r.*
                    FROM patient_reviews r
                    WHERE r.patient_id = ?
                    ORDER BY r.created_at DESC
                    LIMIT ?
                """
                
                cursor = conn.execute(query, (patient_id, limit))
                rows = cursor.fetchall()
                
                reviews = []
                for row in rows:
                    review = PatientReview(
                        uuid=row['uuid'],
                        consultation_id=row['consultation_id'],
                        patient_id=row['patient_id'],
                        doctor_id=row['doctor_id'],
                        overall_rating=row['overall_rating'],
                        professional_score=row['professional_score'],
                        service_score=row['service_score'],
                        effect_score=row['effect_score'],
                        review_content=row['review_content'] or '',
                        is_anonymous=bool(row['is_anonymous']),
                        is_visible=bool(row['is_visible']),
                        doctor_reply=row['doctor_reply'] or '',
                        doctor_reply_time=datetime.fromisoformat(row['doctor_reply_time']) if row['doctor_reply_time'] else None,
                        helpful_count=row['helpful_count'] or 0,
                        created_at=datetime.fromisoformat(row['created_at']),
                        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                    )
                    reviews.append(review)
                
                return reviews
                
        except Exception as e:
            logger.error(f"获取患者评价历史失败: {e}")
            return []
    
    def can_patient_review(self, consultation_id: str, patient_id: str) -> Dict[str, Any]:
        """检查患者是否可以评价"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 检查问诊是否完成
                consultation = conn.execute("""
                    SELECT status, selected_doctor_id, created_at
                    FROM consultations
                    WHERE uuid = ? AND patient_id = ?
                """, (consultation_id, patient_id)).fetchone()
                
                if not consultation:
                    return {'can_review': False, 'reason': '问诊记录不存在'}
                
                if consultation[0] != 'completed':
                    return {'can_review': False, 'reason': '问诊尚未完成'}
                
                # 检查是否已经评价过
                existing_review = conn.execute("""
                    SELECT uuid FROM patient_reviews
                    WHERE consultation_id = ? AND patient_id = ?
                """, (consultation_id, patient_id)).fetchone()
                
                if existing_review:
                    return {'can_review': False, 'reason': '已经评价过此次问诊'}
                
                # 检查时间限制（7天内可评价）
                consultation_date = datetime.fromisoformat(consultation[2])
                days_passed = (datetime.now() - consultation_date).days
                
                if days_passed > 7:
                    return {'can_review': False, 'reason': '评价时限已过（7天内）'}
                
                return {
                    'can_review': True, 
                    'doctor_id': consultation[1],
                    'days_left': 7 - days_passed
                }
                
        except Exception as e:
            logger.error(f"检查评价权限失败: {e}")
            return {'can_review': False, 'reason': '系统错误'}
    
    def mark_review_helpful(self, review_id: str, patient_id: str) -> bool:
        """标记评价为有用"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 简单实现，后续可扩展为防重复点赞
                conn.execute("""
                    UPDATE patient_reviews SET
                        helpful_count = helpful_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE uuid = ?
                """, (review_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"标记评价有用失败: {e}")
            return False