#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全事件记录API路由
为前端提供安全事件记录和监控功能
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime
import hashlib
from app.services import local_sqlite_service as sqlite_service

router = APIRouter(prefix="/api/security", tags=["安全管理"])


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


class SecurityEventRequest(BaseModel):
    """安全事件记录请求"""
    event_type: Optional[str] = None
    eventType: Optional[str] = None
    user_id: Optional[str] = None
    userId: Optional[str] = None
    patient_id: Optional[str] = None
    patientId: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None
    severity: Optional[str] = "info"  # info, warning, error, critical
    risk_level: Optional[str] = None
    description: Optional[str] = ""
    message: Optional[str] = None
    content: Optional[str] = None
    text: Optional[str] = None
    conversation_id: Optional[str] = None
    timestamp: Optional[str] = None

class SecurityLogResponse(BaseModel):
    """安全日志响应"""
    success: bool
    message: str
    event_id: Optional[int] = None

@router.post("/log-event")
async def log_security_event(request: SecurityEventRequest, req: Request):
    """记录安全事件"""
    try:
        # 获取客户端信息
        ip_address = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("User-Agent", "unknown")
        now_iso = datetime.now().isoformat()
        request_id = hashlib.md5(f"{ip_address}_{now_iso}".encode()).hexdigest()[:12]
        event_type = _first_non_empty(request.event_type, request.eventType, "frontend_event")
        user_id = _first_non_empty(
            request.user_id,
            request.userId,
            request.patient_id,
            request.patientId,
        )
        severity = str(_first_non_empty(request.severity, request.risk_level, "info")).lower()
        if severity not in {"info", "warning", "error", "critical"}:
            severity = "info"
        description = _first_non_empty(
            request.description,
            request.message,
            request.content,
            request.text,
            "",
        ) or ""

        event_data: Dict[str, Any] = dict(request.event_data or {})
        if isinstance(request.details, dict):
            event_data.update(request.details)
        if request.conversation_id:
            event_data.setdefault("conversation_id", request.conversation_id)
        if request.timestamp:
            event_data.setdefault("timestamp", request.timestamp)

        event_id = sqlite_service.log_security_event(
            event_type=str(event_type),
            user_id=str(user_id) if user_id is not None else None,
            severity=severity,
            description=str(description),
            event_data_json=json.dumps(event_data, ensure_ascii=False),
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            created_at=now_iso,
        )
        
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

@router.get("/events")
async def get_security_events(
    limit: int = 100,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None
):
    """获取安全事件列表"""
    try:
        raw_events = sqlite_service.fetch_security_events(
            limit=limit,
            severity=severity,
            event_type=event_type,
            user_id=user_id,
        )

        events = []
        for event in raw_events:
            try:
                event['event_data'] = json.loads(event['event_data'])
            except json.JSONDecodeError:
                event['event_data'] = {}
            events.append(event)
        
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
        alerts = sqlite_service.fetch_security_alerts(status=status)
        
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
        affected_rows = sqlite_service.resolve_security_alert(
            alert_id=alert_id,
            resolved_at=datetime.now().isoformat(),
        )

        if affected_rows == 0:
            return {
                "success": False,
                "message": "告警不存在",
                "error": "alert_not_found"
            }
        
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
        stats = sqlite_service.fetch_security_statistics()
        
        return {
            "success": True,
            "data": {
                "severity_stats": stats["severity_stats"],
                "event_type_stats": stats["event_type_stats"],
                "pending_alerts": stats["pending_alerts"],
                "today_events": stats["today_events"]
            },
            "message": "安全统计信息获取成功"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取安全统计失败: {str(e)}",
            "error": "security_stats_failed"
        }
