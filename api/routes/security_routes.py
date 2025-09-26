#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全事件记录API路由
为前端提供安全事件记录和监控功能
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json
from datetime import datetime
import hashlib

router = APIRouter(prefix="/api/security", tags=["安全管理"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

class SecurityEventRequest(BaseModel):
    """安全事件记录请求"""
    event_type: str
    user_id: Optional[str] = None
    event_data: Dict[str, Any] = {}
    severity: Optional[str] = "info"  # info, warning, error, critical
    description: Optional[str] = ""

class SecurityLogResponse(BaseModel):
    """安全日志响应"""
    success: bool
    message: str
    event_id: Optional[int] = None

@router.post("/log-event")
async def log_security_event(request: SecurityEventRequest, req: Request):
    """记录安全事件"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 确保安全事件表存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                severity TEXT DEFAULT 'info',
                description TEXT,
                event_data TEXT,
                ip_address TEXT,
                user_agent TEXT,
                request_id TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 获取客户端信息
        ip_address = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("User-Agent", "unknown")
        request_id = hashlib.md5(f"{ip_address}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # 插入安全事件记录
        cursor.execute("""
            INSERT INTO security_events 
            (event_type, user_id, risk_level, description, event_data, 
             ip_address, user_agent, request_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.event_type,
            request.user_id,
            request.severity,
            request.description,
            json.dumps(request.event_data),
            ip_address,
            user_agent,
            request_id,
            datetime.now().isoformat()
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        
        # 检查是否需要触发安全告警
        if request.severity in ['error', 'critical']:
            await create_security_alert(cursor, event_id, request)
        
        conn.close()
        
        return SecurityLogResponse(
            success=True,
            message="安全事件记录成功",
            event_id=event_id
        )
        
    except Exception as e:
        return SecurityLogResponse(
            success=False,
            message=f"安全事件记录失败: {str(e)}"
        )

async def create_security_alert(cursor, event_id, request):
    """创建安全告警"""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (event_id) REFERENCES security_events (id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO security_alerts 
            (event_id, alert_type, priority, message, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            request.event_type,
            'high' if request.severity == 'critical' else 'medium',
            f"安全事件触发: {request.description}",
            datetime.now().isoformat()
        ))
        
    except Exception as e:
        print(f"创建安全告警失败: {e}")

@router.get("/events")
async def get_security_events(
    limit: int = 100,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None
):
    """获取安全事件列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if severity:
            conditions.append("risk_level = ?")
            params.append(severity)
        
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        where_clause = ""
        if conditions:
            where_clause = f"WHERE {' AND '.join(conditions)}"
        
        params.append(limit)
        
        cursor.execute(f"""
            SELECT * FROM security_events 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT ?
        """, params)
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            try:
                event['event_data'] = json.loads(event['event_data'])
            except json.JSONDecodeError:
                event['event_data'] = {}
            events.append(event)
        
        conn.close()
        
        return {
            "success": True,
            "data": events,
            "message": f"获取到{len(events)}个安全事件",
            "total": len(events)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取安全事件失败: {str(e)}",
            "error": "security_events_failed"
        }

@router.get("/alerts")
async def get_security_alerts(status: Optional[str] = None):
    """获取安全告警列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        where_clause = ""
        params = []
        
        if status:
            where_clause = "WHERE sa.status = ?"
            params.append(status)
        
        cursor.execute(f"""
            SELECT sa.*, se.event_type, se.user_id, se.description, se.ip_address
            FROM security_alerts sa
            JOIN security_events se ON sa.event_id = se.id
            {where_clause}
            ORDER BY sa.created_at DESC
            LIMIT 50
        """, params)
        
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "data": alerts,
            "message": f"获取到{len(alerts)}个安全告警",
            "total": len(alerts)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取安全告警失败: {str(e)}",
            "error": "security_alerts_failed"
        }

@router.post("/alerts/{alert_id}/resolve")
async def resolve_security_alert(alert_id: int):
    """解决安全告警"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE security_alerts 
            SET status = 'resolved', resolved_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), alert_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "message": "告警不存在",
                "error": "alert_not_found"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "安全告警已解决"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"解决安全告警失败: {str(e)}",
            "error": "resolve_alert_failed"
        }

@router.get("/statistics")
async def get_security_statistics():
    """获取安全统计信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 事件统计
        cursor.execute("""
            SELECT risk_level, COUNT(*) as count 
            FROM security_events 
            WHERE datetime(created_at) > datetime('now', '-7 days')
            GROUP BY risk_level
        """)
        severity_stats = dict(cursor.fetchall())
        
        # 事件类型统计
        cursor.execute("""
            SELECT event_type, COUNT(*) as count 
            FROM security_events 
            WHERE datetime(created_at) > datetime('now', '-24 hours')
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
        """)
        event_type_stats = dict(cursor.fetchall())
        
        # 未解决告警数量
        cursor.execute("""
            SELECT COUNT(*) as pending_alerts 
            FROM security_alerts 
            WHERE status = 'pending'
        """)
        pending_alerts = cursor.fetchone()['pending_alerts']
        
        # 今日事件总数
        cursor.execute("""
            SELECT COUNT(*) as today_events 
            FROM security_events 
            WHERE DATE(created_at) = DATE('now')
        """)
        today_events = cursor.fetchone()['today_events']
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "severity_stats": severity_stats,
                "event_type_stats": event_type_stats,
                "pending_alerts": pending_alerts,
                "today_events": today_events
            },
            "message": "安全统计信息获取成功"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取安全统计失败: {str(e)}",
            "error": "security_stats_failed"
        }