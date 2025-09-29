#!/usr/bin/env python3
"""
对话分析器
分析对话内容以确定阶段转换和结束条件
"""

import re
import jieba
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

from .conversation_state_manager import ConversationStage, ConversationEndType

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """分析结果"""
    suggested_stage: Optional[ConversationStage] = None
    confidence: float = 0.0
    should_end: bool = False
    end_type: Optional[ConversationEndType] = None
    end_reason: str = ""
    extracted_symptoms: List[str] = None
    diagnosis_confidence: float = 0.0
    has_prescription_keywords: bool = False
    requires_more_info: bool = False
    
    def __post_init__(self):
        if self.extracted_symptoms is None:
            self.extracted_symptoms = []

class ConversationAnalyzer:
    """对话内容分析器"""
    
    def __init__(self):
        # 初始化分词器
        jieba.initialize()
        
        # 症状关键词
        self.symptom_keywords = {
            '头痛', '头晕', '头胀', '偏头痛', '头重',
            '失眠', '多梦', '易醒', '入睡困难', '睡眠浅',
            '胃痛', '胃胀', '胃酸', '消化不良', '恶心', '呕吐',
            '便秘', '腹泻', '大便干', '大便稀', '腹胀', '腹痛',
            '咳嗽', '咳痰', '气喘', '胸闷', '气短',
            '乏力', '疲劳', '精神差', '倦怠', '无力',
            '心慌', '心悸', '胸痛', '心跳快',
            '腰痛', '腰酸', '腿软', '膝盖痛', '关节痛',
            '月经不调', '痛经', '白带异常', '性功能减退',
            '眼干', '眼涩', '视力模糊', '耳鸣', '听力下降',
            '口干', '口苦', '口臭', '牙痛', '咽喉痛',
            '皮肤干燥', '皮疹', '瘙痒', '湿疹'
        }
        
        # 🔑 修复：移除容易误判的结束关键词，保留明确的结束表达
        self.end_keywords = {
            'natural': [
                # 移除了'谢谢', '明白了', '好的'等容易误判的词
                '谢谢医生', '感谢医生', '多谢了',
                '先这样吧', '就这样吧', '够了', '可以了', '不用了',
                '再见', '拜拜', '问诊结束', '暂时不问了'
            ],
            'satisfied': [
                # 移除了'满意', '很好', '不错'等容易误判的词
                '很满意', '非常满意', '满意的', '很有帮助', '非常有用',
                '清楚了谢谢', '明白了谢谢', '知道怎么做了'
            ]
        }
        
        # 紧急情况关键词
        self.emergency_keywords = [
            '剧痛', '剧烈疼痛', '无法忍受', '痛得厉害',
            '呼吸困难', '喘不过气', '胸痛厉害', '心慌严重',
            '昏迷', '意识不清', '抽搐', '痉挛',
            '大出血', '出血不止', '吐血', '大量便血',  # 修改：只有"大量便血"才是紧急情况
            '高热', '发烧很厉害', '烧得很高',
            '急诊', '需要急救', '送医院', '叫救护车'
        ]
        
        # 处方相关关键词
        self.prescription_keywords = [
            '处方', '方剂', '药方', '中药', '汤剂',
            '君药', '臣药', '佐药', '使药',
            '克', 'g', '煎服', '水煎', '用法',
            '每日', '每天', '早晚', '饭前', '饭后'
        ]
        
        # 继续问诊关键词
        self.continue_keywords = [
            '还有什么', '继续', '再问', '想了解', '想知道',
            '其他', '别的', '还需要', '补充', '详细',
            '为什么', '怎么', '如何', '什么原因'
        ]
        
        # 临时建议关键词
        self.interim_advice_keywords = [
            '初步', '暂时', '先', '临时', '初步考虑',
            '建议', '可以', '试试', '先调理',
            '待', '等', '完善', '补充信息后'
        ]
    
    def analyze_user_message(self, message: str, current_stage: ConversationStage,
                           turn_count: int, conversation_history: List[Dict]) -> AnalysisResult:
        """分析用户消息"""
        result = AnalysisResult()
        
        # 1. 检查是否应该结束对话
        should_end, end_type, end_reason = self._check_conversation_end(message)
        if should_end:
            result.should_end = True
            result.end_type = end_type
            result.end_reason = end_reason
            return result
        
        # 2. 提取症状信息
        result.extracted_symptoms = self._extract_symptoms(message)
        
        # 3. 分析用户意图
        intent = self._analyze_user_intent(message)
        
        # 4. 基于当前阶段和意图建议下一阶段
        result.suggested_stage, result.confidence = self._suggest_next_stage(
            current_stage, intent, result.extracted_symptoms, turn_count
        )
        
        return result
    
    def analyze_ai_response(self, response: str, current_stage: ConversationStage) -> AnalysisResult:
        """分析AI响应"""
        result = AnalysisResult()
        
        # 1. 检查是否包含处方
        result.has_prescription_keywords = self._contains_prescription(response)
        
        # 2. 检查是否为临时建议
        is_interim_advice = self._is_interim_advice(response)
        
        # 3. 评估诊断置信度
        result.diagnosis_confidence = self._evaluate_diagnosis_confidence(response)
        
        # 4. 检查是否需要更多信息
        result.requires_more_info = self._requires_more_information(response)
        
        # 5. 基于响应内容建议阶段转换
        if result.has_prescription_keywords and not is_interim_advice:
            result.suggested_stage = ConversationStage.PRESCRIPTION
            result.confidence = 0.9
        elif is_interim_advice:
            result.suggested_stage = ConversationStage.INTERIM_ADVICE
            result.confidence = 0.8
        elif result.diagnosis_confidence > 0.7:
            result.suggested_stage = ConversationStage.DIAGNOSIS
            result.confidence = result.diagnosis_confidence
        elif current_stage == ConversationStage.INQUIRY:
            result.suggested_stage = ConversationStage.DETAILED_INQUIRY
            result.confidence = 0.6
        
        return result
    
    def _check_conversation_end(self, message: str) -> Tuple[bool, Optional[ConversationEndType], str]:
        """检查是否应该结束对话"""
        message_lower = message.lower()
        
        # 🔑 修复：更精准的结束检测，避免误判
        # 检查明确的结束表达，需要单独成句或在句子开头/结尾
        clear_end_patterns = [
            '谢谢医生', '谢谢大夫', '多谢了', '感谢医生', '明白了谢谢',
            '先这样吧', '就这样吧', '够了', '可以了', '不用了',
            '再见', '拜拜', '就到这里', '问诊结束', '暂时不问了'
        ]
        
        for pattern in clear_end_patterns:
            if pattern in message:
                return True, ConversationEndType.NATURAL, f"用户表示结束: {pattern}"
        
        # 检查是否是明确的满意表达（独立成句）
        satisfied_patterns = [
            '很满意', '非常满意', '满意的', '很有帮助', '非常有用',
            '清楚了谢谢', '明白了谢谢', '知道怎么做了'
        ]
        
        for pattern in satisfied_patterns:
            if pattern in message:
                return True, ConversationEndType.NATURAL, f"用户表示满意: {pattern}"
        
        # 检查紧急情况（保持原有逻辑）
        for keyword in self.emergency_keywords:
            if keyword in message:
                return True, ConversationEndType.EMERGENCY_REFERRAL, f"检测到紧急情况: {keyword}"
        
        # 🔑 新增：检查消息长度和症状内容，避免误判症状描述为结束
        # 如果消息包含症状描述或医学术语，不应该结束
        medical_indicators = ['痛', '疼', '酸', '胀', '麻', '症状', '不适', '难受', '舌苔', '大便', '小便', '睡眠', '食欲']
        has_medical_content = any(indicator in message for indicator in medical_indicators)
        
        if has_medical_content and len(message) > 10:
            # 包含医学内容且较长的消息，不应该被判断为结束
            return False, None, ""
        
        return False, None, ""
    
    def _extract_symptoms(self, message: str) -> List[str]:
        """提取症状信息"""
        extracted = []
        
        # 使用关键词匹配
        for symptom in self.symptom_keywords:
            if symptom in message:
                extracted.append(symptom)
        
        # 使用正则表达式提取常见症状描述模式
        patterns = [
            r'(.{0,5})(痛|疼|酸|胀|闷|紧|重|麻|木)(.{0,3})',
            r'(头|胃|腰|腹|胸|心|眼|耳|口|咽)(.{0,3})(不舒服|难受|异常)',
            r'(睡不着|失眠|多梦|易醒|入睡困难)',
            r'(拉肚子|腹泻|便秘|大便.*)',
            r'(咳嗽|咳痰|气喘|胸闷)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, message)
            for match in matches:
                symptom_desc = ''.join(match).strip()
                if len(symptom_desc) > 1 and symptom_desc not in extracted:
                    extracted.append(symptom_desc)
        
        return extracted
    
    def _analyze_user_intent(self, message: str) -> str:
        """分析用户意图"""
        # 继续问诊意图
        if any(keyword in message for keyword in self.continue_keywords):
            return "continue_inquiry"
        
        # 确认意图
        if any(keyword in message for keyword in ['确认', '同意', '接受', '可以', '好的']):
            return "confirm"
        
        # 拒绝意图
        if any(keyword in message for keyword in ['不同意', '不接受', '不要', '拒绝']):
            return "reject"
        
        # 症状描述意图
        if self._extract_symptoms(message):
            return "symptom_description"
        
        # 问题咨询意图
        if any(char in message for char in ['？', '?', '吗', '呢', '为什么', '怎么']):
            return "question"
        
        return "general"
    
    def _suggest_next_stage(self, current_stage: ConversationStage, intent: str,
                          symptoms: List[str], turn_count: int) -> Tuple[Optional[ConversationStage], float]:
        """建议下一阶段"""
        
        # 基于意图的阶段转换规则
        if intent == "confirm":
            if current_stage == ConversationStage.PRESCRIPTION:
                return ConversationStage.PRESCRIPTION_CONFIRM, 0.9
            elif current_stage == ConversationStage.PRESCRIPTION_CONFIRM:
                return ConversationStage.COMPLETED, 0.95
        
        elif intent == "reject":
            if current_stage in [ConversationStage.PRESCRIPTION, ConversationStage.PRESCRIPTION_CONFIRM]:
                return ConversationStage.DETAILED_INQUIRY, 0.8
        
        elif intent == "continue_inquiry":
            return ConversationStage.DETAILED_INQUIRY, 0.7
        
        elif intent == "symptom_description":
            if current_stage == ConversationStage.INQUIRY:
                return ConversationStage.DETAILED_INQUIRY, 0.6
            elif turn_count >= 3:  # 多轮症状收集后
                return ConversationStage.DIAGNOSIS, 0.7
        
        # 基于轮数的自然进展
        if turn_count >= 8 and current_stage in [ConversationStage.DETAILED_INQUIRY, ConversationStage.INTERIM_ADVICE]:
            return ConversationStage.DIAGNOSIS, 0.6
        
        return None, 0.0
    
    def _contains_prescription(self, text: str) -> bool:
        """检查是否包含处方"""
        # 处方关键词计数
        prescription_count = sum(1 for keyword in self.prescription_keywords if keyword in text)
        
        # 剂量模式检测
        dosage_pattern = re.findall(r'\d+[克g]\s*[，,]', text)
        
        # 方剂结构检测
        formula_pattern = re.search(r'(君药|臣药|佐药|使药|方解)', text)
        
        return prescription_count >= 3 or len(dosage_pattern) >= 3 or formula_pattern is not None
    
    def _is_interim_advice(self, text: str) -> bool:
        """检查是否为临时建议"""
        return any(keyword in text for keyword in self.interim_advice_keywords)
    
    def _evaluate_diagnosis_confidence(self, text: str) -> float:
        """评估诊断置信度"""
        confidence_indicators = {
            '确诊': 0.9,
            '明确': 0.8,
            '考虑': 0.6,
            '可能': 0.5,
            '疑似': 0.4,
            '初步': 0.3
        }
        
        max_confidence = 0.0
        for indicator, confidence in confidence_indicators.items():
            if indicator in text:
                max_confidence = max(max_confidence, confidence)
        
        # 基于中医术语的置信度评估
        tcm_terms = ['证候', '辨证', '证型', '病机', '治法', '方药']
        tcm_count = sum(1 for term in tcm_terms if term in text)
        
        return min(max_confidence + tcm_count * 0.1, 1.0)
    
    def _requires_more_information(self, text: str) -> bool:
        """检查是否需要更多信息"""
        info_request_keywords = [
            '请问', '需要了解', '请描述', '请补充', '能否提供',
            '舌象', '脉象', '具体', '详细', '还有', '其他'
        ]
        
        return any(keyword in text for keyword in info_request_keywords)
    
    def analyze_conversation_summary(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析对话摘要"""
        if not messages:
            return {}
        
        # 提取所有症状
        all_symptoms = []
        for msg in messages:
            if msg.get('role') == 'user':
                symptoms = self._extract_symptoms(msg.get('content', ''))
                all_symptoms.extend(symptoms)
        
        # 去重并按出现频率排序
        symptom_counts = {}
        for symptom in all_symptoms:
            symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
        
        sorted_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)
        
        # 分析对话质量
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        ai_messages = [msg for msg in messages if msg.get('role') == 'assistant']
        
        quality_score = self._calculate_conversation_quality(user_messages, ai_messages)
        
        return {
            'total_messages': len(messages),
            'user_messages': len(user_messages),
            'ai_messages': len(ai_messages),
            'unique_symptoms': len(symptom_counts),
            'main_symptoms': [symptom for symptom, count in sorted_symptoms[:5]],
            'symptom_details': dict(sorted_symptoms),
            'conversation_quality': quality_score,
            'avg_message_length': sum(len(msg.get('content', '')) for msg in messages) / len(messages) if messages else 0
        }
    
    def _calculate_conversation_quality(self, user_messages: List[Dict], ai_messages: List[Dict]) -> float:
        """计算对话质量评分"""
        if not user_messages or not ai_messages:
            return 0.0
        
        quality_score = 0.0
        
        # 1. 用户参与度 (30%)
        avg_user_length = sum(len(msg.get('content', '')) for msg in user_messages) / len(user_messages)
        participation_score = min(avg_user_length / 20, 1.0)  # 平均长度20字为满分
        quality_score += participation_score * 0.3
        
        # 2. AI响应质量 (40%)
        avg_ai_length = sum(len(msg.get('content', '')) for msg in ai_messages) / len(ai_messages)
        response_score = min(avg_ai_length / 100, 1.0)  # 平均长度100字为满分
        quality_score += response_score * 0.4
        
        # 3. 对话轮次合理性 (30%)
        turn_ratio = len(user_messages) / len(ai_messages)
        balance_score = 1.0 - abs(1.0 - turn_ratio)  # 1:1为最佳比例
        quality_score += max(balance_score, 0) * 0.3
        
        return round(quality_score, 2)