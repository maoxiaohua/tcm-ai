#!/usr/bin/env python3
"""
简化的模板化AI提示词生成器
强制AI严格按照预定义模板回复
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """提示词类型"""
    STRICT_TEMPLATE = "strict_template"
    GUIDED_TEMPLATE = "guided_template"
    FALLBACK = "fallback"

@dataclass
class SimpleTemplateContext:
    """简化模板提示词上下文"""
    stage: str
    doctor_persona: str
    patient_message: str
    conversation_history: List[Dict]
    available_info: Dict[str, Any]

class SimpleTemplatePromptGenerator:
    """简化的模板化AI提示词生成器"""
    
    def __init__(self):
        """初始化提示词生成器"""
        self.doctor_info = {
            "zhang_zhongjing": {"name": "张仲景", "school": "伤寒派"},
            "ye_tianshi": {"name": "叶天士", "school": "温病派"},
            "li_dongyuan": {"name": "李东垣", "school": "脾胃派"},
            "zhu_danxi": {"name": "朱丹溪", "school": "滋阴派"},
            "liu_duzhou": {"name": "刘渡舟", "school": "经方派"},
            "zheng_qin_an": {"name": "郑钦安", "school": "扶阳派"}
        }
    
    def generate_optimal_prompt(self, context: SimpleTemplateContext) -> str:
        """生成最优提示词"""
        try:
            doctor_info = self.doctor_info.get(context.doctor_persona, {"name": "中医师", "school": "传统中医"})
            
            # 构建基础指令
            base_instruction = f"""你是一位遵循{doctor_info['school']}的{doctor_info['name']}风格中医师。

**严格要求**:
1. 必须按照中医标准格式回复
2. 只能推荐中药材和中医疗法
3. 严禁提及任何西药或化学药物
4. 必须包含医疗安全声明
5. 回复内容专业、准确、安全

**当前任务**:
- 医生角色: {doctor_info['name']} ({doctor_info['school']})
- 患者消息: {context.patient_message}
- 可用信息: {self._format_available_info(context.available_info)}

**回复要求**:
- 保持专业的中医师身份
- 基于四诊合参原则
- 如信息充足则给出处方建议
- 如信息不足则继续问诊
- 必须包含"本建议仅供参考，请咨询专业医师"声明

请基于以上要求专业回复患者。"""
            
            return base_instruction
            
        except Exception as e:
            logger.error(f"生成提示词失败: {e}")
            return self._generate_fallback_prompt(context)
    
    def _format_available_info(self, available_info: Dict[str, Any]) -> str:
        """格式化可用信息"""
        if not available_info:
            return "暂无已收集信息"
        
        info_lines = []
        for key, value in available_info.items():
            if value:
                info_lines.append(f"{key}: {value}")
        
        return "; ".join(info_lines) if info_lines else "暂无已收集信息"
    
    def _generate_fallback_prompt(self, context: SimpleTemplateContext) -> str:
        """生成备用提示词"""
        doctor_info = self.doctor_info.get(context.doctor_persona, {"name": "中医师", "school": "传统中医"})
        
        return f"""请作为{doctor_info['name']}回复患者问题: {context.patient_message}

要求:
1. 保持中医师的专业身份
2. 只推荐中药和中医疗法
3. 包含医疗安全声明
4. 回复简洁明了"""

# 全局提示词生成器实例
_simple_prompt_generator = None

def get_simple_prompt_generator() -> SimpleTemplatePromptGenerator:
    """获取简化提示词生成器实例"""
    global _simple_prompt_generator
    if _simple_prompt_generator is None:
        _simple_prompt_generator = SimpleTemplatePromptGenerator()
    return _simple_prompt_generator