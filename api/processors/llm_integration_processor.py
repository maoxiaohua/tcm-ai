#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM集成处理模块
从chat_with_ai_endpoint函数中提取的AI大模型集成相关功能
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..utils.common_utils import safe_execute, get_current_timestamp_iso
from ..utils.text_utils import clean_ai_response_text, split_long_text, count_chinese_characters
from ...core.prescription.prescription_format_enforcer import get_prescription_enforcer

logger = logging.getLogger(__name__)

class LLMIntegrationProcessor:
    """LLM集成处理器"""
    
    def __init__(self, llm_service, config_manager):
        self.llm_service = llm_service
        self.config = config_manager.get_ai_config()
        
        # LLM配置参数
        self.default_model = self.config.get('default_model', 'qwen-max')
        self.default_temperature = self.config.get('temperature', 0.7)
        self.max_tokens = self.config.get('max_tokens', 2000)
        self.timeout = self.config.get('timeout', 60)
        
        # 提示词模板
        self.prompt_templates = {
            'tcm_diagnosis': self._get_tcm_diagnosis_template(),
            'prescription_generation': self._get_prescription_template(),
            'symptom_analysis': self._get_symptom_analysis_template(),
            'lifestyle_advice': self._get_lifestyle_advice_template(),
            'follow_up': self._get_follow_up_template()
        }
        
        # 响应质量检查规则
        self.quality_rules = {
            'min_length': 100,
            'max_length': 3000,
            'required_sections': ['分析', '建议'],
            'forbidden_words': ['不负责任', '仅供参考', '请咨询医生']
        }
    
    def generate_ai_response(self, query: str, context: Dict[str, Any], 
                           response_type: str = 'tcm_diagnosis') -> Dict[str, Any]:
        """生成AI响应"""
        response_result = {
            'success': False,
            'response': '',
            'response_type': response_type,
            'metadata': {},
            'quality_score': 0.0,
            'processing_time': 0,
            'error_message': ''
        }
        
        start_time = datetime.now()
        
        try:
            # 构建提示词
            prompt = self._build_prompt(query, context, response_type)
            
            # 参数配置
            llm_params = self._get_llm_parameters(response_type, context)
            
            # 调用LLM服务
            llm_response = self._call_llm_service(prompt, llm_params)
            
            if llm_response['success']:
                # 后处理响应
                processed_response = self._post_process_response(
                    llm_response['response'], 
                    response_type
                )
                
                # 质量评估
                quality_score = self._evaluate_response_quality(
                    processed_response, 
                    query, 
                    response_type
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                response_result.update({
                    'success': True,
                    'response': processed_response,
                    'metadata': {
                        'model_used': llm_params.get('model', self.default_model),
                        'temperature': llm_params.get('temperature', self.default_temperature),
                        'prompt_tokens': len(prompt),
                        'response_tokens': len(processed_response),
                        'chinese_chars': count_chinese_characters(processed_response)
                    },
                    'quality_score': quality_score,
                    'processing_time': processing_time
                })
                
                # 质量检查
                if quality_score < 0.6:
                    logger.warning(f"响应质量较低: {quality_score}")
                    # 可以选择重新生成或添加警告信息
                
            else:
                response_result['error_message'] = llm_response.get('error', 'LLM调用失败')
                
        except Exception as e:
            logger.error(f"AI响应生成失败: {e}")
            response_result['error_message'] = str(e)
            response_result['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        return response_result
    
    def _build_prompt(self, query: str, context: Dict[str, Any], 
                     response_type: str) -> str:
        """构建提示词"""
        # 获取基础模板
        base_template = self.prompt_templates.get(response_type, self.prompt_templates['tcm_diagnosis'])
        
        # 构建上下文信息
        context_info = self._build_context_info(context)
        
        # 用户查询预处理
        cleaned_query = clean_ai_response_text(query)
        
        # 组装完整提示词
        full_prompt = f"""
{base_template}

用户咨询内容：
{cleaned_query}

{context_info}

请基于以上信息，提供专业、准确、实用的中医诊疗建议。
"""
        
        return full_prompt.strip()
    
    def _build_context_info(self, context: Dict[str, Any]) -> str:
        """构建上下文信息"""
        context_parts = []
        
        # 知识检索上下文
        if context.get('retrieved_knowledge'):
            knowledge_items = context['retrieved_knowledge'].get('retrieved_items', [])
            if knowledge_items:
                context_parts.append("相关知识参考：")
                for i, item in enumerate(knowledge_items[:3], 1):
                    content = item.get('content', '')[:300]
                    context_parts.append(f"{i}. {content}")
        
        # 用户历史上下文
        if context.get('user_history'):
            history_summary = context['user_history'].get('context_summary', '')
            if history_summary:
                context_parts.append(f"\n用户背景：{history_summary}")
        
        # 图像分析上下文
        if context.get('image_analysis'):
            for analysis in context['image_analysis']:
                if analysis.get('success'):
                    features = analysis.get('features_extracted', {})
                    if features:
                        context_parts.append("\n图像分析结果：")
                        for feature, description in features.items():
                            context_parts.append(f"- {feature}: {description}")
        
        # 症状上下文
        if context.get('symptoms'):
            symptoms_text = '、'.join(context['symptoms'])
            context_parts.append(f"\n主要症状：{symptoms_text}")
        
        return '\n'.join(context_parts) if context_parts else ""
    
    def _get_llm_parameters(self, response_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取LLM参数配置"""
        base_params = {
            'model': self.default_model,
            'temperature': self.default_temperature,
            'max_tokens': self.max_tokens,
            'timeout': self.timeout
        }
        
        # 根据响应类型调整参数
        type_adjustments = {
            'tcm_diagnosis': {'temperature': 0.7, 'max_tokens': 2000},
            'prescription_generation': {'temperature': 0.5, 'max_tokens': 1500},
            'symptom_analysis': {'temperature': 0.8, 'max_tokens': 1200},
            'lifestyle_advice': {'temperature': 0.9, 'max_tokens': 1000},
            'follow_up': {'temperature': 0.6, 'max_tokens': 800}
        }
        
        if response_type in type_adjustments:
            base_params.update(type_adjustments[response_type])
        
        # 根据上下文复杂度调整
        context_complexity = self._assess_context_complexity(context)
        if context_complexity > 0.7:
            base_params['max_tokens'] = min(base_params['max_tokens'] + 500, 3000)
            base_params['temperature'] = max(base_params['temperature'] - 0.1, 0.3)
        
        return base_params
    
    def _assess_context_complexity(self, context: Dict[str, Any]) -> float:
        """评估上下文复杂度"""
        complexity_score = 0.0
        
        # 知识检索复杂度
        if context.get('retrieved_knowledge', {}).get('retrieved_items'):
            knowledge_count = len(context['retrieved_knowledge']['retrieved_items'])
            complexity_score += min(knowledge_count * 0.1, 0.3)
        
        # 图像分析复杂度
        if context.get('image_analysis'):
            image_count = len(context['image_analysis'])
            complexity_score += min(image_count * 0.15, 0.3)
        
        # 用户历史复杂度
        if context.get('user_history', {}).get('recent_history'):
            history_count = len(context['user_history']['recent_history'])
            complexity_score += min(history_count * 0.1, 0.2)
        
        # 症状数量复杂度
        if context.get('symptoms'):
            symptom_count = len(context['symptoms'])
            complexity_score += min(symptom_count * 0.05, 0.2)
        
        return min(complexity_score, 1.0)
    
    def _call_llm_service(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用LLM服务"""
        try:
            response = self.llm_service.generate_response(
                prompt=prompt,
                model=params.get('model', self.default_model),
                temperature=params.get('temperature', self.default_temperature),
                max_tokens=params.get('max_tokens', self.max_tokens),
                timeout=params.get('timeout', self.timeout)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM服务调用失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _post_process_response(self, response: str, response_type: str) -> str:
        """后处理AI响应"""
        # 基础清理
        cleaned_response = clean_ai_response_text(response)
        
        # 🔥 处方格式强制执行 (v2.9新增) - 确保AI回复包含具体剂量
        try:
            prescription_enforcer = get_prescription_enforcer()
            cleaned_response = prescription_enforcer.enforce_prescription_format(cleaned_response)
            logger.info("处方格式强制执行完成")
        except Exception as e:
            logger.error(f"处方格式强制执行失败: {e}")
        
        # 根据类型进行特定处理
        if response_type == 'prescription_generation':
            cleaned_response = self._format_prescription_response(cleaned_response)
        elif response_type == 'symptom_analysis':
            cleaned_response = self._format_symptom_analysis_response(cleaned_response)
        elif response_type == 'lifestyle_advice':
            cleaned_response = self._format_lifestyle_advice_response(cleaned_response)
        
        # 长度控制
        if len(cleaned_response) > 3000:
            cleaned_response = self._truncate_response_intelligently(cleaned_response)
        
        # 添加免责声明（如果需要）
        if self.config.get('add_disclaimer', True):
            cleaned_response = self._add_medical_disclaimer(cleaned_response)
        
        return cleaned_response
    
    def _format_prescription_response(self, response: str) -> str:
        """格式化处方响应"""
        # 确保处方格式正确
        lines = response.split('\n')
        formatted_lines = []
        
        in_prescription_section = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 识别处方部分
            if '处方' in line or '药方' in line:
                in_prescription_section = True
                formatted_lines.append(line)
                continue
            
            # 格式化处方条目
            if in_prescription_section and any(char in line for char in ['g', '克', '钱']):
                # 确保药材名和用量格式正确
                from ..utils.text_utils import normalize_prescription_dosage
                formatted_line = normalize_prescription_dosage(line)
                formatted_lines.append(formatted_line)
            else:
                formatted_lines.append(line)
                if line.endswith('。') or line.endswith('：'):
                    in_prescription_section = False
        
        return '\n'.join(formatted_lines)
    
    def _format_symptom_analysis_response(self, response: str) -> str:
        """格式化症状分析响应"""
        # 确保有明确的分析结构
        if '症状分析' not in response and '分析' not in response:
            response = f"## 症状分析\n\n{response}"
        
        return response
    
    def _format_lifestyle_advice_response(self, response: str) -> str:
        """格式化生活建议响应"""
        # 添加结构化标题
        if '生活调理' not in response and '建议' not in response:
            response = f"## 生活调理建议\n\n{response}"
        
        return response
    
    def _truncate_response_intelligently(self, response: str) -> str:
        """智能截断响应"""
        # 按段落截断，保持完整性
        paragraphs = response.split('\n\n')
        
        truncated_paragraphs = []
        current_length = 0
        
        for paragraph in paragraphs:
            if current_length + len(paragraph) > 2800:  # 留一些空间给结尾
                break
            truncated_paragraphs.append(paragraph)
            current_length += len(paragraph)
        
        truncated_response = '\n\n'.join(truncated_paragraphs)
        
        # 添加截断提示
        if len(truncated_response) < len(response):
            truncated_response += '\n\n[响应内容较长，已智能截断]'
        
        return truncated_response
    
    def _add_medical_disclaimer(self, response: str) -> str:
        """添加医疗免责声明"""
        disclaimer = "\n\n---\n**医疗声明**: 以上内容仅供参考学习，不能替代专业医疗诊断。如有疾病，请及时就医。"
        
        return response + disclaimer
    
    def _evaluate_response_quality(self, response: str, query: str, 
                                  response_type: str) -> float:
        """评估响应质量"""
        quality_score = 1.0
        
        # 长度检查
        response_length = len(response)
        if response_length < self.quality_rules['min_length']:
            quality_score -= 0.3
        elif response_length > self.quality_rules['max_length']:
            quality_score -= 0.2
        
        # 结构完整性检查
        required_sections = self.quality_rules.get('required_sections', [])
        for section in required_sections:
            if section not in response:
                quality_score -= 0.2
        
        # 禁用词检查
        forbidden_words = self.quality_rules.get('forbidden_words', [])
        for word in forbidden_words:
            if word in response:
                quality_score -= 0.1
        
        # 中医专业性检查
        tcm_keywords = ['中医', '证型', '辨证', '脉象', '舌象', '气血', '阴阳', '脏腑']
        tcm_keyword_count = sum(1 for kw in tcm_keywords if kw in response)
        if response_type == 'tcm_diagnosis' and tcm_keyword_count < 3:
            quality_score -= 0.2
        
        # 查询相关性检查
        from ..utils.text_utils import extract_keywords_from_query
        query_keywords = extract_keywords_from_query(query)
        matched_keywords = sum(1 for kw in query_keywords if kw.lower() in response.lower())
        relevance_ratio = matched_keywords / len(query_keywords) if query_keywords else 1.0
        if relevance_ratio < 0.5:
            quality_score -= 0.3
        
        # 确保质量分数在合理范围内
        return max(0.0, min(quality_score, 1.0))
    
    def generate_follow_up_questions(self, conversation_context: Dict[str, Any]) -> List[str]:
        """生成后续问题建议"""
        follow_up_questions = []
        
        try:
            # 基于对话类型生成不同的后续问题
            user_pattern = conversation_context.get('user_history', {}).get('user_pattern', {})
            most_common_type = user_pattern.get('most_common_type', '')
            
            question_templates = {
                'symptom_inquiry': [
                    "症状出现多长时间了？",
                    "是否有其他伴随症状？",
                    "什么情况下症状会加重？"
                ],
                'prescription_request': [
                    "您是否有药物过敏史？",
                    "目前是否在服用其他药物？",
                    "希望了解用药注意事项吗？"
                ],
                'lifestyle_advice': [
                    "您的日常作息如何？",
                    "饮食习惯有什么特点？",
                    "工作压力大吗？"
                ]
            }
            
            # 根据历史模式选择问题
            if most_common_type in question_templates:
                follow_up_questions.extend(question_templates[most_common_type][:2])
            
            # 基于当前症状生成针对性问题
            current_symptoms = conversation_context.get('symptoms', [])
            if '头痛' in current_symptoms:
                follow_up_questions.append("头痛是胀痛还是刺痛？")
            elif '咳嗽' in current_symptoms:
                follow_up_questions.append("咳嗽时有痰吗？痰的颜色如何？")
            
            # 通用后续问题
            if len(follow_up_questions) < 3:
                generic_questions = [
                    "还有什么需要了解的吗？",
                    "对建议有疑问吗？",
                    "需要了解用药方法吗？"
                ]
                follow_up_questions.extend(generic_questions[:3-len(follow_up_questions)])
            
        except Exception as e:
            logger.error(f"生成后续问题失败: {e}")
            follow_up_questions = ["还有什么需要了解的吗？"]
        
        return follow_up_questions[:3]
    
    # 提示词模板
    def _get_tcm_diagnosis_template(self) -> str:
        # 获取处方格式提示（如果需要开处方的话）
        try:
            prescription_enforcer = get_prescription_enforcer()
            format_prompt = prescription_enforcer.add_prescription_format_prompt()
        except:
            format_prompt = ""
            
        return f"""你是一位经验丰富的中医专家，请根据用户的症状描述和提供的信息，进行专业的中医诊疗分析。

请按照以下步骤进行分析：
1. 症状分析：分析用户描述的症状特点
2. 证型判断：基于中医理论判断可能的证型
3. 治疗方案：提供相应的治疗建议
4. 生活调理：给出日常调理建议

{format_prompt}

请确保建议专业、实用，符合中医理论。"""
    
    def _get_prescription_template(self) -> str:
        # 获取处方格式提示
        try:
            prescription_enforcer = get_prescription_enforcer()
            format_prompt = prescription_enforcer.add_prescription_format_prompt()
        except:
            format_prompt = ""
            
        return f"""你是一位中医处方专家，请根据用户的症状和证型，开具适当的中药处方。

{format_prompt}

请包含以下内容：
1. 证型分析：说明辨证思路
2. 处方组成：列出具体药物和用量（必须包含具体克数）
3. 方解：解释处方组成原理
4. 服用方法：详细说明煎煮和服用方法
5. 注意事项：用药禁忌和注意事项

请确保处方安全、有效，符合中医处方原则。"""
    
    def _get_symptom_analysis_template(self) -> str:
        return """作为中医症状分析专家，请对用户的症状进行详细分析。

分析要点：
1. 症状特征：描述症状的性质、程度、时间规律
2. 病因分析：从中医角度分析可能的病因
3. 脏腑关联：分析涉及的脏腑系统
4. 证型倾向：初步判断证型方向
5. 进一步检查建议：建议需要关注的其他症状

请提供专业、准确的症状分析。"""
    
    def _get_lifestyle_advice_template(self) -> str:
        return """作为中医养生专家，请根据用户情况提供全面的生活调理建议。

建议包含：
1. 饮食调理：推荐适宜的食物和饮食习惯
2. 作息调整：合理的作息时间安排
3. 运动养生：适宜的运动方式和强度
4. 情志调理：情绪调节和心理健康建议
5. 季节养生：结合当前季节的特殊注意事项

请确保建议实用、可操作，符合中医养生理念。"""
    
    def _get_follow_up_template(self) -> str:
        return """基于之前的对话内容，请提供后续咨询的建议。

请包含：
1. 治疗效果评估：询问治疗效果和变化
2. 症状跟踪：需要持续关注的症状
3. 调理建议：后续调理重点
4. 复诊建议：是否需要进一步诊疗

请提供专业、贴心的后续指导。"""