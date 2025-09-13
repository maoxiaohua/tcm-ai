#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评价系统路由 - 智汇中医工作流API
支持患者评价、医生回复、评价统计等功能
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from core.review_system.review_manager import ReviewManager, PatientReview, ReviewSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["评价系统"])

# Pydantic模型定义
class CreateReviewRequest(BaseModel):
    consultation_id: str = Field(..., description="问诊ID")
    patient_id: str = Field(..., description="患者ID")
    overall_rating: int = Field(..., description="总体评分", ge=1, le=5)
    professional_score: Optional[int] = Field(None, description="专业性评分", ge=1, le=5)
    service_score: Optional[int] = Field(None, description="服务态度评分", ge=1, le=5)
    effect_score: Optional[int] = Field(None, description="治疗效果评分", ge=1, le=5)
    review_content: Optional[str] = Field("", description="评价内容", max_length=500)
    is_anonymous: Optional[bool] = Field(False, description="是否匿名评价")

class DoctorReplyRequest(BaseModel):
    review_id: str = Field(..., description="评价ID")
    doctor_id: str = Field(..., description="医生ID")
    reply_content: str = Field(..., description="回复内容", min_length=1, max_length=300)

class ReviewResponse(BaseModel):
    uuid: str
    consultation_id: str
    patient_id: str
    doctor_id: str
    overall_rating: int
    professional_score: Optional[int]
    service_score: Optional[int]
    effect_score: Optional[int]
    review_content: str
    is_anonymous: bool
    doctor_reply: str
    doctor_reply_time: Optional[datetime]
    helpful_count: int
    created_at: datetime

class ReviewSummaryResponse(BaseModel):
    doctor_id: str
    total_reviews: int
    average_rating: float
    rating_distribution: Dict[int, int]
    professional_avg: float
    service_avg: float
    effect_avg: float

# 服务实例
review_manager = ReviewManager()

@router.post("/create", response_model=Dict[str, Any])
async def create_review(request: CreateReviewRequest):
    """创建患者评价"""
    try:
        # 检查是否可以评价
        can_review = review_manager.can_patient_review(
            consultation_id=request.consultation_id,
            patient_id=request.patient_id
        )
        
        if not can_review['can_review']:
            raise HTTPException(
                status_code=400, 
                detail=f"无法创建评价: {can_review['reason']}"
            )
        
        # 创建评价
        review_data = {
            'overall_rating': request.overall_rating,
            'professional_score': request.professional_score,
            'service_score': request.service_score,
            'effect_score': request.effect_score,
            'review_content': request.review_content,
            'is_anonymous': request.is_anonymous
        }
        
        review = review_manager.create_review(
            consultation_id=request.consultation_id,
            patient_id=request.patient_id,
            review_data=review_data
        )
        
        if not review:
            raise HTTPException(status_code=400, detail="评价创建失败")
        
        return {
            "success": True,
            "message": "评价提交成功",
            "data": {
                "review_id": review.uuid,
                "doctor_id": review.doctor_id,
                "overall_rating": review.overall_rating,
                "created_at": review.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建评价失败: {e}")
        raise HTTPException(status_code=500, detail="评价服务异常")

@router.get("/doctor/{doctor_id}", response_model=Dict[str, Any])
async def get_doctor_reviews(
    doctor_id: str,
    limit: int = Query(10, description="返回数量", ge=1, le=50),
    offset: int = Query(0, description="偏移量", ge=0)
):
    """获取医生的评价列表"""
    try:
        reviews = review_manager.get_doctor_reviews(
            doctor_id=doctor_id,
            limit=limit,
            offset=offset
        )
        
        reviews_data = []
        for review in reviews:
            review_data = {
                "uuid": review.uuid,
                "consultation_id": review.consultation_id,
                "patient_id": review.patient_id if not review.is_anonymous else "匿名用户",
                "doctor_id": review.doctor_id,
                "overall_rating": review.overall_rating,
                "professional_score": review.professional_score,
                "service_score": review.service_score,
                "effect_score": review.effect_score,
                "review_content": review.review_content,
                "is_anonymous": review.is_anonymous,
                "doctor_reply": review.doctor_reply,
                "doctor_reply_time": review.doctor_reply_time.isoformat() if review.doctor_reply_time else None,
                "helpful_count": review.helpful_count,
                "created_at": review.created_at.isoformat()
            }
            reviews_data.append(review_data)
        
        return {
            "success": True,
            "message": f"获取评价成功",
            "data": {
                "reviews": reviews_data,
                "total_count": len(reviews_data),
                "has_more": len(reviews_data) == limit
            }
        }
        
    except Exception as e:
        logger.error(f"获取医生评价失败: {e}")
        raise HTTPException(status_code=500, detail="获取评价失败")

@router.get("/summary/{doctor_id}", response_model=Dict[str, Any])
async def get_doctor_review_summary(doctor_id: str):
    """获取医生评价汇总统计"""
    try:
        summary = review_manager.get_review_summary(doctor_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="医生评价统计不存在")
        
        return {
            "success": True,
            "message": "获取评价统计成功",
            "data": {
                "doctor_id": summary.doctor_id,
                "total_reviews": summary.total_reviews,
                "average_rating": summary.average_rating,
                "rating_distribution": summary.rating_distribution,
                "dimension_scores": {
                    "professional_avg": summary.professional_avg,
                    "service_avg": summary.service_avg,
                    "effect_avg": summary.effect_avg
                },
                "recent_reviews_count": len(summary.recent_reviews)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取评价统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取评价统计失败")

@router.post("/reply", response_model=Dict[str, Any])
async def doctor_reply_to_review(request: DoctorReplyRequest):
    """医生回复患者评价"""
    try:
        success = review_manager.doctor_reply_to_review(
            review_id=request.review_id,
            doctor_id=request.doctor_id,
            reply_content=request.reply_content
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="回复评价失败")
        
        return {
            "success": True,
            "message": "回复评价成功",
            "data": {
                "review_id": request.review_id,
                "doctor_id": request.doctor_id,
                "reply_time": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"医生回复评价失败: {e}")
        raise HTTPException(status_code=500, detail="回复评价失败")

@router.get("/patient/{patient_id}", response_model=Dict[str, Any])
async def get_patient_review_history(
    patient_id: str,
    limit: int = Query(10, description="返回数量", ge=1, le=50)
):
    """获取患者的评价历史"""
    try:
        reviews = review_manager.get_patient_review_history(
            patient_id=patient_id,
            limit=limit
        )
        
        reviews_data = []
        for review in reviews:
            review_data = {
                "uuid": review.uuid,
                "consultation_id": review.consultation_id,
                "doctor_id": review.doctor_id,
                "overall_rating": review.overall_rating,
                "professional_score": review.professional_score,
                "service_score": review.service_score,
                "effect_score": review.effect_score,
                "review_content": review.review_content,
                "is_anonymous": review.is_anonymous,
                "doctor_reply": review.doctor_reply,
                "doctor_reply_time": review.doctor_reply_time.isoformat() if review.doctor_reply_time else None,
                "created_at": review.created_at.isoformat()
            }
            reviews_data.append(review_data)
        
        return {
            "success": True,
            "message": "获取评价历史成功",
            "data": {
                "patient_id": patient_id,
                "reviews": reviews_data,
                "total_count": len(reviews_data)
            }
        }
        
    except Exception as e:
        logger.error(f"获取患者评价历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取评价历史失败")

@router.get("/can-review/{consultation_id}", response_model=Dict[str, Any])
async def check_can_review(consultation_id: str, patient_id: str = Query(...)):
    """检查是否可以评价"""
    try:
        can_review_info = review_manager.can_patient_review(
            consultation_id=consultation_id,
            patient_id=patient_id
        )
        
        return {
            "success": True,
            "message": "检查评价权限成功",
            "data": can_review_info
        }
        
    except Exception as e:
        logger.error(f"检查评价权限失败: {e}")
        raise HTTPException(status_code=500, detail="检查评价权限失败")

@router.post("/helpful/{review_id}", response_model=Dict[str, Any])
async def mark_review_helpful(review_id: str, patient_id: str = Query(...)):
    """标记评价为有用"""
    try:
        success = review_manager.mark_review_helpful(
            review_id=review_id,
            patient_id=patient_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="标记失败")
        
        return {
            "success": True,
            "message": "标记成功",
            "data": {
                "review_id": review_id,
                "marked_by": patient_id,
                "marked_at": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记评价有用失败: {e}")
        raise HTTPException(status_code=500, detail="标记失败")

@router.get("/stats/platform", response_model=Dict[str, Any])
async def get_platform_review_stats():
    """获取平台评价统计"""
    try:
        # 这里可以扩展为更复杂的平台统计
        # 暂时返回基础统计信息
        return {
            "success": True,
            "message": "获取平台统计成功",
            "data": {
                "total_reviews": 0,
                "average_platform_rating": 0.0,
                "top_rated_doctors": [],
                "recent_reviews_trend": {}
            }
        }
        
    except Exception as e:
        logger.error(f"获取平台评价统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取平台统计失败")