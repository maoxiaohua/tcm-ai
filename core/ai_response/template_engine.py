#!/usr/bin/env python3
"""
TCM-AI 智能回复模板引擎
从源头控制AI回复格式，确保质量一致性和医疗安全
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ResponseStage(Enum):
    """回复阶段枚举"""
    INITIAL_INQUIRY = "initial_inquiry"          # 初始问诊
    DETAILED_INQUIRY = "detailed_inquiry"        # 详细问诊
    REPETITION_HANDLING = "repetition_handling"  # 重复问询处理
    DIAGNOSIS = "diagnosis"                      # 诊断分析
    PRESCRIPTION = "prescription"                # 完整处方
    INTERIM_ADVICE = "interim_advice"           # 临时建议
    EMERGENCY = "emergency"                     # 紧急情况

@dataclass
class TemplateContext:
    """模板上下文数据"""
    doctor_name: str
    doctor_school: str
    patient_symptoms: List[str]
    known_info: Dict[str, Any]
    stage: ResponseStage
    confidence_level: float
    conversation_history: List[Dict]
    safety_flags: List[str] = None

class TCMResponseTemplateEngine:
    """TCM AI回复模板引擎"""
    
    def __init__(self):
        """初始化模板引擎"""
        self.templates = self._initialize_templates()
        self.safety_phrases = self._load_safety_phrases()
        self.tcm_herbs_dict = self._load_tcm_herbs()
        
    def _initialize_templates(self) -> Dict[ResponseStage, Dict[str, str]]:
        """初始化所有回复模板"""
        return {
            ResponseStage.INITIAL_INQUIRY: {
                "template": """您好！我是{doctor_name}，{doctor_introduction}

根据您描述的症状：{symptom_summary}

为了准确辨证论治，还需了解以下情况：
{targeted_questions}

请详细说明，以便为您制定精准的治疗方案。

{safety_disclaimer}""",
                "required_fields": ["doctor_name", "doctor_introduction", "symptom_summary", "targeted_questions"]
            },
            
            ResponseStage.DETAILED_INQUIRY: {
                "template": """根据您提供的信息：{known_symptoms}

{preliminary_analysis}

为进一步明确诊断，需要了解：
{followup_questions}

{stage_guidance}

{safety_disclaimer}""",
                "required_fields": ["known_symptoms", "preliminary_analysis", "followup_questions"]
            },
            
            ResponseStage.REPETITION_HANDLING: {
                "template": """我理解您的关切。让我总结您已提供的信息：
{symptom_recap}

基于这些症状，{current_analysis}

{next_action}

{safety_disclaimer}""",
                "required_fields": ["symptom_recap", "current_analysis", "next_action"]
            },
            
            ResponseStage.DIAGNOSIS: {
                "template": """【辨证分析】
根据您的症状表现：{symptom_analysis}
舌脉情况：{tongue_pulse_info}
病程特点：{disease_course}

**证候诊断**：{syndrome_diagnosis}
**病机分析**：{pathogenesis_analysis}

【治疗建议】
{treatment_recommendation}

{safety_disclaimer}""",
                "required_fields": ["symptom_analysis", "syndrome_diagnosis", "pathogenesis_analysis", "treatment_recommendation"]
            },
            
            ResponseStage.PRESCRIPTION: {
                "template": """【处方方案】

**基本信息**
- 症状总结：{symptom_summary}
- 证候诊断：{syndrome_name}
- 治疗原则：{treatment_principle}

**方剂组成**

【君药】
{sovereign_herbs}

【臣药】
{minister_herbs}

【佐药】
{assistant_herbs}

【使药】
{envoy_herbs}

**煎服方法**
{preparation_method}

**生活调理**
{lifestyle_advice}

**注意事项**
{precautions}

{prescription_safety_disclaimer}""",
                "required_fields": ["symptom_summary", "syndrome_name", "treatment_principle", 
                                  "sovereign_herbs", "minister_herbs", "assistant_herbs", "envoy_herbs"]
            },
            
            ResponseStage.INTERIM_ADVICE: {
                "template": """【初步处方建议】

基于目前症状，初步考虑：{preliminary_treatment}

**需要补充的信息**：
{missing_info}

**临时调理建议**：
{temporary_advice}

**重要说明**：完整处方需要更详细的四诊信息。建议{next_steps}

{safety_disclaimer}""",
                "required_fields": ["preliminary_treatment", "missing_info", "temporary_advice", "next_steps"]
            },
            
            ResponseStage.EMERGENCY: {
                "template": """**紧急提醒**

根据您描述的症状：{emergency_symptoms}

建议您立即前往医院急诊科就诊，不宜延误。

AI中医咨询主要针对慢性调理，急性严重症状需要专业医疗机构的及时处理。

{emergency_disclaimer}""",
                "required_fields": ["emergency_symptoms"]
            }
        }
    
    def _load_safety_phrases(self) -> Dict[str, str]:
        """加载安全声明短语"""
        return {
            "general": "**重要声明**：本建议为AI预诊，仅供参考，请务必咨询专业中医师后使用。",
            "prescription": "**处方声明**：本处方为AI生成的预诊建议，不能替代执业医师面诊，使用前请咨询专业中医师。",
            "emergency": "**紧急声明**：如症状严重或持续加重，请立即就医，切勿延误。",
            "limitation": "AI咨询有局限性，无法替代专业医疗诊断和治疗。"
        }
    
    def _load_tcm_herbs(self) -> Dict[str, Dict]:
        """加载中药材数据库"""
        # 这里应该从实际的中药数据库加载
        return {
            "生地黄": {"category": "清热凉血", "dosage_range": (15, 30), "contraindications": ["脾胃虚寒"]},
            "黄芪": {"category": "补气", "dosage_range": (15, 30), "contraindications": ["实热证"]},
            "当归": {"category": "补血", "dosage_range": (10, 15), "contraindications": ["湿盛中满"]},
            # ... 更多中药数据
        }
    
    def generate_response(self, context: TemplateContext) -> str:
        """生成标准化回复"""
        try:
            # 1. 选择合适的模板
            template_info = self.templates.get(context.stage)
            if not template_info:
                logger.error(f"未找到阶段 {context.stage} 的模板")
                return self._generate_fallback_response(context)
            
            # 2. 填充模板内容
            filled_content = self._fill_template(template_info, context)
            
            # 3. 安全验证
            validated_content = self._validate_content(filled_content)
            
            # 4. 最终格式化
            final_response = self._finalize_response(validated_content, context)
            
            logger.info(f"成功生成 {context.stage.value} 阶段回复")
            return final_response
            
        except Exception as e:
            logger.error(f"模板生成失败: {e}")
            return self._generate_fallback_response(context)
    
    def _fill_template(self, template_info: Dict, context: TemplateContext) -> str:
        """填充模板内容"""
        template = template_info["template"]
        
        # 构建填充数据
        fill_data = self._build_fill_data(context)
        
        # 验证必填字段
        required_fields = template_info.get("required_fields", [])
        for field in required_fields:
            if field not in fill_data or not fill_data[field]:
                logger.warning(f"缺少必填字段: {field}")
                fill_data[field] = f"[{field}信息待完善]"
        
        # 填充模板
        try:
            filled_template = template.format(**fill_data)
            return filled_template
        except KeyError as e:
            logger.error(f"模板填充失败，缺少字段: {e}")
            return template  # 返回原模板
    
    def _build_fill_data(self, context: TemplateContext) -> Dict[str, Any]:
        """构建模板填充数据"""
        fill_data = {
            "doctor_name": context.doctor_name,
            "doctor_introduction": self._get_doctor_introduction(context.doctor_name, context.doctor_school),
            "symptom_summary": self._summarize_symptoms(context.patient_symptoms),
            "safety_disclaimer": self._get_safety_disclaimer(context.stage),
        }
        
        # 根据阶段添加特定数据
        if context.stage == ResponseStage.INITIAL_INQUIRY:
            fill_data.update({
                "targeted_questions": self._generate_targeted_questions(context),
            })
        
        elif context.stage == ResponseStage.DETAILED_INQUIRY:
            fill_data.update({
                "known_symptoms": self._format_known_symptoms(context.known_info),
                "preliminary_analysis": self._generate_preliminary_analysis(context),
                "followup_questions": self._generate_followup_questions(context),
                "stage_guidance": self._get_stage_guidance(context),
            })
        
        elif context.stage == ResponseStage.REPETITION_HANDLING:
            fill_data.update({
                "symptom_recap": self._generate_symptom_recap(context),
                "current_analysis": self._generate_current_analysis(context),
                "next_action": self._determine_next_action(context),
            })
        
        elif context.stage == ResponseStage.PRESCRIPTION:
            fill_data.update(self._build_prescription_data(context))
        
        elif context.stage == ResponseStage.INTERIM_ADVICE:
            fill_data.update({
                "preliminary_treatment": self._generate_preliminary_treatment(context),
                "missing_info": self._identify_missing_info(context),
                "temporary_advice": self._generate_temporary_advice(context),
                "next_steps": self._suggest_next_steps(context),
            })
        
        elif context.stage == ResponseStage.EMERGENCY:
            fill_data.update({
                "emergency_symptoms": self._format_emergency_symptoms(context),
                "emergency_disclaimer": self.safety_phrases["emergency"],
            })
        
        return fill_data
    
    def _get_doctor_introduction(self, doctor_name: str, school: str) -> str:
        """获取医生介绍"""
        introductions = {
            "张仲景": f"擅长六经辨证，遵循《伤寒论》理论，精于方证相应。",
            "叶天士": f"温病学派传人，擅长卫气营血辨证，精于时令病证。",
            "李东垣": f"脾胃学派创始人，重视后天之本，擅长升阳益胃。",
            "朱丹溪": f"滋阴派宗师，倡导'阴常不足，阳常有余'，精于滋阴降火。",
            "刘渡舟": f"经方大师，严格按仲景思想，重视方证对应关系。",
            "郑钦安": f"扶阳派传人，重视阳气，善用附子，精于急危重症。"
        }
        return introductions.get(doctor_name, f"{school}医师，遵循传统中医理论。")
    
    def _summarize_symptoms(self, symptoms: List[str]) -> str:
        """总结症状"""
        if not symptoms:
            return "您的症状"
        
        if len(symptoms) <= 3:
            return "、".join(symptoms)
        else:
            return "、".join(symptoms[:3]) + f"等{len(symptoms)}个症状"
    
    def _get_safety_disclaimer(self, stage: ResponseStage) -> str:
        """获取安全声明"""
        if stage == ResponseStage.PRESCRIPTION:
            return self.safety_phrases["prescription"]
        elif stage == ResponseStage.EMERGENCY:
            return self.safety_phrases["emergency"]
        else:
            return self.safety_phrases["general"]
    
    def _generate_targeted_questions(self, context: TemplateContext) -> str:
        """生成针对性问题"""
        questions = [
            "1. 症状持续时间和发作规律如何？",
            "2. 是否有明显的诱发或缓解因素？",
            "3. 伴随症状有哪些？",
            "4. 既往病史和用药情况如何？",
            "5. 能否提供舌象照片或描述舌苔情况？"
        ]
        return "\n".join(questions)
    
    def _validate_content(self, content: str) -> str:
        """验证内容安全性"""
        # 检查是否包含西药
        western_drugs = ["阿司匹林", "布洛芬", "青霉素", "头孢", "激素"]
        for drug in western_drugs:
            if drug in content:
                logger.warning(f"检测到西药名称: {drug}")
                content = content.replace(drug, "[中药替代]")
        
        # 确保包含安全声明
        if "重要声明" not in content and "紧急提醒" not in content:
            content += f"\n\n{self.safety_phrases['general']}"
        
        return content
    
    def _finalize_response(self, content: str, context: TemplateContext) -> str:
        """最终格式化回复"""
        # 添加时间戳（如果需要）
        # 添加医生签名（如果需要）
        # 其他格式化处理
        
        return content.strip()
    
    def _generate_fallback_response(self, context: TemplateContext) -> str:
        """生成备用回复"""
        return f"""抱歉，{context.doctor_name}暂时无法提供详细回复。

请详细描述您的症状，我会尽快为您分析。

{self.safety_phrases['general']}"""
    
    # 其他辅助方法的占位符实现
    def _format_known_symptoms(self, known_info: Dict) -> str:
        return "已了解的症状信息"
    
    def _generate_preliminary_analysis(self, context: TemplateContext) -> str:
        return "基于现有信息的初步分析"
    
    def _generate_followup_questions(self, context: TemplateContext) -> str:
        return "1. 后续问题1\n2. 后续问题2"
    
    def _get_stage_guidance(self, context: TemplateContext) -> str:
        return "问诊进度指导"
    
    def _generate_symptom_recap(self, context: TemplateContext) -> str:
        return "症状回顾总结"
    
    def _generate_current_analysis(self, context: TemplateContext) -> str:
        return "当前症状分析"
    
    def _determine_next_action(self, context: TemplateContext) -> str:
        return "下一步行动建议"
    
    def _build_prescription_data(self, context: TemplateContext) -> Dict:
        return {
            "syndrome_name": "证候名称",
            "treatment_principle": "治疗原则",
            "sovereign_herbs": "- 君药1 15g (主要作用)",
            "minister_herbs": "- 臣药1 12g (辅助作用)",
            "assistant_herbs": "- 佐药1 10g (佐助作用)",
            "envoy_herbs": "- 使药1 6g (调和作用)",
            "preparation_method": "每日一剂，水煎服，分早晚两次温服。",
            "lifestyle_advice": "1. 饮食清淡\n2. 规律作息",
            "precautions": "1. 忌辛辣食物\n2. 观察药物反应",
            "prescription_safety_disclaimer": self.safety_phrases["prescription"]
        }
    
    def _generate_preliminary_treatment(self, context: TemplateContext) -> str:
        return "初步治疗建议"
    
    def _identify_missing_info(self, context: TemplateContext) -> str:
        return "- 缺少信息1\n- 缺少信息2"
    
    def _generate_temporary_advice(self, context: TemplateContext) -> str:
        return "1. 临时建议1\n2. 临时建议2"
    
    def _suggest_next_steps(self, context: TemplateContext) -> str:
        return "提供更多信息后确认处方"
    
    def _format_emergency_symptoms(self, context: TemplateContext) -> str:
        return "紧急症状描述"

# 全局模板引擎实例
_template_engine = None

def get_template_engine() -> TCMResponseTemplateEngine:
    """获取模板引擎实例（单例模式）"""
    global _template_engine
    if _template_engine is None:
        _template_engine = TCMResponseTemplateEngine()
    return _template_engine