#!/usr/bin/env python3
"""
统一问诊服务模块
为智能工作流程和原系统提供完全相同的AI问诊功能
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.append('/opt/tcm-ai')

# 核心依赖导入
from core.doctor_system.tcm_doctor_personas import PersonalizedTreatmentGenerator
from core.cache_system.intelligent_cache_system import IntelligentCacheSystem
from core.prescription.prescription_checker import PrescriptionSafetyChecker
from core.conversation.conversation_state_manager import conversation_state_manager, ConversationStage
from core.conversation.conversation_analyzer import ConversationAnalyzer
from config.settings import PATHS, AI_CONFIG

logger = logging.getLogger(__name__)

@dataclass
class ConsultationRequest:
    """问诊请求"""
    message: str
    conversation_id: str
    selected_doctor: str
    conversation_history: List[Dict[str, str]] = None
    patient_id: Optional[str] = None
    has_images: bool = False

@dataclass
class ConsultationResponse:
    """问诊响应"""
    reply: str
    conversation_id: str
    doctor_name: str
    contains_prescription: bool
    prescription_data: Optional[Dict] = None
    confidence_score: float = 0.0
    processing_time: float = 0.0
    stage: str = "inquiry"  # inquiry, diagnosis, prescription
    # 新增对话状态相关字段
    conversation_active: bool = True
    should_end: bool = False
    end_reason: str = ""
    progress_info: Optional[Dict] = None
    stage_guidance: Optional[Dict] = None
    requires_confirmation: bool = False

class UnifiedConsultationService:
    """统一问诊服务"""
    
    def __init__(self):
        """初始化统一问诊服务"""
        try:
            # 医生人格系统
            self.persona_generator = PersonalizedTreatmentGenerator()
            
            # 智能缓存系统
            cache_db_path = str(PATHS['data_dir'] / 'intelligent_cache.db')
            self.cache_system = IntelligentCacheSystem(cache_db_path)
            
            # 处方安全检查器
            self.safety_checker = PrescriptionSafetyChecker()
            
            # 对话状态管理器
            self.state_manager = conversation_state_manager
            
            # 对话分析器
            self.analyzer = ConversationAnalyzer()
            
            # AI配置
            self.ai_model = AI_CONFIG.get("main_model", "qwen-turbo")
            self.ai_timeout = AI_CONFIG.get("timeout", 40.0)
            
            # 医疗安全提示词
            self.medical_safety_prompt = self._get_medical_safety_prompt()
            
            logger.info("统一问诊服务初始化完成")
            
        except Exception as e:
            logger.error(f"统一问诊服务初始化失败: {e}")
            raise
    
    def _get_medical_safety_prompt(self) -> str:
        """获取医疗安全提示词"""
        return """
**【严格医疗安全规则】**

1. **症状描述严格限制**：
   - 绝对禁止添加、推测、编造患者未明确描述的任何症状细节
   - 绝对禁止从"便秘"推测出"大便干结如栗，数日一行"
   - 只能使用患者确切的原始表述

2. **舌象脉象信息严格限制**：
   - 绝对禁止在没有患者上传舌象图片时描述任何具体的舌象特征
   - 绝对禁止编造任何脉象描述
   - 如无图像和患者描述，写"未见舌象脉象信息"

3. **西药过滤**：
   - 严禁推荐任何西药成分
   - 只能使用中药材和经典方剂
   - 如发现西药成分立即过滤

4. **处方责任声明**：
   - 所有处方建议必须包含"本处方为AI预诊建议，请务必咨询专业中医师后使用"

违反以上任何一条都是严重的医疗安全事故！
"""
    
    async def process_consultation(self, request: ConsultationRequest) -> ConsultationResponse:
        """处理问诊请求"""
        start_time = datetime.now()
        
        try:
            # 1. 对话状态管理
            conversation_state = await self._manage_conversation_state(request)
            if not conversation_state:
                return self._create_error_response(request, start_time, "对话状态初始化失败")
            
            # 2. 检查超时和结束条件
            timeout_check = self.state_manager.check_timeout(request.conversation_id)
            if timeout_check[0]:  # 已超时
                return self._create_end_response(request, start_time, timeout_check[1])
            
            # 3. 分析用户消息
            user_analysis = self.analyzer.analyze_user_message(
                request.message, 
                conversation_state.current_stage,
                conversation_state.turn_count,
                request.conversation_history or []
            )
            
            # 4. 检查是否应该结束对话
            if user_analysis.should_end:
                self.state_manager.end_conversation(
                    request.conversation_id,
                    user_analysis.end_type,
                    user_analysis.end_reason
                )
                return self._create_end_response(request, start_time, user_analysis.end_reason)
            
            # 5. 更新症状收集
            if user_analysis.extracted_symptoms:
                self.state_manager.update_symptoms(request.conversation_id, user_analysis.extracted_symptoms)
            
            # 6. 缓存检查
            cached_response = await self._check_cache(request)
            if cached_response:
                return self._enrich_response_with_state(cached_response, conversation_state)
            
            # 7. 生成医生人格提示词
            persona_prompt = self._generate_doctor_persona_prompt(request, conversation_state)
            
            # 8. 构建完整的消息上下文
            messages = self._build_message_context(request, persona_prompt)
            
            # 9. 调用AI生成响应
            ai_response = await self._call_ai_model(messages)
            
            # 10. 分析AI响应
            ai_analysis = self.analyzer.analyze_ai_response(ai_response, conversation_state.current_stage)
            
            # 11. 安全检查和后处理
            processed_response = await self._post_process_response(ai_response, request, ai_analysis)
            
            # 12. 更新对话状态
            await self._update_conversation_state(request, user_analysis, ai_analysis, processed_response)
            
            # 13. 缓存响应
            await self._cache_response(request, processed_response)
            
            # 14. 构建最终响应
            final_response = self._create_final_response(request, processed_response, start_time, conversation_state)
            
            logger.info(f"问诊处理完成: {request.selected_doctor}, 用时: {final_response.processing_time:.2f}s")
            return final_response
            
        except Exception as e:
            logger.error(f"问诊处理失败: {e}")
            return self._create_error_response(request, start_time, str(e))
    
    def _generate_doctor_persona_prompt_old(self, request: ConsultationRequest) -> str:
        """生成医生人格提示词"""
        try:
            # 使用原系统的人格生成器
            persona_prompt = self.persona_generator.generate_persona_prompt(
                doctor_name=request.selected_doctor,
                user_query=request.message,
                knowledge_context="",  # 知识检索暂时留空
                conversation_history=request.conversation_history or []
            )
            
            if not persona_prompt:
                # 备用通用提示词
                persona_prompt = self._get_default_tcm_prompt(request.selected_doctor)
            
            return persona_prompt
            
        except Exception as e:
            logger.warning(f"生成医生人格提示词失败: {e}")
            return self._get_default_tcm_prompt(request.selected_doctor)
    
    def _get_default_tcm_prompt(self, doctor_name: str) -> str:
        """获取默认中医提示词"""
        doctor_info = {
            "zhang_zhongjing": {"name": "张仲景", "school": "伤寒派", "method": "六经辨证"},
            "ye_tianshi": {"name": "叶天士", "school": "温病派", "method": "卫气营血辨证"},
            "li_dongyuan": {"name": "李东垣", "school": "脾胃派", "method": "脾胃调理"},
            "zhu_danxi": {"name": "朱丹溪", "school": "滋阴派", "method": "滋阴降火"},
            "liu_duzhou": {"name": "刘渡舟", "school": "经方派", "method": "经方运用"},
            "zheng_qin_an": {"name": "郑钦安", "school": "扶阳派", "method": "扶阳抑阴"}
        }
        
        info = doctor_info.get(doctor_name, {"name": "中医专家", "school": "综合", "method": "辨证论治"})
        
        return f"""
# 医生人格设定
你现在是一位遵循{info['name']}思想的资深中医师，属于{info['school']}。

## 诊疗方法
采用{info['method']}为主的诊疗思路，结合四诊合参，详细问诊。

## 问诊原则
1. **循序渐进**：从主症到兼症，从现在到既往
2. **四诊合参**：望闻问切，全面了解
3. **个性化问诊**：根据患者回答深入追问
4. **适时开方**：信息充足时给出具体治疗方案

{self.medical_safety_prompt}

请以专业、耐心、细致的态度进行问诊。
"""
    
    def _build_message_context(self, request: ConsultationRequest, persona_prompt: str) -> List[Dict[str, str]]:
        """构建消息上下文"""
        messages = [{"role": "system", "content": persona_prompt}]
        
        # 添加对话历史
        if request.conversation_history:
            messages.extend(request.conversation_history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": request.message})
        
        return messages
    
    async def _call_ai_model(self, messages: List[Dict[str, str]]) -> str:
        """调用AI模型"""
        try:
            import dashscope
            from http import HTTPStatus
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    dashscope.Generation.call,
                    model=self.ai_model,
                    messages=messages,
                    result_format='message'
                ),
                timeout=self.ai_timeout
            )
            
            if response.status_code == HTTPStatus.OK and response.output and response.output.choices:
                return response.output.choices[0]['message']['content']
            else:
                raise Exception(f"AI调用失败: {getattr(response, 'message', 'Unknown')}")
                
        except asyncio.TimeoutError:
            raise Exception(f"AI调用超时 ({self.ai_timeout}秒)")
        except Exception as e:
            raise Exception(f"AI调用异常: {str(e)}")
    
    async def _post_process_response(self, ai_response: str, request: ConsultationRequest) -> Dict[str, Any]:
        """后处理AI响应"""
        try:
            # 安全检查 - 使用简化的安全检查
            safety_result = {"is_safe": True, "issues": []}
            
            # 检查是否包含危险内容
            dangerous_keywords = ["西药", "化学药物", "抗生素", "激素"]
            for keyword in dangerous_keywords:
                if keyword in ai_response:
                    safety_result = {
                        "is_safe": False,
                        "issues": [f"响应包含不当内容: {keyword}"]
                    }
                    logger.warning(f"AI响应安全检查失败: 包含{keyword}")
                    break
            
            # 检查是否包含处方
            contains_prescription = self._contains_prescription(ai_response)
            
            # 提取处方数据（如果有）
            prescription_data = None
            if contains_prescription:
                prescription_data = self._extract_prescription_data(ai_response)
            
            # 判断问诊阶段
            stage = self._determine_consultation_stage(ai_response, request.conversation_history or [])
            
            return {
                "content": ai_response,
                "contains_prescription": contains_prescription,
                "prescription_data": prescription_data,
                "stage": stage,
                "confidence": 0.85,  # 可以根据实际情况调整
                "safety_check": safety_result
            }
            
        except Exception as e:
            logger.error(f"响应后处理失败: {e}")
            return {
                "content": ai_response,
                "contains_prescription": False,
                "stage": "inquiry",
                "confidence": 0.5
            }
    
    def _contains_prescription(self, text: str) -> bool:
        """检查是否包含完整处方（非临时建议）"""
        # 明确的处方关键词
        prescription_keywords = [
            '处方如下', '方剂组成', '药物组成', '具体方药',
            '方解', '君药', '臣药', '佐药', '使药',
            '处方方案', '治疗方案', '用药方案',
            '【君药】', '【臣药】', '【佐药】', '【使药】'
        ]
        
        # 临时建议关键词（这些不算完整处方）
        temporary_keywords = [
            '初步处方建议', '待确认', '若您能提供', '请补充',
            '需要了解', '建议进一步', '完善信息后', '详细描述',
            '暂拟方药', '初步考虑', '待详诊后', '待补充',
            '补充舌象', '舌象信息后', '脉象信息后', '上传舌象',
            '提供舌象', '确认处方', '后确认', '暂拟处方'
        ]
        
        # 如果包含临时建议关键词，不认为是完整处方
        if any(keyword in text for keyword in temporary_keywords):
            return False
            
        # 检查是否包含处方关键词
        has_prescription_keywords = any(keyword in text for keyword in prescription_keywords)
        
        # 检查是否包含具体剂量信息
        import re
        has_dosage_pattern = bool(re.search(r'\d+[克g]\s*[，,]', text)) or bool(re.search(r'[\u4e00-\u9fa5]+\s*\d+[克g]', text))
        
        # 只有同时包含处方关键词和具体剂量才认为是完整处方
        return has_prescription_keywords and has_dosage_pattern
    
    def _extract_prescription_data(self, text: str) -> Optional[Dict]:
        """提取处方数据"""
        # 这里可以实现更复杂的处方解析逻辑
        if self._contains_prescription(text):
            return {
                "has_prescription": True,
                "extracted_at": datetime.now().isoformat(),
                "source": "ai_generated"
            }
        return None
    
    def _determine_consultation_stage(self, response: str, history: List[Dict]) -> str:
        """判断问诊阶段"""
        # 检查是否包含完整处方
        if self._contains_prescription(response):
            return "prescription"
        
        # 检查是否是临时建议阶段
        temporary_keywords = [
            '初步处方建议', '待确认', '若您能提供', '请补充',
            '需要了解', '建议进一步', '完善信息后', '详细描述',
            '暂拟方药', '初步考虑', '待详诊后', '待补充',
            '补充舌象', '舌象信息后', '脉象信息后', '上传舌象',
            '提供舌象', '确认处方', '后确认', '暂拟处方'
        ]
        
        if any(keyword in response for keyword in temporary_keywords):
            return "interim_advice"  # 临时建议阶段
        
        # 根据对话轮数判断
        if len(history) > 6:  # 多轮对话后，可能进入诊断阶段
            return "diagnosis"
        elif len(history) > 2:  # 中等对话轮数，详细问诊阶段
            return "detailed_inquiry"
        else:
            return "inquiry"  # 初始问诊阶段
    
    async def _check_cache(self, request: ConsultationRequest) -> Optional[ConsultationResponse]:
        """检查缓存"""
        try:
            if not self.cache_system:
                return None
                
            # 简化的缓存键
            cache_key = f"{request.selected_doctor}_{request.message[:100]}"
            
            # 这里可以实现更复杂的缓存逻辑
            return None
            
        except Exception as e:
            logger.warning(f"缓存检查失败: {e}")
            return None
    
    async def _cache_response(self, request: ConsultationRequest, response: Dict):
        """缓存响应"""
        try:
            if not self.cache_system:
                return
                
            # 这里可以实现缓存逻辑
            pass
            
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")
    
    # 新增对话状态管理相关方法
    async def _manage_conversation_state(self, request: ConsultationRequest):
        """管理对话状态"""
        try:
            # 获取或创建对话状态
            state = self.state_manager.get_conversation_state(request.conversation_id)
            
            if not state:
                # 创建新对话状态
                user_id = request.patient_id or "guest"
                state = self.state_manager.create_conversation(
                    request.conversation_id, 
                    user_id, 
                    request.selected_doctor
                )
            
            # 增加对话轮数
            self.state_manager.increment_turn(request.conversation_id)
            
            return state
            
        except Exception as e:
            logger.error(f"对话状态管理失败: {e}")
            return None
    
    def _generate_doctor_persona_prompt(self, request: ConsultationRequest, state=None) -> str:
        """生成医生人格提示词（增强版）"""
        try:
            # 基础人格生成
            base_prompt = self.persona_generator.generate_persona_prompt(
                doctor_name=request.selected_doctor,
                user_query=request.message,
                knowledge_context="",
                conversation_history=request.conversation_history or []
            )
            
            if not base_prompt:
                base_prompt = self._get_default_tcm_prompt(request.selected_doctor)
            
            # 添加对话状态上下文
            if state:
                stage_context = self._get_stage_specific_context(state.current_stage, state)
                base_prompt += f"\n\n## 当前对话状态\n{stage_context}"
            
            return base_prompt
            
        except Exception as e:
            logger.warning(f"生成医生人格提示词失败: {e}")
            return self._get_default_tcm_prompt(request.selected_doctor)
    
    def _get_stage_specific_context(self, stage: ConversationStage, state) -> str:
        """获取阶段特定的上下文"""
        context_map = {
            ConversationStage.INQUIRY: f"当前是初始问诊阶段（第{state.turn_count}轮），请重点收集患者的主要症状和基本情况。",
            ConversationStage.DETAILED_INQUIRY: f"当前是详细问诊阶段（第{state.turn_count}轮），请深入了解症状细节，已收集症状：{', '.join(state.symptoms_collected[:5])}。",
            ConversationStage.INTERIM_ADVICE: f"当前是临时建议阶段（第{state.turn_count}轮），给出初步建议但需要更多信息确认。",
            ConversationStage.DIAGNOSIS: f"当前是诊断阶段（第{state.turn_count}轮），请进行证候分析，已收集{len(state.symptoms_collected)}个症状。",
            ConversationStage.PRESCRIPTION: f"当前是处方阶段（第{state.turn_count}轮），请给出完整的治疗方案。",
            ConversationStage.PRESCRIPTION_CONFIRM: f"当前是处方确认阶段，等待患者确认处方方案。"
        }
        
        return context_map.get(stage, f"当前对话阶段：{stage.value}，第{state.turn_count}轮。")
    
    async def _update_conversation_state(self, request, user_analysis, ai_analysis, processed_response):
        """更新对话状态"""
        try:
            # 基于分析结果建议新阶段
            suggested_stage = None
            confidence = 0.0
            reason = ""
            
            if ai_analysis.suggested_stage:
                suggested_stage = ai_analysis.suggested_stage
                confidence = ai_analysis.confidence
                reason = "基于AI响应内容分析"
            elif user_analysis.suggested_stage:
                suggested_stage = user_analysis.suggested_stage
                confidence = user_analysis.confidence
                reason = "基于用户消息分析"
            
            # 更新阶段
            if suggested_stage and confidence > 0.5:
                self.state_manager.update_stage(
                    request.conversation_id,
                    suggested_stage,
                    reason,
                    confidence
                )
            
            # 更新诊断置信度
            if ai_analysis.diagnosis_confidence > 0:
                state = self.state_manager.get_conversation_state(request.conversation_id)
                if state:
                    state.diagnosis_confidence = ai_analysis.diagnosis_confidence
                    self.state_manager._save_state(state)
            
        except Exception as e:
            logger.error(f"更新对话状态失败: {e}")
    
    def _create_final_response(self, request, processed_response, start_time, conversation_state) -> ConsultationResponse:
        """创建最终响应"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 获取进度信息和阶段引导
        progress_info = self.state_manager.get_conversation_progress(request.conversation_id)
        stage_guidance = self.state_manager.get_stage_guidance(request.conversation_id)
        
        # 判断是否需要确认
        requires_confirmation = (
            conversation_state.current_stage == ConversationStage.PRESCRIPTION and
            processed_response.get("contains_prescription", False)
        )
        
        return ConsultationResponse(
            reply=processed_response["content"],
            conversation_id=request.conversation_id,
            doctor_name=request.selected_doctor,
            contains_prescription=processed_response.get("contains_prescription", False),
            prescription_data=processed_response.get("prescription_data"),
            confidence_score=processed_response.get("confidence", 0.8),
            processing_time=processing_time,
            stage=conversation_state.current_stage.value,
            conversation_active=conversation_state.is_active,
            progress_info=progress_info,
            stage_guidance=stage_guidance,
            requires_confirmation=requires_confirmation
        )
    
    def _create_error_response(self, request, start_time, error_msg) -> ConsultationResponse:
        """创建错误响应"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ConsultationResponse(
            reply=f"抱歉，AI医生暂时无法回应，请稍后重试。错误信息：{error_msg}",
            conversation_id=request.conversation_id,
            doctor_name=request.selected_doctor,
            contains_prescription=False,
            processing_time=processing_time,
            conversation_active=False
        )
    
    def _create_end_response(self, request, start_time, end_reason) -> ConsultationResponse:
        """创建结束响应"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        end_messages = {
            "用户表示结束": "感谢您的咨询，如有其他问题随时联系。祝您身体健康！",
            "检测到紧急情况": "检测到紧急情况，建议您立即前往医院急诊科就诊，切勿延误！",
            "会话已超时": "会话已超时，感谢您的咨询。如需继续问诊，请重新开始。",
            "多次无响应": "由于长时间无响应，会话已结束。如需继续问诊，请重新开始。"
        }
        
        reply = end_messages.get(end_reason, "对话已结束，感谢您的咨询。")
        
        return ConsultationResponse(
            reply=reply,
            conversation_id=request.conversation_id,
            doctor_name=request.selected_doctor,
            contains_prescription=False,
            processing_time=processing_time,
            conversation_active=False,
            should_end=True,
            end_reason=end_reason
        )
    
    def _enrich_response_with_state(self, cached_response, conversation_state):
        """用状态信息丰富缓存响应"""
        if hasattr(cached_response, 'progress_info'):
            cached_response.progress_info = self.state_manager.get_conversation_progress(
                cached_response.conversation_id
            )
            cached_response.stage_guidance = self.state_manager.get_stage_guidance(
                cached_response.conversation_id
            )
        return cached_response
    
    async def _post_process_response(self, ai_response: str, request: ConsultationRequest, ai_analysis=None) -> Dict[str, Any]:
        """后处理AI响应（增强版）"""
        try:
            # 基础安全检查
            safety_result = {"is_safe": True, "issues": []}
            
            dangerous_keywords = ["西药", "化学药物", "抗生素", "激素"]
            for keyword in dangerous_keywords:
                if keyword in ai_response:
                    safety_result = {
                        "is_safe": False,
                        "issues": [f"响应包含不当内容: {keyword}"]
                    }
                    logger.warning(f"AI响应安全检查失败: 包含{keyword}")
                    break
            
            # 使用分析结果
            contains_prescription = ai_analysis.has_prescription_keywords if ai_analysis else self._contains_prescription(ai_response)
            prescription_data = None
            
            if contains_prescription:
                prescription_data = self._extract_prescription_data(ai_response)
            
            # 基于状态确定阶段
            stage = "inquiry"  # 默认
            if ai_analysis and ai_analysis.suggested_stage:
                stage = ai_analysis.suggested_stage.value
            elif contains_prescription:
                stage = "prescription"
            
            return {
                "content": ai_response,
                "contains_prescription": contains_prescription,
                "prescription_data": prescription_data,
                "stage": stage,
                "confidence": ai_analysis.diagnosis_confidence if ai_analysis else 0.8,
                "safety_check": safety_result
            }
            
        except Exception as e:
            logger.error(f"响应后处理失败: {e}")
            return {
                "content": ai_response,
                "contains_prescription": False,
                "stage": "inquiry",
                "confidence": 0.5
            }

# 全局服务实例
_consultation_service = None

def get_consultation_service() -> UnifiedConsultationService:
    """获取统一问诊服务实例（单例模式）"""
    global _consultation_service
    if _consultation_service is None:
        _consultation_service = UnifiedConsultationService()
    return _consultation_service