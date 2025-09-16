#!/usr/bin/env python3
"""
模板化AI提示词生成器
强制AI严格按照预定义模板回复，确保输出格式统一和内容安全
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .template_engine import ResponseStage, TemplateContext, get_template_engine

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """提示词类型"""
    STRICT_TEMPLATE = "strict_template"      # 严格模板模式
    GUIDED_TEMPLATE = "guided_template"      # 引导模板模式
    FALLBACK = "fallback"                    # 备用模式

@dataclass
class TemplatePromptContext:
    """模板提示词上下文"""
    stage: ResponseStage
    doctor_persona: str
    patient_message: str
    conversation_history: List[Dict]
    available_info: Dict[str, Any]
    template_requirements: Dict[str, Any]

class TemplatePromptGenerator:
    """模板化AI提示词生成器"""
    
    def __init__(self):
        """初始化提示词生成器"""
        self.template_engine = get_template_engine()
        self.base_instructions = self._load_base_instructions()
        self.format_constraints = self._load_format_constraints()
        
    def _load_base_instructions(self) -> Dict[str, str]:
        """加载基础指令"""
        return {
            "core_principle": """你是一位严格遵循模板的中医AI医师。你必须且只能按照提供的模板格式回复，不得偏离。""",
            
            "template_adherence": """
**严格模板要求**：
1. 必须使用提供的模板格式
2. 只能填写{占位符}部分，不得添加模板外内容
3. 所有药物必须是中药材，禁止任何西药
4. 必须包含安全医疗声明
5. 回复内容必须专业、准确、安全""",
            
            "content_safety": """
**内容安全规则**：
1. 只能推荐中药材和中医疗法
2. 严禁提及任何西药、化学药物、抗生素
3. 必须包含"仅供参考，请咨询专业医师"类声明
4. 对于危急症状，必须建议立即就医
5. 不得夸大疗效或作出绝对承诺""",
            
            "tcm_principles": """
**中医原则**：
1. 四诊合参：望闻问切，全面了解
2. 辨证论治：根据证候选择治法
3. 整体观念：考虑人体整体状态
4. 因人制宜：个体化治疗方案"""
        }
    
    def _load_format_constraints(self) -> Dict[ResponseStage, Dict]:
        """加载格式约束"""
        return {
            ResponseStage.INITIAL_INQUIRY: {
                "required_sections": ["症状了解", "针对性问题", "安全声明"],
                "max_questions": 5,
                "tone": "专业、亲和"
            },
            
            ResponseStage.DETAILED_INQUIRY: {
                "required_sections": ["已知信息总结", "初步分析", "后续问题"],
                "max_questions": 3,
                "tone": "深入、专业"
            },
            
            ResponseStage.PRESCRIPTION: {
                "required_sections": ["君臣佐使", "煎服方法", "注意事项", "安全声明"],
                "herb_limit": (12, 25),  # 药味数量范围
                "mandatory_safety": True
            },
            
            ResponseStage.EMERGENCY: {
                "required_sections": ["紧急提醒", "建议就医", "免责声明"],
                "urgency_level": "highest",
                "tone": "严肃、明确"
            }
        }
    
    def generate_strict_template_prompt(self, context: TemplatePromptContext) -> str:
        """生成严格模板提示词"""
        
        # 1. 获取对应的模板
        template_info = self.template_engine.templates.get(context.stage)
        if not template_info:
            logger.error(f"未找到 {context.stage} 阶段的模板")
            return self.generate_fallback_prompt(context)
        
        # 2. 构建严格指令
        strict_prompt = self._build_strict_instructions(context, template_info)
        
        # 3. 添加模板示例
        template_example = self._build_template_example(context, template_info)
        
        # 4. 添加填充指导
        filling_guidance = self._build_filling_guidance(context)
        
        # 5. 组合完整提示词
        full_prompt = f"""{strict_prompt}

{template_example}

{filling_guidance}

**最终要求**：严格按照上述模板回复，不得添加任何模板外内容。"""
        
        return full_prompt
    
    def _build_strict_instructions(self, context: TemplatePromptContext, template_info: Dict) -> str:
        """构建严格指令"""
        doctor_info = self._get_doctor_info(context.doctor_persona)
        stage_constraints = self.format_constraints.get(context.stage, {})
        
        instructions = f"""# {doctor_info['name']} - 严格模板回复模式

{self.base_instructions['core_principle']}

## 当前任务
- 医生角色：{doctor_info['name']} ({doctor_info['school']})
- 回复阶段：{context.stage.value}
- 患者消息：{context.patient_message}

{self.base_instructions['template_adherence']}

## 阶段特定要求
- 必需章节：{stage_constraints.get('required_sections', [])}
- 回复语调：{stage_constraints.get('tone', '专业')}
- 特殊限制：{self._format_special_constraints(context.stage, stage_constraints)}

{self.base_instructions['content_safety']}"""
        
        return instructions
    
    def _build_template_example(self, context: TemplatePromptContext, template_info: Dict) -> str:
        """构建模板示例"""
        template = template_info["template"]
        required_fields = template_info.get("required_fields", [])
        
        example = f"""## 必须使用的回复模板

```
{template}
```

## 模板填充说明
{self._generate_field_explanations(required_fields, context.stage)}"""
        
        return example
    
    def _build_filling_guidance(self, context: TemplatePromptContext) -> str:
        """构建填充指导"""
        available_info = self._format_available_info(context.available_info)
        
        guidance = f"""## 填充指导

### 可用信息
{available_info}

### 填充规则
1. 只填写 {{占位符}} 部分，保持其他文字不变
2. 基于患者信息和对话历史进行填充
3. 中药材名称必须准确，剂量在安全范围内
4. 问题设计要有针对性，避免重复已知信息
5. 分析内容要符合中医理论

### 禁止事项
❌ 添加模板外的任何内容
❌ 提及任何西药或化学药物
❌ 遗漏安全声明
❌ 重复询问已知信息
❌ 使用不确定或模糊的表述\"\"\"
        
        return guidance
    
    def _get_doctor_info(self, doctor_persona: str) -> Dict[str, str]:
        """获取医生信息"""
        doctor_map = {
            "zhang_zhongjing": {"name": "张仲景", "school": "伤寒派"},
            "ye_tianshi": {"name": "叶天士", "school": "温病派"},
            "li_dongyuan": {"name": "李东垣", "school": "脾胃派"},
            "zhu_danxi": {"name": "朱丹溪", "school": "滋阴派"},
            "liu_duzhou": {"name": "刘渡舟", "school": "经方派"},
            "zheng_qin_an": {"name": "郑钦安", "school": "扶阳派"}
        }
        return doctor_map.get(doctor_persona, {"name": "中医师", "school": "传统中医"})
    
    def _format_special_constraints(self, stage: ResponseStage, constraints: Dict) -> str:
        """格式化特殊约束"""
        special = []
        
        if "max_questions" in constraints:
            special.append(f"问题数量不超过{constraints['max_questions']}个")
        
        if "herb_limit" in constraints:
            min_herbs, max_herbs = constraints["herb_limit"]
            special.append(f"药味数量{min_herbs}-{max_herbs}味")
        
        if constraints.get("mandatory_safety"):
            special.append("必须包含医疗安全声明")
        
        if constraints.get("urgency_level") == "highest":
            special.append("必须强调紧急就医")
        
        return "；".join(special) if special else "无特殊限制"
    
    def _generate_field_explanations(self, required_fields: List[str], stage: ResponseStage) -> str:
        """生成字段说明"""
        explanations = {
            "doctor_name": "医生姓名（如：张仲景）",
            "doctor_introduction": "医生流派介绍（1-2句话）", 
            "symptom_summary": "患者症状总结（简洁明了）",
            "targeted_questions": "针对性问题（编号列表，避免重复已知）",
            "known_symptoms": "已了解的症状信息",
            "preliminary_analysis": "基于现有信息的初步中医分析",
            "followup_questions": "后续需要了解的问题",
            "syndrome_diagnosis": "中医证候诊断（如：肝阳上亢）",
            "pathogenesis_analysis": "病机分析（中医理论解释）",
            "sovereign_herbs": "君药（主要药物，格式：- 药名 剂量g (作用)）",
            "minister_herbs": "臣药（辅助药物，同上格式）",
            "assistant_herbs": "佐药（佐助药物，同上格式）",
            "envoy_herbs": "使药（调和药物，同上格式）",
        }
        
        field_lines = []
        for field in required_fields:
            explanation = explanations.get(field, f"{field}相关内容")
            field_lines.append(f"- {{{field}}}：{explanation}")
        
        return "\\n".join(field_lines)
    
    def _format_available_info(self, available_info: Dict[str, Any]) -> str:
        """格式化可用信息"""
        if not available_info:
            return "暂无已收集信息"
        
        info_lines = []
        for key, value in available_info.items():
            if value:
                info_lines.append(f"- {key}：{value}")
        
        return "\\n".join(info_lines) if info_lines else "暂无已收集信息"
    
    def generate_guided_template_prompt(self, context: TemplatePromptContext) -> str:
        """生成引导模板提示词(较宽松的模板指导)"""
        
        guidance = f"""# {self._get_doctor_info(context.doctor_persona)['name']} - 引导模板模式

## 回复结构指导
根据当前阶段 {context.stage.value}，请按照以下结构回复：

{self._get_stage_structure_guidance(context.stage)}

## 内容要求
{self.base_instructions['content_safety']}

## 格式建议
- 使用清晰的章节标题
- 重要信息使用**粗体**强调
- 问题使用编号列表
- 必须包含安全医疗声明

请基于以上指导回复患者。\"\"\"
        
        return guidance
    
    def _get_stage_structure_guidance(self, stage: ResponseStage) -> str:
        """获取阶段结构指导"""
        guidance_map = {
            ResponseStage.INITIAL_INQUIRY: """
1. 医生自我介绍和流派特色
2. 对患者症状的初步了解确认
3. 针对性问题（3-5个）
4. 安全声明""",
            
            ResponseStage.DETAILED_INQUIRY: """
1. 已了解信息的总结
2. 初步中医分析
3. 需要进一步了解的问题（1-3个）
4. 引导患者提供更多信息""",
            
            ResponseStage.PRESCRIPTION: """
1. 辨证分析（症状、舌脉、证候）
2. 处方方案（君臣佐使分类）
3. 煎服方法和注意事项
4. 生活调理建议
5. 医疗安全声明""",
            
            ResponseStage.EMERGENCY: """
1. 紧急情况识别
2. 强烈建议立即就医
3. 简要说明为什么需要紧急处理
4. 紧急免责声明"""
        }
        
        return guidance_map.get(stage, "按照中医标准流程回复")
    
    def generate_fallback_prompt(self, context: TemplatePromptContext) -> str:
        """生成备用提示词"""
        return f"""请作为{self._get_doctor_info(context.doctor_persona)['name']}，
简洁回复患者问题：{context.patient_message}

要求：
1. 保持中医师的专业身份
2. 只推荐中药和中医疗法
3. 包含医疗安全声明
4. 回复简洁明了\"\"\"
    
    def determine_optimal_prompt_type(self, context: TemplatePromptContext) -> PromptType:
        """确定最优提示词类型"""
        
        # 处方阶段使用严格模板
        if context.stage == ResponseStage.PRESCRIPTION:
            return PromptType.STRICT_TEMPLATE
        
        # 紧急情况使用严格模板
        if context.stage == ResponseStage.EMERGENCY:
            return PromptType.STRICT_TEMPLATE
        
        # 信息足够时使用严格模板
        if len(context.available_info) >= 3:
            return PromptType.STRICT_TEMPLATE
        
        # 其他情况使用引导模板
        return PromptType.GUIDED_TEMPLATE
    
    def generate_optimal_prompt(self, context: TemplatePromptContext) -> str:
        """生成最优提示词"""
        prompt_type = self.determine_optimal_prompt_type(context)
        
        if prompt_type == PromptType.STRICT_TEMPLATE:
            return self.generate_strict_template_prompt(context)
        elif prompt_type == PromptType.GUIDED_TEMPLATE:
            return self.generate_guided_template_prompt(context)
        else:
            return self.generate_fallback_prompt(context)

# 全局提示词生成器实例
_prompt_generator = None

def get_prompt_generator() -> TemplatePromptGenerator:
    \"\"\"获取提示词生成器实例（单例模式）\"\"\"
    global _prompt_generator
    if _prompt_generator is None:
        _prompt_generator = TemplatePromptGenerator()
    return _prompt_generator