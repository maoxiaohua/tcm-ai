#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话状态同步API路由
解决患者跨设备登录问诊记录丢失问题的服务端支持
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timedelta
from app.services import local_sqlite_service as sqlite_service

router = APIRouter(prefix="/api/conversation", tags=["对话状态同步"])

class ConversationState(BaseModel):
    """对话状态模型"""
    conversation_id: str
    user_id: str
    doctor_id: str
    current_state: str
    state_history: List[Dict[str, Any]] = []
    conversation_data: Dict[str, Any] = {}
    start_time: int
    last_updated: int
    is_active: bool = True

class ConversationSyncRequest(BaseModel):
    """对话同步请求"""
    user_id: str
    doctor_id: str
    state_data: Dict[str, Any]
    device_info: Optional[Dict[str, Any]] = {}

class HistoryResponse(BaseModel):
    """历史记录响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

@router.post("/sync", response_model=HistoryResponse)
async def sync_conversation_state(request: ConversationSyncRequest, req: Request):
    """同步对话状态到服务器"""
    try:
        user_id = request.user_id
        doctor_id = request.doctor_id
        state_data = request.state_data
        
        if not user_id or not doctor_id:
            raise HTTPException(status_code=400, detail="用户ID和医生ID不能为空")
        now_iso = datetime.now().isoformat()
        ip_address = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("User-Agent", "unknown")

        conversation_id = sqlite_service.sync_conversation_state_record(
            user_id=user_id,
            doctor_id=doctor_id,
            state_data=state_data,
            device_info=request.device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            now_iso=now_iso,
        )
        
        return HistoryResponse(
            success=True,
            message="对话状态同步成功",
            data={
                "conversation_id": conversation_id,
                "sync_time": now_iso
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")

@router.get("/history/{user_id}", response_model=HistoryResponse)
async def get_conversation_history(user_id: str, doctor_id: Optional[str] = None):
    """获取用户的对话历史，支持跨设备同步"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")
        result_data = sqlite_service.fetch_conversation_history_bundle(
            user_id=user_id,
            doctor_id=doctor_id,
            sync_time=datetime.now().isoformat(),
        )
        
        return HistoryResponse(
            success=True,
            message=(
                f"成功获取{len(result_data['conversation_states'])}个对话状态，"
                f"{len(result_data['consultation_records'])}个问诊记录"
            ),
            data=result_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")

@router.post("/clear", response_model=HistoryResponse)
async def clear_conversation_history(request: Dict[str, Any]):
    """清空用户与特定医生的对话记录"""
    try:
        user_id = request.get('user_id')
        doctor_id = request.get('doctor_id')
        clear_type = request.get('clear_type', 'all')
        
        if not user_id or not doctor_id:
            raise HTTPException(status_code=400, detail="用户ID和医生ID不能为空")

        deleted_count = sqlite_service.clear_conversation_history_records(
            user_id=user_id,
            doctor_id=doctor_id,
            clear_type=clear_type,
        )
        
        return HistoryResponse(
            success=True,
            message=f"已清空{deleted_count}条相关记录",
            data={
                "user_id": user_id,
                "doctor_id": doctor_id,
                "deleted_count": deleted_count,
                "clear_type": clear_type,
                "clear_time": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空记录失败: {str(e)}")

@router.get("/status/{user_id}/{doctor_id}", response_model=HistoryResponse)
async def get_conversation_status(user_id: str, doctor_id: str):
    """获取特定用户和医生的当前对话状态"""
    try:
        result = sqlite_service.fetch_conversation_status(
            user_id=user_id,
            doctor_id=doctor_id,
        )
        
        if result:
            status_data = dict(result)
            # 解析JSON字段
            try:
                status_data['symptoms_collected'] = json.loads(status_data['symptoms_collected'] or '{}')
                status_data['stage_history'] = json.loads(status_data['stage_history'] or '[]')
            except json.JSONDecodeError:
                status_data['symptoms_collected'] = {}
                status_data['stage_history'] = []
            
            return HistoryResponse(
                success=True,
                message="成功获取对话状态",
                data=status_data
            )
        else:
            return HistoryResponse(
                success=True,
                message="未找到活跃的对话状态",
                data=None
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话状态失败: {str(e)}")

@router.delete("/cleanup/{user_id}")
async def cleanup_old_conversations(user_id: str, days: int = 7):
    """清理用户的过期对话数据"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        cleanup_count = sqlite_service.cleanup_old_conversation_states(
            user_id=user_id,
            cutoff_date=cutoff_date,
        )
        
        return HistoryResponse(
            success=True,
            message=f"已清理{cleanup_count}个过期对话状态",
            data={"cleanup_count": cleanup_count, "cutoff_date": cutoff_date}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

@router.post("/backup/{user_id}")
async def create_user_backup(user_id: str):
    """为用户创建完整的数据备份"""
    try:
        backup_time = datetime.now().isoformat()
        backup_data = sqlite_service.create_user_backup_data(
            user_id=user_id,
            backup_time=backup_time,
        )
        
        # 可以选择将备份保存到文件或返回给前端
        return HistoryResponse(
            success=True,
            message=f"成功创建用户备份，包含{sum(len(v) for v in backup_data['data'].values())}条记录",
            data=backup_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")
