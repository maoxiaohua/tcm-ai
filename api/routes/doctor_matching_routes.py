#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医生匹配路由 - 智汇中医工作流API
支持医生选择、智能推荐、偏好设置等功能
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from core.doctor_matching.doctor_matching_service import (
    DoctorMatchingService, MatchingCriteria, DoctorInfo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/doctor-matching", tags=["医生匹配"])

# Pydantic模型定义
class DoctorRecommendationRequest(BaseModel):
    patient_id: str = Field(..., description="患者ID")
    symptoms: List[str] = Field(..., description="症状列表")
    preferred_specialties: Optional[List[str]] = Field(None, description="偏好专科")
    consultation_time: Optional[str] = Field(None, description="问诊时间偏好")
    gender_preference: Optional[str] = Field(None, description="医生性别偏好")
    max_results: Optional[int] = Field(5, description="最大返回结果数", ge=1, le=20)

class DoctorAssignmentRequest(BaseModel):
    patient_id: str = Field(..., description="患者ID")
    doctor_id: str = Field(..., description="医生ID")
    selection_method: str = Field("specified", description="选择方式")

class PatientPreferencesRequest(BaseModel):
    patient_id: str = Field(..., description="患者ID")
    preferred_specialties: Optional[List[str]] = Field(None, description="偏好专科")
    preferred_doctor_id: Optional[str] = Field(None, description="偏好医生ID")
    avoid_doctor_ids: Optional[List[str]] = Field(None, description="避免的医生ID列表")
    preferred_consultation_time: Optional[str] = Field(None, description="偏好问诊时间")
    gender_preference: Optional[str] = Field(None, description="性别偏好")

class DoctorResponse(BaseModel):
    uuid: str
    name: str
    title: str
    specialties: List[str]
    average_rating: float
    total_reviews: int
    consultation_count: int
    introduction: str
    avatar_url: str
    is_available: bool

# 服务实例
matching_service = DoctorMatchingService()

@router.post("/recommend", response_model=Dict[str, Any])
async def recommend_doctors(request: DoctorRecommendationRequest):
    """根据症状智能推荐医生"""
    try:
        # 获取推荐医生
        recommended_doctors = matching_service.recommend_doctors_for_symptoms(
            symptoms=request.symptoms,
            patient_id=request.patient_id
        )
        
        # 转换为响应格式
        doctors_data = []
        for doctor in recommended_doctors:
            doctors_data.append(DoctorResponse(
                uuid=doctor.uuid,
                name=doctor.name,
                title=doctor.title,
                specialties=doctor.specialties,
                average_rating=doctor.average_rating,
                total_reviews=doctor.total_reviews,
                consultation_count=doctor.consultation_count,
                introduction=doctor.introduction,
                avatar_url=doctor.avatar_url,
                is_available=doctor.is_available
            ).dict())
        
        return {
            "success": True,
            "message": f"为您推荐了 {len(doctors_data)} 位医生",
            "data": {
                "recommended_doctors": doctors_data,
                "recommendation_reason": f"基于症状：{', '.join(request.symptoms)}",
                "total_count": len(doctors_data)
            }
        }
        
    except Exception as e:
        logger.error(f"医生推荐失败: {e}")
        raise HTTPException(status_code=500, detail="医生推荐服务暂时不可用")

@router.get("/available", response_model=Dict[str, Any])
async def get_available_doctors(
    patient_id: str = Query(..., description="患者ID"),
    specialties: Optional[List[str]] = Query(None, description="专科筛选"),
    limit: int = Query(10, description="返回数量限制", ge=1, le=50)
):
    """获取可用医生列表"""
    try:
        criteria = MatchingCriteria(
            patient_id=patient_id,
            symptoms=[],
            preferred_specialties=specialties,
            max_results=limit
        )
        
        doctors = matching_service.get_available_doctors(criteria)
        
        doctors_data = []
        for doctor in doctors:
            doctors_data.append(DoctorResponse(
                uuid=doctor.uuid,
                name=doctor.name,
                title=doctor.title,
                specialties=doctor.specialties,
                average_rating=doctor.average_rating,
                total_reviews=doctor.total_reviews,
                consultation_count=doctor.consultation_count,
                introduction=doctor.introduction,
                avatar_url=doctor.avatar_url,
                is_available=doctor.is_available
            ).dict())
        
        return {
            "success": True,
            "message": f"找到 {len(doctors_data)} 位可用医生",
            "data": {
                "doctors": doctors_data,
                "total_count": len(doctors_data),
                "filters_applied": {
                    "specialties": specialties or [],
                    "limit": limit
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取可用医生失败: {e}")
        raise HTTPException(status_code=500, detail="获取医生列表失败")

@router.get("/doctor/{doctor_id}", response_model=Dict[str, Any])
async def get_doctor_detail(doctor_id: str):
    """获取医生详细信息"""
    try:
        doctor = matching_service.get_doctor_by_id(doctor_id)
        
        if not doctor:
            raise HTTPException(status_code=404, detail="医生不存在")
        
        doctor_data = DoctorResponse(
            uuid=doctor.uuid,
            name=doctor.name,
            title=doctor.title,
            specialties=doctor.specialties,
            average_rating=doctor.average_rating,
            total_reviews=doctor.total_reviews,
            consultation_count=doctor.consultation_count,
            introduction=doctor.introduction,
            avatar_url=doctor.avatar_url,
            is_available=doctor.is_available
        ).dict()
        
        return {
            "success": True,
            "message": "获取医生信息成功",
            "data": {
                "doctor": doctor_data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取医生详细信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取医生信息失败")

@router.post("/assign", response_model=Dict[str, Any])
async def assign_doctor_to_patient(request: DoctorAssignmentRequest):
    """分配医生给患者"""
    try:
        # 验证医生是否存在且可用
        doctor = matching_service.get_doctor_by_id(request.doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="医生不存在")
        
        # 执行分配
        success = matching_service.assign_doctor_to_patient(
            patient_id=request.patient_id,
            doctor_id=request.doctor_id,
            selection_method=request.selection_method
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="医生分配失败")
        
        return {
            "success": True,
            "message": f"成功分配医生：{doctor.name}",
            "data": {
                "patient_id": request.patient_id,
                "doctor_id": request.doctor_id,
                "doctor_name": doctor.name,
                "selection_method": request.selection_method,
                "assigned_at": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分配医生失败: {e}")
        raise HTTPException(status_code=500, detail="医生分配服务异常")

@router.post("/preferences", response_model=Dict[str, Any])
async def save_patient_preferences(request: PatientPreferencesRequest):
    """保存患者偏好设置"""
    try:
        preferences = {
            'preferred_specialties': request.preferred_specialties or [],
            'preferred_doctor_id': request.preferred_doctor_id,
            'avoid_doctor_ids': request.avoid_doctor_ids or [],
            'preferred_consultation_time': request.preferred_consultation_time,
            'gender_preference': request.gender_preference
        }
        
        success = matching_service.save_patient_preferences(
            patient_id=request.patient_id,
            preferences=preferences
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="偏好设置保存失败")
        
        return {
            "success": True,
            "message": "偏好设置保存成功",
            "data": {
                "patient_id": request.patient_id,
                "preferences": preferences,
                "updated_at": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存患者偏好失败: {e}")
        raise HTTPException(status_code=500, detail="偏好设置服务异常")

@router.get("/preferences/{patient_id}", response_model=Dict[str, Any])
async def get_patient_preferences(patient_id: str):
    """获取患者偏好设置"""
    try:
        preferences = matching_service._get_patient_preferences(patient_id)
        
        return {
            "success": True,
            "message": "获取偏好设置成功",
            "data": {
                "patient_id": patient_id,
                "preferences": preferences or {},
                "has_preferences": preferences is not None
            }
        }
        
    except Exception as e:
        logger.error(f"获取患者偏好失败: {e}")
        raise HTTPException(status_code=500, detail="获取偏好设置失败")

@router.get("/specialties", response_model=Dict[str, Any])
async def get_available_specialties():
    """获取可用专科列表"""
    try:
        # 预定义的中医专科列表
        specialties = [
            {"code": "internal", "name": "内科", "description": "内科杂病，脏腑调理"},
            {"code": "gynecology", "name": "妇科", "description": "妇科疾病，月经调理"},
            {"code": "pediatrics", "name": "儿科", "description": "小儿疾病，生长发育"},
            {"code": "orthopedics", "name": "骨伤科", "description": "筋骨疼痛，外伤骨折"},
            {"code": "dermatology", "name": "皮肤科", "description": "皮肤疾病，美容养颜"},
            {"code": "respiratory", "name": "肺病科", "description": "呼吸系统，咳嗽哮喘"},
            {"code": "digestive", "name": "脾胃病科", "description": "消化系统，胃肠调理"},
            {"code": "neurology", "name": "脑病科", "description": "神经系统，头痛眩晕"},
            {"code": "psychiatry", "name": "神志病科", "description": "情志调节，失眠焦虑"},
            {"code": "oncology", "name": "肿瘤科", "description": "肿瘤康复，扶正祛邪"}
        ]
        
        return {
            "success": True,
            "message": "获取专科列表成功",
            "data": {
                "specialties": specialties,
                "total_count": len(specialties)
            }
        }
        
    except Exception as e:
        logger.error(f"获取专科列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取专科列表失败")