"""
对话管理路由 - v4.0 重构版

核心理念：后端是唯一权威数据源，基于数据库状态做所有决策
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import sqlite3
import json
import uuid
from datetime import datetime

# 导入统一账号管理器
from core.unified_account.account_manager import unified_account_manager

router = APIRouter()

# 辅助函数：从token获取用户
async def get_current_user_from_header(authorization: Optional[str] = Header(None)):
    """从Header中获取当前用户（复用现有认证系统）"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔍 [Auth Debug] Authorization header: {authorization[:50] if authorization else 'None'}...")
        
        if not authorization or not authorization.startswith('Bearer '):
            logger.warning("⚠️ [Auth Debug] Missing or invalid Authorization header")
            raise HTTPException(status_code=401, detail="需要认证")

        session_id = authorization.replace('Bearer ', '')
        logger.info(f"🔑 [Auth Debug] Extracted session_id: {session_id[:20]}...")
        
        session = unified_account_manager.get_session(session_id)
        logger.info(f"📋 [Auth Debug] Session lookup result: {session is not None}")
        
        if not session:
            logger.warning(f"❌ [Auth Debug] Session not found for session_id: {session_id[:20]}...")
            raise HTTPException(status_code=401, detail="会话无效或已过期")

        user = unified_account_manager.get_user_by_id(session.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        return user, session
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"认证过程出错: {e}")
        raise HTTPException(status_code=500, detail=f"认证系统错误: {str(e)}")


class SwitchDoctorRequest(BaseModel):
    doctor_id: str


class SwitchDoctorResponse(BaseModel):
    success: bool
    consultation_id: str
    messages: list
    is_new: bool
    reason: str
    message: str


@router.post("/conversation/switch-doctor", response_model=SwitchDoctorResponse)
async def switch_doctor(
    request: SwitchDoctorRequest,
    current_user_data: tuple = Depends(get_current_user_from_header)
):
    """
    智能切换医生

    核心逻辑：
    1. 查询该医生的最新consultation
    2. 检查该consultation是否有prescription
    3. 如果有处方 → 创建新consultation（新对话）
    4. 如果无处方 → 返回现有consultation（继续对话）
    5. 如果无历史 → 创建新consultation（首次对话）

    这样确保：
    - 每个完整问诊（开始→处方）在独立的consultation中
    - 用户切换医生时能看到历史，但新问题会开启新对话
    - 不依赖前端状态，完全基于数据库
    """

    # 提取用户信息
    user, session = current_user_data
    user_id = user.global_user_id

    conn = sqlite3.connect('/opt/tcm-ai/data/user_history.sqlite')
    cursor = conn.cursor()

    try:
        # 1. 查询该医生的最新consultation
        cursor.execute("""
            SELECT uuid, conversation_log, created_at
            FROM consultations
            WHERE patient_id = ? AND selected_doctor_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, request.doctor_id))

        latest = cursor.fetchone()

        if latest:
            consultation_id = latest[0]
            conversation_log = latest[1]

            # 2. 检查该consultation是否有prescription
            cursor.execute("""
                SELECT id, created_at
                FROM prescriptions
                WHERE consultation_id = ?
                LIMIT 1
            """, (consultation_id,))

            prescription = cursor.fetchone()
            has_prescription = prescription is not None

            if has_prescription:
                # === 情况A：该医生的最新对话已有处方 ===
                # 创建新consultation，开启新对话

                new_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO consultations
                    (uuid, patient_id, selected_doctor_id, conversation_log, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_id,
                    user_id,
                    request.doctor_id,
                    json.dumps({
                        "conversation_id": new_id,
                        "conversation_history": [],
                        "current_stage": "inquiry",
                        "confidence_score": 0
                    }),
                    datetime.now().isoformat() + 'Z'
                ))
                conn.commit()

                return SwitchDoctorResponse(
                    success=True,
                    consultation_id=new_id,
                    messages=[],
                    is_new=True,
                    reason="previous_conversation_has_prescription",
                    message=f"上次对话已完成（处方ID: {prescription[0]}），已开启新对话"
                )

            else:
                # === 情况B：该医生的最新对话未完成（无处方） ===
                # 返回现有consultation，继续对话

                # 解析conversation_log获取历史消息
                try:
                    log_data = json.loads(conversation_log) if conversation_log else {}

                    # 处理旧格式（list）和新格式（dict）
                    if isinstance(log_data, list):
                        conversation_history = log_data
                    else:
                        conversation_history = log_data.get('conversation_history', [])

                    # 转换为前端格式
                    messages = []
                    for item in conversation_history:
                        # 🔑 v4.2 修复：优先处理新格式 {type, content}
                        if 'type' in item and 'content' in item:
                            # 新格式：直接使用 type 和 content
                            messages.append({
                                'type': item['type'],
                                'content': item['content'],
                                'time': item.get('time', ''),
                                'timestamp': item.get('timestamp', 0)
                            })
                        else:
                            # 旧格式：patient_query / ai_response
                            if 'patient_query' in item:
                                messages.append({
                                    'type': 'user',
                                    'content': item['patient_query'],
                                    'time': item.get('time', ''),
                                    'timestamp': item.get('timestamp', 0)
                                })
                            if 'ai_response' in item:
                                messages.append({
                                    'type': 'ai',
                                    'content': item['ai_response'],
                                    'time': item.get('time', ''),
                                    'timestamp': item.get('timestamp', 0)
                                })

                    return SwitchDoctorResponse(
                        success=True,
                        consultation_id=consultation_id,
                        messages=messages,
                        is_new=False,
                        reason="continue_unfinished_conversation",
                        message=f"继续未完成的对话（{len(messages)}条消息）"
                    )

                except json.JSONDecodeError:
                    # conversation_log格式错误，返回空消息
                    return SwitchDoctorResponse(
                        success=True,
                        consultation_id=consultation_id,
                        messages=[],
                        is_new=False,
                        reason="continue_conversation_parse_error",
                        message="继续对话（历史消息解析失败）"
                    )

        else:
            # === 情况C：该医生无历史对话 ===
            # 创建新consultation，首次对话

            new_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO consultations
                (uuid, patient_id, selected_doctor_id, conversation_log, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                new_id,
                user_id,
                request.doctor_id,
                json.dumps({
                    "conversation_id": new_id,
                    "conversation_history": [],
                    "current_stage": "inquiry",
                    "confidence_score": 0
                }),
                datetime.now().isoformat() + 'Z'
            ))
            conn.commit()

            return SwitchDoctorResponse(
                success=True,
                consultation_id=new_id,
                messages=[],
                is_new=True,
                reason="first_conversation_with_doctor",
                message=f"首次与该医生对话"
            )

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"切换医生失败: {str(e)}")

    finally:
        conn.close()


@router.get("/conversation/info/{consultation_id}")
async def get_conversation_info(
    consultation_id: str,
    current_user_data: tuple = Depends(get_current_user_from_header)
):
    """
    获取指定对话的详细信息
    """
    # 提取用户信息
    user, session = current_user_data
    user_id = user.global_user_id

    conn = sqlite3.connect('/opt/tcm-ai/data/user_history.sqlite')
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                c.uuid,
                c.selected_doctor_id,
                c.conversation_log,
                c.created_at,
                p.id as prescription_id,
                p.status as prescription_status
            FROM consultations c
            LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
            WHERE c.uuid = ? AND c.patient_id = ?
        """, (consultation_id, user_id))

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="对话不存在")

        return {
            "success": True,
            "consultation_id": row[0],
            "doctor_id": row[1],
            "created_at": row[3],
            "has_prescription": row[4] is not None,
            "prescription_id": row[4],
            "prescription_status": row[5]
        }

    finally:
        conn.close()
