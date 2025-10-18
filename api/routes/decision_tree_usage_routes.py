#!/usr/bin/env python3
"""
决策树使用记录API路由
记录和统计决策树在实际问诊中的使用情况
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from core.consultation.decision_tree_matcher import get_decision_tree_matcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/decision-tree", tags=["decision-tree-usage"])

class RecordUsageRequest(BaseModel):
    """记录决策树使用请求"""
    pattern_id: str
    conversation_id: str
    success: bool = False
    feedback: Optional[str] = None

class RecordUsageResponse(BaseModel):
    """记录使用响应"""
    success: bool
    message: str

@router.post("/record-usage", response_model=RecordUsageResponse)
async def record_pattern_usage(request: RecordUsageRequest):
    """
    记录决策树使用情况

    当患者问诊中使用了某个决策树,并且:
    - 患者确认处方: success=True
    - 患者未确认或有其他问题: success=False
    """
    try:
        matcher = get_decision_tree_matcher()

        await matcher.record_pattern_usage(
            pattern_id=request.pattern_id,
            success=request.success,
            feedback=request.feedback
        )

        logger.info(f"✅ 记录决策树使用: {request.pattern_id}, 成功={request.success}")

        return RecordUsageResponse(
            success=True,
            message="决策树使用记录已保存"
        )

    except Exception as e:
        logger.error(f"记录决策树使用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{pattern_id}")
async def get_pattern_stats(pattern_id: str):
    """
    获取决策树使用统计
    """
    try:
        matcher = get_decision_tree_matcher()
        pattern = await matcher.get_pattern_by_id(pattern_id)

        if not pattern:
            raise HTTPException(status_code=404, detail="决策树不存在")

        success_rate = (pattern.success_count / pattern.usage_count * 100) if pattern.usage_count > 0 else 0

        return {
            "success": True,
            "data": {
                "pattern_id": pattern.pattern_id,
                "disease_name": pattern.disease_name,
                "doctor_id": pattern.doctor_id,
                "usage_count": pattern.usage_count,
                "success_count": pattern.success_count,
                "success_rate": success_rate,
                "confidence": pattern.confidence
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取决策树统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
