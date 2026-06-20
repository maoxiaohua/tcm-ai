#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户历史处理模块
从chat_with_ai_endpoint函数中提取的用户历史相关功能
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..utils.common_utils import safe_execute, get_current_timestamp_iso
from ..utils.text_utils import clean_medical_text, has_medical_keywords

logger = logging.getLogger(__name__)

class UserHistoryProcessor:
    """用户历史处理器"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_user_recent_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取用户最近的对话历史"""
        try:
            query = """
            SELECT conversation_id, user_input, ai_response, created_at, diagnosis_type
            FROM conversations 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
            """
            
            result = self.db_manager.execute_query(query, (user_id, limit))
            if result['success'] and result['data']:
                return result['data']
            return []
            
        except Exception as e:
            logger.error(f"获取用户历史失败: {e}")
            return []
    
    def analyze_user_pattern(self, user_id: str) -> Dict[str, Any]:
        """分析用户咨询模式"""
        try:
            # 获取最近30天的咨询记录
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            
            query = """
            SELECT diagnosis_type, COUNT(*) as count, AVG(satisfaction_score) as avg_satisfaction
            FROM conversations 
            WHERE user_id = %s AND created_at > %s
            GROUP BY diagnosis_type
            """
            
            result = self.db_manager.execute_query(query, (user_id, thirty_days_ago))
            
            pattern_analysis = {
                'total_consultations': 0,
                'diagnosis_types': {},
                'avg_satisfaction': 0.0,
                'most_common_type': '',
                'consultation_frequency': 0
            }
            
            if result['success'] and result['data']:
                total_count = sum(row['count'] for row in result['data'])
                total_satisfaction = sum(row['avg_satisfaction'] * row['count'] for row in result['data'] if row['avg_satisfaction'])
                
                pattern_analysis['total_consultations'] = total_count
                pattern_analysis['avg_satisfaction'] = total_satisfaction / total_count if total_count > 0 else 0.0
                pattern_analysis['consultation_frequency'] = total_count / 30.0  # 每日平均咨询次数
                
                # 诊断类型分布
                for row in result['data']:
                    pattern_analysis['diagnosis_types'][row['diagnosis_type']] = {
                        'count': row['count'],
                        'percentage': (row['count'] / total_count) * 100
                    }
                
                # 最常见的诊断类型
                if result['data']:
                    most_common = max(result['data'], key=lambda x: x['count'])
                    pattern_analysis['most_common_type'] = most_common['diagnosis_type']
            
            return pattern_analysis
            
        except Exception as e:
            logger.error(f"分析用户模式失败: {e}")
            return {}
    
    def get_context_for_conversation(self, user_id: str, current_query: str) -> Dict[str, Any]:
        """为当前对话获取上下文信息"""
        context = {
            'recent_history': [],
            'user_pattern': {},
            'relevant_symptoms': [],
            'suggested_focus': '',
            'context_summary': ''
        }
        
        try:
            # 获取最近历史
            context['recent_history'] = self.get_user_recent_history(user_id, limit=3)
            
            # 分析用户模式
            context['user_pattern'] = self.analyze_user_pattern(user_id)
            
            # 提取相关症状关键词
            if has_medical_keywords(current_query):
                from ..utils.text_utils import extract_symptom_keywords
                context['relevant_symptoms'] = extract_symptom_keywords(current_query)
            
            # 生成上下文摘要
            context['context_summary'] = self._generate_context_summary(context)
            
            # 建议关注点
            context['suggested_focus'] = self._suggest_consultation_focus(context)
            
            return context
            
        except Exception as e:
            logger.error(f"获取对话上下文失败: {e}")
            return context
    
    def _generate_context_summary(self, context: Dict[str, Any]) -> str:
        """生成上下文摘要"""
        summary_parts = []
        
        # 历史咨询摘要
        if context['recent_history']:
            history_count = len(context['recent_history'])
            summary_parts.append(f"用户最近{history_count}次咨询记录")
            
            # 最常见的诊断类型
            if context['user_pattern'].get('most_common_type'):
                most_common = context['user_pattern']['most_common_type']
                summary_parts.append(f"常咨询{most_common}相关问题")
        
        # 当前症状
        if context['relevant_symptoms']:
            symptoms_str = '、'.join(context['relevant_symptoms'][:3])
            summary_parts.append(f"当前症状包含：{symptoms_str}")
        
        return '，'.join(summary_parts) if summary_parts else "首次咨询用户"
    
    def _suggest_consultation_focus(self, context: Dict[str, Any]) -> str:
        """建议咨询关注点"""
        suggestions = []
        
        # 基于用户历史模式的建议
        pattern = context.get('user_pattern', {})
        
        if pattern.get('avg_satisfaction', 0) < 3.0:
            suggestions.append("注重详细解释和用药指导")
        
        if pattern.get('consultation_frequency', 0) > 0.5:
            suggestions.append("关注慢性病管理和生活调理")
        
        most_common = pattern.get('most_common_type', '')
        if most_common:
            suggestions.append(f"结合{most_common}诊疗经验")
        
        # 基于当前症状的建议
        symptoms = context.get('relevant_symptoms', [])
        if '头痛' in symptoms or '眩晕' in symptoms:
            suggestions.append("重点询问诱发因素和伴随症状")
        elif '咳嗽' in symptoms:
            suggestions.append("详细了解咳嗽性质和痰液特点")
        elif '失眠' in symptoms:
            suggestions.append("关注情志因素和生活作息")
        
        return '；'.join(suggestions[:2]) if suggestions else "常规中医四诊合参"
    
    def save_conversation_context(self, conversation_id: str, context: Dict[str, Any]) -> bool:
        """保存对话上下文信息"""
        try:
            context_json = safe_execute(
                lambda: context,
                default_return={},
                error_message="序列化上下文失败"
            )
            
            query = """
            UPDATE conversations 
            SET context_data = %s, updated_at = %s
            WHERE conversation_id = %s
            """
            
            result = self.db_manager.execute_query(
                query, 
                (context_json, get_current_timestamp_iso(), conversation_id)
            )
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"保存对话上下文失败: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好设置"""
        try:
            query = """
            SELECT preference_key, preference_value
            FROM user_preferences 
            WHERE user_id = %s
            """
            
            result = self.db_manager.execute_query(query, (user_id,))
            preferences = {}
            
            if result['success'] and result['data']:
                for row in result['data']:
                    preferences[row['preference_key']] = row['preference_value']
            
            # 设置默认偏好
            default_preferences = {
                'language': 'zh-CN',
                'detail_level': 'standard',
                'include_lifestyle_advice': True,
                'notification_enabled': True
            }
            
            # 合并默认设置
            for key, default_value in default_preferences.items():
                if key not in preferences:
                    preferences[key] = default_value
            
            return preferences
            
        except Exception as e:
            logger.error(f"获取用户偏好失败: {e}")
            return {
                'language': 'zh-CN',
                'detail_level': 'standard',
                'include_lifestyle_advice': True,
                'notification_enabled': True
            }
    
    def update_user_satisfaction(self, conversation_id: str, satisfaction_score: int) -> bool:
        """更新用户满意度评分"""
        try:
            if not (1 <= satisfaction_score <= 5):
                logger.warning(f"无效的满意度评分: {satisfaction_score}")
                return False
            
            query = """
            UPDATE conversations 
            SET satisfaction_score = %s, updated_at = %s
            WHERE conversation_id = %s
            """
            
            result = self.db_manager.execute_query(
                query,
                (satisfaction_score, get_current_timestamp_iso(), conversation_id)
            )
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"更新用户满意度失败: {e}")
            return False