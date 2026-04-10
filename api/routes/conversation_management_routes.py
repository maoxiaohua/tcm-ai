"""
对话管理路由 - v4.0 重构版

核心理念：后端是唯一权威数据源，基于数据库状态做所有决策
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Any

# 导入统一账号管理器
from core.unified_account.account_manager import unified_account_manager
from app.services import local_sqlite_service as sqlite_service

router = APIRouter()


def _first_non_empty(*values: Any) -> Optional[Any]:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
            continue
        if value is not None:
            return value
    return None

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
    doctor_id: Optional[str] = None
    selected_doctor: Optional[str] = None
    doctor_name: Optional[str] = None


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

    try:
        doctor_id = _first_non_empty(
            request.doctor_id,
            request.selected_doctor,
            request.doctor_name,
        )
        if not doctor_id:
            raise HTTPException(status_code=400, detail="doctor_id 不能为空")

        result = sqlite_service.switch_doctor_conversation(
            user_id=user_id,
            doctor_id=str(doctor_id),
        )

        return SwitchDoctorResponse(
            success=True,
            consultation_id=result["consultation_id"],
            messages=result["messages"],
            is_new=result["is_new"],
            reason=result["reason"],
            message=result["message"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换医生失败: {str(e)}")


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

    try:
        info = sqlite_service.fetch_conversation_info(
            consultation_id=consultation_id,
            user_id=user_id,
        )
        if not info:
            raise HTTPException(status_code=404, detail="对话不存在")

        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话信息失败: {str(e)}")
