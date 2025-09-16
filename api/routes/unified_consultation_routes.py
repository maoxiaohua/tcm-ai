#!/usr/bin/env python3
"""
统一问诊API路由
为智能工作流程和原系统提供统一的问诊接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import traceback

# 导入统一问诊服务
import sys
sys.path.append('/opt/tcm-ai')
from core.consultation.unified_consultation_service import (
    get_consultation_service, 
    ConsultationRequest,
    ConsultationResponse
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/consultation", tags=["unified-consultation"])

# Pydantic模型
class ChatMessage(BaseModel):
    message: str
    conversation_id: str
    selected_doctor: str = "zhang_zhongjing"
    patient_id: Optional[str] = None
    has_images: bool = False
    conversation_history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: str = ""

@router.post("/chat", response_model=ChatResponse)
async def unified_chat_endpoint(request: ChatMessage):
    """
    统一问诊聊天接口
    兼容智能工作流程和原系统的调用方式
    """
    try:
        logger.info(f"统一问诊请求: 医生={request.selected_doctor}, 消息长度={len(request.message)}")
        
        # 获取统一问诊服务
        consultation_service = get_consultation_service()
        
        # 构建请求对象
        consultation_request = ConsultationRequest(
            message=request.message,
            conversation_id=request.conversation_id,
            selected_doctor=request.selected_doctor,
            conversation_history=request.conversation_history or [],
            patient_id=request.patient_id,
            has_images=request.has_images
        )
        
        # 处理问诊
        response = await consultation_service.process_consultation(consultation_request)
        
        # 构建响应数据
        response_data = {
            "reply": response.reply,
            "conversation_id": response.conversation_id,
            "doctor_name": response.doctor_name,
            "contains_prescription": response.contains_prescription,
            "prescription_data": response.prescription_data,
            "confidence_score": response.confidence_score,
            "processing_time": response.processing_time,
            "stage": response.stage,
            # 🔑 关键修复：添加处方支付相关字段
            "prescription_id": response.prescription_data.get("prescription_id") if response.prescription_data else None,
            "is_paid": response.prescription_data.get("is_paid", False) if response.prescription_data else False
        }
        
        logger.info(f"统一问诊响应: 包含处方={response.contains_prescription}, 阶段={response.stage}")
        
        return ChatResponse(
            success=True,
            data=response_data,
            message="问诊处理成功"
        )
        
    except Exception as e:
        logger.error(f"统一问诊处理失败: {e}")
        logger.error(traceback.format_exc())
        
        return ChatResponse(
            success=False,
            data={
                "reply": f"抱歉，AI医生暂时无法回应，请稍后重试。",
                "conversation_id": request.conversation_id,
                "doctor_name": request.selected_doctor,
                "contains_prescription": False,
                "error": str(e)
            },
            message=f"处理失败: {str(e)}"
        )

@router.post("/chat-legacy", response_model=Dict[str, Any])
async def legacy_chat_endpoint(request: ChatMessage):
    """
    兼容原系统的问诊接口
    返回格式与原chat_with_ai完全兼容
    """
    try:
        # 调用统一问诊处理
        unified_response = await unified_chat_endpoint(request)
        
        if unified_response.success:
            # 返回原系统兼容的格式
            response_data = unified_response.data
            return {
                "reply": response_data["reply"],
                "conversation_id": response_data["conversation_id"]
            }
        else:
            # 错误处理
            return {
                "reply": unified_response.data["reply"],
                "conversation_id": request.conversation_id
            }
            
    except Exception as e:
        logger.error(f"兼容接口处理失败: {e}")
        return {
            "reply": "抱歉，AI医生暂时无法回应，请稍后重试。",
            "conversation_id": request.conversation_id
        }

@router.get("/doctor-info/{doctor_name}")
async def get_doctor_info(doctor_name: str):
    """获取医生信息"""
    try:
        consultation_service = get_consultation_service()
        
        # 获取医生信息（如果有的话）
        doctor_info = {
            "zhang_zhongjing": {
                "name": "张仲景",
                "school": "伤寒派", 
                "specialty": ["外感病", "内伤杂病", "急症"],
                "method": "六经辨证"
            },
            "ye_tianshi": {
                "name": "叶天士",
                "school": "温病派",
                "specialty": ["温病", "内科"],
                "method": "卫气营血辨证"
            },
            "li_dongyuan": {
                "name": "李东垣",
                "school": "脾胃派",
                "specialty": ["脾胃病", "内科"],
                "method": "脾胃调理"
            }
        }
        
        info = doctor_info.get(doctor_name, {
            "name": "中医专家",
            "school": "综合",
            "specialty": ["内科"],
            "method": "辨证论治"
        })
        
        return {
            "success": True,
            "data": info
        }
        
    except Exception as e:
        logger.error(f"获取医生信息失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.get("/service-status")
async def get_service_status():
    """获取统一问诊服务状态"""
    try:
        consultation_service = get_consultation_service()
        
        return {
            "success": True,
            "data": {
                "service_name": "统一问诊服务",
                "version": "1.0.0",
                "status": "healthy",
                "features": [
                    "医生人格系统",
                    "智能缓存",
                    "处方安全检查", 
                    "多阶段问诊",
                    "辨证论治"
                ],
                "supported_doctors": [
                    "zhang_zhongjing",
                    "ye_tianshi", 
                    "li_dongyuan",
                    "zhu_danxi",
                    "liu_duzhou",
                    "zheng_qin_an"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"获取服务状态失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.get("/conversation/{conversation_id}/progress")
async def get_conversation_progress(conversation_id: str):
    """获取对话进度信息"""
    try:
        from core.conversation import conversation_state_manager
        
        progress = conversation_state_manager.get_conversation_progress(conversation_id)
        if not progress:
            return {
                "success": False,
                "message": "对话不存在"
            }
        
        return {
            "success": True,
            "data": progress
        }
        
    except Exception as e:
        logger.error(f"获取对话进度失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.get("/conversation/{conversation_id}/guidance")
async def get_stage_guidance(conversation_id: str):
    """获取阶段引导信息"""
    try:
        from core.conversation import conversation_state_manager
        
        guidance = conversation_state_manager.get_stage_guidance(conversation_id)
        if not guidance:
            return {
                "success": False,
                "message": "对话不存在"
            }
        
        return {
            "success": True,
            "data": guidance
        }
        
    except Exception as e:
        logger.error(f"获取阶段引导失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.post("/conversation/{conversation_id}/confirm-prescription")
async def confirm_prescription(conversation_id: str):
    """确认处方"""
    try:
        from core.conversation import conversation_state_manager, ConversationStage
        
        # 更新对话状态为处方确认
        success = conversation_state_manager.update_stage(
            conversation_id,
            ConversationStage.PRESCRIPTION_CONFIRM,
            "用户确认处方"
        )
        
        if success:
            return {
                "success": True,
                "message": "处方确认成功",
                "data": {
                    "next_step": "proceed_to_payment",
                    "message": "请继续完成支付流程"
                }
            }
        else:
            return {
                "success": False,
                "message": "处方确认失败"
            }
            
    except Exception as e:
        logger.error(f"处方确认失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.post("/conversation/{conversation_id}/end")
async def end_conversation(conversation_id: str, request: Dict[str, Any]):
    """结束对话"""
    try:
        from core.conversation import conversation_state_manager, ConversationEndType
        
        end_type = ConversationEndType.USER_TERMINATED
        reason = request.get("reason", "用户主动结束")
        satisfaction = request.get("satisfaction")
        
        success = conversation_state_manager.end_conversation(
            conversation_id,
            end_type,
            reason,
            satisfaction
        )
        
        if success:
            return {
                "success": True,
                "message": "对话已结束",
                "data": {
                    "end_type": end_type.value,
                    "reason": reason
                }
            }
        else:
            return {
                "success": False,
                "message": "结束对话失败"
            }
            
    except Exception as e:
        logger.error(f"结束对话失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.get("/conversation/{conversation_id}/summary")
async def get_conversation_summary(conversation_id: str):
    """获取对话摘要"""
    try:
        from core.conversation import conversation_state_manager, ConversationAnalyzer
        from datetime import datetime
        
        # 获取对话状态
        state = conversation_state_manager.get_conversation_state(conversation_id)
        if not state:
            return {
                "success": False,
                "message": "对话不存在"
            }
        
        # 这里可以获取完整的对话历史进行分析
        # 暂时返回基本信息
        analyzer = ConversationAnalyzer()
        
        summary = {
            "conversation_id": conversation_id,
            "doctor_name": state.doctor_id,
            "start_time": state.start_time.isoformat(),
            "duration_minutes": int((datetime.now() - state.start_time).total_seconds() / 60),
            "turn_count": state.turn_count,
            "current_stage": state.current_stage.value,
            "symptoms_collected": state.symptoms_collected,
            "has_prescription": state.has_prescription,
            "is_active": state.is_active,
            "end_type": state.end_type.value if state.end_type else None
        }
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"获取对话摘要失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }