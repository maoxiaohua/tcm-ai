#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话状态同步API路由
解决患者跨设备登录问诊记录丢失问题的服务端支持
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json
import uuid
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/conversation", tags=["对话状态同步"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

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
        
        # 生成对话ID
        conversation_id = f"conv_{user_id}_{doctor_id}_{int(datetime.now().timestamp())}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在活跃的对话状态
        cursor.execute("""
            SELECT conversation_id, current_stage, last_activity 
            FROM conversation_states 
            WHERE user_id = ? AND doctor_id = ? AND is_active = 1
            ORDER BY last_activity DESC LIMIT 1
        """, (user_id, doctor_id))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有对话状态
            conversation_id = existing['conversation_id']
            cursor.execute("""
                UPDATE conversation_states 
                SET current_stage = ?, 
                    last_activity = ?, 
                    turn_count = turn_count + 1,
                    symptoms_collected = ?,
                    stage_history = ?,
                    updated_at = ?
                WHERE conversation_id = ?
            """, (
                state_data.get('currentState', 'initial_inquiry'),
                datetime.now().isoformat(),
                json.dumps(state_data.get('conversationData', {})),
                json.dumps(state_data.get('stateHistory', [])),
                datetime.now().isoformat(),
                conversation_id
            ))
        else:
            # 创建新的对话状态
            cursor.execute("""
                INSERT INTO conversation_states 
                (conversation_id, user_id, doctor_id, current_stage, start_time, 
                 last_activity, turn_count, symptoms_collected, stage_history, 
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                user_id,
                doctor_id,
                state_data.get('currentState', 'initial_inquiry'),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                1,
                json.dumps(state_data.get('conversationData', {})),
                json.dumps(state_data.get('stateHistory', [])),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        # 记录设备信息
        if request.device_info:
            ip_address = req.client.host if req.client else "unknown"
            user_agent = req.headers.get("User-Agent", "unknown")
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_devices 
                (user_id, device_fingerprint, ip_address, user_agent, last_used, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                user_id,
                request.device_info.get('fingerprint', 'unknown'),
                ip_address,
                user_agent,
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        
        return HistoryResponse(
            success=True,
            message="对话状态同步成功",
            data={
                "conversation_id": conversation_id,
                "sync_time": datetime.now().isoformat()
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取对话状态
        if doctor_id:
            # 获取特定医生的对话状态
            cursor.execute("""
                SELECT * FROM conversation_states 
                WHERE user_id = ? AND doctor_id = ? AND is_active = 1
                ORDER BY last_activity DESC LIMIT 1
            """, (user_id, doctor_id))
        else:
            # 获取所有活跃对话
            cursor.execute("""
                SELECT * FROM conversation_states 
                WHERE user_id = ? AND is_active = 1
                ORDER BY last_activity DESC LIMIT 5
            """, (user_id,))
        
        conversation_states = cursor.fetchall()
        
        # 获取问诊记录
        cursor.execute("""
            SELECT uuid, selected_doctor_id, symptoms_analysis, tcm_syndrome, 
                   status, created_at, updated_at
            FROM consultations 
            WHERE patient_id = ?
            ORDER BY created_at DESC LIMIT 10
        """, (user_id,))
        
        consultation_records = cursor.fetchall()
        
        # 获取最近的消息记录（如果有会话元数据表）
        cursor.execute("""
            SELECT conversation_id, message_count, diagnosis_summary, 
                   prescription_given, created_at
            FROM conversation_metadata cm
            JOIN doctor_sessions ds ON cm.session_id = ds.session_id
            WHERE ds.patient_id = ?
            ORDER BY cm.created_at DESC LIMIT 5
        """, (user_id,))
        
        recent_messages = cursor.fetchall()
        
        conn.close()
        
        # 转换为字典格式
        result_data = {
            "conversation_states": [dict(row) for row in conversation_states],
            "consultation_records": [dict(row) for row in consultation_records],
            "recent_messages": [dict(row) for row in recent_messages],
            "user_id": user_id,
            "sync_time": datetime.now().isoformat()
        }
        
        return HistoryResponse(
            success=True,
            message=f"成功获取{len(conversation_states)}个对话状态，{len(consultation_records)}个问诊记录",
            data=result_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")

@router.get("/status/{user_id}/{doctor_id}", response_model=HistoryResponse)
async def get_conversation_status(user_id: str, doctor_id: str):
    """获取特定用户和医生的当前对话状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cs.*, 
                   COUNT(csh.id) as state_transitions,
                   MAX(csh.created_at) as last_transition_time
            FROM conversation_states cs
            LEFT JOIN conversation_stage_history csh ON cs.conversation_id = csh.conversation_id
            WHERE cs.user_id = ? AND cs.doctor_id = ? AND cs.is_active = 1
            GROUP BY cs.conversation_id
            ORDER BY cs.last_activity DESC LIMIT 1
        """, (user_id, doctor_id))
        
        result = cursor.fetchone()
        conn.close()
        
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 清理过期的对话状态
        cursor.execute("""
            UPDATE conversation_states 
            SET is_active = 0 
            WHERE user_id = ? AND last_activity < ? AND is_active = 1
        """, (user_id, cutoff_date))
        
        cleanup_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 备份所有用户相关数据
        tables_to_backup = [
            ('conversation_states', 'user_id'),
            ('consultations', 'patient_id'),
            ('conversation_metadata', None),  # 通过JOIN获取
            ('user_sessions', 'user_id')
        ]
        
        backup_data = {
            "user_id": user_id,
            "backup_time": datetime.now().isoformat(),
            "data": {}
        }
        
        for table_name, user_field in tables_to_backup:
            if user_field:
                cursor.execute(f"SELECT * FROM {table_name} WHERE {user_field} = ?", (user_id,))
            else:
                # 特殊处理conversation_metadata
                cursor.execute("""
                    SELECT cm.* FROM conversation_metadata cm
                    JOIN doctor_sessions ds ON cm.session_id = ds.session_id
                    WHERE ds.patient_id = ?
                """, (user_id,))
            
            rows = cursor.fetchall()
            backup_data["data"][table_name] = [dict(row) for row in rows]
        
        conn.close()
        
        # 可以选择将备份保存到文件或返回给前端
        return HistoryResponse(
            success=True,
            message=f"成功创建用户备份，包含{sum(len(v) for v in backup_data['data'].values())}条记录",
            data=backup_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")