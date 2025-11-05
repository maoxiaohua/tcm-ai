#!/usr/bin/env python3
"""
AI通用思维导图生成器
支持多行业的智能思维导图生成

功能特点:
1. 基于qwen-max的AI智能分析
2. 支持医疗、技术、商业等多个领域
3. 自动识别层级结构和节点关系
4. 生成标准化的树状数据结构
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from dashscope import Generation
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logging.warning("dashscope not available, AI features will be limited")

logger = logging.getLogger(__name__)


@dataclass
class MindMapNode:
    """思维导图节点"""
    id: str
    title: str  # 节点标题
    content: str  # 节点内容描述
    level: int  # 层级 (0=根节点)
    parent_id: Optional[str]  # 父节点ID
    children: List[str]  # 子节点ID列表
    category: str  # 分类标签
    color: str  # 节点颜色
    metadata: Dict[str, Any]  # 额外元数据


@dataclass
class MindMapStructure:
    """完整思维导图结构"""
    id: str
    title: str  # 主题标题
    description: str  # 主题描述
    domain: str  # 应用领域 (medical/technical/business/other)
    root_node: str  # 根节点ID
    nodes: Dict[str, MindMapNode]  # 所有节点字典
    created_at: str
    updated_at: str


class AIMindMapGenerator:
    """AI思维导图生成器"""

    def __init__(self):
        """初始化生成器"""
        self.api_key = os.getenv('DASHSCOPE_API_KEY', '')
        if self.api_key and DASHSCOPE_AVAILABLE:
            dashscope.api_key = self.api_key
            logger.info("✅ AI思维导图生成器初始化成功")
        else:
            logger.warning("⚠️ DASHSCOPE_API_KEY未设置或dashscope不可用")

    def generate_mindmap(
        self,
        topic: str,
        description: str,
        domain: str = "general",
        max_levels: int = 4,
        max_children: int = 5
    ) -> MindMapStructure:
        """
        生成思维导图

        Args:
            topic: 主题标题
            description: 详细描述
            domain: 应用领域
            max_levels: 最大层级数
            max_children: 每个节点最大子节点数

        Returns:
            完整的思维导图结构
        """
        try:
            logger.info(f"🎨 开始生成思维导图: {topic} (领域: {domain})")

            # 构建AI提示词
            prompt = self._build_generation_prompt(
                topic, description, domain, max_levels, max_children
            )

            # 调用AI生成
            if self.api_key and DASHSCOPE_AVAILABLE:
                ai_response = self._call_qwen_api(prompt)
                nodes_data = self._parse_ai_response(ai_response)
            else:
                # 降级方案：使用模板生成
                nodes_data = self._generate_template_mindmap(topic, description, domain)

            # 构建思维导图结构
            mindmap = self._build_mindmap_structure(
                topic, description, domain, nodes_data
            )

            logger.info(f"✅ 思维导图生成成功，共 {len(mindmap.nodes)} 个节点")
            return mindmap

        except Exception as e:
            logger.error(f"❌ 生成思维导图失败: {str(e)}")
            raise

    def _build_generation_prompt(
        self,
        topic: str,
        description: str,
        domain: str,
        max_levels: int,
        max_children: int
    ) -> str:
        """构建AI生成提示词"""

        domain_examples = {
            "medical": "医疗诊断思路、疾病分析、治疗方案",
            "technical": "技术问题排查、系统架构、故障诊断",
            "business": "商业决策、项目规划、战略分析",
            "general": "通用主题分析"
        }

        domain_desc = domain_examples.get(domain, "通用主题分析")

        prompt = f"""请帮我生成一个思维导图结构，要求如下：

**主题**: {topic}
**描述**: {description}
**领域**: {domain_desc}
**层级要求**: 最多{max_levels}层
**分支要求**: 每个节点最多{max_children}个子节点

请按照以下JSON格式输出思维导图结构：
```json
{{
  "nodes": [
    {{
      "id": "node_1",
      "title": "节点标题",
      "content": "节点详细内容描述",
      "level": 0,
      "parent_id": null,
      "category": "分类标签",
      "children_ids": ["node_2", "node_3"]
    }}
  ]
}}
```

**要求**:
1. 根节点level=0，parent_id=null
2. 子节点level依次递增
3. 节点ID使用 node_1, node_2 格式
4. category用于分类（如：原因、症状、方案、步骤等）
5. 内容要具体、专业、有深度
6. 结构要清晰、层次分明
7. 每个节点的title要简洁（5-15字），content要详细（20-100字）

请直接输出JSON，不要有其他说明文字。"""

        return prompt

    def _call_qwen_api(self, prompt: str) -> str:
        """调用千问API"""
        try:
            response = Generation.call(
                model='qwen-max',
                messages=[
                    {'role': 'system', 'content': '你是一个专业的思维导图生成助手，擅长将复杂主题结构化为清晰的层级关系。'},
                    {'role': 'user', 'content': prompt}
                ],
                result_format='message',
                temperature=0.7
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                logger.info(f"✅ AI响应成功，长度: {len(content)}")
                return content
            else:
                logger.error(f"❌ AI调用失败: {response.message}")
                raise Exception(f"AI API调用失败: {response.message}")

        except Exception as e:
            logger.error(f"❌ 调用千问API异常: {str(e)}")
            raise

    def _parse_ai_response(self, ai_response: str) -> List[Dict[str, Any]]:
        """解析AI响应的JSON数据"""
        try:
            # 提取JSON部分
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("响应中未找到有效的JSON")

            json_str = ai_response[json_start:json_end]
            data = json.loads(json_str)

            nodes = data.get('nodes', [])
            logger.info(f"✅ 解析得到 {len(nodes)} 个节点")

            return nodes

        except Exception as e:
            logger.error(f"❌ 解析AI响应失败: {str(e)}")
            # 返回空列表，使用模板生成
            return []

    def _generate_template_mindmap(
        self,
        topic: str,
        description: str,
        domain: str
    ) -> List[Dict[str, Any]]:
        """生成模板思维导图（降级方案）"""

        logger.info("⚠️ 使用模板生成思维导图")

        templates = {
            "medical": {
                "categories": ["病因", "症状", "诊断", "治疗"],
                "sub_items": ["主要原因", "次要原因", "典型症状", "伴随症状"]
            },
            "technical": {
                "categories": ["问题分析", "可能原因", "排查步骤", "解决方案"],
                "sub_items": ["网络层", "系统层", "应用层", "数据层"]
            },
            "business": {
                "categories": ["现状分析", "机会识别", "策略制定", "执行计划"],
                "sub_items": ["市场环境", "竞争态势", "资源评估", "风险分析"]
            }
        }

        template = templates.get(domain, templates["technical"])

        nodes = [
            {
                "id": "node_0",
                "title": topic,
                "content": description,
                "level": 0,
                "parent_id": None,
                "category": "root",
                "children_ids": [f"node_{i+1}" for i in range(len(template["categories"]))]
            }
        ]

        # 生成第一层子节点
        for i, category in enumerate(template["categories"]):
            node_id = f"node_{i+1}"
            children_start = len(nodes) + len(template["categories"])
            children_ids = [f"node_{children_start + j}" for j in range(min(3, len(template["sub_items"])))]

            nodes.append({
                "id": node_id,
                "title": category,
                "content": f"{category}的详细分析和说明",
                "level": 1,
                "parent_id": "node_0",
                "category": category,
                "children_ids": children_ids
            })

        # 生成第二层子节点
        node_counter = len(nodes)
        for i in range(len(template["categories"])):
            for j in range(min(3, len(template["sub_items"]))):
                if j < len(template["sub_items"]):
                    nodes.append({
                        "id": f"node_{node_counter}",
                        "title": template["sub_items"][j],
                        "content": f"{template['sub_items'][j]}的具体内容",
                        "level": 2,
                        "parent_id": f"node_{i+1}",
                        "category": template["categories"][i],
                        "children_ids": []
                    })
                    node_counter += 1

        return nodes

    def _build_mindmap_structure(
        self,
        topic: str,
        description: str,
        domain: str,
        nodes_data: List[Dict[str, Any]]
    ) -> MindMapStructure:
        """构建完整的思维导图结构"""

        # 颜色方案
        color_scheme = {
            0: "#5470c6",  # 蓝色 - 根节点
            1: "#91cc75",  # 绿色 - 一级节点
            2: "#fac858",  # 黄色 - 二级节点
            3: "#ee6666",  # 红色 - 三级节点
            4: "#73c0de",  # 青色 - 四级节点
        }

        nodes = {}
        root_node_id = None

        for node_data in nodes_data:
            node_id = node_data.get('id', f"node_{len(nodes)}")
            level = node_data.get('level', 0)

            if level == 0:
                root_node_id = node_id

            node = MindMapNode(
                id=node_id,
                title=node_data.get('title', '未命名节点'),
                content=node_data.get('content', ''),
                level=level,
                parent_id=node_data.get('parent_id'),
                children=node_data.get('children_ids', []),
                category=node_data.get('category', 'general'),
                color=color_scheme.get(level, "#999999"),
                metadata={}
            )

            nodes[node_id] = node

        # 如果没有根节点，创建一个
        if not root_node_id:
            root_node_id = "node_0"
            nodes[root_node_id] = MindMapNode(
                id=root_node_id,
                title=topic,
                content=description,
                level=0,
                parent_id=None,
                children=list(nodes.keys()),
                category="root",
                color=color_scheme[0],
                metadata={}
            )

        now = datetime.now().isoformat()

        mindmap = MindMapStructure(
            id=f"mindmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=topic,
            description=description,
            domain=domain,
            root_node=root_node_id,
            nodes=nodes,
            created_at=now,
            updated_at=now
        )

        return mindmap

    def export_to_dict(self, mindmap: MindMapStructure) -> Dict[str, Any]:
        """导出为字典格式"""
        return {
            "id": mindmap.id,
            "title": mindmap.title,
            "description": mindmap.description,
            "domain": mindmap.domain,
            "root_node": mindmap.root_node,
            "nodes": {
                node_id: asdict(node)
                for node_id, node in mindmap.nodes.items()
            },
            "created_at": mindmap.created_at,
            "updated_at": mindmap.updated_at
        }

    def export_to_echarts_format(self, mindmap: MindMapStructure) -> Dict[str, Any]:
        """导出为ECharts树图格式"""

        def build_tree_node(node_id: str) -> Dict[str, Any]:
            """递归构建树节点"""
            node = mindmap.nodes[node_id]

            tree_node = {
                "name": node.title,
                "value": node.content,
                "itemStyle": {"color": node.color},
                "label": {"color": "#fff" if node.level == 0 else "#000"},
                "symbolSize": max(60 - node.level * 10, 30),
                "children": []
            }

            # 递归处理子节点
            for child_id in node.children:
                if child_id in mindmap.nodes:
                    tree_node["children"].append(build_tree_node(child_id))

            return tree_node

        root_data = build_tree_node(mindmap.root_node)

        return {
            "title": mindmap.title,
            "data": root_data
        }


# 全局实例
mindmap_generator = AIMindMapGenerator()
