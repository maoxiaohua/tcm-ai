#!/usr/bin/env python3
"""
AI智能决策树生成器 - 思维导图模式
自动分析医生诊疗思路，生成结构化的思维导图式决策树

核心功能：
1. 分析医生的自然语言描述
2. 自动识别：主证、证见、处方、药物加减
3. 生成思维导图形式的决策树结构
4. 支持多分支证候鉴别
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class SyndromeNode:
    """证候节点"""
    syndrome_name: str  # 证候名称，如"风热犯表"
    symptoms: List[str]  # 症状列表
    tongue_pulse: str  # 舌脉描述
    pathogenesis: str  # 病机分析

@dataclass
class PrescriptionNode:
    """处方节点"""
    formula_name: str  # 方剂名称
    base_herbs: List[Dict[str, str]]  # 基础药物 [{"name": "桑叶", "dosage": "10g", "role": "君药"}]
    modifications: List[Dict[str, Any]]  # 加减法 [{"condition": "热重", "add": ["黄芩"], "remove": []}]
    instructions: str  # 煎服法

@dataclass
class MindMapDecisionTree:
    """思维导图式决策树"""
    disease_name: str  # 主病名称
    main_syndrome: str  # 主证
    syndrome_branches: List[Dict[str, Any]]  # 证候分支
    nodes: List[Dict[str, Any]]  # 节点列表（用于Canvas渲染）
    connections: List[Dict[str, str]]  # 连接关系
    metadata: Dict[str, Any]  # 元数据

class AIDecisionTreeGenerator:
    """AI智能决策树生成器"""

    def __init__(self):
        self.api_key = os.getenv('DASHSCOPE_API_KEY', '')
        if not DASHSCOPE_AVAILABLE or not self.api_key:
            logger.warning("⚠️ Dashscope不可用，AI决策树生成功能将被禁用")

    async def analyze_and_generate(
        self,
        doctor_input: str,
        doctor_id: str
    ) -> MindMapDecisionTree:
        """
        分析医生输入并生成思维导图式决策树

        Args:
            doctor_input: 医生的自然语言诊疗思路
            doctor_id: 医生ID

        Returns:
            MindMapDecisionTree: 思维导图式决策树
        """
        logger.info(f"🧠 开始AI分析医生诊疗思路，输入长度: {len(doctor_input)}字")

        # Step 1: AI分析医生输入，提取结构化信息
        analysis_result = await self._analyze_thinking_process(doctor_input)

        if not analysis_result:
            raise ValueError("AI分析失败，无法提取诊疗思路")

        # Step 2: 构建思维导图式决策树
        mind_map_tree = self._build_mind_map_tree(analysis_result, doctor_id)

        logger.info(f"✅ 决策树生成完成: {mind_map_tree.disease_name}, {len(mind_map_tree.nodes)}个节点")

        return mind_map_tree

    async def _analyze_thinking_process(self, doctor_input: str) -> Optional[Dict[str, Any]]:
        """
        使用AI分析医生的诊疗思路

        返回结构化数据：
        {
            "disease_name": "风热感冒",
            "main_syndrome": "风热犯表",
            "syndromes": [
                {
                    "name": "风热犯表证",
                    "symptoms": ["发热", "恶风", "汗出不畅", "头痛", "鼻塞", "咽喉肿痛"],
                    "tongue_pulse": "舌边尖红，苔薄黄，脉浮数",
                    "pathogenesis": "外感风热，邪袭肺卫",
                    "prescription": {
                        "formula": "桑菊饮加减",
                        "base_herbs": [
                            {"name": "桑叶", "dosage": "10g", "role": "君药"},
                            {"name": "菊花", "dosage": "10g", "role": "君药"}
                        ],
                        "modifications": [
                            {"condition": "热重", "add": ["黄芩 10g", "板蓝根 15g"], "remove": []},
                            {"condition": "咽痛甚", "add": ["射干 10g", "山豆根 10g"], "remove": []}
                        ]
                    }
                }
            ]
        }
        """
        if not DASHSCOPE_AVAILABLE or not self.api_key:
            logger.error("Dashscope不可用")
            return None

        prompt = f"""你是一位资深中医专家，请分析以下医生的诊疗思路，提取结构化信息。

【医生输入】
{doctor_input}

请识别以下内容并返回JSON格式：
1. **主病名称**：如"风热感冒"、"脾胃虚寒型胃痛"
2. **主证**：核心证候，如"风热犯表"
3. **证候分支**：可能有多个分型，每个包含：
   - 证候名称
   - 症状列表（主症）
   - 舌脉描述
   - 病机分析
   - 对应处方：
     * 方剂名称
     * 基础药物（君臣佐使）
     * 加减法（条件→加什么药、减什么药）

⚠️ 输出格式要求：
```json
{{
    "disease_name": "疾病名称",
    "main_syndrome": "主证",
    "syndromes": [
        {{
            "name": "证候名称（如：风热犯表证）",
            "symptoms": ["发热", "恶风", "头痛", "咽痛", "咳嗽", "痰黄"],
            "tongue_pulse": "舌边尖红，苔薄黄，脉浮数",
            "pathogenesis": "外感风热，邪袭肺卫",
            "prescription": {{
                "formula": "桑菊饮加减",
                "base_herbs": [
                    {{"name": "桑叶", "dosage": "10g", "role": "君药"}},
                    {{"name": "菊花", "dosage": "10g", "role": "君药"}},
                    {{"name": "薄荷", "dosage": "6g", "role": "臣药"}},
                    {{"name": "桔梗", "dosage": "6g", "role": "佐药"}},
                    {{"name": "甘草", "dosage": "3g", "role": "使药"}}
                ],
                "modifications": [
                    {{
                        "condition": "热重",
                        "add": ["黄芩 10g", "板蓝根 15g"],
                        "remove": []
                    }},
                    {{
                        "condition": "咽痛甚",
                        "add": ["射干 10g", "山豆根 10g"],
                        "remove": []
                    }}
                ],
                "instructions": "水煎服，每日1剂，分2次温服"
            }}
        }}
    ]
}}
```

只返回JSON，不要其他内容。"""

        try:
            response = Generation.call(
                model='qwen-max',
                api_key=self.api_key,
                prompt=prompt,
                result_format='message'
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                # 提取JSON
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info(f"🤖 AI分析成功: 提取到疾病={result.get('disease_name')}, {len(result.get('syndromes', []))}个证候分支")
                    return result
                else:
                    logger.error(f"AI返回内容无法解析为JSON: {content[:200]}")
                    return None
            else:
                logger.error(f"AI调用失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return None

    def _build_mind_map_tree(
        self,
        analysis_result: Dict[str, Any],
        doctor_id: str
    ) -> MindMapDecisionTree:
        """
        根据AI分析结果构建思维导图式决策树

        思维导图布局：
        ```
                       [疾病名称]
                            |
                       [主证节点]
                            |
            +---------------+---------------+
            |                               |
        [证候1]                         [证候2]
            |                               |
        [症见描述]                      [症见描述]
            |                               |
        [处方1]                         [处方2]
            |                               |
        [加减法]                        [加减法]
        ```
        """
        disease_name = analysis_result.get('disease_name', '未知疾病')
        main_syndrome = analysis_result.get('main_syndrome', '未知证候')
        syndromes = analysis_result.get('syndromes', [])

        nodes = []
        connections = []
        syndrome_branches = []

        # 布局参数
        start_x = 400  # 中心X坐标
        start_y = 50   # 起始Y坐标
        y_gap = 150    # 垂直间距
        x_gap = 300    # 水平间距（多分支时）

        # 1. 主证根节点（合并疾病名称和主证）
        main_syndrome_id = "main_syndrome"
        main_syndrome_display = f"{disease_name}（{main_syndrome}）" if main_syndrome else disease_name
        nodes.append({
            "id": main_syndrome_id,
            "name": main_syndrome_display,
            "description": main_syndrome_display,
            "type": "disease",
            "x": start_x,
            "y": start_y,
            "style": "root"  # 标记为根节点
        })

        # 2. 证候分支（直接从主证开始）
        syndrome_count = len(syndromes)
        if syndrome_count == 0:
            logger.warning("未提取到任何证候分支")
            syndrome_count = 1
            syndromes = [{
                "name": "基础证候",
                "symptoms": [],
                "tongue_pulse": "",
                "pathogenesis": "",
                "prescription": {"formula": "", "base_herbs": [], "modifications": []}
            }]

        # 计算每个分支的X坐标（居中分布）
        if syndrome_count == 1:
            branch_x_positions = [start_x]
        else:
            total_width = (syndrome_count - 1) * x_gap
            branch_x_positions = [start_x - total_width / 2 + i * x_gap for i in range(syndrome_count)]

        for idx, syndrome in enumerate(syndromes):
            syndrome_name = syndrome.get('name', f'证候{idx+1}')
            symptoms = syndrome.get('symptoms', [])
            tongue_pulse = syndrome.get('tongue_pulse', '')
            pathogenesis = syndrome.get('pathogenesis', '')
            prescription_data = syndrome.get('prescription', {})

            branch_x = branch_x_positions[idx]
            current_y = start_y + y_gap  # 减少一层，从主证后直接开始

            # 2.1 证候节点
            syndrome_id = f"syndrome_{idx}"
            nodes.append({
                "id": syndrome_id,
                "name": syndrome_name,
                "description": syndrome_name,
                "type": "syndrome_branch",
                "x": branch_x,
                "y": current_y,
                "style": "branch"
            })
            connections.append({"from": main_syndrome_id, "to": syndrome_id})

            # 2.2 症见节点（包含症状、舌脉、病机）
            current_y += y_gap
            symptom_id = f"symptom_{idx}"
            symptom_desc = self._format_symptom_description(symptoms, tongue_pulse, pathogenesis)
            nodes.append({
                "id": symptom_id,
                "name": "症见",
                "description": symptom_desc,
                "type": "symptom",
                "x": branch_x,
                "y": current_y,
                "data": {
                    "symptoms": symptoms,
                    "tongue_pulse": tongue_pulse,
                    "pathogenesis": pathogenesis
                }
            })
            connections.append({"from": syndrome_id, "to": symptom_id})

            # 2.3 处方节点
            current_y += y_gap
            prescription_id = f"prescription_{idx}"
            formula_name = prescription_data.get('formula', '未知方剂')
            base_herbs = prescription_data.get('base_herbs', [])
            prescription_desc = self._format_prescription_description(formula_name, base_herbs)
            nodes.append({
                "id": prescription_id,
                "name": formula_name,
                "description": prescription_desc,
                "type": "prescription",
                "x": branch_x,
                "y": current_y,
                "data": {
                    "formula": formula_name,
                    "base_herbs": base_herbs,
                    "instructions": prescription_data.get('instructions', '')
                }
            })
            connections.append({"from": symptom_id, "to": prescription_id})

            # 2.4 加减法节点（如果有多个加减法，可以展开为子节点）
            modifications = prescription_data.get('modifications', [])
            if modifications:
                current_y += y_gap
                for mod_idx, modification in enumerate(modifications):
                    mod_id = f"modification_{idx}_{mod_idx}"
                    condition = modification.get('condition', '')
                    add_herbs = modification.get('add', [])
                    remove_herbs = modification.get('remove', [])

                    mod_desc = f"若{condition}：加 {', '.join(add_herbs)}"
                    if remove_herbs:
                        mod_desc += f"；减 {', '.join(remove_herbs)}"

                    # 多个加减法横向排列
                    mod_x = branch_x + (mod_idx - len(modifications) / 2 + 0.5) * 150

                    nodes.append({
                        "id": mod_id,
                        "name": f"加减：{condition}",
                        "description": mod_desc,
                        "type": "modification",
                        "x": mod_x,
                        "y": current_y,
                        "data": modification
                    })
                    connections.append({"from": prescription_id, "to": mod_id})

            # 保存分支信息
            syndrome_branches.append({
                "syndrome_name": syndrome_name,
                "symptoms": symptoms,
                "tongue_pulse": tongue_pulse,
                "pathogenesis": pathogenesis,
                "prescription": prescription_data
            })

        # 构建元数据
        metadata = {
            "pattern_name": disease_name,
            "main_syndrome": main_syndrome,
            "scenario": "mind_map_auto_generated",
            "created_at": datetime.now().isoformat(),
            "created_by": doctor_id,
            "node_count": len(nodes),
            "connection_count": len(connections),
            "ai_generated": True
        }

        return MindMapDecisionTree(
            disease_name=disease_name,
            main_syndrome=main_syndrome,
            syndrome_branches=syndrome_branches,
            nodes=nodes,
            connections=connections,
            metadata=metadata
        )

    def _format_symptom_description(
        self,
        symptoms: List[str],
        tongue_pulse: str,
        pathogenesis: str
    ) -> str:
        """格式化症见描述"""
        parts = []

        if pathogenesis:
            parts.append(f"病机：{pathogenesis}")

        if symptoms:
            parts.append(f"主症：{' '.join(symptoms)}")

        if tongue_pulse:
            parts.append(f"舌脉：{tongue_pulse}")

        return "。".join(parts) if parts else "症见未详"

    def _format_prescription_description(
        self,
        formula_name: str,
        base_herbs: List[Dict[str, str]]
    ) -> str:
        """格式化处方描述"""
        if not base_herbs:
            return f"方剂：{formula_name}"

        # 按君臣佐使分组
        role_groups = {"君药": [], "臣药": [], "佐药": [], "使药": []}
        for herb in base_herbs:
            name = herb.get('name', '')
            dosage = herb.get('dosage', '')
            role = herb.get('role', '其他')
            if role in role_groups:
                role_groups[role].append(f"{name} {dosage}")

        # 格式化输出
        parts = [f"方剂：{formula_name}"]
        for role, herbs in role_groups.items():
            if herbs:
                parts.append(f"{role}：{', '.join(herbs)}")

        return "。".join(parts)

    def to_database_format(self, mind_map_tree: MindMapDecisionTree) -> Dict[str, Any]:
        """
        转换为数据库存储格式

        返回格式：
        {
            "disease_name": "风热感冒",
            "thinking_process": "主证：风热犯表...",
            "tree_structure": {...},  # nodes + connections
            "clinical_patterns": {...}  # 结构化的证候信息
        }
        """
        # 构建thinking_process文本
        thinking_parts = [
            f"主病：{mind_map_tree.disease_name}",
            f"主证：{mind_map_tree.main_syndrome}",
            ""
        ]

        for idx, branch in enumerate(mind_map_tree.syndrome_branches, 1):
            thinking_parts.append(f"【证候{idx}】{branch['syndrome_name']}")
            thinking_parts.append(f"病机：{branch['pathogenesis']}")
            thinking_parts.append(f"症见：{' '.join(branch['symptoms'])}")
            thinking_parts.append(f"舌脉：{branch['tongue_pulse']}")

            prescription = branch['prescription']
            thinking_parts.append(f"处方：{prescription.get('formula', '')}")

            if prescription.get('base_herbs'):
                herbs_text = "、".join([f"{h['name']}{h['dosage']}" for h in prescription['base_herbs']])
                thinking_parts.append(f"药物：{herbs_text}")

            if prescription.get('modifications'):
                thinking_parts.append("加减：")
                for mod in prescription['modifications']:
                    add_text = "、".join(mod.get('add', []))
                    thinking_parts.append(f"  若{mod['condition']}：加 {add_text}")

            thinking_parts.append("")

        thinking_process = "\n".join(thinking_parts)

        # 树结构
        tree_structure = {
            "nodes": mind_map_tree.nodes,
            "connections": mind_map_tree.connections,
            "metadata": mind_map_tree.metadata
        }

        # 临床模式
        clinical_patterns = json.dumps({
            "main_syndrome": mind_map_tree.main_syndrome,
            "syndromes": mind_map_tree.syndrome_branches
        }, ensure_ascii=False)

        return {
            "disease_name": mind_map_tree.disease_name,
            "thinking_process": thinking_process,
            "tree_structure": json.dumps(tree_structure, ensure_ascii=False),
            "clinical_patterns": clinical_patterns
        }


# 全局单例
_generator_instance = None

def get_ai_decision_tree_generator() -> AIDecisionTreeGenerator:
    """获取AI决策树生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = AIDecisionTreeGenerator()
    return _generator_instance
