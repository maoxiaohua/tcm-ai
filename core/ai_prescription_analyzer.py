#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实的AI处方分析服务
使用阿里云Dashscope API进行真实的中医处方智能分析
"""

import dashscope
from dashscope import Generation
import logging
import json
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AIPrescriptionAnalyzer:
    """AI处方分析器 - 使用真实的AI模型"""

    def __init__(self):
        self.model = "qwen-max"

    def analyze_prescription_comprehensive(self, prescription_content: str, diagnosis: str = "", symptoms: str = "") -> Dict:
        """
        全面分析处方

        Args:
            prescription_content: 处方内容
            diagnosis: 诊断信息
            symptoms: 症状信息

        Returns:
            分析结果字典
        """
        try:
            prompt = f"""你是一位资深的中医药学专家，请对以下处方进行全面的专业分析。

【患者症状】
{symptoms or "未提供"}

【中医诊断】
{diagnosis or "未提供"}

【处方内容】
{prescription_content}

请从以下几个维度进行专业分析，并以JSON格式返回：

1. **安全性评分** (safety_score: 0-1之间的小数)
   - 评估处方的用药安全性
   - 检查是否有剂量过大、配伍禁忌等问题

2. **疗效评分** (efficacy_score: 0-1之间的小数)
   - 评估处方对症状的针对性
   - 判断方药配伍的合理性

3. **中医理论符合度** (tcm_theory_compliance: 0-1之间的小数)
   - 评估是否符合中医辨证论治原则
   - 检查君臣佐使配伍是否合理

4. **风险等级** (risk_level: "low", "medium", "high")
   - low: 安全性高，无明显风险
   - medium: 存在一定注意事项，需要监测
   - high: 存在明显风险，需要调整

5. **置信度** (confidence: 0-1之间的小数)
   - 本次分析的可信度

6. **药物相互作用** (drug_interactions: 列表)
   - 列出潜在的药物相互作用，每项包含：
     - interaction: 相互作用描述
     - severity: 严重程度 (low/medium/high)

7. **剂量警告** (dosage_warnings: 列表)
   - 列出需要注意的剂量问题

8. **禁忌症** (contraindications: 列表)
   - 列出使用禁忌

9. **中医证型** (tcm_pattern: 字符串)
   - 判断对应的中医证型

10. **方剂结构** (formula_structure: 字典)
    - monarch: 君药列表
    - minister: 臣药列表
    - assistant: 佐药列表
    - envoy: 使药列表

11. **建议** (recommendations: 列表)
    - 给出具体的用药建议和注意事项

请严格按照以下JSON格式返回，不要包含任何其他文字：
{{
    "safety_score": 0.85,
    "efficacy_score": 0.88,
    "tcm_theory_compliance": 0.92,
    "risk_level": "low",
    "confidence": 0.90,
    "drug_interactions": [
        {{"interaction": "描述", "severity": "low"}}
    ],
    "dosage_warnings": ["警告内容"],
    "contraindications": ["禁忌内容"],
    "tcm_pattern": "证型名称",
    "formula_structure": {{
        "monarch": ["药名"],
        "minister": ["药名"],
        "assistant": ["药名"],
        "envoy": ["药名"]
    }},
    "recommendations": ["建议内容"]
}}
"""

            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3,
                top_p=0.8
            )

            if response.status_code == 200:
                result_text = response.output.text.strip()

                # 提取JSON内容
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info(f"✅ AI处方全面分析完成")
                    return result
                else:
                    logger.error("❌ 无法从AI响应中提取JSON")
                    return self._get_fallback_analysis()
            else:
                logger.error(f"❌ AI API调用失败: {response.code} - {response.message}")
                return self._get_fallback_analysis()

        except Exception as e:
            logger.error(f"❌ AI处方分析失败: {e}")
            return self._get_fallback_analysis()

    def analyze_prescription_safety(self, prescription_content: str) -> Dict:
        """
        安全性分析

        Args:
            prescription_content: 处方内容

        Returns:
            安全性分析结果
        """
        try:
            prompt = f"""你是一位中医药安全专家，请对以下处方进行安全性分析。

【处方内容】
{prescription_content}

请重点分析：
1. 用药剂量是否安全
2. 是否存在配伍禁忌
3. 可能的副作用和风险
4. 需要监测的指标

请以JSON格式返回：
{{
    "safety_score": 0.85,
    "risk_factors": [
        {{
            "factor": "风险因素名称",
            "level": "low/medium/high",
            "description": "详细描述"
        }}
    ],
    "warnings": ["警告内容"],
    "monitoring_points": ["需要监测的指标"]
}}
"""

            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=1500,
                temperature=0.2,
                top_p=0.7
            )

            if response.status_code == 200:
                result_text = response.output.text.strip()
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info(f"✅ AI处方安全性分析完成")
                    return result

            return self._get_fallback_safety_analysis()

        except Exception as e:
            logger.error(f"❌ AI安全性分析失败: {e}")
            return self._get_fallback_safety_analysis()

    def analyze_risk_assessment(self, prescriptions_data: List[Dict]) -> Dict:
        """
        批量处方风险评估

        Args:
            prescriptions_data: 处方数据列表，每个包含 {prescription_content, diagnosis, symptoms}

        Returns:
            风险评估结果
        """
        try:
            # 构建批量分析提示
            prescriptions_summary = []
            for i, p in enumerate(prescriptions_data[:20], 1):  # 最多分析20个
                prescriptions_summary.append(f"""
处方{i}:
症状: {p.get('symptoms', '未知')[:100]}
诊断: {p.get('diagnosis', '未知')[:100]}
处方: {p.get('prescription_content', '')[:200]}
""")

            prompt = f"""你是一位中医药风险管理专家，请对以下批量处方进行风险评估和统计分析。

共有 {len(prescriptions_data)} 份处方需要分析。

【处方概览】
{''.join(prescriptions_summary)}

请进行风险评估和统计分析，以JSON格式返回：
{{
    "total_prescriptions": {len(prescriptions_data)},
    "risk_distribution": {{
        "high": 数量,
        "medium": 数量,
        "low": 数量
    }},
    "risk_factors": [
        {{
            "factor": "风险因素名称",
            "count": 出现次数,
            "severity": "high/medium/low",
            "description": "描述"
        }}
    ],
    "common_issues": [
        "发现的共性问题"
    ],
    "recommendations": [
        "整体建议"
    ]
}}
"""

            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3,
                top_p=0.8
            )

            if response.status_code == 200:
                result_text = response.output.text.strip()
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info(f"✅ AI批量风险评估完成")
                    return result

            return self._get_fallback_risk_assessment(len(prescriptions_data))

        except Exception as e:
            logger.error(f"❌ AI风险评估失败: {e}")
            return self._get_fallback_risk_assessment(len(prescriptions_data))

    def generate_insights(self, stats: Dict, recent_prescriptions: List[Dict] = None) -> Dict:
        """
        生成AI洞察分析

        Args:
            stats: 统计数据
            recent_prescriptions: 近期处方列表

        Returns:
            洞察分析结果
        """
        try:
            # 构建处方概览
            prescriptions_summary = ""
            if recent_prescriptions:
                for i, p in enumerate(recent_prescriptions[:10], 1):
                    prescriptions_summary += f"处方{i}: {p.get('diagnosis', '未知')[:50]} - {p.get('symptoms', '未知')[:50]}\n"

            prompt = f"""你是一位中医药数据分析专家，请根据以下统计数据和近期处方情况，提供专业的AI洞察分析。

【统计数据】
- 总处方数: {stats.get('total_prescriptions', 0)}
- 已审核数: {stats.get('approved_count', 0)}
- 今日处方: {stats.get('today_count', 0)}
- 本人审核: {stats.get('reviewed_by_me', 0)}

【近期处方概览】
{prescriptions_summary or "暂无详细数据"}

请提供以下分析，以JSON格式返回：
{{
    "trends": {{
        "prescription_volume": {{
            "direction": "increasing/stable/decreasing",
            "change_percent": 数值,
            "analysis": "分析说明"
        }},
        "approval_rate": {{
            "current": 审核通过率百分比,
            "trend": "improving/stable/declining",
            "analysis": "分析说明"
        }}
    }},
    "patterns": [
        "发现的疾病/证型模式1",
        "发现的疾病/证型模式2"
    ],
    "alerts": [
        "需要关注的风险或异常1",
        "需要关注的风险或异常2"
    ],
    "recommendations": [
        "具体可执行的建议1",
        "具体可执行的建议2"
    ]
}}
"""

            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=1500,
                temperature=0.4,
                top_p=0.8
            )

            if response.status_code == 200:
                result_text = response.output.text.strip()
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info(f"✅ AI洞察分析完成")
                    return result

            return self._get_fallback_insights(stats)

        except Exception as e:
            logger.error(f"❌ AI洞察分析失败: {e}")
            return self._get_fallback_insights(stats)

    def _get_fallback_insights(self, stats: Dict) -> Dict:
        """降级返回基础洞察"""
        total = stats.get('total_prescriptions', 0)
        approved = stats.get('approved_count', 0)
        approval_rate = (approved / total * 100) if total > 0 else 0

        return {
            "trends": {
                "prescription_volume": {
                    "direction": "stable",
                    "change_percent": 0,
                    "analysis": "数据分析中"
                },
                "approval_rate": {
                    "current": round(approval_rate, 1),
                    "trend": "stable",
                    "analysis": "数据分析中"
                }
            },
            "patterns": ["数据量不足，暂无明显模式"],
            "alerts": ["AI分析服务暂时不可用"],
            "recommendations": ["建议继续积累数据以获得更精准的分析"]
        }

    def _get_fallback_analysis(self) -> Dict:
        """降级返回基础分析结果"""
        return {
            "safety_score": 0.80,
            "efficacy_score": 0.80,
            "tcm_theory_compliance": 0.85,
            "risk_level": "low",
            "confidence": 0.60,
            "drug_interactions": [],
            "dosage_warnings": ["AI分析服务暂时不可用，建议人工复核"],
            "contraindications": [],
            "tcm_pattern": "待人工判断",
            "formula_structure": {
                "monarch": [],
                "minister": [],
                "assistant": [],
                "envoy": []
            },
            "recommendations": [
                "当前为基础评估，建议进行人工专业审核"
            ]
        }

    def _get_fallback_safety_analysis(self) -> Dict:
        """降级返回基础安全分析"""
        return {
            "safety_score": 0.75,
            "risk_factors": [
                {
                    "factor": "AI服务不可用",
                    "level": "medium",
                    "description": "建议人工审核"
                }
            ],
            "warnings": ["建议进行人工安全审核"],
            "monitoring_points": ["常规监测指标"]
        }

    def _get_fallback_risk_assessment(self, total: int) -> Dict:
        """降级返回基础风险评估"""
        return {
            "total_prescriptions": total,
            "risk_distribution": {
                "high": 0,
                "medium": max(1, int(total * 0.3)),
                "low": total - max(1, int(total * 0.3))
            },
            "risk_factors": [
                {
                    "factor": "AI分析不可用",
                    "count": total,
                    "severity": "medium",
                    "description": "建议人工审核"
                }
            ],
            "common_issues": ["AI服务暂时不可用"],
            "recommendations": ["建议进行人工专业审核"]
        }


# 全局单例
_analyzer_instance = None

def get_ai_analyzer() -> AIPrescriptionAnalyzer:
    """获取AI分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = AIPrescriptionAnalyzer()
    return _analyzer_instance
