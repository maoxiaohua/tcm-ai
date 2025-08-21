#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天端点处理模块
重构后的chat_with_ai_endpoint函数，使用模块化的处理器
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .user_history_processor import UserHistoryProcessor
from .image_analysis_processor import ImageAnalysisProcessor
from .knowledge_retrieval_processor import KnowledgeRetrievalProcessor
from .llm_integration_processor import LLMIntegrationProcessor
from .medical_safety_processor import MedicalSafetyProcessor

from ..utils.common_utils import (
    safe_execute, 
    generate_conversation_id,
    get_current_timestamp_iso,
    create_success_response,
    create_error_response
)
from ..utils.text_utils import clean_medical_text, has_medical_keywords

logger = logging.getLogger(__name__)

class ChatEndpointProcessor:
    """聊天端点处理器 - 替代原来的510行chat_with_ai_endpoint函数"""
    
    def __init__(self, services_container):
        """初始化所有处理器"""
        self.services = services_container
        
        # 初始化各个专业处理器
        self.user_history_processor = UserHistoryProcessor(
            db_manager=self.services.get('db_manager')
        )
        
        self.image_analysis_processor = ImageAnalysisProcessor(
            multimodal_service=self.services.get('multimodal_service'),
            config_manager=self.services.get('config_manager')
        )
        
        self.knowledge_retrieval_processor = KnowledgeRetrievalProcessor(
            vector_store_service=self.services.get('vector_store_service'),
            faiss_service=self.services.get('faiss_service'),
            db_manager=self.services.get('db_manager')
        )
        
        self.llm_integration_processor = LLMIntegrationProcessor(
            llm_service=self.services.get('llm_service'),
            config_manager=self.services.get('config_manager')
        )
        
        self.medical_safety_processor = MedicalSafetyProcessor(
            db_manager=self.services.get('db_manager'),
            config_manager=self.services.get('config_manager')
        )
        
        # 缓存服务
        self.cache_service = self.services.get('cache_service')
        
        # 配置参数
        self.config = self.services.get('config_manager').get_ai_config()
        self.enable_caching = self.config.get('enable_response_caching', True)
        self.enable_safety_check = self.config.get('enable_safety_check', True)
        
    def process_chat_request(self, user_input: str, user_id: str, 
                           images: List[bytes] = None, 
                           additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理聊天请求 - 替代原来的510行chat_with_ai_endpoint函数
        
        Args:
            user_input: 用户输入内容
            user_id: 用户ID
            images: 图像数据列表（可选）
            additional_context: 额外上下文信息（可选）
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 生成对话ID
        conversation_id = generate_conversation_id()
        start_time = datetime.now()
        
        logger.info(f"开始处理对话请求: {conversation_id}")
        
        try:
            # 第一步：预处理和验证
            preprocessing_result = self._preprocess_request(
                user_input, user_id, images, additional_context
            )
            
            if not preprocessing_result['success']:
                return create_error_response(
                    preprocessing_result['error'], 
                    code=400
                )
            
            # 第二步：检查缓存
            cache_result = self._check_response_cache(user_input, user_id) if self.enable_caching else None
            if cache_result and cache_result['found']:
                logger.info(f"返回缓存响应: {conversation_id}")
                return self._format_cached_response(cache_result, conversation_id)
            
            # 第三步：构建处理上下文
            processing_context = self._build_processing_context(
                user_input=preprocessing_result['cleaned_input'],
                user_id=user_id,
                images=preprocessing_result['processed_images'],
                additional_context=additional_context or {}
            )
            
            # 第四步：执行各个处理步骤
            processing_steps = [
                ('用户历史分析', self._process_user_history),
                ('图像分析', self._process_images),
                ('知识检索', self._process_knowledge_retrieval),
                ('AI响应生成', self._process_ai_response),
                ('安全检查', self._process_safety_check),
                ('响应后处理', self._post_process_response)
            ]
            
            for step_name, step_function in processing_steps:
                logger.info(f"执行步骤: {step_name}")
                
                step_result = safe_execute(
                    step_function,
                    processing_context,
                    default_return={'success': False, 'error': f'{step_name}失败'},
                    error_message=f'{step_name}执行出错'
                )
                
                if not step_result['success']:
                    logger.error(f"{step_name}失败: {step_result.get('error')}")
                    return create_error_response(
                        f"{step_name}失败: {step_result.get('error', '未知错误')}",
                        code=500,
                        details={'step': step_name, 'conversation_id': conversation_id}
                    )
                
                # 更新处理上下文
                processing_context.update(step_result.get('context_updates', {}))
            
            # 第五步：保存对话记录
            conversation_saved = self._save_conversation_record(
                conversation_id=conversation_id,
                user_id=user_id,
                user_input=user_input,
                ai_response=processing_context.get('final_response', ''),
                processing_context=processing_context
            )
            
            if not conversation_saved:
                logger.warning(f"对话记录保存失败: {conversation_id}")
            
            # 第六步：缓存响应
            if self.enable_caching and processing_context.get('final_response'):
                self._cache_response(user_input, user_id, processing_context['final_response'])
            
            # 构建最终响应
            processing_time = (datetime.now() - start_time).total_seconds()
            
            final_result = create_success_response({
                'conversation_id': conversation_id,
                'response': processing_context.get('final_response', ''),
                'response_type': processing_context.get('response_type', 'general'),
                'confidence_score': processing_context.get('confidence_score', 0.0),
                'safety_status': processing_context.get('safety_status', {}),
                'processing_time': processing_time,
                'metadata': {
                    'user_id': user_id,
                    'has_images': len(images) > 0 if images else False,
                    'knowledge_items_used': len(processing_context.get('retrieved_knowledge', {}).get('retrieved_items', [])),
                    'safety_checks_passed': processing_context.get('safety_status', {}).get('safety_passed', True),
                    'processing_steps_completed': len(processing_steps)
                }
            })
            
            # 生成后续问题建议
            follow_up_questions = self.llm_integration_processor.generate_follow_up_questions(
                processing_context
            )
            final_result['data']['follow_up_questions'] = follow_up_questions
            
            logger.info(f"对话处理完成: {conversation_id}, 耗时: {processing_time:.2f}秒")
            return final_result
            
        except Exception as e:
            logger.error(f"对话处理失败: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return create_error_response(
                f"对话处理出现异常: {str(e)}",
                code=500,
                details={
                    'conversation_id': conversation_id,
                    'processing_time': processing_time,
                    'error_type': type(e).__name__
                }
            )
    
    def _preprocess_request(self, user_input: str, user_id: str, 
                           images: List[bytes] = None, 
                           additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """预处理请求"""
        result = {
            'success': True,
            'cleaned_input': '',
            'processed_images': [],
            'error': ''
        }
        
        try:
            # 验证输入
            if not user_input or not user_input.strip():
                result['success'] = False
                result['error'] = '用户输入为空'
                return result
            
            if not user_id:
                result['success'] = False
                result['error'] = '用户ID缺失'
                return result
            
            # 清理用户输入
            result['cleaned_input'] = clean_medical_text(user_input)
            
            # 处理图像数据
            if images:
                for i, image_data in enumerate(images):
                    if image_data and len(image_data) > 0:
                        result['processed_images'].append({
                            'index': i,
                            'data': image_data,
                            'type': 'image',  # 可以通过其他方式确定具体类型
                            'size': len(image_data)
                        })
            
            # 验证是否包含医疗相关内容
            if not has_medical_keywords(result['cleaned_input']) and not result['processed_images']:
                logger.warning(f"用户输入可能不包含医疗相关内容: {user_input[:50]}")
            
        except Exception as e:
            logger.error(f"请求预处理失败: {e}")
            result['success'] = False
            result['error'] = f'预处理失败: {str(e)}'
        
        return result
    
    def _check_response_cache(self, user_input: str, user_id: str) -> Optional[Dict[str, Any]]:
        """检查响应缓存"""
        try:
            # 生成缓存键
            cache_key = f"chat_response:{user_id}:{hash(user_input.lower().strip())}"
            
            cached_response = self.cache_service.get(cache_key) if self.cache_service else None
            
            if cached_response:
                return {
                    'found': True,
                    'response': cached_response,
                    'cache_key': cache_key
                }
            
        except Exception as e:
            logger.error(f"缓存检查失败: {e}")
        
        return {'found': False}
    
    def _build_processing_context(self, user_input: str, user_id: str, 
                                 images: List[Dict[str, Any]], 
                                 additional_context: Dict[str, Any]) -> Dict[str, Any]:
        """构建处理上下文"""
        context = {
            'user_input': user_input,
            'user_id': user_id,
            'images': images,
            'additional_context': additional_context,
            'timestamp': get_current_timestamp_iso(),
            'processing_metadata': {},
            'step_results': {}
        }
        
        return context
    
    def _process_user_history(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户历史"""
        try:
            user_id = context['user_id']
            current_query = context['user_input']
            
            # 获取用户对话上下文
            user_context = self.user_history_processor.get_context_for_conversation(
                user_id, current_query
            )
            
            # 获取用户偏好
            user_preferences = self.user_history_processor.get_user_preferences(user_id)
            
            return {
                'success': True,
                'context_updates': {
                    'user_history': user_context,
                    'user_preferences': user_preferences
                }
            }
            
        except Exception as e:
            logger.error(f"用户历史处理失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_images(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理图像分析"""
        try:
            images = context.get('images', [])
            if not images:
                return {
                    'success': True,
                    'context_updates': {'image_analysis': []}
                }
            
            image_results = []
            
            for image_info in images:
                # 确定分析类型（基于用户输入推测）
                user_input = context['user_input'].lower()
                if '舌' in user_input:
                    analysis_type = 'tongue'
                elif '脉' in user_input:
                    analysis_type = 'pulse'
                elif '皮肤' in user_input:
                    analysis_type = 'skin'
                else:
                    analysis_type = 'general'
                
                # 执行图像分析
                analysis_result = self.image_analysis_processor.analyze_medical_image(
                    image_data=image_info['data'],
                    image_type='jpg',  # 默认类型，可以通过其他方式确定
                    analysis_type=analysis_type,
                    additional_context=context['user_input']
                )
                
                image_results.append(analysis_result)
            
            return {
                'success': True,
                'context_updates': {'image_analysis': image_results}
            }
            
        except Exception as e:
            logger.error(f"图像处理失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_knowledge_retrieval(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理知识检索"""
        try:
            user_input = context['user_input']
            user_context = context.get('user_history', {})
            
            # 执行知识检索
            retrieval_result = self.knowledge_retrieval_processor.retrieve_relevant_knowledge(
                query=user_input,
                user_context=user_context,
                top_k=5
            )
            
            return {
                'success': True,
                'context_updates': {'retrieved_knowledge': retrieval_result}
            }
            
        except Exception as e:
            logger.error(f"知识检索失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_ai_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理AI响应生成"""
        try:
            user_input = context['user_input']
            
            # 确定响应类型
            response_type = self._determine_response_type(user_input, context)
            
            # 构建LLM上下文
            llm_context = {
                'retrieved_knowledge': context.get('retrieved_knowledge', {}),
                'user_history': context.get('user_history', {}),
                'image_analysis': context.get('image_analysis', []),
                'symptoms': context.get('additional_context', {}).get('symptoms', [])
            }
            
            # 生成AI响应
            ai_result = self.llm_integration_processor.generate_ai_response(
                query=user_input,
                context=llm_context,
                response_type=response_type
            )
            
            if ai_result['success']:
                return {
                    'success': True,
                    'context_updates': {
                        'ai_response_raw': ai_result['response'],
                        'response_type': response_type,
                        'response_metadata': ai_result['metadata'],
                        'confidence_score': ai_result['quality_score']
                    }
                }
            else:
                return {'success': False, 'error': ai_result['error_message']}
            
        except Exception as e:
            logger.error(f"AI响应生成失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_safety_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理安全检查"""
        try:
            if not self.enable_safety_check:
                return {
                    'success': True,
                    'context_updates': {
                        'safety_status': {'safety_passed': True, 'checks_performed': []}
                    }
                }
            
            ai_response = context.get('ai_response_raw', '')
            
            # 构建用户档案（基于历史和偏好）
            user_profile = self._build_user_safety_profile(context)
            
            # 执行安全检查
            safety_result = self.medical_safety_processor.perform_comprehensive_safety_check(
                prescription_text=ai_response,
                user_profile=user_profile
            )
            
            return {
                'success': True,
                'context_updates': {'safety_status': safety_result}
            }
            
        except Exception as e:
            logger.error(f"安全检查失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _post_process_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """后处理响应"""
        try:
            ai_response = context.get('ai_response_raw', '')
            safety_status = context.get('safety_status', {})
            
            # 根据安全检查结果调整响应
            if not safety_status.get('safety_passed', True):
                # 添加安全警告
                safety_warnings = '\\n\\n**安全提醒**: ' + '; '.join(
                    safety_status.get('recommendations', ['请在专业医师指导下用药'])
                )
                ai_response += safety_warnings
            
            # 添加个性化内容（基于用户偏好）
            user_preferences = context.get('user_preferences', {})
            if user_preferences.get('include_lifestyle_advice', True):
                # 可以添加生活建议等个性化内容
                pass
            
            # 格式化最终响应
            final_response = self._format_final_response(ai_response, context)
            
            return {
                'success': True,
                'context_updates': {'final_response': final_response}
            }
            
        except Exception as e:
            logger.error(f"响应后处理失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _determine_response_type(self, user_input: str, context: Dict[str, Any]) -> str:
        """确定响应类型"""
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in ['处方', '药方', '吃什么药']):
            return 'prescription_generation'
        elif any(keyword in user_input_lower for keyword in ['症状', '不舒服', '疼痛']):
            return 'symptom_analysis'
        elif any(keyword in user_input_lower for keyword in ['如何调理', '生活', '饮食']):
            return 'lifestyle_advice'
        elif context.get('user_history', {}).get('recent_history'):
            return 'follow_up'
        else:
            return 'tcm_diagnosis'
    
    def _build_user_safety_profile(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """构建用户安全档案"""
        profile = {}
        
        # 从用户历史推测信息
        user_history = context.get('user_history', {})
        user_pattern = user_history.get('user_pattern', {})
        
        # 从历史咨询推测年龄组（简化逻辑）
        consultation_frequency = user_pattern.get('consultation_frequency', 0)
        if consultation_frequency > 1.0:
            profile['elderly'] = True  # 高频咨询可能是老年人
        
        # 从额外上下文获取信息
        additional_context = context.get('additional_context', {})
        if 'user_profile' in additional_context:
            profile.update(additional_context['user_profile'])
        
        return profile
    
    def _format_final_response(self, response: str, context: Dict[str, Any]) -> str:
        """格式化最终响应"""
        # 基本清理和格式化
        formatted_response = response.strip()
        
        # 添加处理时间戳（如果需要）
        if context.get('user_preferences', {}).get('include_timestamps'):
            timestamp_note = f"\\n\\n---\\n*处理时间: {get_current_timestamp_iso()}*"
            formatted_response += timestamp_note
        
        return formatted_response
    
    def _save_conversation_record(self, conversation_id: str, user_id: str, 
                                 user_input: str, ai_response: str, 
                                 processing_context: Dict[str, Any]) -> bool:
        """保存对话记录"""
        try:
            # 提取关键信息用于存储
            response_type = processing_context.get('response_type', 'general')
            confidence_score = processing_context.get('confidence_score', 0.0)
            safety_passed = processing_context.get('safety_status', {}).get('safety_passed', True)
            
            # 构建存储数据
            conversation_data = {
                'conversation_id': conversation_id,
                'user_id': user_id,
                'user_input': user_input,
                'ai_response': ai_response,
                'response_type': response_type,
                'confidence_score': confidence_score,
                'safety_passed': safety_passed,
                'created_at': get_current_timestamp_iso(),
                'processing_metadata': {
                    'knowledge_items_count': len(processing_context.get('retrieved_knowledge', {}).get('retrieved_items', [])),
                    'images_processed': len(processing_context.get('image_analysis', [])),
                    'safety_checks_performed': len(processing_context.get('safety_status', {}).get('checks_performed', []))
                }
            }
            
            # 保存到数据库
            insert_query = """
            INSERT INTO conversations 
            (conversation_id, user_id, user_input, ai_response, response_type, 
             confidence_score, safety_passed, processing_metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            db_manager = self.services.get('db_manager')
            result = db_manager.execute_query(
                insert_query,
                (
                    conversation_data['conversation_id'],
                    conversation_data['user_id'],
                    conversation_data['user_input'],
                    conversation_data['ai_response'],
                    conversation_data['response_type'],
                    conversation_data['confidence_score'],
                    conversation_data['safety_passed'],
                    conversation_data['processing_metadata'],
                    conversation_data['created_at']
                )
            )
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"保存对话记录失败: {e}")
            return False
    
    def _cache_response(self, user_input: str, user_id: str, response: str):
        """缓存响应"""
        try:
            if not self.cache_service:
                return
            
            cache_key = f"chat_response:{user_id}:{hash(user_input.lower().strip())}"
            cache_ttl = self.config.get('response_cache_ttl', 3600)  # 默认1小时
            
            self.cache_service.set(cache_key, response, ttl=cache_ttl)
            
        except Exception as e:
            logger.error(f"缓存响应失败: {e}")
    
    def _format_cached_response(self, cache_result: Dict[str, Any], 
                               conversation_id: str) -> Dict[str, Any]:
        """格式化缓存响应"""
        return create_success_response({
            'conversation_id': conversation_id,
            'response': cache_result['response'],
            'from_cache': True,
            'cache_key': cache_result['cache_key'],
            'metadata': {
                'processing_time': 0.001,  # 缓存响应几乎无处理时间
                'source': 'cache'
            }
        })