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
async def get_user_sessions(user_id: str = None):
    """获取用户的会话历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 🔑 获取基础问诊记录，包含处方信息，支持按用户ID过滤
        if user_id:
            # 如果提供了用户ID，只返回该用户的记录
            cursor.execute("""
                SELECT 
                    c.uuid as session_id,
                    c.patient_id,
                    c.selected_doctor_id as doctor_name,
                    c.conversation_log,
                    c.status,
                    c.created_at,
                    c.updated_at,
                    p.id as prescription_id,
                    p.status as prescription_status,
                    p.payment_status,
                    p.is_visible_to_patient
                FROM consultations c
                LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
                WHERE c.patient_id = ?
                ORDER BY c.created_at DESC
                LIMIT 50
            """, (user_id,))
        else:
            # 如果没有提供用户ID，返回所有记录（向后兼容）
            cursor.execute("""
                SELECT 
                    c.uuid as session_id,
                    c.patient_id,
                    c.selected_doctor_id as doctor_name,
                    c.conversation_log,
                    c.status,
                    c.created_at,
                    c.updated_at,
                    p.id as prescription_id,
                    p.status as prescription_status,
                    p.payment_status,
                    p.is_visible_to_patient
                FROM consultations c
                LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
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
                # 提取主诉、诊断摘要等信息
                chief_complaint = "问诊记录"
                diagnosis_summary = "问诊记录"
                prescription_given = "未知"
                has_prescription = bool(row['prescription_id'])
                message_count = 1
                
                # 尝试解析conversation_log
                if row['conversation_log']:
                    try:
                        log_data = json.loads(row['conversation_log'])
                        if isinstance(log_data, dict):
                            # 从conversation_history中提取信息
                            conversation_history = log_data.get('conversation_history', [])
                            if conversation_history and len(conversation_history) > 0:
                                message_count = len(conversation_history)
                                # 🔑 修复：取第一条用户消息作为主诉，兼容新旧格式
                                for item in conversation_history:
                                    # 新格式：patient_query
                                    if item.get('patient_query'):
                                        chief_complaint = item['patient_query'][:50] + ("..." if len(item['patient_query']) > 50 else "")
                                        break
                                    # 旧格式：type + content
                                    elif item.get('type') == 'user' and item.get('content'):
                                        chief_complaint = item['content'][:50] + ("..." if len(item['content']) > 50 else "")
                                        break
                                        
                                # 🔑 修复：提取诊断信息，清理HTML内容，兼容新旧格式
                                for item in conversation_history:
                                    # 新格式：ai_response
                                    ai_response = item.get('ai_response')
                                    # 旧格式：type + content
                                    if not ai_response and item.get('type') == 'ai':
                                        ai_response = item.get('content')

                                    if ai_response:
                                        # 🔑 如果包含HTML标签，跳过
                                        if 'prescription-locked' in ai_response or '<div' in ai_response:
                                            diagnosis_summary = '【包含处方信息】'
                                            break

                                        if '辨证分析' in ai_response or '证' in ai_response or '诊断' in ai_response:
                                            # 提取辨证分析段落
                                            if '【辨证分析】' in ai_response:
                                                start = ai_response.find('【辨证分析】')
                                                end = ai_response.find('【', start + 1)
                                                if end == -1:
                                                    end = ai_response.find('---', start)
                                                if end == -1:
                                                    end = start + 200
                                                diagnosis_content = ai_response[start:end].strip()
                                                diagnosis_summary = diagnosis_content[:100] + ("..." if len(diagnosis_content) > 100 else "")
                                            else:
                                                # 备用方案：提取证候信息
                                                import re
                                                pattern = r'([^。]*?证[^。]*?)'
                                                matches = re.findall(pattern, ai_response)
                                                if matches:
                                                    diagnosis_summary = matches[0][:50] + ("..." if len(matches[0]) > 50 else "")
                                        break
                            else:
                                # 备用方案：从顶层字段获取
                                if 'last_query' in log_data:
                                    chief_complaint = log_data['last_query'][:50] + ("..." if len(log_data['last_query']) > 50 else "")
                                if 'last_response' in log_data:
                                    response = log_data['last_response']
                                    if '证' in response or '诊断' in response:
                                        import re
                                        pattern = r'([^。]*?证[^。]*?)'
                                        matches = re.findall(pattern, response)
                                        if matches:
                                            diagnosis_summary = matches[0][:30] + ("..." if len(matches[0]) > 30 else "")
                        elif isinstance(log_data, list) and len(log_data) > 0:
                            # 如果是数组格式，过滤掉只有欢迎消息的记录
                            user_messages = [msg for msg in log_data if msg.get('type') == 'user']
                            if user_messages:
                                # 有用户消息，取第一条用户消息作为主诉
                                first_user_msg = user_messages[0]
                                if 'content' in first_user_msg:
                                    chief_complaint = first_user_msg['content'][:50] + ("..." if len(first_user_msg['content']) > 50 else "")
                                
                                # 🔑 修复：查找AI回复中的诊断信息，同时检查HTML
                                ai_messages = [msg for msg in log_data if msg.get('type') == 'ai']
                                for ai_msg in ai_messages:
                                    if ai_msg.get('content'):
                                        ai_content = ai_msg['content']

                                        # 🔑 如果包含HTML标签，跳过
                                        if 'prescription-locked' in ai_content or '<div' in ai_content:
                                            diagnosis_summary = '【包含处方信息】'
                                            break

                                        if '辨证分析' in ai_content or '证' in ai_content or '诊断' in ai_content:
                                            # 提取辨证分析段落
                                            if '【辨证分析】' in ai_content:
                                                start = ai_content.find('【辨证分析】')
                                                end = ai_content.find('【', start + 1)
                                                if end == -1:
                                                    end = ai_content.find('---', start)
                                                if end == -1:
                                                    end = start + 200
                                                diagnosis_content = ai_content[start:end].strip()
                                                diagnosis_summary = diagnosis_content[:100] + ("..." if len(diagnosis_content) > 100 else "")
                                            break
                                
                                message_count = len(log_data)
                            else:
                                # 只有AI消息（可能是欢迎消息），跳过这条记录
                                continue
                    except:
                        pass
                
                # 🔑 修复：根据支付状态和可见性正确判断问诊状态
                session_status = row['status']  # 原始状态
                if has_prescription:
                    if row['payment_status'] == 'paid' and row['is_visible_to_patient'] == 1:
                        prescription_given = "已开处方（已支付）"
                        session_status = 'completed'  # 支付且可见时为已完成
                    elif row['payment_status'] == 'paid':
                        prescription_given = "已开处方（已支付）"
                        session_status = 'completed'  # 已支付即为已完成
                    elif row['prescription_status'] == 'patient_confirmed':
                        prescription_given = "已开处方（待支付）"
                        session_status = 'in_progress'  # 患者确认但未支付为进行中
                    else:
                        prescription_given = "已开处方"
                        session_status = 'in_progress'  # 其他情况为进行中
                else:
                    # 无处方但对话完整的情况
                    if session_status == 'completed':
                        session_status = 'completed'
                    else:
                        session_status = 'in_progress'
                
                session = {
                    "session_id": row['session_id'],
                    "doctor_name": row['doctor_name'],
                    "doctor_display_name": doctor_names.get(row['doctor_name'], row['doctor_name']),
                    "chief_complaint": chief_complaint,
                    "session_count": 1,
                    "message_count": message_count,
                    "messages": [],  # 简化处理
                    "status": session_status,  # 🔑 使用修正后的状态
                    "session_status": session_status,  # 🔑 添加前端期望的字段
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "diagnosis_summary": diagnosis_summary,
                    "prescription_given": prescription_given,
                    "has_prescription": has_prescription
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
                (c.selected_doctor_id = 'zhang_zhongjing' AND d.id = 4) OR
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
        
        # 提取更详细的对话信息 - 兼容新旧格式
        conversation_history = []
        chief_complaint = "未记录"
        diagnosis_summary = "问诊记录"
        prescription_given = "未知"
        has_prescription = bool(row['prescription_id'])
        
        # 判断数据格式并提取信息
        if isinstance(conversation_log, dict):
            # 新格式：{conversation_history: [...]}
            conversation_history = conversation_log.get('conversation_history', [])
        elif isinstance(conversation_log, list):
            # 旧格式：[{type: "user", content: "..."}, {type: "ai", content: "..."}]
            conversation_history = []
            user_messages = [msg for msg in conversation_log if msg.get('type') == 'user']
            ai_messages = [msg for msg in conversation_log if msg.get('type') == 'ai']
            
            # 转换为新格式
            for i, user_msg in enumerate(user_messages):
                item = {"patient_query": user_msg.get('content', '')}
                if i < len(ai_messages):
                    item["ai_response"] = ai_messages[i].get('content', '')
                conversation_history.append(item)
        
        # 从对话历史中提取信息
        if conversation_history and len(conversation_history) > 0:
            # 取第一条用户消息作为主诉
            for item in conversation_history:
                if item.get('patient_query'):
                    chief_complaint = item['patient_query'][:50] + "..." if len(item['patient_query']) > 50 else item['patient_query']
                    break
            
            # 🔑 修复：检查是否有AI给出的诊断 - 提取完整辨证分析并清理HTML
            for item in conversation_history:
                if item.get('ai_response'):
                    ai_response = item['ai_response']

                    # 🔑 如果包含prescription-locked说明是HTML格式，跳过
                    if 'prescription-locked' in ai_response or '<div' in ai_response:
                        diagnosis_summary = '【此问诊包含处方信息，请在智能问诊页面查看完整内容】'
                        break

                    if '辨证分析' in ai_response or '证' in ai_response or '诊断' in ai_response:
                        # 提取辨证分析段落
                        if '【辨证分析】' in ai_response:
                            start = ai_response.find('【辨证分析】')
                            end = ai_response.find('【', start + 1)
                            if end == -1:
                                end = ai_response.find('---', start)
                            if end == -1:
                                end = start + 300
                            diagnosis_content = ai_response[start:end].strip()
                            diagnosis_summary = diagnosis_content[:200] + ("..." if len(diagnosis_content) > 200 else "")
                        else:
                            # 备用方案：提取证候信息
                            import re
                            pattern = r'([^。]*?证[^。]*?)'
                            matches = re.findall(pattern, ai_response)
                            if matches:
                                diagnosis_summary = matches[0][:50] + ("..." if len(matches[0]) > 50 else "")
                    break
        else:
            # 备用方案：从顶层字段获取
            if conversation_log.get('last_query'):
                chief_complaint = conversation_log['last_query'][:50] + "..." if len(conversation_log['last_query']) > 50 else conversation_log['last_query']
        
        # 检查处方状态 - 支持新的审核流程
        if has_prescription:
            if row['prescription_status'] == 'doctor_approved':
                prescription_given = "已开处方（医生审核完成）"
            elif row['prescription_status'] == 'doctor_modified':
                prescription_given = "已开处方（经医生修改）"
            elif row['prescription_status'] == 'pending_review':
                prescription_given = "已开处方（等待医生审核，请勿配药）"
            elif row['prescription_status'] == 'ai_generated':
                prescription_given = "已开处方（待支付解锁）"
            elif row['prescription_status'] == 'paid':
                prescription_given = "已开处方（已支付）"
            elif row['prescription_status'] == 'pending':
                prescription_given = "已开处方（待支付）"
            else:
                prescription_given = "已开处方"
        
        return {
            "success": True,
            "session_id": session_id,
            "doctor_name": row['doctor_display_name'] or row['selected_doctor_id'],
            "conversation_history": conversation_history,
            "chief_complaint": chief_complaint,
            "diagnosis_summary": diagnosis_summary,
            "prescription_given": prescription_given,
            "has_prescription": has_prescription,
            "status": row['status'],
            "created_at": row['created_at'],
            "prescription": {
                "exists": has_prescription,
                "content": row['ai_prescription'] if row['prescription_id'] else None,
                "status": row['prescription_status'] if row['prescription_id'] else None,
                "prescription_id": row['prescription_id']
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
        
        # 清空相关表 - 获取详细统计信息
        tables_to_clear = [
            "consultations",
            "prescriptions", 
            "conversation_states",
            "doctor_sessions"
        ]
        
        table_stats = {}
        total_deleted = 0
        
        for table in tables_to_clear:
            # 先查询记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_stats[table] = count
            
            # 删除记录
            cursor.execute(f"DELETE FROM {table}")
            total_deleted += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # 生成详细的清空报告
        stats_message = []
        for table, count in table_stats.items():
            if count > 0:
                table_name_map = {
                    "consultations": "问诊记录",
                    "prescriptions": "处方记录",
                    "conversation_states": "对话状态",
                    "doctor_sessions": "医生会话"
                }
                stats_message.append(f"{table_name_map.get(table, table)}: {count}条")
        
        detail_message = f"已清空历史数据 ({', '.join(stats_message)})" if stats_message else "无数据需要清空"
        
        return {
            "success": True,
            "message": detail_message,
            "deleted_count": total_deleted,
            "table_stats": table_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空历史记录失败: {str(e)}")