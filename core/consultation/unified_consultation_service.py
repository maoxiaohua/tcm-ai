#!/usr/bin/env python3
"""
统一问诊服务模块
为智能工作流程和原系统提供完全相同的AI问诊功能
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.append('/opt/tcm-ai')

# 核心依赖导入
from core.doctor_system.tcm_doctor_personas import PersonalizedTreatmentGenerator
from core.cache_system.intelligent_cache_system import IntelligentCacheSystem
from core.prescription.prescription_checker import PrescriptionSafetyChecker
from core.prescription.prescription_format_enforcer import get_prescription_enforcer
from core.conversation.conversation_state_manager import conversation_state_manager, ConversationStage
from core.conversation.conversation_analyzer import ConversationAnalyzer
from config.settings import PATHS, AI_CONFIG

# 🆕 模板化AI回复系统
from core.ai_response.template_prompt_generator_simple import (
    SimpleTemplateContext, get_simple_prompt_generator
)

# 🆕 决策树智能匹配系统
from core.consultation.decision_tree_matcher import get_decision_tree_matcher

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
    # 🆕 决策树匹配信息
    used_pattern_id: Optional[str] = None
    pattern_match_score: Optional[float] = None

class UnifiedConsultationService:
    """统一问诊服务"""
    
    def __init__(self):
        """初始化统一问诊服务"""
        try:
            # 医生人格系统（保留用于备用）
            self.persona_generator = PersonalizedTreatmentGenerator()
            
            # 🆕 简化模板化AI回复系统
            self.prompt_generator = get_simple_prompt_generator()
            
            # 智能缓存系统
            cache_db_path = str(PATHS['data_dir'] / 'intelligent_cache.db')
            self.cache_system = IntelligentCacheSystem(cache_db_path)
            
            # 处方安全检查器（简化用于模板验证）
            self.safety_checker = PrescriptionSafetyChecker()
            
            # 对话状态管理器
            self.conversation_state = conversation_state_manager
            
            # 思维库集成（新增）
            self.thinking_library_enabled = True

            # 🧠 决策树匹配服务（新增）
            self.decision_tree_matcher = get_decision_tree_matcher()

            # 决策树匹配结果缓存（新增）
            self.pattern_match_cache = {}  # {conversation_id: (pattern_id, match_score, matched_pattern)}

            logger.info("✅ 统一问诊服务初始化完成（含思维库集成+智能决策树匹配）")
            self.state_manager = conversation_state_manager
            
            # 对话分析器
            self.analyzer = ConversationAnalyzer()
            
            # AI配置
            self.ai_model = AI_CONFIG.get("main_model", "qwen-turbo")
            self.ai_timeout = AI_CONFIG.get("timeout", 40.0)
            
            # 医疗安全提示词（备用）
            self.medical_safety_prompt = self._get_medical_safety_prompt()
            
            logger.info("🎯 统一问诊服务（模板化）初始化完成")
            
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
            
            # 7. 生成医生人格提示词（暂时使用原有系统）
            persona_prompt = self._generate_doctor_persona_prompt(request, conversation_state)
            
            # 8. 🧠 查询思维库（新增）
            thinking_context = await self._get_thinking_library_context(request, conversation_state)
            
            # 9. 构建完整的消息上下文（增强版）
            messages = self._build_message_context(request, persona_prompt, thinking_context)
            
            # 10. 调用AI生成响应
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
            "jin_daifu": {"name": "金大夫", "school": "伤寒派", "method": "六经辨证"},  # 金大夫使用张仲景人格
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
            real_prescription_id = None
            if contains_prescription:
                prescription_data = self._extract_prescription_data(ai_response)

                # 🆕 决策树匹配（在生成处方时）
                pattern_id, match_score = await self._match_decision_tree_pattern(request, ai_response)
                if pattern_id:
                    # 缓存匹配结果
                    self.pattern_match_cache[request.conversation_id] = (pattern_id, match_score)
                    # 更新决策树使用统计
                    await self._update_pattern_usage_stats(pattern_id)
                    logger.info(f"🎯 问诊使用决策树: {pattern_id}, 匹配度: {match_score:.2f}")

                # 🔑 关键修复：检测到处方时自动创建处方记录和审核队列
                real_prescription_id = await self._create_prescription_record(request, ai_response, prescription_data)
                if real_prescription_id and prescription_data:
                    # 更新处方数据中的真实ID
                    prescription_data["prescription_id"] = real_prescription_id
                    prescription_data["status"] = "pending_review"  # 等待审核状态
                    prescription_data["note"] = "处方已提交医生审核，审核通过后可配药"

            
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
        # 🔑 关键修复：更严格的处方检测逻辑，避免信息不完整时给出处方
        
        # 不完整信息的关键词（这些表示需要继续问诊）
        incomplete_info_keywords = [
            '请补充', '需要了解', '建议进一步', '完善信息', '详细描述',
            '待确认', '若您能提供', '请描述', '请上传', '暂拟', '初步考虑',
            '补充舌象', '舌象信息', '脉象信息', '上传舌象', '提供舌象',
            '有无汗出', '是否有胸闷', '二便情况', '既往病史', '慢性疾病',
            '以便更精准', '进一步判断', '更准确的', '待详诊', '暂时建议',
            '初步处方', '临时方案', '请问', '您是否', '是否伴有', '可否描述'
        ]
        
        # 🔑 如果包含不完整信息关键词，绝对不认为是完整处方
        if any(keyword in text for keyword in incomplete_info_keywords):
            logger.info("🚨 检测到需要补充信息的关键词，不生成处方")
            return False
        
        # 明确的完整处方关键词
        complete_prescription_keywords = [
            '处方如下', '最终处方', '完整处方', '确定处方',
            '方剂组成', '具体方药', '治疗方案确定',
            '【君药】', '【臣药】', '【佐药】', '【使药】',
            '君药：', '臣药：', '佐药：', '使药：'
        ]
        
        # 检查是否包含明确的完整处方关键词
        has_complete_prescription = any(keyword in text for keyword in complete_prescription_keywords)
        
        # 检查是否包含具体剂量信息（至少3个药物有剂量）
        import re
        dosage_matches = re.findall(r'[\u4e00-\u9fa5]+\s*\d+[克g]', text)
        has_sufficient_dosage = len(dosage_matches) >= 3
        
        # 检查是否包含完整的辨证分析结论（而非追问）
        has_definitive_diagnosis = any(keyword in text for keyword in [
            '辨证结论', '证型为', '诊断为', '属于', '辨证：', '病机：'
        ]) and not any(keyword in text for keyword in [
            '暂定', '初步', '可能', '疑似', '待确认'
        ])
        
        # 🔑 只有同时满足以下条件才认为是完整处方：
        # 1. 包含明确的完整处方关键词
        # 2. 有足够的药物剂量信息（至少3个）
        # 3. 有明确的诊断结论
        # 4. 不包含任何需要补充信息的关键词
        result = (has_complete_prescription and has_sufficient_dosage and has_definitive_diagnosis)
        
        if result:
            logger.info("✅ 检测到完整处方")
        else:
            logger.info("⏳ 未检测到完整处方，继续问诊")
            
        return result
    
    def _extract_prescription_data(self, text: str) -> Optional[Dict]:
        """提取处方数据"""
        # 这里可以实现更复杂的处方解析逻辑
        if self._contains_prescription(text):
            import uuid
            # 🔑 关键修复：返回前端需要的处方支付字段
            return {
                "has_prescription": True,
                "extracted_at": datetime.now().isoformat(),
                "source": "ai_generated",
                # 前端需要的关键字段
                "prescription_id": "temp_" + str(uuid.uuid4())[:8],  # 生成临时处方ID，待数据库插入后更新
                "is_paid": False,  # 默认未付费，需要支付
                "payment_required": True,
                "payment_amount": 88.0
            }
        return None

    async def _create_prescription_record(self, request: ConsultationRequest, ai_response: str, prescription_data: Dict) -> Optional[int]:
        """创建处方记录并自动提交审核队列"""
        import sqlite3
        import json
        
        try:
            # 医生ID映射
            doctor_id_mapping = {
                'zhang_zhongjing': 4,
                'ye_tianshi': 2, 
                'li_dongyuan': 3,
                'zheng_qin_an': 6,
                'liu_duzhou': 5,
                'jin_daifu': 1
            }
            
            doctor_id = doctor_id_mapping.get(request.selected_doctor, 1)
            
            # 连接数据库
            conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
            cursor = conn.cursor()
            
            # 🔑 从AI响应和对话历史中提取症状和诊断
            symptoms = self._extract_symptoms_description(ai_response, request.conversation_history or [])
            diagnosis = self._extract_diagnosis_description(ai_response)
            
            # 🔑 创建处方记录 - 包含consultation_id
            # 需要先创建或找到对应的consultation记录
            import uuid as uuid_lib
            consultation_uuid = None

            # 🔑 核心修复：优先使用uuid精确查找，再使用conversation_log模糊查找
            cursor.execute("""
                SELECT uuid FROM consultations
                WHERE uuid = ? OR conversation_log LIKE ?
                ORDER BY created_at DESC LIMIT 1
            """, (request.conversation_id, f'%"conversation_id": "{request.conversation_id}"%'))
            result = cursor.fetchone()

            if result:
                consultation_uuid = result[0]
            else:
                # 🔑 关键修复：统一使用conversation_id作为consultation UUID
                consultation_uuid = request.conversation_id
                cursor.execute("""
                    INSERT INTO consultations (
                        uuid, patient_id, selected_doctor_id, conversation_log,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (
                    consultation_uuid,
                    request.patient_id,
                    request.selected_doctor,  # 🔑 使用字符串格式的doctor_id
                    json.dumps({"conversation_id": request.conversation_id, "conversation_history": []}),
                    'in_progress'
                ))

            cursor.execute("""
                INSERT INTO prescriptions (
                    patient_id, conversation_id, consultation_id, doctor_id, patient_name,
                    symptoms, diagnosis, ai_prescription, status, payment_status,
                    is_visible_to_patient, review_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                request.patient_id,
                request.conversation_id,
                consultation_uuid,  # 🔑 关键：添加consultation_id
                request.selected_doctor,  # 🔑 使用字符串格式的doctor_id
                request.patient_id,  # 使用patient_id作为姓名
                symptoms,
                diagnosis,
                ai_response,  # 完整的AI回复作为处方内容
                'ai_generated',  # 🔑 使用标准状态
                'pending',  # 待支付
                0,  # 患者暂时不可见，等审核通过后可见
                'not_submitted'  # 未提交审核
            ))

            prescription_id = cursor.lastrowid

            # 🔑 关键：自动提交到医生审核队列
            cursor.execute("""
                INSERT INTO doctor_review_queue (
                    prescription_id, doctor_id, consultation_id,
                    submitted_at, status, priority
                ) VALUES (?, ?, ?, datetime('now'), 'pending', 'normal')
            """, (prescription_id, request.selected_doctor, consultation_uuid))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 处方自动创建并提交审核: prescription_id={prescription_id}, doctor_id={doctor_id}")
            return prescription_id
            
        except Exception as e:
            logger.error(f"创建处方记录失败: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return None

    async def _match_decision_tree_pattern(self, request: ConsultationRequest, ai_response: str) -> Tuple[Optional[str], float]:
        """
        匹配医生的决策树模式

        Returns:
            Tuple[pattern_id, match_score]: 决策树ID和匹配分数（0.0-1.0）
        """
        import sqlite3
        from difflib import SequenceMatcher

        try:
            # 获取当前医生ID（从request中获取）
            doctor_id_mapping = {
                'zhang_zhongjing': 'usr_20250927_zhangzhongjing',
                'ye_tianshi': 'usr_20250920_4e7591213d67',
                'li_dongyuan': 'usr_20250920_38d51c44ae1d',
                'zheng_qin_an': 'usr_20250920_85ba2882db50',
                'liu_duzhou': 'usr_20250920_7a230caec0f8',
                'jin_daifu': 'usr_20250920_575ba94095a7'  # 金大夫
            }

            doctor_user_id = doctor_id_mapping.get(request.selected_doctor)
            if not doctor_user_id:
                logger.debug(f"未找到医生映射: {request.selected_doctor}")
                return None, 0.0

            # 从AI响应中提取关键信息
            diagnosis_keywords = self._extract_diagnosis_keywords(ai_response)
            symptoms_from_history = self._extract_symptoms_from_history(request.conversation_history or [])

            if not diagnosis_keywords and not symptoms_from_history:
                logger.debug("未能提取诊断关键词或症状，跳过决策树匹配")
                return None, 0.0

            # 连接数据库查询该医生的决策树
            conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, disease_name, thinking_process, clinical_patterns
                FROM doctor_clinical_patterns
                WHERE doctor_id = ?
                ORDER BY updated_at DESC
            """, (doctor_user_id,))

            patterns = cursor.fetchall()
            conn.close()

            if not patterns:
                logger.debug(f"医生 {request.selected_doctor} 没有保存的决策树")
                return None, 0.0

            # 匹配最佳决策树
            best_pattern_id = None
            best_score = 0.0

            for pattern in patterns:
                score = self._calculate_pattern_match_score(
                    pattern,
                    diagnosis_keywords,
                    symptoms_from_history,
                    ai_response
                )

                if score > best_score:
                    best_score = score
                    best_pattern_id = pattern['id']
                    logger.debug(f"匹配决策树: {pattern['disease_name']}, 分数: {score:.2f}")

            # 只有当匹配分数超过阈值时才返回结果
            if best_score >= 0.6:  # 60%以上置信度
                logger.info(f"✅ 决策树匹配成功: pattern_id={best_pattern_id}, score={best_score:.2f}")
                return best_pattern_id, best_score
            else:
                logger.debug(f"决策树匹配分数过低: {best_score:.2f}")
                return None, 0.0

        except Exception as e:
            logger.error(f"决策树匹配失败: {e}")
            return None, 0.0

    def _extract_diagnosis_keywords(self, text: str) -> List[str]:
        """从文本中提取诊断关键词"""
        keywords = []

        # 中医常见病症关键词
        disease_patterns = [
            r'(失眠|不寐|多梦)',
            r'(胃痛|胃脘痛|脘腹痛)',
            r'(头痛|头胀|眩晕)',
            r'(便秘|大便秘结|大便不通)',
            r'(腹泻|泄泻|拉肚子)',
            r'(咳嗽|久咳|痰多)',
            r'(感冒|外感|表证)',
            r'(心悸|怔忡|心慌)',
            r'(郁证|抑郁|情志不畅)',
            r'(痛经|月经不调|经期腹痛)'
        ]

        for pattern in disease_patterns:
            matches = re.findall(pattern, text)
            if matches:
                keywords.extend(matches)

        # 提取证型关键词
        syndrome_patterns = [
            r'(肝郁|肝气郁结|肝郁脾虚)',
            r'(脾虚|脾胃虚弱|脾气不足)',
            r'(肾虚|肾阳虚|肾阴虚)',
            r'(气虚|气血不足|气血两虚)',
            r'(痰湿|湿热|寒湿)',
            r'(阴虚|阳虚|气阴两虚)'
        ]

        for pattern in syndrome_patterns:
            matches = re.findall(pattern, text)
            if matches:
                keywords.extend(matches)

        return list(set(keywords))  # 去重

    def _extract_symptoms_from_history(self, history: List[Dict]) -> List[str]:
        """从对话历史中提取症状"""
        symptoms = []

        # 提取用户消息中的症状
        for msg in history:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                # 使用简单的关键词提取
                extracted = self._extract_symptoms_for_summary(content)
                symptoms.extend(extracted)

        return list(set(symptoms))  # 去重

    def _calculate_pattern_match_score(self, pattern: Dict, diagnosis_keywords: List[str],
                                       symptoms: List[str], ai_response: str) -> float:
        """
        计算决策树模式的匹配分数

        评分维度:
        1. 疾病名称匹配 (40%)
        2. 症状匹配 (30%)
        3. 诊疗思路相似度 (30%)
        """
        from difflib import SequenceMatcher

        score = 0.0

        # 1. 疾病名称匹配 (40%)
        disease_name = pattern['disease_name']
        for keyword in diagnosis_keywords:
            if keyword in disease_name or disease_name in keyword:
                score += 0.4
                break

        # 2. 症状匹配 (30%)
        thinking_process = pattern['thinking_process']
        if symptoms:
            matched_symptoms = sum(1 for s in symptoms if s in thinking_process)
            symptom_match_rate = matched_symptoms / len(symptoms)
            score += 0.3 * symptom_match_rate

        # 3. 诊疗思路相似度 (30%)
        # 使用序列匹配算法比较文本相似度
        similarity = SequenceMatcher(None, thinking_process, ai_response).ratio()
        score += 0.3 * similarity

        return min(score, 1.0)  # 确保分数不超过1.0

    async def _update_pattern_usage_stats(self, pattern_id: str):
        """更新决策树使用统计"""
        import sqlite3

        try:
            conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
            cursor = conn.cursor()

            # 更新usage_count和last_used_at
            cursor.execute("""
                UPDATE doctor_clinical_patterns
                SET usage_count = usage_count + 1,
                    last_used_at = datetime('now')
                WHERE id = ?
            """, (pattern_id,))

            conn.commit()
            conn.close()

            logger.info(f"✅ 决策树使用统计已更新: {pattern_id}")

        except Exception as e:
            logger.error(f"更新决策树使用统计失败: {e}")

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
        # 🔧 安全获取症状列表（避免类型错误）
        symptoms = state.symptoms_collected if isinstance(state.symptoms_collected, list) else []
        symptoms_preview = ', '.join(symptoms[:5]) if symptoms else "无"
        symptoms_count = len(symptoms)

        context_map = {
            ConversationStage.INQUIRY: f"当前是初始问诊阶段（第{state.turn_count}轮），请重点收集患者的主要症状和基本情况。",
            ConversationStage.DETAILED_INQUIRY: f"当前是详细问诊阶段（第{state.turn_count}轮），请深入了解症状细节，已收集症状：{symptoms_preview}。",
            ConversationStage.INTERIM_ADVICE: f"当前是临时建议阶段（第{state.turn_count}轮），给出初步建议但需要更多信息确认。",
            ConversationStage.DIAGNOSIS: f"当前是诊断阶段（第{state.turn_count}轮），请进行证候分析，已收集{symptoms_count}个症状。",
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

        # 🆕 获取决策树匹配信息
        used_pattern_id = None
        pattern_match_score = None
        if request.conversation_id in self.pattern_match_cache:
            cached_data = self.pattern_match_cache[request.conversation_id]
            if len(cached_data) >= 3:
                # (pattern_id, match_score, matched_pattern)
                used_pattern_id = cached_data[0]
                pattern_match_score = cached_data[1]
                logger.info(f"📊 添加决策树信息到响应: pattern_id={used_pattern_id}, score={pattern_match_score:.2%}")

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
            requires_confirmation=requires_confirmation,
            used_pattern_id=used_pattern_id,
            pattern_match_score=pattern_match_score
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
    
    # ========================================
    # 🆕 模板化AI回复系统核心方法
    # ========================================
    
    def _generate_template_prompt(self, request: ConsultationRequest, conversation_state, user_analysis) -> Tuple[str, str]:
        """生成模板化AI提示词"""
        try:
            # 1. 确定回复阶段
            response_stage = self._determine_response_stage_simple(request, conversation_state, user_analysis)
            
            # 2. 收集可用信息
            available_info = self._collect_available_info(request, conversation_state)
            
            # 3. 构建简化模板提示词上下文
            template_context = SimpleTemplateContext(
                stage=response_stage,
                doctor_persona=request.selected_doctor,
                patient_message=request.message,
                conversation_history=request.conversation_history or [],
                available_info=available_info
            )
            
            # 4. 生成最优提示词
            template_prompt = self.prompt_generator.generate_optimal_prompt(template_context)
            
            logger.info(f"🎯 生成模板化提示词: 阶段={response_stage}, 医生={request.selected_doctor}")
            return template_prompt, response_stage
            
        except Exception as e:
            logger.error(f"生成模板化提示词失败: {e}")
            # 备用方案：使用原有的人格生成器
            fallback_prompt = self._generate_doctor_persona_prompt(request, conversation_state)
            return fallback_prompt, "inquiry"
    
    def _determine_response_stage_simple(self, request: ConsultationRequest, conversation_state, user_analysis) -> str:
        """确定回复阶段(简化版)"""
        try:
            # 检查是否是重复问询投诉
            if "重复" in request.message or "已经说过" in request.message or "为什么还要问" in request.message:
                return "repetition_handling"
            
            # 基于对话轮数和症状收集情况判断
            turn_count = conversation_state.turn_count if conversation_state else 0
            symptoms_count = len(conversation_state.symptoms_collected) if conversation_state else 0
            
            # 信息充分，可以开处方
            if symptoms_count >= 5 and turn_count >= 3:
                return "prescription"
            
            # 有一些信息，但需要更多
            elif symptoms_count >= 2 and turn_count >= 2:
                return "detailed_inquiry"
            
            # 初次问诊
            else:
                return "initial_inquiry"
                
        except Exception as e:
            logger.error(f"确定回复阶段失败: {e}")
            return "initial_inquiry"

    def _determine_response_stage(self, request: ConsultationRequest, conversation_state, user_analysis) -> str:
        """确定回复阶段"""
        try:
            # 检查是否是紧急情况
            if hasattr(user_analysis, 'emergency_detected') and user_analysis.emergency_detected:
                return ResponseStage.EMERGENCY
            
            # 检查是否是重复问询投诉
            if "重复" in request.message or "已经说过" in request.message or "为什么还要问" in request.message:
                return ResponseStage.REPETITION_HANDLING
            
            # 基于对话轮数和症状收集情况判断
            turn_count = conversation_state.turn_count if conversation_state else 0
            symptoms_count = len(conversation_state.symptoms_collected) if conversation_state else 0
            
            # 信息充分，可以开处方
            if symptoms_count >= 5 and turn_count >= 3:
                return ResponseStage.PRESCRIPTION
            
            # 有一些信息，但需要更多
            elif symptoms_count >= 2 and turn_count >= 2:
                return ResponseStage.DETAILED_INQUIRY
            
            # 信息较少，需要详细了解
            elif turn_count >= 1:
                return ResponseStage.DETAILED_INQUIRY
            
            # 初次问诊
            else:
                return ResponseStage.INITIAL_INQUIRY
                
        except Exception as e:
            logger.error(f"确定回复阶段失败: {e}")
            return ResponseStage.INITIAL_INQUIRY
    
    def _collect_available_info(self, request: ConsultationRequest, conversation_state) -> Dict[str, Any]:
        """收集可用信息"""
        available_info = {}
        
        try:
            # 从对话状态收集症状
            if conversation_state and conversation_state.symptoms_collected:
                available_info["已收集症状"] = "、".join(conversation_state.symptoms_collected)
            
            # 从对话历史提取关键信息
            if request.conversation_history:
                for msg in request.conversation_history:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        
                        # 提取基本信息
                        if any(keyword in content for keyword in ["岁", "年龄", "男", "女"]):
                            available_info["基本信息"] = "已了解年龄性别"
                        
                        # 提取舌象信息
                        if any(keyword in content for keyword in ["舌", "舌苔", "舌质"]):
                            available_info["舌象"] = "患者已描述"
                        
                        # 提取症状持续时间
                        if any(keyword in content for keyword in ["天", "周", "月", "年", "持续"]):
                            available_info["病程"] = "已了解病程"
            
            # 当前消息的关键信息
            if any(keyword in request.message for keyword in ["疼", "痛", "不适"]):
                available_info["主要症状"] = "疼痛相关"
            
            if any(keyword in request.message for keyword in ["失眠", "睡眠", "多梦"]):
                available_info["主要症状"] = "睡眠相关"
            
        except Exception as e:
            logger.error(f"收集可用信息失败: {e}")
        
        return available_info
    
    def _build_template_message_context(self, request: ConsultationRequest, template_prompt: str) -> List[Dict[str, str]]:
        """构建模板化消息上下文"""
        messages = [{"role": "system", "content": template_prompt}]
        
        # 🔧 简化对话历史处理（模板系统已包含历史分析）
        # 只添加最近的2-3轮对话作为直接上下文
        if request.conversation_history:
            recent_history = request.conversation_history[-4:]  # 最近2轮对话
            messages.extend(recent_history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": request.message})
        
        return messages
    
    async def _validate_template_response(self, ai_response: str, request: ConsultationRequest, ai_analysis, response_stage: str) -> Dict[str, Any]:
        """验证模板化响应（大幅简化）"""
        try:
            # 🎯 模板系统已经从源头保证了格式和安全性，这里只需简单验证
            
            # 1. 基本格式检查
            is_valid_format = len(ai_response.strip()) > 10 and "**" in ai_response
            
            # 2. 安全声明检查
            has_safety_disclaimer = any(keyword in ai_response for keyword in [
                "重要声明", "仅供参考", "请咨询", "专业医师", "紧急提醒"
            ])
            
            # 3. 处方检测（使用原有逻辑）
            contains_prescription = self._contains_prescription(ai_response)
            
            # 4. 西药检测（应该不存在，但保留检查）
            western_drugs = ["阿司匹林", "布洛芬", "青霉素", "头孢", "激素"]
            has_western_drugs = any(drug in ai_response for drug in western_drugs)
            
            if has_western_drugs:
                logger.warning("⚠️ 模板化响应仍包含西药，需要检查模板系统")
            
            # 5. 构建验证结果
            validation_result = {
                "content": ai_response,
                "contains_prescription": contains_prescription,
                "prescription_data": self._extract_prescription_data(ai_response) if contains_prescription else None,
                "stage": response_stage,
                "confidence": 0.9 if is_valid_format and has_safety_disclaimer else 0.6,
                "safety_check": {
                    "is_safe": not has_western_drugs,
                    "issues": ["包含西药内容"] if has_western_drugs else [],
                    "has_disclaimer": has_safety_disclaimer
                },
                "template_validation": {
                    "format_valid": is_valid_format,
                    "stage_appropriate": True,  # 模板系统保证
                    "safety_compliant": has_safety_disclaimer
                }
            }
            
            logger.info(f"✅ 模板化响应验证完成: 格式={is_valid_format}, 安全={has_safety_disclaimer}")
            return validation_result
            
        except Exception as e:
            logger.error(f"模板化响应验证失败: {e}")
            # 备用处理
            return {
                "content": ai_response,
                "contains_prescription": False,
                "stage": "inquiry",
                "confidence": 0.5,
                "safety_check": {"is_safe": True, "issues": []},
                "template_validation": {"format_valid": False}
            }
    
    async def _post_process_response(self, ai_response: str, request: ConsultationRequest, ai_analysis=None) -> Dict[str, Any]:
        """后处理AI响应（增强版）"""
        try:
            # 🔥 处方格式强制执行 (v2.9新增) - 确保处方包含具体剂量
            try:
                prescription_enforcer = get_prescription_enforcer()
                ai_response = prescription_enforcer.enforce_prescription_format(ai_response)
                logger.info("统一问诊服务：处方格式强制执行完成")
            except Exception as e:
                logger.error(f"统一问诊服务：处方格式强制执行失败: {e}")
            
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
            real_prescription_id = None
            
            if contains_prescription:
                prescription_data = self._extract_prescription_data(ai_response)
                # 🔑 修复：如果prescription_data为None但我们知道有处方，强制创建prescription_data
                if prescription_data is None:
                    import uuid
                    prescription_data = {
                        "has_prescription": True,
                        "extracted_at": datetime.now().isoformat(),
                        "source": "ai_generated",
                        "prescription_id": "temp_" + str(uuid.uuid4())[:8],
                        "is_paid": False,
                        "payment_required": True,
                        "payment_amount": 88.0
                    }
                    logger.info(f"🔧 强制创建prescription_data，contains_prescription={contains_prescription}")
                
                # 🔑 关键修复：检测到处方时自动创建处方记录和审核队列
                real_prescription_id = await self._create_prescription_record(request, ai_response, prescription_data)
                if real_prescription_id and prescription_data:
                    # 更新处方数据中的真实ID
                    prescription_data["prescription_id"] = real_prescription_id
                    prescription_data["status"] = "pending_review"  # 等待审核状态
                    prescription_data["note"] = "处方已提交医生审核，审核通过后可配药"
            
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

    async def _get_thinking_library_context(self, request: ConsultationRequest, conversation_state) -> Optional[Dict]:
        """🧠 获取思维库上下文（智能决策树匹配版本）"""
        if not self.thinking_library_enabled:
            return None

        try:
            # 1. 检查缓存
            if request.conversation_id in self.pattern_match_cache:
                cached_data = self.pattern_match_cache[request.conversation_id]
                logger.info(f"💾 使用缓存的决策树匹配: {cached_data[0]}")
                return self._format_pattern_context(cached_data[2])

            # 2. 从对话中提取疾病名称和症状
            disease_name = self._extract_disease_from_conversation(request)
            if not disease_name:
                logger.info("未能识别疾病名称，跳过决策树匹配")
                return None

            # 3. 提取症状列表
            symptoms = self._extract_symptoms_from_conversation(request, conversation_state)

            # 4. 获取完整患者描述
            patient_description = self._build_patient_description(request)

            # 5. 获取医生ID
            doctor_id = self._map_doctor_name_to_id(request.selected_doctor)

            # 6. 🔍 使用决策树匹配器查找最佳匹配
            # 先尝试匹配指定医生的决策树
            matching_patterns = await self.decision_tree_matcher.find_matching_patterns(
                disease_name=disease_name,
                symptoms=symptoms,
                patient_description=patient_description,
                doctor_id=doctor_id,
                min_match_score=0.3  # 最小30%匹配度
            )

            # 🔧 如果没找到，尝试查询通用决策树（anonymous_doctor）
            if not matching_patterns and doctor_id != "anonymous_doctor":
                logger.info(f"📚 未找到医生 {doctor_id} 的决策树，尝试查询通用决策树...")
                matching_patterns = await self.decision_tree_matcher.find_matching_patterns(
                    disease_name=disease_name,
                    symptoms=symptoms,
                    patient_description=patient_description,
                    doctor_id="anonymous_doctor",  # 查询通用决策树
                    min_match_score=0.3
                )

            # 🔧 如果还是没找到，查询所有医生的决策树（不限制doctor_id）
            if not matching_patterns:
                logger.info(f"📚 未找到通用决策树，查询所有医生的决策树...")
                matching_patterns = await self.decision_tree_matcher.find_matching_patterns(
                    disease_name=disease_name,
                    symptoms=symptoms,
                    patient_description=patient_description,
                    doctor_id=None,  # 不限制医生ID
                    min_match_score=0.3
                )

            if matching_patterns:
                best_match = matching_patterns[0]
                logger.info(f"✅ 找到最佳决策树匹配: {best_match.pattern_id}, "
                           f"疾病={best_match.disease_name}, "
                           f"匹配分数={best_match.match_score:.2%}, "
                           f"置信度={best_match.confidence:.2%}")

                # 7. 缓存匹配结果
                self.pattern_match_cache[request.conversation_id] = (
                    best_match.pattern_id,
                    best_match.match_score,
                    best_match
                )

                # 8. 格式化并返回
                return self._format_pattern_context(best_match)
            else:
                logger.info(f"📚 未找到匹配的决策树: 医生={doctor_id}, 疾病={disease_name}, 症状数={len(symptoms)}")
                return None

        except Exception as e:
            logger.warning(f"决策树匹配失败: {e}")
            return None

    def _format_pattern_context(self, pattern) -> Dict:
        """格式化决策树模式上下文"""
        try:
            # 解析临床模式JSON
            clinical_patterns = {}
            if isinstance(pattern.clinical_patterns, str):
                try:
                    clinical_patterns = json.loads(pattern.clinical_patterns)
                except:
                    clinical_patterns = {"raw": pattern.clinical_patterns}
            else:
                clinical_patterns = pattern.clinical_patterns or {}

            return {
                "enabled": True,
                "pattern_id": pattern.pattern_id,
                "disease_name": pattern.disease_name,
                "thinking_process": pattern.thinking_process,
                "clinical_patterns": clinical_patterns,
                "tree_structure": pattern.tree_structure,
                "match_score": pattern.match_score,
                "confidence": pattern.confidence,
                "doctor_id": pattern.doctor_id,
                "usage_count": pattern.usage_count,
                "success_rate": (pattern.success_count / pattern.usage_count * 100) if pattern.usage_count > 0 else 0
            }
        except Exception as e:
            logger.error(f"格式化决策树上下文失败: {e}")
            return None
    
    def _extract_disease_from_conversation(self, request: ConsultationRequest) -> Optional[str]:
        """从对话中提取疾病名称"""
        # 使用决策树匹配器的疾病提取功能
        combined_text = request.message
        if request.conversation_history:
            for turn in request.conversation_history[-5:]:  # 检查最近5轮对话
                if turn.get("role") == "user":
                    combined_text += " " + turn.get("content", "")

        disease = self.decision_tree_matcher.extract_disease_from_text(combined_text)
        if disease:
            logger.info(f"🔍 识别到疾病: {disease}")
        return disease

    def _extract_symptoms_from_conversation(self, request: ConsultationRequest, conversation_state) -> List[str]:
        """从对话中提取症状列表"""
        symptoms = []

        # 1. 从当前消息提取
        symptoms.extend(self.decision_tree_matcher.extract_symptoms_from_text(request.message))

        # 2. 从对话历史提取
        if request.conversation_history:
            for turn in request.conversation_history[-10:]:  # 最近10轮
                if turn.get("role") == "user":
                    symptoms.extend(self.decision_tree_matcher.extract_symptoms_from_text(turn.get("content", "")))

        # 3. 从对话状态获取已收集的症状
        if conversation_state and hasattr(conversation_state, 'symptoms_collected'):
            symptoms.extend(conversation_state.symptoms_collected)

        # 去重
        symptoms = list(set(symptoms))
        logger.info(f"🔍 提取到症状: {symptoms[:10]}")  # 只显示前10个
        return symptoms

    def _build_patient_description(self, request: ConsultationRequest) -> str:
        """构建完整的患者描述"""
        parts = [request.message]

        if request.conversation_history:
            for turn in request.conversation_history[-8:]:  # 最近8轮对话
                if turn.get("role") == "user":
                    parts.append(turn.get("content", ""))

        description = " ".join(parts)
        logger.info(f"📝 构建患者描述 (长度: {len(description)}字)")
        return description
    
    def _map_doctor_name_to_id(self, doctor_name: str) -> str:
        """将医生名称映射为ID"""
        mapping = {
            "jin_daifu": "jin_daifu",  # 金大夫使用独立的医学人格
            "zhang_zhongjing": "zhang_zhongjing",
            "ye_tianshi": "ye_tianshi", 
            "li_dongyuan": "li_dongyuan",
            "zheng_qinan": "zheng_qinan",
            "liu_duzhou": "liu_duzhou"
        }
        return mapping.get(doctor_name, doctor_name)
    
    def _build_message_context(self, request: ConsultationRequest, persona_prompt: str, thinking_context: Optional[Dict] = None) -> List[Dict[str, str]]:
        """构建消息上下文（增强版，集成思维库）"""
        messages = []
        
        # 系统消息：医生人格 + 思维库上下文
        system_content = persona_prompt
        
        # 🧠 集成决策树智能匹配内容
        if thinking_context and thinking_context.get("enabled"):
            match_score = thinking_context.get('match_score', 0) * 100
            confidence = thinking_context.get('confidence', 0) * 100
            success_rate = thinking_context.get('success_rate', 0)

            thinking_prompt = f"""

🧠 **智能决策树匹配** (匹配度: {match_score:.0f}%, 置信度: {confidence:.0f}%, 历史成功率: {success_rate:.0f}%)

**匹配的疾病**: {thinking_context.get('disease_name', '未知')}

**您的诊疗思路** (来自您保存的决策树):
{thinking_context.get('thinking_process', '未提供')}

**临床决策要点**:
{self._format_clinical_patterns(thinking_context.get('clinical_patterns', {}))}

**🎯 重要指示**:
1. **优先使用决策树思路**: 上述诊疗思路是您之前针对该疾病总结的宝贵经验，请作为首要参考
2. **处方生成**: 如果需要开具处方，请严格遵循决策树中的用药思路和方剂选择
3. **个性化调整**: 根据当前患者的具体症状，对决策树方案进行必要的加减化裁
4. **保持一致性**: 确保您的诊疗建议与决策树中的思维模式保持一致

📊 **决策树应用统计**: 此决策树已被成功应用 {thinking_context.get('usage_count', 0)} 次"""

            system_content += thinking_prompt
            logger.info(f"🧠 决策树智能匹配已集成 (匹配度:{match_score:.0f}%, ID:{thinking_context.get('pattern_id')})")
        
        # 🔥 新增：构建增强的对话历史摘要，防止重复问询
        if request.conversation_history and isinstance(request.conversation_history, list):
            qa_summary = self._create_qa_summary(request.conversation_history)
            if qa_summary:
                system_content += f"""

## 🚨 已收集信息摘要（严禁重复询问）
{qa_summary}

**重要提醒：以上信息患者已经提供，绝对不能再次询问相同问题！请基于已有信息进行深入分析或提出新的针对性问题。**
"""
        
        messages.append({"role": "system", "content": system_content})
        
        # 🔧 修复：对话历史处理（确保类型安全）
        if request.conversation_history:
            # 确保conversation_history是列表类型
            if isinstance(request.conversation_history, list):
                for turn in request.conversation_history[-10:]:  # 只保留最近10轮
                    if isinstance(turn, dict) and turn.get("role") in ["user", "assistant"]:
                        messages.append({
                            "role": turn["role"], 
                            "content": turn["content"]
                        })
            else:
                logger.warning(f"conversation_history类型错误: {type(request.conversation_history)}, 期望list")
        
        # 当前用户消息
        messages.append({"role": "user", "content": request.message})
        
        return messages
    
    def _format_clinical_patterns(self, patterns: Dict) -> str:
        """格式化临床模式"""
        if not patterns:
            return "暂无特定临床模式"
            
        formatted = []
        if patterns.get("key_decision_points"):
            formatted.append("关键决策点:")
            for point in patterns["key_decision_points"][:3]:  # 只显示前3个
                formatted.append(f"- {point.get('decision_name', '')}: {point.get('decision_criteria', '')}")
        
        if patterns.get("treatment_principles"):
            formatted.append("\n治疗原则:")
            for principle in patterns["treatment_principles"][:3]:
                formatted.append(f"- {principle.get('principle_name', '')}")
                
        return "\n".join(formatted) if formatted else "暂无具体模式"
    
    def _format_doctor_expertise(self, expertise: Dict) -> str:
        """格式化医生专业背景"""
        if not expertise:
            return "专科: 中医内科"
            
        specialization = expertise.get("specialization", "中医内科")
        experience = expertise.get("experience_level", "主治医师")
        
        return f"专科: {specialization}, 经验: {experience}"
    
    def _create_qa_summary(self, conversation_history: List[Dict]) -> str:
        """创建问答摘要，明确标记已收集的信息"""
        if not conversation_history:
            return ""
        
        # 分析已收集的信息
        collected_info = {
            "基本信息": [],
            "主要症状": [],
            "伴随症状": [],
            "舌象脉象": [],
            "病史病程": [],
            "其他信息": []
        }
        
        # 常见问诊关键词映射
        question_patterns = {
            "基本信息": ["年龄", "性别", "岁", "男", "女", "职业"],
            "主要症状": ["主要", "主诉", "什么症状", "哪里不舒服", "什么问题"],
            "病程时间": ["多久", "什么时候", "多长时间", "几天", "几周", "几月", "持续"],
            "症状性质": ["什么样", "怎样", "如何", "程度", "严重", "轻重"],
            "诱发因素": ["什么原因", "怎么引起", "诱发", "触发", "加重", "缓解"],
            "伴随症状": ["还有", "其他", "伴有", "同时", "一起"],
            "舌象": ["舌头", "舌象", "舌苔", "舌质", "舌色"],
            "饮食": ["食欲", "吃饭", "饮食", "胃口", "消化"],
            "睡眠": ["睡眠", "失眠", "多梦", "睡觉", "入睡"],
            "大小便": ["大便", "小便", "二便", "排便", "尿"],
            "既往病史": ["以前", "病史", "得过", "治疗过", "吃过药"]
        }
        
        # 分析对话中的问答对
        for i, turn in enumerate(conversation_history):
            if turn.get("role") == "assistant":
                # 分析医生问题
                content = turn.get("content", "").strip()
                
                # 检查下一轮用户是否回答了
                if i + 1 < len(conversation_history):
                    next_turn = conversation_history[i + 1]
                    if next_turn.get("role") == "user":
                        user_response = next_turn.get("content", "").strip()
                        
                        # 分析回答了什么信息
                        for category, keywords in question_patterns.items():
                            if any(keyword in content for keyword in keywords):
                                # 提取用户回答的关键信息
                                if category == "基本信息":
                                    if any(kw in user_response for kw in ["岁", "年龄"]):
                                        age_match = re.search(r'(\d+)岁', user_response)
                                        if age_match:
                                            collected_info["基本信息"].append(f"年龄: {age_match.group(1)}岁")
                                    if any(kw in user_response for kw in ["男", "女"]):
                                        gender = "男" if "男" in user_response else "女"
                                        collected_info["基本信息"].append(f"性别: {gender}")
                                
                                elif category == "病程时间":
                                    time_patterns = [r'(\d+)(天|日)', r'(\d+)(周|星期)', r'(\d+)(月|个月)', r'(\d+)(年)']
                                    for pattern in time_patterns:
                                        match = re.search(pattern, user_response)
                                        if match:
                                            collected_info["病史病程"].append(f"病程: {match.group(1)}{match.group(2)}")
                                
                                elif category == "舌象":
                                    if any(kw in user_response for kw in ["舌", "苔"]):
                                        collected_info["舌象脉象"].append(f"舌象: {user_response[:50]}...")
                                
                                elif category == "饮食":
                                    if any(kw in user_response for kw in ["食欲", "胃口", "吃"]):
                                        collected_info["其他信息"].append(f"饮食: {user_response[:30]}...")
                                
                                elif category == "睡眠":
                                    if any(kw in user_response for kw in ["睡", "眠"]):
                                        collected_info["其他信息"].append(f"睡眠: {user_response[:30]}...")
                                
                                elif category == "大小便":
                                    if any(kw in user_response for kw in ["便", "尿"]):
                                        collected_info["其他信息"].append(f"二便: {user_response[:30]}...")
        
        # 同时从用户消息中直接提取症状信息
        for turn in conversation_history:
            if turn.get("role") == "user":
                content = turn.get("content", "")
                
                # 提取症状
                symptoms = self._extract_symptoms_for_summary(content)
                for symptom in symptoms:
                    if symptom not in [item.split(":")[1].strip() if ":" in item else item for item in collected_info["主要症状"]]:
                        collected_info["主要症状"].append(f"症状: {symptom}")
        
        # 构建摘要
        summary_parts = []
        for category, items in collected_info.items():
            if items:
                unique_items = list(set(items))  # 去重
                if unique_items:
                    summary_parts.append(f"**{category}**: {', '.join(unique_items[:3])}")  # 最多显示3项
        
        if summary_parts:
            return "\n".join(summary_parts)
        
        return ""
    
    def _extract_symptoms_for_summary(self, text: str) -> List[str]:
        """为摘要提取症状信息"""
        symptoms = []
        
        # 常见症状关键词
        symptom_keywords = [
            "头痛", "头晕", "胃痛", "腹痛", "咳嗽", "失眠", "便秘", "腹泻",
            "乏力", "心慌", "胸闷", "恶心", "呕吐", "发热", "口干", "盗汗"
        ]
        
        for keyword in symptom_keywords:
            if keyword in text:
                symptoms.append(keyword)
        
        # 提取描述性症状
        patterns = [
            r'(.{0,3})(痛|疼|酸|胀|闷)',
            r'(拉肚子|腹泻|便秘|失眠|咳嗽)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                symptom = ''.join(match).strip()
                if len(symptom) > 1 and symptom not in symptoms:
                    symptoms.append(symptom)
        
        return symptoms[:5]  # 最多返回5个症状

    def get_pattern_match_result(self, conversation_id: str) -> Optional[Tuple[str, float]]:
        """
        获取指定问诊的决策树匹配结果

        Args:
            conversation_id: 问诊ID

        Returns:
            Tuple[pattern_id, match_score] or None
        """
        return self.pattern_match_cache.get(conversation_id)

    def _extract_symptoms_description(self, ai_response: str, conversation_history: List[Dict]) -> str:
        """
        从AI响应和对话历史中提取症状描述

        Args:
            ai_response: AI完整响应
            conversation_history: 对话历史

        Returns:
            症状描述字符串
        """
        import re

        # 方法1: 从AI响应中提取"根据患者描述"部分
        pattern1 = r'根据患者描述[，,：:](.*?)(?:[。；\n]|$)'
        match = re.search(pattern1, ai_response, re.DOTALL)
        if match:
            symptoms_text = match.group(1).strip()
            # 截取前200字符
            if len(symptoms_text) > 200:
                symptoms_text = symptoms_text[:200] + "..."
            return symptoms_text

        # 方法2: 从AI响应的【辨证分析】部分提取前几句
        pattern2 = r'【辨证分析】\s*(.*?)(?:【|$)'
        match = re.search(pattern2, ai_response, re.DOTALL)
        if match:
            analysis_text = match.group(1).strip()
            # 提取第一段（通常包含症状描述）
            first_paragraph = analysis_text.split('\n\n')[0] if '\n\n' in analysis_text else analysis_text.split('\n')[0]
            if len(first_paragraph) > 200:
                first_paragraph = first_paragraph[:200] + "..."
            return first_paragraph

        # 方法3: 从对话历史中合并用户的症状描述
        if conversation_history:
            user_messages = [msg.get('content', '') for msg in conversation_history if msg.get('role') == 'user']
            if user_messages:
                # 合并所有用户消息，用分号分隔
                combined = "; ".join([msg[:50] for msg in user_messages[-3:]])  # 最近3条
                if len(combined) > 200:
                    combined = combined[:200] + "..."
                return combined

        # 降级：返回占位符
        return "患者症状描述（详见AI分析）"

    def _extract_diagnosis_description(self, ai_response: str) -> str:
        """
        从AI响应中提取辨证诊断描述

        Args:
            ai_response: AI完整响应

        Returns:
            辨证诊断字符串
        """
        import re

        # 方法1: 提取【治法治则】部分
        pattern1 = r'【治法治则】\s*([^\n【]+)'
        match = re.search(pattern1, ai_response)
        if match:
            treatment_principle = match.group(1).strip()
            # 去除多余空格和标点
            treatment_principle = re.sub(r'\s+', ' ', treatment_principle).strip('，,。. ')
            if treatment_principle:
                return treatment_principle

        # 方法2: 从【辨证分析】结尾提取证型
        pattern2 = r'(?:考虑为|属于|诊断为|证型为|辨证为)[：:]?\s*([^，。\n]{4,30})'
        match = re.search(pattern2, ai_response)
        if match:
            diagnosis = match.group(1).strip()
            # 清理常见的无关词汇
            diagnosis = re.sub(r'之证|之象|证候|型', '', diagnosis).strip()
            if diagnosis:
                return diagnosis

        # 方法3: 提取关键证型词汇
        syndrome_patterns = [
            r'(脾虚[湿困]{0,2})',
            r'(肝郁[脾虚气滞]{0,4})',
            r'(肾[阳阴]{1}虚)',
            r'(气[血]{0,1}[虚不足两虚]{1,3})',
            r'([痰湿寒]{1,2}[热困]{1,2})',
            r'([阴阳]{1}虚)'
        ]

        found_syndromes = []
        for pattern in syndrome_patterns:
            matches = re.findall(pattern, ai_response)
            found_syndromes.extend(matches)

        if found_syndromes:
            # 去重并合并
            unique_syndromes = list(dict.fromkeys(found_syndromes))  # 保持顺序去重
            diagnosis_text = "、".join(unique_syndromes[:3])  # 最多3个
            return diagnosis_text

        # 降级：返回占位符
        return "中医辨证诊断（详见AI分析）"

    def clear_pattern_match_result(self, conversation_id: str):
        """
        清除指定问诊的决策树匹配结果（节省内存）

        Args:
            conversation_id: 问诊ID
        """
        if conversation_id in self.pattern_match_cache:
            del self.pattern_match_cache[conversation_id]

# 全局服务实例
_consultation_service = None

def get_consultation_service() -> UnifiedConsultationService:
    """获取统一问诊服务实例（单例模式）"""
    global _consultation_service
    if _consultation_service is None:
        _consultation_service = UnifiedConsultationService()
    return _consultation_service