#!/usr/bin/env python3
"""
统一问诊API路由
为智能工作流程和原系统提供统一的问诊接口
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import traceback
import sqlite3
import json
import uuid
from datetime import datetime

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

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

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
async def unified_chat_endpoint(request: ChatMessage, http_request: Request):
    """
    统一问诊聊天接口 - 支持跨设备同步
    兼容智能工作流程和原系统的调用方式
    """
    try:
        logger.info(f"统一问诊请求: 医生={request.selected_doctor}, 消息长度={len(request.message)}")
        
        # 🔑 获取真实用户ID (优先认证用户，回退到设备用户)
        real_user_id = None
        
        # 1. 尝试从认证token获取用户ID
        auth_header = http_request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            try:
                from api.main import get_user_info_by_token
                auth_user_info = await get_user_info_by_token(token)
                if auth_user_info and auth_user_info.get('user_id'):
                    real_user_id = auth_user_info['user_id']
                    logger.info(f"✅ 使用认证用户ID进行问诊: {real_user_id}")
            except:
                pass
        
        # 2. 如果没有认证用户，使用前端传递的patient_id或生成设备用户
        if not real_user_id:
            real_user_id = request.patient_id or "guest"
            logger.info(f"⚠️ 使用设备/guest用户进行问诊: {real_user_id}")
        
        # 获取统一问诊服务
        consultation_service = get_consultation_service()
        
        # 构建请求对象 (使用真实用户ID)
        consultation_request = ConsultationRequest(
            message=request.message,
            conversation_id=request.conversation_id,
            selected_doctor=request.selected_doctor,
            conversation_history=request.conversation_history or [],
            patient_id=real_user_id,  # 🔑 使用真实用户ID
            has_images=request.has_images
        )
        
        # 处理问诊
        response = await consultation_service.process_consultation(consultation_request)
        
        # 🔑 存储问诊记录到数据库（唯一保存点，避免重复）
        await _store_consultation_record(real_user_id, request, response)
        
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

# 新增：对话保存相关的数据模型
class ConsultationSaveRequest(BaseModel):
    """对话保存请求"""
    consultation_id: str
    patient_id: str
    doctor_id: str
    conversation_log: str  # JSON字符串格式的对话记录
    status: str = "completed"
    created_at: str
    updated_at: str

@router.post("/save")
async def save_consultation(request: ConsultationSaveRequest):
    """
    保存问诊对话到数据库
    注意：为避免重复保存，系统已在聊天过程中自动保存数据
    此接口主要用于兼容性，不再执行实际的插入操作
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在相同的consultation_id
        cursor.execute("""
            SELECT uuid, updated_at FROM consultations WHERE uuid = ?
        """, (request.consultation_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # 记录已存在，说明在聊天时已自动保存，无需重复操作
            logger.info(f"问诊记录已存在，跳过重复保存: {request.consultation_id}")
            message = "问诊记录已存在，数据已自动保存"
        else:
            # 记录不存在，说明自动保存可能失败，这时才手动保存
            cursor.execute("""
                INSERT INTO consultations (
                    uuid, patient_id, selected_doctor_id,
                    conversation_log, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                request.consultation_id,
                request.patient_id,
                request.doctor_id,
                request.conversation_log,
                request.status,
                request.created_at,
                request.updated_at
            ))
            logger.info(f"补充保存问诊记录: {request.consultation_id}")
            message = "问诊记录已补充保存"
        
        # 🔑 关键修复：同步到doctor_sessions表，确保历史记录显示
        try:
            # 解析对话日志获取摘要信息
            conversation_data = json.loads(request.conversation_log)
            chief_complaint = "问诊咨询"
            total_conversations = 0
            
            # 从conversation_history提取信息
            if 'conversation_history' in conversation_data:
                history = conversation_data['conversation_history']
                if isinstance(history, list) and len(history) > 0:
                    # 提取主诉（第一条用户消息）
                    first_query = history[0].get('patient_query', '')
                    if first_query:
                        chief_complaint = first_query[:100] + ('...' if len(first_query) > 100 else '')
                    total_conversations = len(history)
            
            # 检查doctor_sessions表是否已存在记录
            cursor.execute("""
                SELECT session_id FROM doctor_sessions WHERE session_id = ?
            """, (request.consultation_id,))
            
            session_exists = cursor.fetchone()
            
            if session_exists:
                # 更新doctor_sessions记录
                cursor.execute("""
                    UPDATE doctor_sessions 
                    SET chief_complaint = ?,
                        total_conversations = ?,
                        session_status = ?,
                        last_updated = ?
                    WHERE session_id = ?
                """, (
                    chief_complaint,
                    total_conversations,
                    'completed' if request.status == 'completed' else 'active',
                    request.updated_at,
                    request.consultation_id
                ))
                logger.info(f"更新doctor_sessions记录: {request.consultation_id}")
            else:
                # 插入新的doctor_sessions记录
                cursor.execute("""
                    INSERT INTO doctor_sessions (
                        session_id, user_id, doctor_name, session_count,
                        chief_complaint, total_conversations, session_status,
                        created_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request.consultation_id,
                    request.patient_id,
                    request.doctor_id,
                    1,  # 默认为第1次问诊
                    chief_complaint,
                    total_conversations,
                    'completed' if request.status == 'completed' else 'active',
                    request.created_at,
                    request.updated_at
                ))
                logger.info(f"新增doctor_sessions记录: {request.consultation_id}")
            
        except Exception as sync_error:
            logger.warning(f"同步到doctor_sessions失败，但consultations已保存: {sync_error}")
            # 不抛出异常，允许consultations保存成功
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": message,
            "data": {
                "consultation_id": request.consultation_id,
                "patient_id": request.patient_id,
                "doctor_id": request.doctor_id,
                "status": request.status,
                "note": "系统已在聊天过程中自动保存数据，避免重复记录"
            }
        }
        
    except Exception as e:
        logger.error(f"保存问诊记录失败: {e}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"保存失败: {str(e)}"
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

async def _store_consultation_record(user_id: str, request: ChatMessage, response) -> None:
    """
    存储问诊记录到数据库以支持跨设备同步
    整合多个存储机制确保数据完整性
    """
    try:
        import sqlite3
        import json
        import uuid
        from datetime import datetime
        
        conn = sqlite3.connect('/opt/tcm-ai/data/user_history.sqlite')
        cursor = conn.cursor()
        
        # 1. 存储到 consultations 表（问诊主记录）
        # 🔑 修复：强化查重逻辑，避免重复记录
        cursor.execute("""
            SELECT uuid, conversation_log FROM consultations 
            WHERE patient_id = ? AND (
                conversation_log LIKE ? OR 
                (selected_doctor_id = ? AND ABS(strftime('%s', 'now') - strftime('%s', created_at)) < 3600)
            )
            ORDER BY created_at DESC LIMIT 1
        """, (user_id, f'%"conversation_id": "{request.conversation_id}"%', request.selected_doctor))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录，合并对话历史
            existing_log = json.loads(existing[1]) if existing[1] else {}
            conversation_history = existing_log.get('conversation_history', [])
            
            # 添加新的对话轮次
            conversation_history.append({
                "patient_query": request.message,
                "ai_response": response.reply,
                "timestamp": datetime.now().isoformat(),
                "stage": response.stage
            })
            
            updated_log = {
                "conversation_id": request.conversation_id,
                "conversation_history": conversation_history,
                "current_stage": response.stage,
                "confidence_score": response.confidence_score,
                "last_query": request.message,
                "last_response": response.reply
            }
            
            cursor.execute("""
                UPDATE consultations 
                SET conversation_log = ?, 
                    symptoms_analysis = ?,
                    tcm_syndrome = ?,
                    status = ?,
                    updated_at = ?
                WHERE uuid = ?
            """, (
                json.dumps(updated_log),
                json.dumps({"confidence_score": response.confidence_score, "stage": response.stage}),
                json.dumps(response.prescription_data.get('syndrome', {}) if response.prescription_data else {}),
                _determine_consultation_status(response),
                datetime.now().isoformat(),
                existing[0]
            ))
            consultation_uuid = existing[0]
        else:
            # 创建新记录
            consultation_uuid = str(uuid.uuid4())
            conversation_log = json.dumps({
                "conversation_id": request.conversation_id,
                "conversation_history": [{
                    "patient_query": request.message,
                    "ai_response": response.reply,
                    "timestamp": datetime.now().isoformat(),
                    "stage": response.stage
                }],
                "current_stage": response.stage,
                "confidence_score": response.confidence_score,
                "last_query": request.message,
                "last_response": response.reply
            })
            
            cursor.execute("""
                INSERT INTO consultations (
                    uuid, patient_id, selected_doctor_id, conversation_log,
                    symptoms_analysis, tcm_syndrome, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                consultation_uuid,
                user_id,
                request.selected_doctor,
                conversation_log,
                json.dumps({"confidence_score": response.confidence_score, "stage": response.stage}),
                json.dumps(response.prescription_data.get('syndrome', {}) if response.prescription_data else {}),
                _determine_consultation_status(response),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        # 2. 更新或创建 conversation_states 表（对话状态）
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_states (
                conversation_id, user_id, doctor_id, current_stage, 
                start_time, last_activity, turn_count, symptoms_collected, 
                has_prescription, is_active, diagnosis_confidence, 
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.conversation_id,
            user_id,
            request.selected_doctor,
            response.stage,
            datetime.now().isoformat(),  # start_time
            datetime.now().isoformat(),  # last_activity
            len(request.conversation_history or []) + 1,
            json.dumps({"last_query": request.message, "last_response": response.reply}),
            1 if response.contains_prescription else 0,
            1,
            response.confidence_score,  # diagnosis_confidence
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        # 3. 如果有处方，存储到 prescriptions 表并自动提交审核
        logger.info(f"🔍 处方检查: contains_prescription={response.contains_prescription}, prescription_data={response.prescription_data is not None}")
        if response.contains_prescription and response.prescription_data:
            logger.info(f"💊 开始保存处方到数据库, prescription_data={response.prescription_data}")
            # 提取处方内容和诊断信息
            prescription_text = response.prescription_data.get('prescription', '')
            if not prescription_text:
                # 如果没有单独的prescription字段，尝试从完整数据中提取
                prescription_text = json.dumps(response.prescription_data, ensure_ascii=False, indent=2)
            
            diagnosis_text = response.prescription_data.get('diagnosis', '')
            syndrome_text = response.prescription_data.get('syndrome', '')
            
            logger.info(f"📝 处方文本长度: {len(prescription_text) if prescription_text else 0}")
            
            cursor.execute("""
                INSERT INTO prescriptions (
                    patient_id, conversation_id, consultation_id, doctor_id, 
                    ai_prescription, diagnosis, symptoms,
                    status, created_at, is_visible_to_patient,
                    payment_status, prescription_fee, review_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                request.conversation_id,  # 对话ID
                consultation_uuid,        # 问诊记录UUID
                request.selected_doctor,
                prescription_text,
                diagnosis_text + ('\n\n' + syndrome_text if syndrome_text else ''),
                response.prescription_data.get('symptoms_summary', ''),
                "pending_review",  # 🔑 修改：等待医生审核
                datetime.now().isoformat(),
                0,  # 默认不可见，需审核通过后支付解锁
                "pending",  # 待支付
                88.0,  # 处方费用
                "pending_review"  # 🔑 新增：审核状态
            ))
            
            # 获取新创建的处方ID
            prescription_id = cursor.lastrowid
            logger.info(f"✅ 处方保存成功，prescription_id={prescription_id}")
            
            # 🔑 自动提交到医生审核队列
            await _submit_to_doctor_review_queue(cursor, prescription_id, request, consultation_uuid)
            
            # 🔑 将处方ID添加到响应数据中，供前端使用
            if response.prescription_data:
                response.prescription_data['prescription_id'] = prescription_id
                response.prescription_data['payment_status'] = 'pending'
                response.prescription_data['review_status'] = 'pending_review'
                response.prescription_data['requires_review'] = True  # 🔑 新增：标记需要审核
            
            # 更新对话状态，标记已有处方
            cursor.execute("""
                UPDATE conversation_states 
                SET has_prescription = 1,
                    prescription_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = ?
            """, (prescription_id, consultation_uuid))
            
            logger.info(f"✅ 对话状态更新完成，conversation_id={consultation_uuid}")
        
        # 4. 存储到 doctor_sessions 表（兼容历史记录系统）
        cursor.execute("""
            INSERT OR REPLACE INTO doctor_sessions (
                session_id, user_id, doctor_name, chief_complaint,
                session_status, created_at, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request.conversation_id,
            user_id,
            request.selected_doctor,
            request.message[:100] if request.message else "问诊咨询",  # 截取前100字符作为主诉
            "active" if _determine_consultation_status(response) in ['in_progress', 'pending_payment', 'pending_review'] else "completed",
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        logger.info(f"✅ 问诊记录已存储: user={user_id}, doctor={request.selected_doctor}, 包含处方={response.contains_prescription}")
        
    except Exception as e:
        logger.error(f"❌ 存储问诊记录失败: {e}")
        logger.error(traceback.format_exc())
    finally:
        if 'conn' in locals():
            conn.close()

async def _submit_to_doctor_review_queue(cursor, prescription_id: int, request: ChatMessage, consultation_uuid: str) -> None:
    """
    🔑 自动提交处方到医生审核队列
    实现患者问诊后处方自动进入审核流程
    """
    try:
        # 提交到医生审核队列
        cursor.execute("""
            INSERT INTO doctor_review_queue (
                prescription_id, doctor_id, consultation_id, 
                submitted_at, status, priority
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prescription_id,
            request.selected_doctor,  # AI医生ID，后续可由真实医生审核
            consultation_uuid,
            datetime.now().isoformat(),
            'pending',  # 待审核
            'normal'    # 正常优先级
        ))
        
        logger.info(f"✅ 处方已提交到审核队列: prescription_id={prescription_id}, doctor={request.selected_doctor}")
        
    except Exception as e:
        logger.error(f"❌ 提交审核队列失败: {e}")
        # 不抛出异常，避免影响主流程，但记录错误
        import traceback
        logger.error(traceback.format_exc())

async def _sync_prescription_status_to_patient(prescription_id: int, new_status: str) -> None:
    """
    🔑 医生审核后同步处方状态到患者端
    实现医生审核结果的实时同步
    """
    try:
        conn = sqlite3.connect('/opt/tcm-ai/data/user_history.sqlite')
        cursor = conn.cursor()
        
        # 根据审核结果更新患者端可见性
        if new_status in ['doctor_approved', 'doctor_modified']:
            # 审核通过，设置为支付等待状态
            cursor.execute("""
                UPDATE prescriptions 
                SET is_visible_to_patient = 1,
                    payment_status = 'pending',
                    visibility_unlock_time = datetime('now')
                WHERE id = ?
            """, (prescription_id,))
            
            logger.info(f"✅ 处方审核通过，患者可支付解锁: prescription_id={prescription_id}")
            
        elif new_status == 'doctor_rejected':
            # 审核拒绝，仍保持不可见
            cursor.execute("""
                UPDATE prescriptions 
                SET is_visible_to_patient = 0,
                    payment_status = 'rejected'
                WHERE id = ?
            """, (prescription_id,))
            
            logger.info(f"❌ 处方审核拒绝，患者不可见: prescription_id={prescription_id}")
        
        # 获取处方相关信息，用于通知患者
        cursor.execute("""
            SELECT patient_id, conversation_id 
            FROM prescriptions 
            WHERE id = ?
        """, (prescription_id,))
        
        prescription_info = cursor.fetchone()
        if prescription_info:
            patient_id, conversation_id = prescription_info
            
            # TODO: 这里可以扩展为实时通知系统
            # 比如WebSocket推送、短信通知等
            logger.info(f"📱 处方状态已更新，患者 {patient_id} 将在下次刷新时看到更新")
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"❌ 同步处方状态到患者端失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if 'conn' in locals():
            conn.close()

# 🔑 新增：更新问诊状态API
class ConsultationUpdateRequest(BaseModel):
    """问诊状态更新请求"""
    patient_id: str
    status: str  # 'completed', 'cancelled', 'in_progress'
    prescription_id: Optional[int] = None
    conversation_log: Optional[str] = None
    symptoms_analysis: Optional[str] = None
    updated_at: Optional[str] = None

@router.post("/update-status")
async def update_consultation_status(request: ConsultationUpdateRequest):
    """更新问诊状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查找最近的问诊记录
        cursor.execute("""
            SELECT id, uuid FROM consultations 
            WHERE patient_id = ? AND status <> 'completed'
            ORDER BY created_at DESC LIMIT 1
        """, (request.patient_id,))
        
        consultation = cursor.fetchone()
        if not consultation:
            raise HTTPException(status_code=404, detail="未找到进行中的问诊记录")
        
        # 更新问诊记录
        update_fields = ["status = ?", "updated_at = ?"]
        update_values = [request.status, datetime.now().isoformat()]
        
        if request.conversation_log:
            update_fields.append("conversation_log = ?")
            update_values.append(request.conversation_log)
        
        if request.symptoms_analysis:
            update_fields.append("symptoms_analysis = ?")
            update_values.append(request.symptoms_analysis)
        
        update_values.append(consultation['id'])
        
        cursor.execute(f"""
            UPDATE consultations 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """, update_values)
        
        # 如果有处方ID，关联到问诊记录
        if request.prescription_id:
            cursor.execute("""
                UPDATE prescriptions 
                SET consultation_id = ?
                WHERE id = ?
            """, (consultation['uuid'], request.prescription_id))
        
        conn.commit()
        
        logger.info(f"✅ 问诊状态更新成功: id={consultation['id']}, status={request.status}")
        
        return {
            "success": True,
            "message": "问诊状态更新成功",
            "consultation_id": consultation['uuid'],
            "status": request.status
        }
        
    except Exception as e:
        logger.error(f"❌ 问诊状态更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

@router.get("/detail/{session_id}")
async def get_conversation_detail(session_id: str):
    """获取对话详细信息，用于详情弹窗显示"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 从consultations表获取完整对话记录
        cursor.execute("""
            SELECT c.uuid, c.patient_id, c.selected_doctor_id, c.conversation_log, 
                   c.symptoms_analysis, c.tcm_syndrome, c.status, c.created_at, c.updated_at,
                   p.id as prescription_id, p.ai_prescription, p.diagnosis, p.symptoms,
                   p.payment_status, p.prescription_fee, p.is_visible_to_patient
            FROM consultations c
            LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
            WHERE c.uuid = ? OR EXISTS (
                SELECT 1 FROM doctor_sessions ds 
                WHERE ds.session_id = ? AND ds.user_id = c.patient_id 
                AND ds.doctor_name = c.selected_doctor_id
            )
            ORDER BY c.created_at DESC
            LIMIT 1
        """, (session_id, session_id))
        
        result = cursor.fetchone()
        if not result:
            # 尝试从doctor_sessions表查找并获取对应的consultations记录
            cursor.execute("""
                SELECT ds.session_id, ds.user_id, ds.doctor_name, ds.chief_complaint,
                       ds.session_status, ds.created_at, ds.last_updated,
                       c.uuid, c.conversation_log, c.symptoms_analysis, c.tcm_syndrome,
                       p.id as prescription_id, p.ai_prescription, p.diagnosis, p.symptoms,
                       p.payment_status, p.prescription_fee
                FROM doctor_sessions ds
                LEFT JOIN consultations c ON ds.user_id = c.patient_id AND ds.doctor_name = c.selected_doctor_id
                LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
                WHERE ds.session_id = ?
                ORDER BY ds.created_at DESC
                LIMIT 1
            """, (session_id,))
            
            ds_result = cursor.fetchone()
            if not ds_result:
                return {
                    "success": False,
                    "message": "未找到对话记录"
                }
            
            # 构建基于doctor_sessions的响应
            conversation_data = {
                "session_id": ds_result['session_id'],
                "patient_id": ds_result['user_id'],
                "doctor_id": ds_result['doctor_name'],
                "chief_complaint": ds_result['chief_complaint'],
                "status": ds_result['session_status'],
                "created_at": ds_result['created_at'],
                "updated_at": ds_result['last_updated'],
                "conversation_history": [],
                "symptoms_summary": ds_result['chief_complaint'] if ds_result['chief_complaint'] else "暂无详细症状记录",
                "diagnosis": "基于主诉的初步评估",
                "syndrome": "待进一步辨证",
                "prescription": None,
                "prescription_info": None
            }
            
            # 如果有关联的完整consultation记录，使用更详细的信息
            if ds_result['conversation_log']:
                try:
                    log_data = json.loads(ds_result['conversation_log'])
                    conversation_data.update({
                        "conversation_history": log_data.get('conversation_history', []),
                        "symptoms_analysis": ds_result['symptoms_analysis'],
                        "syndrome": ds_result['tcm_syndrome']
                    })
                except:
                    pass
        else:
            # 解析conversation_log获取对话历史
            conversation_history = []
            symptoms_summary = ""
            diagnosis = ""
            syndrome = ""
            
            try:
                if result['conversation_log']:
                    log_data = json.loads(result['conversation_log'])
                    conversation_history = log_data.get('conversation_history', [])
                    
                    # 提取患者症状描述（第一轮对话）
                    if conversation_history:
                        symptoms_summary = conversation_history[0].get('patient_query', '')
                
                # 解析症状分析
                if result['symptoms_analysis']:
                    symptoms_data = json.loads(result['symptoms_analysis'])
                    # 可以从这里提取更多症状分析信息
                
                # 🔑 修复：从对话历史中提取实际的中医诊断信息
                diagnosis_extracted = ""
                syndrome_extracted = ""
                
                # 从AI回复中提取诊断和证候信息
                for conv in conversation_history:
                    ai_response = conv.get('ai_response', '')
                    if ai_response:
                        # 提取诊断信息
                        if ('诊断' in ai_response or '证' in ai_response or '辨证' in ai_response) and not diagnosis_extracted:
                            # 尝试提取诊断部分
                            import re
                            diagnosis_patterns = [
                                r'诊断[：:](.*?)(?=[。\n]|证候|处方|$)',
                                r'中医诊断[：:](.*?)(?=[。\n]|证候|处方|$)',
                                r'([^。]*证[^。]*)',
                                r'辨证[：:](.*?)(?=[。\n]|处方|$)'
                            ]
                            for pattern in diagnosis_patterns:
                                match = re.search(pattern, ai_response, re.DOTALL)
                                if match:
                                    diagnosis_extracted = match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
                                    break
                        
                        # 提取证候信息
                        if ('证候' in ai_response or '证型' in ai_response) and not syndrome_extracted:
                            syndrome_patterns = [
                                r'证候[：:](.*?)(?=[。\n]|处方|$)',
                                r'证型[：:](.*?)(?=[。\n]|处方|$)',
                                r'([^。]*?证候[^。]*?)'
                            ]
                            for pattern in syndrome_patterns:
                                match = re.search(pattern, ai_response, re.DOTALL)
                                if match:
                                    syndrome_extracted = match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
                                    break
                
                # 解析存储的中医证候
                if result['tcm_syndrome'] and not syndrome_extracted:
                    try:
                        syndrome_data = json.loads(result['tcm_syndrome'])
                        if isinstance(syndrome_data, dict):
                            syndrome_extracted = syndrome_data.get('syndrome', '') or json.dumps(syndrome_data, ensure_ascii=False)
                        else:
                            syndrome_extracted = str(syndrome_data)
                    except:
                        pass
                
                # 使用提取的信息或备用信息
                diagnosis = diagnosis_extracted or result.get('diagnosis', '') or "基于患者症状的中医辨证分析"
                syndrome = syndrome_extracted or "待进一步辨证分析"
                
            except json.JSONDecodeError as e:
                logger.warning(f"解析conversation_log失败: {e}")
            
            # 构建响应数据
            conversation_data = {
                "session_id": result['uuid'],
                "patient_id": result['patient_id'],
                "doctor_id": result['selected_doctor_id'],
                "chief_complaint": symptoms_summary[:100] + ('...' if len(symptoms_summary) > 100 else ''),
                "status": result['status'],
                "created_at": result['created_at'],
                "updated_at": result['updated_at'],
                "conversation_history": conversation_history,
                "symptoms_summary": symptoms_summary,
                "diagnosis": diagnosis,
                "syndrome": syndrome,
                "prescription": result['ai_prescription'] if result['ai_prescription'] else None,
                "prescription_info": {
                    "prescription_id": result['prescription_id'],
                    "payment_status": result['payment_status'],
                    "prescription_fee": result['prescription_fee'],
                    "is_visible": result['is_visible_to_patient']
                } if result['prescription_id'] else None
            }
        
        conn.close()
        
        # 获取医生信息
        doctor_names = {
            "zhang_zhongjing": "张仲景",
            "ye_tianshi": "叶天士", 
            "li_dongyuan": "李东垣",
            "zheng_qin_an": "郑钦安",
            "liu_duzhou": "刘渡舟",
            "zhu_danxi": "朱丹溪"
        }
        
        conversation_data["doctor_name"] = doctor_names.get(conversation_data["doctor_id"], conversation_data["doctor_id"])
        
        # 计算问诊轮次
        conversation_data["total_rounds"] = len(conversation_data["conversation_history"])
        
        # 计算问诊时长（如果有开始和结束时间）
        try:
            from datetime import datetime
            start_time = datetime.fromisoformat(conversation_data["created_at"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(conversation_data["updated_at"].replace('Z', '+00:00'))
            duration_minutes = int((end_time - start_time).total_seconds() / 60)
            conversation_data["duration_minutes"] = duration_minutes
        except:
            conversation_data["duration_minutes"] = 0
        
        return {
            "success": True,
            "data": conversation_data,
            "message": "获取对话详情成功"
        }
        
    except Exception as e:
        logger.error(f"获取对话详情失败: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"获取详情失败: {str(e)}"
        }

@router.get("/patient/history")
async def get_patient_consultation_history(http_request: Request):
    """
    🔑 获取患者历史问诊内容，包括未支付状态的处方
    支持跨设备同步和实时状态更新
    """
    try:
        # 获取用户ID (优先认证用户，回退到URL参数或guest)
        user_id = None
        
        # 1. 尝试从认证token获取
        auth_header = http_request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            try:
                from api.main import get_user_info_by_token
                auth_user_info = await get_user_info_by_token(token)
                if auth_user_info and auth_user_info.get('user_id'):
                    user_id = auth_user_info['user_id']
            except:
                pass
        
        # 2. 从URL参数获取
        if not user_id:
            user_id = http_request.query_params.get('user_id', 'guest')
        
        logger.info(f"📋 获取患者历史问诊: user_id={user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取患者的完整问诊历史（包含处方状态）
        cursor.execute("""
            SELECT 
                c.uuid, c.patient_id, c.selected_doctor_id, c.conversation_log,
                c.symptoms_analysis, c.tcm_syndrome, c.status, c.created_at, c.updated_at,
                p.id as prescription_id, p.ai_prescription, p.doctor_prescription, 
                p.diagnosis, p.symptoms, p.status as prescription_status,
                p.review_status, p.payment_status, p.prescription_fee, 
                p.is_visible_to_patient, p.visibility_unlock_time, p.reviewed_at,
                d.name as doctor_name, d.speciality as doctor_specialty
            FROM consultations c
            LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
            LEFT JOIN doctors d ON CAST(p.doctor_id AS INTEGER) = d.id
            WHERE c.patient_id = ?
            ORDER BY c.created_at DESC
            LIMIT 50
        """, (user_id,))
        
        rows = cursor.fetchall()
        
        # 构建历史记录数据
        consultation_history = []
        
        for row in rows:
            # 解析对话历史
            conversation_history = []
            try:
                if row['conversation_log']:
                    log_data = json.loads(row['conversation_log'])
                    conversation_history = log_data.get('conversation_history', [])
            except:
                pass
            
            # 医生信息映射
            doctor_names = {
                "zhang_zhongjing": "张仲景",
                "ye_tianshi": "叶天士", 
                "li_dongyuan": "李东垣",
                "zheng_qin_an": "郑钦安",
                "liu_duzhou": "刘渡舟",
                "zhu_danxi": "朱丹溪",
                "jin_daifu": "金大夫"
            }
            
            doctor_display_name = doctor_names.get(row['selected_doctor_id'], row['doctor_name'] or row['selected_doctor_id'])
            
            # 构建单条历史记录
            consultation_record = {
                "consultation_id": row['uuid'],
                "doctor_id": row['selected_doctor_id'],
                "doctor_name": doctor_display_name,
                "doctor_specialty": row['doctor_specialty'] or "中医内科",
                "created_at": row['created_at'],
                "updated_at": row['updated_at'],
                "consultation_status": row['status'],
                "conversation_history": conversation_history,
                "total_messages": len(conversation_history),
                
                # 处方信息
                "has_prescription": bool(row['prescription_id']),
                "prescription_info": None
            }
            
            # 如果有处方，添加处方详情
            if row['prescription_id']:
                # 🔑 根据审核状态和支付状态决定处方可见性
                is_prescription_visible = False
                prescription_display_text = ""
                prescription_action_required = ""
                
                if row['review_status'] == 'pending_review':
                    prescription_display_text = "处方正在医生审核中，请耐心等待..."
                    prescription_action_required = "waiting_review"
                    
                elif row['review_status'] == 'approved' and row['payment_status'] == 'pending':
                    prescription_display_text = "处方审核通过，需要支付后查看完整内容"
                    prescription_action_required = "payment_required"
                    is_prescription_visible = bool(row['is_visible_to_patient'])
                    
                elif row['review_status'] == 'approved' and row['payment_status'] == 'completed':
                    prescription_display_text = row['doctor_prescription'] or row['ai_prescription']
                    prescription_action_required = "completed"
                    is_prescription_visible = True
                    
                elif row['review_status'] == 'rejected':
                    prescription_display_text = "处方审核未通过，建议重新问诊"
                    prescription_action_required = "rejected"
                    
                else:
                    # 默认情况（旧数据兼容）
                    prescription_display_text = row['ai_prescription'] or "处方信息不完整"
                    prescription_action_required = "unknown"
                
                consultation_record["prescription_info"] = {
                    "prescription_id": row['prescription_id'],
                    "status": row['prescription_status'],
                    "review_status": row['review_status'],
                    "payment_status": row['payment_status'],
                    "prescription_fee": row['prescription_fee'] or 88.0,
                    "is_visible": is_prescription_visible,
                    "display_text": prescription_display_text,
                    "action_required": prescription_action_required,
                    "diagnosis": row['diagnosis'] or "",
                    "symptoms": row['symptoms'] or "",
                    "reviewed_at": row['reviewed_at'],
                    "visibility_unlock_time": row['visibility_unlock_time']
                }
            
            consultation_history.append(consultation_record)
        
        conn.close()
        
        logger.info(f"✅ 获取到 {len(consultation_history)} 条历史问诊记录")
        
        return {
            "success": True,
            "data": {
                "consultation_history": consultation_history,
                "total_count": len(consultation_history),
                "user_id": user_id
            },
            "message": "历史记录获取成功"
        }
        
    except Exception as e:
        logger.error(f"获取患者历史问诊失败: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"获取历史记录失败: {str(e)}"
        }


def _determine_consultation_status(response) -> str:
    """
    🔑 根据问诊回复确定问诊状态，修复历史记录重复问题
    """
    if response.contains_prescription:
        # 包含处方时，应该是等待患者支付/医生审核状态，而不是完成状态
        if hasattr(response, 'prescription_data') and response.prescription_data:
            payment_status = response.prescription_data.get('payment_status', 'pending')
            if payment_status == 'paid':
                return 'pending_review'  # 已支付，等待医生审核
            else:
                return 'pending_payment'  # 等待患者支付
        else:
            return 'pending_payment'  # 默认等待支付
    else:
        return 'in_progress'  # 仍在问诊中

