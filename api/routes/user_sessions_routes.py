#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户会话历史API路由
为历史记录页面提供完整的会话数据
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
from datetime import datetime

router = APIRouter(prefix="/api/user", tags=["用户会话"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

# 导入统一认证系统
import sys
sys.path.append('/opt/tcm-ai')
from core.unified_account.account_manager import unified_account_manager

async def get_current_user_from_header(authorization: Optional[str] = Header(None)):
    """从Header中获取当前用户"""
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="需要认证")
        
        session_id = authorization.replace('Bearer ', '')
        session = unified_account_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="会话已过期")
        
        return session['user']
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"认证失败: {str(e)}")

@router.get("/sessions")
async def get_user_sessions(current_user = None):
    """获取用户的会话历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 🔑 简化版本：获取基础问诊记录
        cursor.execute("""
            SELECT 
                c.uuid as session_id,
                c.patient_id,
                c.selected_doctor_id as doctor_name,
                c.conversation_log,
                c.status,
                c.created_at,
                c.updated_at
            FROM consultations c
            ORDER BY c.created_at DESC
            LIMIT 50
        """)
        
        sessions_data = cursor.fetchall()
        
        # 获取医生名称映射
        doctor_names = {
            'jin_daifu': '金大夫',
            'ye_tianshi': '叶天士', 
            'zhang_zhongjing': '张仲景',
            'li_dongyuan': '李东垣',
            'liu_duzhou': '刘渡舟',
            'zheng_qin_an': '郑钦安'
        }
        
        # 转换为前端期望的格式
        sessions = []
        for row in sessions_data:
            try:
                # 简化的主诉提取
                chief_complaint = "问诊记录"
                message_count = 1
                
                # 尝试解析conversation_log
                if row['conversation_log']:
                    try:
                        log_data = json.loads(row['conversation_log'])
                        if isinstance(log_data, dict):
                            # 如果是对象格式
                            if 'last_query' in log_data:
                                chief_complaint = log_data['last_query'][:50]
                            elif 'patient_query' in log_data:
                                chief_complaint = log_data['patient_query'][:50]
                        elif isinstance(log_data, list) and len(log_data) > 0:
                            # 如果是数组格式
                            first_item = log_data[0]
                            if isinstance(first_item, dict) and 'content' in first_item:
                                chief_complaint = first_item['content'][:50]
                            message_count = len(log_data)
                    except:
                        pass
                
                session = {
                    "session_id": row['session_id'],
                    "doctor_name": row['doctor_name'],
                    "doctor_display_name": doctor_names.get(row['doctor_name'], row['doctor_name']),
                    "chief_complaint": chief_complaint,
                    "session_count": 1,
                    "message_count": message_count,
                    "messages": [],  # 简化处理
                    "status": row['status'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "diagnosis_summary": "问诊记录",
                    "prescription_given": "未知",
                    "has_prescription": False
                }
                sessions.append(session)
                
            except Exception as inner_e:
                # 跳过有问题的记录，但记录错误
                print(f"跳过记录 {row.get('session_id', 'unknown')}: {inner_e}")
                continue
                
        conn.close()
        
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "sessions": [],
            "total": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/conversation/{session_id}")
async def get_conversation_detail(session_id: str):
    """获取单个会话的详细信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.*,
                d.name as doctor_display_name,
                p.id as prescription_id,
                p.ai_prescription,
                p.status as prescription_status
            FROM consultations c
            LEFT JOIN doctors d ON (
                (c.selected_doctor_id = 'jin_daifu' AND d.id = 1) OR
                (c.selected_doctor_id = 'ye_tianshi' AND d.id = 2) OR
                (c.selected_doctor_id = 'zhang_zhongjing' AND d.id = 2) OR
                (c.selected_doctor_id = 'li_dongyuan' AND d.id = 3) OR
                (c.selected_doctor_id = 'liu_duzhou' AND d.id = 5) OR
                (c.selected_doctor_id = 'zheng_qin_an' AND d.id = 6)
            )
            LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
            WHERE c.uuid = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        try:
            conversation_log = json.loads(row['conversation_log']) if row['conversation_log'] else {}
        except json.JSONDecodeError:
            conversation_log = {}
        
        return {
            "success": True,
            "session_id": session_id,
            "doctor_name": row['doctor_display_name'] or row['selected_doctor_id'],
            "conversation_history": conversation_log.get('conversation_history', []),
            "chief_complaint": conversation_log.get('last_query', '未记录')[:50],
            "status": row['status'],
            "created_at": row['created_at'],
            "prescription": {
                "exists": bool(row['prescription_id']),
                "content": row['ai_prescription'] if row['prescription_id'] else None,
                "status": row['prescription_status'] if row['prescription_id'] else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")

@router.delete("/sessions/clear")
async def clear_user_sessions():
    """清空用户的所有会话历史"""
    try:
        # 🔑 实现清空历史记录功能
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 清空相关表
        tables_to_clear = [
            "consultations",
            "prescriptions", 
            "conversation_states",
            "doctor_sessions"
        ]
        
        total_deleted = 0
        for table in tables_to_clear:
            cursor.execute(f"DELETE FROM {table}")
            total_deleted += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"已清空所有历史记录，共删除 {total_deleted} 条记录",
            "deleted_count": total_deleted
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空历史记录失败: {str(e)}")