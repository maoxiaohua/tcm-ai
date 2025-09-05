#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
症状分析路由 - 为决策树构建器提供症状关系API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.symptom_database.symptom_relation_service import symptom_service, SymptomRelation

router = APIRouter(prefix="/api/symptom", tags=["症状分析"])

class SymptomQueryRequest(BaseModel):
    """症状查询请求"""
    main_symptom: str
    context_symptoms: Optional[List[str]] = []
    include_ai_analysis: bool = True

class SymptomRelationResponse(BaseModel):
    """症状关系响应"""
    main_symptom: str
    related_symptom: str
    relationship_type: str
    confidence_score: float
    frequency: str
    source: str

class SymptomAnalysisResponse(BaseModel):
    """症状分析完整响应"""
    success: bool
    message: str
    data: Dict[str, Any]
    analysis_time_ms: int

@router.post("/analyze_relations", response_model=SymptomAnalysisResponse)
async def analyze_symptom_relations(request: SymptomQueryRequest):
    """
    分析症状关系 - 决策树构建器核心API
    支持三层智能架构: 缓存 -> 数据库 -> AI分析
    """
    try:
        import time
        start_time = time.time()
        
        # 调用症状关系服务
        relations = await symptom_service.find_symptom_relations(
            main_symptom=request.main_symptom,
            context_symptoms=request.context_symptoms
        )
        
        # 按关系类型分组
        direct_symptoms = []
        accompanying_symptoms = []
        
        for relation in relations:
            symptom_data = {
                "name": relation.related_symptom,
                "confidence": relation.confidence_score,
                "frequency": relation.frequency,
                "source": relation.source
            }
            
            if relation.relationship_type == 'direct':
                direct_symptoms.append(symptom_data)
            elif relation.relationship_type == 'accompanying':
                accompanying_symptoms.append(symptom_data)
        
        # 获取症状聚类信息
        cluster = symptom_service.get_symptom_cluster(request.main_symptom)
        
        analysis_time = int((time.time() - start_time) * 1000)
        
        return SymptomAnalysisResponse(
            success=True,
            message=f"已找到 {len(relations)} 个相关症状",
            data={
                "main_symptom": request.main_symptom,
                "direct_symptoms": direct_symptoms,
                "accompanying_symptoms": accompanying_symptoms,
                "cluster_info": {
                    "cluster_name": cluster.cluster_name if cluster else None,
                    "confidence": cluster.confidence_score if cluster else 0.0
                },
                "total_relations": len(relations),
                "data_sources": list(set(r.source for r in relations))
            },
            analysis_time_ms=analysis_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"症状分析失败: {str(e)}")

@router.get("/cluster/{symptom_name}")
async def get_symptom_cluster(symptom_name: str):
    """获取症状聚类信息"""
    try:
        cluster = symptom_service.get_symptom_cluster(symptom_name)
        
        if cluster:
            return {
                "success": True,
                "data": {
                    "cluster_name": cluster.cluster_name,
                    "main_symptom": cluster.main_symptom,
                    "related_symptoms": cluster.related_symptoms,
                    "confidence_score": cluster.confidence_score
                }
            }
        else:
            return {
                "success": False, 
                "message": f"未找到症状 '{symptom_name}' 的聚类信息"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取聚类信息失败: {str(e)}")

@router.get("/database/stats")
async def get_database_stats():
    """获取数据库统计信息"""
    try:
        stats = symptom_service.get_database_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.post("/database/init")
async def initialize_database():
    """初始化症状数据库 (管理员功能)"""
    try:
        symptom_service.init_database()
        stats = symptom_service.get_database_stats()
        
        return {
            "success": True,
            "message": "数据库初始化完成",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库初始化失败: {str(e)}")

# 为了快速集成，也提供一个简单的GET接口
@router.get("/quick_analyze/{symptom_name}")
async def quick_symptom_analyze(symptom_name: str):
    """快速症状分析 - 简化接口供前端直接调用"""
    try:
        relations = await symptom_service.find_symptom_relations(symptom_name)
        
        # 简化返回格式，便于前端使用
        result = {
            "main_symptom": symptom_name,
            "related_symptoms": [],
            "accompanying_symptoms": [],
            "source": "database" if relations else "ai"
        }
        
        for relation in relations:
            if relation.relationship_type == 'direct':
                result["related_symptoms"].append(relation.related_symptom)
            elif relation.relationship_type == 'accompanying':
                result["accompanying_symptoms"].append(relation.related_symptom)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "main_symptom": symptom_name,
                "related_symptoms": [],
                "accompanying_symptoms": [],
                "source": "error"
            }
        }