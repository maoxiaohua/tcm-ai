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
        
        # 🔑 修复：从consultations表获取实际的对话消息，转换为前端期望的格式
        messages = []
        try:
            if doctor_id:
                # 获取特定医生的对话记录
                cursor.execute("""
                    SELECT uuid, conversation_log, created_at, updated_at 
                    FROM consultations 
                    WHERE patient_id = ? AND selected_doctor_id = ?
                    ORDER BY created_at DESC LIMIT 20
                """, (user_id, doctor_id))
            else:
                # 获取所有医生的对话记录
                cursor.execute("""
                    SELECT uuid, conversation_log, selected_doctor_id, created_at, updated_at 
                    FROM consultations 
                    WHERE patient_id = ?
                    ORDER BY created_at DESC LIMIT 20
                """, (user_id,))
            
            consultation_logs = cursor.fetchall()
            
            for log_row in consultation_logs:
                conversation_log = log_row[1]  # JSON string
                created_at = log_row[-2]  # 创建时间
                
                if conversation_log:
                    try:
                        log_data = json.loads(conversation_log)
                        
                        # 从conversation_history中提取消息
                        if 'conversation_history' in log_data:
                            conversation_history = log_data['conversation_history']
                            if isinstance(conversation_history, list):
                                for conv_item in conversation_history:
                                    # 用户消息
                                    if conv_item.get('patient_query'):
                                        messages.append({
                                            'type': 'user',
                                            'content': conv_item['patient_query'],
                                            'time': conv_item.get('timestamp', created_at),
                                            'timestamp': conv_item.get('timestamp', created_at)
                                        })
                                    # AI回复
                                    if conv_item.get('ai_response'):
                                        ai_message = {
                                            'type': 'ai',
                                            'content': conv_item['ai_response'],
                                            'time': conv_item.get('timestamp', created_at),
                                            'timestamp': conv_item.get('timestamp', created_at)
                                        }
                                        
                                        # 检查是否包含处方信息
                                        if '处方' in conv_item['ai_response'] or '方剂' in conv_item['ai_response']:
                                            # 查找对应的处方记录
                                            cursor.execute("""
                                                SELECT p.id, p.ai_prescription, p.status, p.payment_status,
                                                       o.payment_status as order_payment_status
                                                FROM prescriptions p
                                                LEFT JOIN orders o ON p.id = o.prescription_id
                                                WHERE p.consultation_id = ? 
                                                ORDER BY p.created_at DESC LIMIT 1
                                            """, (log_row[0],))  # uuid
                                            
                                            prescription_row = cursor.fetchone()
                                            if prescription_row:
                                                # 🔑 关键修复：检查处方表和订单表的支付状态
                                                prescription_paid = prescription_row[3] == 'paid'
                                                order_paid = prescription_row[4] == 'paid'
                                                is_paid = prescription_paid or order_paid
                                                
                                                ai_message['prescriptionData'] = {
                                                    'prescription_id': prescription_row[0],
                                                    'isPaid': is_paid,
                                                    'hasActions': not is_paid
                                                }
                                                
                                                print(f'📋 处方状态检查: prescription_id={prescription_row[0]}, prescription_paid={prescription_paid}, order_paid={order_paid}, final_paid={is_paid}')
                                        
                                        messages.append(ai_message)
                        
                        # 备用方案：直接从last_query和last_response获取
                        elif log_data.get('last_query') and log_data.get('last_response'):
                            messages.append({
                                'type': 'user',
                                'content': log_data['last_query'],
                                'time': created_at,
                                'timestamp': created_at
                            })
                            
                            ai_message = {
                                'type': 'ai',
                                'content': log_data['last_response'],
                                'time': created_at,
                                'timestamp': created_at
                            }
                            
                            # 检查是否包含处方信息
                            if '处方' in log_data['last_response'] or '方剂' in log_data['last_response']:
                                cursor.execute("""
                                    SELECT p.id, p.ai_prescription, p.status, p.payment_status,
                                           o.payment_status as order_payment_status
                                    FROM prescriptions p
                                    LEFT JOIN orders o ON p.id = o.prescription_id
                                    WHERE p.consultation_id = ? 
                                    ORDER BY p.created_at DESC LIMIT 1
                                """, (log_row[0],))
                                
                                prescription_row = cursor.fetchone()
                                if prescription_row:
                                    # 🔑 关键修复：检查处方表和订单表的支付状态
                                    prescription_paid = prescription_row[3] == 'paid'
                                    order_paid = prescription_row[4] == 'paid'
                                    is_paid = prescription_paid or order_paid
                                    
                                    ai_message['prescriptionData'] = {
                                        'prescription_id': prescription_row[0],
                                        'isPaid': is_paid,
                                        'hasActions': not is_paid
                                    }
                                    
                                    print(f'📋 备用方案处方状态检查: prescription_id={prescription_row[0]}, prescription_paid={prescription_paid}, order_paid={order_paid}, final_paid={is_paid}')
                            
                            messages.append(ai_message)
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"获取对话消息失败: {e}")
            messages = []
        
        conn.close()
        
        # 转换为字典格式
        result_data = {
            "conversation_states": [dict(row) for row in conversation_states],
            "consultation_records": [dict(row) for row in consultation_records],
            "messages": messages,  # 🔑 修复：前端期望的字段名
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

@router.post("/clear", response_model=HistoryResponse)
async def clear_conversation_history(request: Dict[str, Any]):
    """清空用户与特定医生的对话记录"""
    try:
        user_id = request.get('user_id')
        doctor_id = request.get('doctor_id')
        clear_type = request.get('clear_type', 'all')
        
        if not user_id or not doctor_id:
            raise HTTPException(status_code=400, detail="用户ID和医生ID不能为空")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        deleted_count = 0
        
        if clear_type in ['all', 'consultations']:
            # 清空问诊记录
            cursor.execute("""
                DELETE FROM consultations 
                WHERE patient_id = ? AND selected_doctor_id = ?
            """, (user_id, doctor_id))
            deleted_count += cursor.rowcount
        
        if clear_type in ['all', 'conversation_states']:
            # 清空对话状态
            cursor.execute("""
                DELETE FROM conversation_states 
                WHERE user_id = ? AND doctor_id = ?
            """, (user_id, doctor_id))
            deleted_count += cursor.rowcount
        
        if clear_type in ['all', 'doctor_sessions']:
            # 清空医生会话记录
            cursor.execute("""
                DELETE FROM doctor_sessions 
                WHERE user_id = ? AND doctor_name = ?
            """, (user_id, doctor_id))
            deleted_count += cursor.rowcount
        
        if clear_type in ['all', 'prescriptions']:
            # 清空相关处方（只清空未支付的）
            cursor.execute("""
                DELETE FROM prescriptions 
                WHERE patient_id = ? AND doctor_id = ? AND payment_status != 'paid'
            """, (user_id, doctor_id))
            deleted_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        
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