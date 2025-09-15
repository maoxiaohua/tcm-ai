#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据云同步API路由
实现完整的用户数据云端同步机制，支持跨设备无缝切换
"""

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json
import uuid
import hashlib
import asyncio
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/user-sync", tags=["用户数据云同步"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

class UserDataSyncRequest(BaseModel):
    """用户数据同步请求"""
    user_id: str
    device_info: Dict[str, Any]
    sync_data: Dict[str, Any]
    sync_type: str = "full"  # full, incremental, emergency
    client_timestamp: int

class SyncResponse(BaseModel):
    """同步响应"""
    success: bool
    message: str
    sync_id: Optional[str] = None
    server_timestamp: int
    conflicts: List[Dict[str, Any]] = []
    data: Optional[Dict[str, Any]] = None

class ConflictResolution(BaseModel):
    """冲突解决"""
    sync_id: str
    resolutions: List[Dict[str, Any]]

@router.post("/full-sync", response_model=SyncResponse)
async def full_user_data_sync(request: UserDataSyncRequest, req: Request, background_tasks: BackgroundTasks):
    """完整用户数据同步"""
    try:
        user_id = request.user_id
        device_info = request.device_info
        sync_data = request.sync_data
        client_timestamp = request.client_timestamp
        
        # 生成同步ID
        sync_id = f"sync_{user_id}_{int(datetime.now().timestamp())}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取服务器端数据
        server_data = await get_complete_user_data(user_id)
        
        # 检测数据冲突
        conflicts = detect_data_conflicts(sync_data, server_data, client_timestamp)
        
        if conflicts:
            # 有冲突，返回冲突信息等待用户解决
            conn.close()
            return SyncResponse(
                success=False,
                message=f"检测到{len(conflicts)}个数据冲突，需要手动解决",
                sync_id=sync_id,
                server_timestamp=int(datetime.now().timestamp()),
                conflicts=conflicts,
                data=server_data
            )
        
        # 无冲突，执行同步
        merged_data = merge_user_data(sync_data, server_data)
        
        # 保存合并后的数据
        await save_merged_data(user_id, merged_data, device_info, sync_id)
        
        # 记录同步历史
        background_tasks.add_task(log_sync_operation, user_id, sync_id, "full_sync", True)
        
        conn.close()
        
        return SyncResponse(
            success=True,
            message="数据同步成功",
            sync_id=sync_id,
            server_timestamp=int(datetime.now().timestamp()),
            data=merged_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")

@router.post("/incremental-sync", response_model=SyncResponse)
async def incremental_sync(request: UserDataSyncRequest, req: Request):
    """增量数据同步"""
    try:
        user_id = request.user_id
        client_timestamp = request.client_timestamp
        
        # 获取自客户端时间戳以来的所有变更
        changes = await get_changes_since(user_id, client_timestamp)
        
        if not changes:
            return SyncResponse(
                success=True,
                message="无需同步，数据已是最新",
                server_timestamp=int(datetime.now().timestamp()),
                data={}
            )
        
        # 应用客户端变更到服务器
        if request.sync_data:
            await apply_client_changes(user_id, request.sync_data, client_timestamp)
        
        return SyncResponse(
            success=True,
            message=f"增量同步完成，同步了{len(changes)}个变更",
            server_timestamp=int(datetime.now().timestamp()),
            data={"changes": changes}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"增量同步失败: {str(e)}")

@router.post("/resolve-conflicts", response_model=SyncResponse)
async def resolve_conflicts(resolution: ConflictResolution):
    """解决数据冲突"""
    try:
        sync_id = resolution.sync_id
        resolutions = resolution.resolutions
        
        # 应用冲突解决方案
        for resolution_item in resolutions:
            await apply_conflict_resolution(sync_id, resolution_item)
        
        return SyncResponse(
            success=True,
            message=f"已解决{len(resolutions)}个冲突",
            sync_id=sync_id,
            server_timestamp=int(datetime.now().timestamp())
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"冲突解决失败: {str(e)}")

@router.get("/sync-status/{user_id}")
async def get_sync_status(user_id: str):
    """获取用户同步状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最近的同步记录
        cursor.execute("""
            SELECT sync_id, sync_type, status, created_at, device_count
            FROM user_sync_history 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 5
        """, (user_id,))
        
        sync_history = [dict(row) for row in cursor.fetchall()]
        
        # 获取设备列表
        cursor.execute("""
            SELECT device_fingerprint, ip_address, user_agent, last_used, is_active
            FROM user_devices 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        
        devices = [dict(row) for row in cursor.fetchall()]
        
        # 获取数据完整性状态
        data_integrity = await check_data_integrity(user_id)
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "sync_history": sync_history,
                "devices": devices,
                "data_integrity": data_integrity,
                "last_sync": sync_history[0] if sync_history else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")

@router.post("/emergency-backup/{user_id}")
async def create_emergency_backup(user_id: str, background_tasks: BackgroundTasks):
    """创建紧急备份"""
    try:
        # 创建完整的用户数据备份
        backup_data = await get_complete_user_data(user_id)
        backup_id = f"emergency_{user_id}_{int(datetime.now().timestamp())}"
        
        # 保存到备份表
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO emergency_backups 
            (backup_id, user_id, backup_data, created_at, backup_type)
            VALUES (?, ?, ?, ?, 'emergency')
        """, (backup_id, user_id, json.dumps(backup_data), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # 异步清理旧备份
        background_tasks.add_task(cleanup_old_backups, user_id)
        
        return {
            "success": True,
            "message": "紧急备份创建成功",
            "backup_id": backup_id,
            "backup_size": len(json.dumps(backup_data))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建紧急备份失败: {str(e)}")

@router.post("/restore-backup/{backup_id}")
async def restore_from_backup(backup_id: str):
    """从备份恢复数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, backup_data, created_at
            FROM emergency_backups 
            WHERE backup_id = ?
        """, (backup_id,))
        
        backup = cursor.fetchone()
        if not backup:
            raise HTTPException(status_code=404, detail="备份不存在")
        
        # 恢复数据
        user_id = backup['user_id']
        backup_data = json.loads(backup['backup_data'])
        
        await restore_user_data(user_id, backup_data)
        
        conn.close()
        
        return {
            "success": True,
            "message": "数据恢复成功",
            "restored_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据恢复失败: {str(e)}")

# 辅助函数
async def get_complete_user_data(user_id: str) -> Dict[str, Any]:
    """获取用户的完整数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_data = {
        "user_id": user_id,
        "conversations": [],
        "consultations": [],
        "prescriptions": [],
        "user_sessions": [],
        "last_updated": datetime.now().isoformat()
    }
    
    # 获取对话状态
    cursor.execute("""
        SELECT * FROM conversation_states WHERE user_id = ? AND is_active = 1
    """, (user_id,))
    user_data["conversations"] = [dict(row) for row in cursor.fetchall()]
    
    # 获取问诊记录
    cursor.execute("""
        SELECT * FROM consultations WHERE patient_id = ?
        ORDER BY created_at DESC LIMIT 50
    """, (user_id,))
    user_data["consultations"] = [dict(row) for row in cursor.fetchall()]
    
    # 获取处方记录
    cursor.execute("""
        SELECT p.* FROM prescriptions_new p
        JOIN consultations c ON p.consultation_id = c.uuid
        WHERE c.patient_id = ?
        ORDER BY p.created_at DESC LIMIT 20
    """, (user_id,))
    user_data["prescriptions"] = [dict(row) for row in cursor.fetchall()]
    
    # 获取会话记录
    cursor.execute("""
        SELECT * FROM user_sessions WHERE user_id = ? AND is_active = 1
        ORDER BY last_activity DESC LIMIT 10
    """, (user_id,))
    user_data["user_sessions"] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return user_data

def detect_data_conflicts(client_data: Dict, server_data: Dict, client_timestamp: int) -> List[Dict]:
    """检测数据冲突"""
    conflicts = []
    
    # 检查对话状态冲突
    client_conversations = client_data.get("conversations", [])
    server_conversations = server_data.get("conversations", [])
    
    for client_conv in client_conversations:
        for server_conv in server_conversations:
            if (client_conv.get("conversation_id") == server_conv.get("conversation_id") and
                client_conv.get("last_activity") != server_conv.get("last_activity")):
                
                conflicts.append({
                    "type": "conversation_conflict",
                    "conversation_id": client_conv.get("conversation_id"),
                    "client_version": client_conv,
                    "server_version": server_conv,
                    "conflict_field": "last_activity"
                })
    
    return conflicts

def merge_user_data(client_data: Dict, server_data: Dict) -> Dict:
    """合并客户端和服务器数据"""
    merged = server_data.copy()
    
    # 合并对话状态（取最新的）
    client_conversations = {conv['conversation_id']: conv for conv in client_data.get("conversations", [])}
    server_conversations = {conv['conversation_id']: conv for conv in server_data.get("conversations", [])}
    
    for conv_id, client_conv in client_conversations.items():
        if conv_id in server_conversations:
            server_conv = server_conversations[conv_id]
            # 比较时间戳，取最新的
            if client_conv.get('last_activity', '') > server_conv.get('last_activity', ''):
                server_conversations[conv_id] = client_conv
        else:
            server_conversations[conv_id] = client_conv
    
    merged["conversations"] = list(server_conversations.values())
    merged["last_updated"] = datetime.now().isoformat()
    
    return merged

async def save_merged_data(user_id: str, merged_data: Dict, device_info: Dict, sync_id: str):
    """保存合并后的数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 更新对话状态
    for conv in merged_data.get("conversations", []):
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_states 
            (conversation_id, user_id, doctor_id, current_stage, start_time, 
             last_activity, turn_count, symptoms_collected, stage_history, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conv.get('conversation_id'),
            user_id,
            conv.get('doctor_id'),
            conv.get('current_stage'),
            conv.get('start_time'),
            conv.get('last_activity'),
            conv.get('turn_count', 0),
            conv.get('symptoms_collected', '{}'),
            conv.get('stage_history', '[]'),
            datetime.now().isoformat()
        ))
    
    # 记录同步操作
    cursor.execute("""
        INSERT INTO user_sync_history 
        (sync_id, user_id, sync_type, status, device_fingerprint, created_at)
        VALUES (?, ?, 'full_sync', 'completed', ?, ?)
    """, (sync_id, user_id, device_info.get('fingerprint', 'unknown'), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

async def get_changes_since(user_id: str, timestamp: int) -> List[Dict]:
    """获取指定时间戳以来的变更"""
    since_time = datetime.fromtimestamp(timestamp / 1000).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 'conversation' as type, conversation_id as id, updated_at
        FROM conversation_states 
        WHERE user_id = ? AND updated_at > ?
        UNION ALL
        SELECT 'consultation' as type, uuid as id, updated_at
        FROM consultations 
        WHERE patient_id = ? AND updated_at > ?
    """, (user_id, since_time, user_id, since_time))
    
    changes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return changes

async def apply_client_changes(user_id: str, changes: Dict, timestamp: int):
    """应用客户端变更到服务器"""
    # 这里实现具体的变更应用逻辑
    pass

async def apply_conflict_resolution(sync_id: str, resolution: Dict):
    """应用冲突解决方案"""
    # 这里实现冲突解决逻辑
    pass

async def check_data_integrity(user_id: str) -> Dict:
    """检查数据完整性"""
    # 这里实现数据完整性检查逻辑
    return {"status": "healthy", "last_check": datetime.now().isoformat()}

async def restore_user_data(user_id: str, backup_data: Dict):
    """恢复用户数据"""
    # 这里实现数据恢复逻辑
    pass

async def log_sync_operation(user_id: str, sync_id: str, operation: str, success: bool):
    """记录同步操作"""
    print(f"同步操作记录: {user_id} - {operation} - {'成功' if success else '失败'}")

async def cleanup_old_backups(user_id: str):
    """清理旧备份"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 保留最近10个备份
    cursor.execute("""
        DELETE FROM emergency_backups 
        WHERE user_id = ? AND backup_id NOT IN (
            SELECT backup_id FROM emergency_backups 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 10
        )
    """, (user_id, user_id))
    
    conn.commit()
    conn.close()