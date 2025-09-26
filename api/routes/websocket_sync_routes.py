#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket实时同步服务
实现多设备间的实时数据同步和状态广播
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.websockets import WebSocketState
from typing import Dict, List, Set, Any
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
import uuid

router = APIRouter()

# 活跃连接管理
class ConnectionManager:
    def __init__(self):
        # 用户连接映射: user_id -> [websockets]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 设备连接映射: device_id -> websocket
        self.device_connections: Dict[str, WebSocket] = {}
        # 用户设备映射: user_id -> [device_ids]
        self.user_devices: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, device_id: str):
        """新设备连接"""
        await websocket.accept()
        
        # 添加到用户连接列表
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # 记录设备连接
        self.device_connections[device_id] = websocket
        
        # 更新用户设备列表
        if user_id not in self.user_devices:
            self.user_devices[user_id] = set()
        self.user_devices[user_id].add(device_id)
        
        # 通知其他设备有新设备连接
        await self.broadcast_to_user_devices(user_id, {
            "type": "device_notification",
            "data": {
                "type": "new_device_connected",
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            }
        }, exclude_device=device_id)
        
        logging.info(f"✅ 用户 {user_id} 设备 {device_id} 已连接实时同步")
        
    def disconnect(self, user_id: str, device_id: str):
        """设备断开连接"""
        # 从用户连接列表移除
        if user_id in self.active_connections:
            websocket = self.device_connections.get(device_id)
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # 如果用户没有其他连接，清理
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # 清理设备连接
        if device_id in self.device_connections:
            del self.device_connections[device_id]
        
        # 清理用户设备列表
        if user_id in self.user_devices:
            self.user_devices[user_id].discard(device_id)
            if not self.user_devices[user_id]:
                del self.user_devices[user_id]
        
        logging.info(f"❌ 用户 {user_id} 设备 {device_id} 已断开实时同步")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logging.error(f"发送个人消息失败: {e}")
    
    async def broadcast_to_user_devices(self, user_id: str, message: dict, exclude_device: str = None):
        """广播消息给用户的所有设备"""
        if user_id not in self.active_connections:
            return
            
        message["timestamp"] = datetime.now().isoformat()
        
        disconnect_devices = []
        
        for websocket in self.active_connections[user_id]:
            # 排除指定设备
            device_id = self.get_device_id_by_websocket(websocket)
            if exclude_device and device_id == exclude_device:
                continue
                
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                else:
                    disconnect_devices.append((user_id, device_id))
            except Exception as e:
                logging.error(f"广播消息失败: {e}")
                disconnect_devices.append((user_id, device_id))
        
        # 清理断开的连接
        for user_id, device_id in disconnect_devices:
            if device_id:
                self.disconnect(user_id, device_id)
    
    def get_device_id_by_websocket(self, websocket: WebSocket) -> str:
        """根据websocket获取设备ID"""
        for device_id, ws in self.device_connections.items():
            if ws == websocket:
                return device_id
        return None
    
    def get_user_connection_count(self, user_id: str) -> int:
        """获取用户连接设备数量"""
        return len(self.active_connections.get(user_id, []))
    
    def get_all_connection_stats(self) -> dict:
        """获取所有连接统计"""
        return {
            "total_users": len(self.active_connections),
            "total_devices": len(self.device_connections),
            "user_connections": {
                user_id: len(connections) 
                for user_id, connections in self.active_connections.items()
            }
        }

# 全局连接管理器
manager = ConnectionManager()

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

@router.websocket("/ws/sync/{user_id}")
async def websocket_sync_endpoint(websocket: WebSocket, user_id: str, device_id: str = None):
    """WebSocket实时同步端点"""
    if not device_id:
        device_id = f"device_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}"
    
    await manager.connect(websocket, user_id, device_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            await handle_sync_message(user_id, device_id, message, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id, device_id)
    except Exception as e:
        logging.error(f"WebSocket连接异常: {e}")
        manager.disconnect(user_id, device_id)

async def handle_sync_message(user_id: str, device_id: str, message: dict, websocket: WebSocket):
    """处理同步消息"""
    message_type = message.get("type")
    
    try:
        if message_type == "heartbeat":
            # 心跳响应
            await manager.send_personal_message({
                "type": "heartbeat_ack",
                "timestamp": datetime.now().isoformat()
            }, websocket)
            
        elif message_type == "conversation_update":
            # 对话状态更新
            await handle_conversation_update(user_id, device_id, message.get("data", {}))
            
        elif message_type == "new_message":
            # 新消息同步
            await handle_new_message_sync(user_id, device_id, message.get("data", {}))
            
        elif message_type == "prescription_update":
            # 处方更新
            await handle_prescription_update(user_id, device_id, message.get("data", {}))
            
        elif message_type == "doctor_switch":
            # 医生切换
            await handle_doctor_switch(user_id, device_id, message.get("data", {}))
            
        elif message_type == "request_latest_state":
            # 请求最新状态
            await send_latest_state(user_id, device_id, websocket)
            
        elif message_type == "conflict_resolution":
            # 冲突解决
            await handle_conflict_resolution(user_id, device_id, message.get("data", {}))
            
        else:
            logging.warning(f"未知的同步消息类型: {message_type}")
            
    except Exception as e:
        logging.error(f"处理同步消息失败: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": f"处理消息失败: {str(e)}"
        }, websocket)

async def handle_conversation_update(user_id: str, device_id: str, data: dict):
    """处理对话状态更新"""
    conversation_id = data.get("conversation_id")
    current_stage = data.get("current_stage")
    
    if not conversation_id or not current_stage:
        return
    
    # 保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_states 
            (conversation_id, user_id, current_stage, last_activity, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            conversation_id,
            user_id,
            current_stage,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        conn.commit()
        
        # 广播给用户的其他设备
        await manager.broadcast_to_user_devices(user_id, {
            "type": "state_sync",
            "data": {
                "conversation_id": conversation_id,
                "current_stage": current_stage,
                "updated_by": device_id
            }
        }, exclude_device=device_id)
        
    finally:
        conn.close()

async def handle_new_message_sync(user_id: str, device_id: str, data: dict):
    """处理新消息同步"""
    message_content = data.get("message")
    sender = data.get("sender", "user")
    conversation_id = data.get("conversation_id")
    
    if not message_content:
        return
    
    # 广播给用户的其他设备
    await manager.broadcast_to_user_devices(user_id, {
        "type": "message_sync",
        "data": {
            "message": message_content,
            "sender": sender,
            "conversation_id": conversation_id,
            "sent_by_device": device_id
        }
    }, exclude_device=device_id)

async def handle_prescription_update(user_id: str, device_id: str, data: dict):
    """处理处方更新"""
    prescription_data = data.get("prescription")
    
    if not prescription_data:
        return
    
    # 广播给用户的其他设备
    await manager.broadcast_to_user_devices(user_id, {
        "type": "prescription_sync",
        "data": {
            "prescription": prescription_data,
            "updated_by": device_id
        }
    }, exclude_device=device_id)

async def handle_doctor_switch(user_id: str, device_id: str, data: dict):
    """处理医生切换"""
    doctor_id = data.get("doctor_id")
    doctor_name = data.get("doctor_name")
    
    if not doctor_id:
        return
    
    # 广播给用户的其他设备
    await manager.broadcast_to_user_devices(user_id, {
        "type": "doctor_sync",
        "data": {
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "switched_by": device_id
        }
    }, exclude_device=device_id)

async def send_latest_state(user_id: str, device_id: str, websocket: WebSocket):
    """发送最新状态给设备"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取最新的对话状态
        cursor.execute("""
            SELECT * FROM conversation_states 
            WHERE user_id = ? AND is_active = 1
            ORDER BY last_activity DESC LIMIT 1
        """, (user_id,))
        
        latest_conversation = cursor.fetchone()
        
        # 获取最近的消息
        cursor.execute("""
            SELECT message_content, sender, created_at
            FROM consultation_messages cm
            JOIN consultations c ON cm.consultation_id = c.uuid
            WHERE c.patient_id = ?
            ORDER BY cm.created_at DESC LIMIT 5
        """, (user_id,))
        
        recent_messages = [dict(row) for row in cursor.fetchall()]
        
        # 发送最新状态
        await manager.send_personal_message({
            "type": "latest_state",
            "data": {
                "conversation_state": dict(latest_conversation) if latest_conversation else None,
                "recent_messages": recent_messages,
                "sync_timestamp": datetime.now().isoformat()
            }
        }, websocket)
        
    finally:
        conn.close()

async def handle_conflict_resolution(user_id: str, device_id: str, data: dict):
    """处理冲突解决"""
    conflict_id = data.get("conflict_id")
    strategy = data.get("strategy")  # 'server_wins' or 'client_wins'
    
    if not conflict_id or not strategy:
        return
    
    # 这里可以实现具体的冲突解决逻辑
    logging.info(f"用户 {user_id} 设备 {device_id} 选择冲突解决策略: {strategy}")
    
    # 广播冲突解决结果
    await manager.broadcast_to_user_devices(user_id, {
        "type": "conflict_resolved",
        "data": {
            "conflict_id": conflict_id,
            "strategy": strategy,
            "resolved_by": device_id
        }
    })

# 辅助API路由
@router.get("/api/sync/connection-stats")
async def get_connection_stats():
    """获取连接统计"""
    try:
        stats = manager.get_all_connection_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取连接统计失败: {str(e)}")

@router.post("/api/sync/broadcast-to-user/{user_id}")
async def broadcast_message_to_user(user_id: str, message_data: dict):
    """向用户的所有设备广播消息"""
    try:
        await manager.broadcast_to_user_devices(user_id, {
            "type": "admin_broadcast",
            "data": message_data
        })
        
        return {
            "success": True,
            "message": f"消息已广播给用户 {user_id} 的所有设备",
            "device_count": manager.get_user_connection_count(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"广播消息失败: {str(e)}")

# 自动同步触发器
async def auto_sync_trigger(user_id: str, event_type: str, event_data: dict):
    """自动同步触发器 - 供其他模块调用"""
    try:
        await manager.broadcast_to_user_devices(user_id, {
            "type": f"auto_{event_type}",
            "data": event_data
        })
        logging.info(f"自动触发同步: {user_id} - {event_type}")
    except Exception as e:
        logging.error(f"自动同步触发失败: {e}")

# 导出给其他模块使用
__all__ = ['router', 'auto_sync_trigger', 'manager']