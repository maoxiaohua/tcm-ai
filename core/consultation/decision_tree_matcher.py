#!/usr/bin/env python3
"""
决策树智能匹配服务 - AI语义匹配版
在患者问诊时,自动匹配医生保存的决策树,实现个性化诊疗

核心理念：
1. 基于中医辨证论治理论，不是简单的文本匹配
2. 利用决策树symptom节点中的完整辨证描述
3. 使用AI进行语义理解和相似度计算
4. 考虑主症、病机、舌脉等多维度匹配
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import asyncio
from app.core.settings import AI_CONFIG

# 导入dashscope用于AI语义分析
try:
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logging.warning("Dashscope not available, falling back to basic matching")

# 导入jieba用于中文分词
try:
    import jieba
except ImportError:
    logging.warning("jieba not available, text similarity calculation will be disabled")

logger = logging.getLogger(__name__)

@dataclass
class DecisionTreeMatch:
    """决策树匹配结果"""
    pattern_id: str
    doctor_id: str
    disease_name: str
    match_score: float
    thinking_process: str
    tree_structure: Dict[str, Any]
    clinical_patterns: str
    usage_count: int
    success_count: int
    confidence: float  # 匹配置信度
    match_reason: str = ""  # 🆕 匹配原因（可解释性）
    syndrome_description: str = ""  # 🆕 提取的证候描述

class DecisionTreeMatcher:
    """决策树智能匹配服务 - AI语义匹配版"""

    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        """初始化决策树匹配服务"""
        self.db_path = db_path
        self.api_key = AI_CONFIG.get("dashscope_api_key", "")

        # 🔑 疾病别名映射 - 支持中医疾病的多种表述
        self.disease_aliases = {
            "感冒": ["感冒", "风寒感冒", "风热感冒", "外感", "伤风", "时行感冒"],
            "咳嗽": ["咳嗽", "咳", "干咳", "痰多咳嗽", "咳痰"],
            "失眠": ["失眠", "不寐", "睡眠障碍", "入睡困难", "多梦"],
            "胃痛": ["胃痛", "胃脘痛", "脘痛", "胃胀", "脾胃不和"],
            "头痛": ["头痛", "头疼", "偏头痛", "巅顶痛"],
            "腹泻": ["腹泻", "泄泻", "大便溏薄", "便溏"],
            "便秘": ["便秘", "大便秘结", "大便难"],
            "心悸": ["心悸", "心慌", "怔忡"],
            "眩晕": ["眩晕", "头晕", "晕"],
            "腰痛": ["腰痛", "腰酸", "腰部疼痛"]
        }

        logger.info(f"✅ 决策树匹配服务初始化完成 (AI语义匹配版): {db_path}")
        if not self.api_key:
            logger.warning("⚠️ DASHSCOPE_API_KEY未设置，将使用基础匹配逻辑")

    def _extract_symptom_node_from_tree(self, tree_structure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从决策树结构中提取symptom类型的节点

        symptom节点包含了完整的辨证描述，是匹配的核心依据
        例如："外感风热，邪袭肺卫。患者发热恶风，汗出不畅，头痛鼻塞..."
        """
        try:
            nodes = tree_structure.get('nodes', [])
            for node in nodes:
                if node.get('type') == 'symptom':
                    return node

            # 如果没有symptom节点，尝试使用第二个节点（通常是症状描述）
            if len(nodes) >= 2:
                logger.info(f"未找到symptom节点，使用第二个节点作为症状描述")
                return nodes[1]

            return None
        except Exception as e:
            logger.error(f"提取symptom节点失败: {e}")
            return None

    async def _calculate_ai_semantic_similarity(
        self,
        patient_description: str,
        syndrome_description: str
    ) -> Tuple[float, str]:
        """
        使用AI计算患者描述与决策树证候描述的语义相似度

        返回：(相似度分数 0-1, 匹配原因说明)
        """
        if not DASHSCOPE_AVAILABLE or not self.api_key:
            # 降级为基础文本匹配
            return self._fallback_similarity(patient_description, syndrome_description)

        try:
            prompt = f"""你是一位资深中医专家，请判断患者症状是否匹配某个临床证候的决策树。

⚠️ 重要判断原则：
1. 必须区分【主病】和【伴随症状】
   - 如果决策树描述的是某个伴随症状（如单纯头痛、单纯咳嗽），而患者是外感疾病（发热+多症状），不应高度匹配
   - 例如：患者"发热38度+头痛+咽痛+鼻塞+咳嗽" → 决策树"头痛（跳着痛）" → 低分(0.2)，因为患者主病是外感，不是单纯头痛

2. 病机必须一致
   - 患者是外感风热（发热+黄痰+咽痛） → 决策树"风寒感冒"（恶寒+清涕） → 低分

3. 症状群必须匹配
   - 患者描述3-5个症状，决策树也应涵盖这些症状

【患者描述】
{patient_description}

【决策树证候描述】
{syndrome_description}

请直接返回JSON格式：
{{
    "match_score": 0.85,  // 0-1之间的匹配分数，请严格评估
    "reason": "主症高度吻合，病机一致",  // 简短说明
    "is_main_disease": true,  // 决策树是否针对患者的主病（不是伴随症状）
    "pathogenesis_match": true   // 病机是否匹配
}}

⚠️ 评分标准：
- 0.8-1.0: 主病+病机+症状群完全匹配
- 0.5-0.7: 主病匹配，但病机或部分症状不符
- 0.2-0.4: 仅有伴随症状匹配，主病不符
- 0.0-0.1: 完全不匹配

只返回JSON，不要其他内容。"""

            response = Generation.call(
                model='qwen-max',
                api_key=self.api_key,
                prompt=prompt,
                result_format='message'
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                # 提取JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    score = float(result.get('match_score', 0))
                    reason = result.get('reason', '')

                    logger.info(f"🤖 AI语义匹配: 分数={score:.2f}, 原因={reason}")
                    return (score, reason)

            # AI调用失败，降级
            logger.warning("AI调用失败，使用基础匹配")
            return self._fallback_similarity(patient_description, syndrome_description)

        except Exception as e:
            logger.error(f"AI语义分析失败: {e}")
            return self._fallback_similarity(patient_description, syndrome_description)

    def _fallback_similarity(self, text1: str, text2: str) -> Tuple[float, str]:
        """
        降级方案：基于关键词匹配的相似度计算
        """
        # 提取关键症状词
        症状关键词 = [
            "发热", "恶寒", "恶风", "头痛", "咳嗽", "咽痛", "鼻塞",
            "口渴", "汗出", "胃痛", "腹痛", "便秘", "腹泻", "失眠",
            "心悸", "气短", "乏力", "舌红", "舌淡", "苔黄", "苔白",
            "脉浮", "脉沉", "脉数", "脉迟"
        ]

        matched_keywords = []
        total_keywords_in_syndrome = 0

        for keyword in 症状关键词:
            if keyword in text2:  # 决策树中包含此症状
                total_keywords_in_syndrome += 1
                if keyword in text1:  # 患者也有此症状
                    matched_keywords.append(keyword)

        if total_keywords_in_syndrome == 0:
            return (0.0, "无关键症状匹配")

        match_rate = len(matched_keywords) / total_keywords_in_syndrome
        reason = f"症状匹配: {len(matched_keywords)}/{total_keywords_in_syndrome} ({', '.join(matched_keywords[:3])}...)"

        logger.info(f"📊 基础匹配: {reason}, 匹配率={match_rate:.2f}")
        return (match_rate, reason)

    async def find_matching_patterns(
        self,
        disease_name: str,
        symptoms: List[str],
        patient_description: str = "",
        doctor_id: Optional[str] = None,
        min_match_score: float = 0.6  # 🆕 AI语义匹配，提高阈值确保质量
    ) -> List[DecisionTreeMatch]:
        """
        查找匹配的决策树 - AI语义匹配版

        核心逻辑：
        1. 从决策树中提取symptom节点（包含完整辨证描述）
        2. 使用AI计算患者描述与symptom节点的语义相似度
        3. 基于相似度、历史成功率等综合评分

        Args:
            disease_name: 疾病名称（AI提取，可能不准确）
            symptoms: 患者症状列表
            patient_description: 患者完整描述（最重要！）
            doctor_id: 指定医生ID(可选)
            min_match_score: 最小匹配分数阈值（0.6表示至少60%相似度）

        Returns:
            匹配的决策树列表,按匹配分数排序
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 🔑 医生ID映射
            actual_doctor_id = doctor_id
            if doctor_id and not doctor_id.startswith('usr_'):
                doctor_name_map = {
                    'jin_daifu': '金大夫',
                    'zhang_zhongjing': '张仲景'
                }
                doctor_name = doctor_name_map.get(doctor_id, doctor_id)

                cursor.execute("""
                    SELECT user_id FROM doctors
                    WHERE name = ?
                    LIMIT 1
                """, (doctor_name,))

                doctor_row = cursor.fetchone()
                if doctor_row and doctor_row['user_id']:
                    actual_doctor_id = doctor_row['user_id']
                    logger.info(f"🔄 医生ID映射: {doctor_id} ({doctor_name}) → {actual_doctor_id}")

            # 🔧 查询决策树
            if actual_doctor_id:
                logger.info(f"🔍 查询医生 {actual_doctor_id} 的决策树（AI语义匹配模式）")
                cursor.execute("""
                    SELECT * FROM doctor_clinical_patterns
                    WHERE doctor_id = ?
                    ORDER BY usage_count DESC, success_count DESC
                """, (actual_doctor_id,))
            else:
                logger.info(f"🔍 查询所有医生的决策树")
                cursor.execute("""
                    SELECT * FROM doctor_clinical_patterns
                    ORDER BY usage_count DESC, success_count DESC
                """)

            patterns = cursor.fetchall()
            conn.close()

            if not patterns:
                logger.info("❌ 未找到任何医生决策树")
                return []

            logger.info(f"📚 找到 {len(patterns)} 个决策树，开始AI语义匹配...")

            # 🆕 使用AI语义匹配
            matches = []
            for pattern in patterns:
                try:
                    tree_structure = json.loads(pattern['tree_structure'])
                except:
                    logger.warning(f"决策树 {pattern['id']} 结构解析失败，跳过")
                    continue

                # 提取symptom节点
                symptom_node = self._extract_symptom_node_from_tree(tree_structure)
                if not symptom_node:
                    logger.warning(f"决策树 {pattern['disease_name']} 没有symptom节点，跳过")
                    continue

                syndrome_description = symptom_node.get('description', '') or symptom_node.get('name', '')
                if not syndrome_description:
                    logger.warning(f"决策树 {pattern['disease_name']} symptom节点为空，跳过")
                    continue

                # 🤖 AI语义匹配
                match_score, match_reason = await self._calculate_ai_semantic_similarity(
                    patient_description,
                    syndrome_description
                )

                logger.info(f"🎯 决策树【{pattern['disease_name']}】匹配分数: {match_score:.2f} - {match_reason}")

                if match_score >= min_match_score:
                    # 计算置信度(基于历史成功率和AI匹配分数)
                    usage = pattern['usage_count']
                    success = pattern['success_count']
                    confidence = (success / usage * 0.5 + match_score * 0.5) if usage > 0 else match_score

                    match = DecisionTreeMatch(
                        pattern_id=pattern['id'],
                        doctor_id=pattern['doctor_id'],
                        disease_name=pattern['disease_name'],
                        match_score=match_score,
                        thinking_process=pattern['thinking_process'],
                        tree_structure=tree_structure,  # 已经在上面解析过了
                        clinical_patterns=pattern['clinical_patterns'],
                        usage_count=usage,
                        success_count=success,
                        confidence=confidence,
                        match_reason=match_reason,  # 🆕 匹配原因
                        syndrome_description=syndrome_description  # 🆕 证候描述
                    )
                    matches.append(match)
                    logger.info(f"✅ 决策树【{pattern['disease_name']}】匹配成功！")

            # 🎯 智能排序：考虑疾病类型优先级
            def get_sort_key(match):
                """
                排序关键字计算

                优先级：
                1. AI匹配分数（主要）
                2. 疾病类型（外感疾病 > 单一症状疾病）
                3. 历史成功率（次要）
                """
                # 基础分数：AI匹配分数(70%) + 置信度(30%)
                base_score = match.match_score * 0.7 + match.confidence * 0.3

                # 疾病优先级加成（当分数接近时起决定性作用）
                disease_priority_bonus = self._get_disease_priority_bonus(match.disease_name)

                # 如果AI分数 >= 0.7，疾病优先级加成生效（防止低分疾病因优先级而排前）
                if match.match_score >= 0.7:
                    final_score = base_score + disease_priority_bonus * 0.1  # 最多增加0.03分
                else:
                    final_score = base_score

                return final_score

            matches.sort(key=get_sort_key, reverse=True)

            if matches:
                logger.info(f"🎉 找到 {len(matches)} 个匹配的决策树！最佳匹配: {matches[0].disease_name} (分数: {matches[0].match_score:.2f})")
                # 🔍 调试信息：显示前3个匹配结果
                for i, m in enumerate(matches[:3]):
                    priority = self._get_disease_priority_bonus(m.disease_name)
                    logger.info(f"  {i+1}. {m.disease_name}: 分数={m.match_score:.2f}, 优先级={priority:.1f}, 原因={m.match_reason}")
            else:
                logger.info(f"❌ 未找到匹配的决策树 (最低阈值: {min_match_score})")

            return matches

        except Exception as e:
            logger.error(f"查找决策树失败: {e}")
            return []

    def _calculate_match_score(
        self,
        pattern: sqlite3.Row,
        disease_name: str,
        symptoms: List[str],
        patient_description: str
    ) -> float:
        """
        计算决策树匹配分数

        匹配算法:
        1. 疾病名称完全匹配: 0.4分
        2. 疾病别名匹配: 0.35分
        3. 核心疾病词匹配: 0.3分 (如"胃痛"匹配"脾胃虚寒型胃痛")
        4. 症状匹配度: 0.5分 (提高权重，支持症状驱动的匹配)
        5. 临床模式文本相似度: 0.2分
        """
        total_score = 0.0
        disease_match_score = 0.0

        # 1. 疾病名称匹配 (权重: 0.4)
        pattern_disease = pattern['disease_name']
        if disease_name == pattern_disease:
            # 完全匹配
            disease_match_score = 0.4
        elif self._is_disease_alias(disease_name, pattern_disease):
            # 别名匹配（增强版，包含感冒类疾病的智能匹配）
            disease_match_score = 0.35
        elif disease_name in pattern_disease:
            # 患者描述的疾病名包含在决策树疾病名中 (如"胃痛" in "脾胃虚寒型胃痛")
            # 这种情况应该给较高分数,因为是核心疾病词匹配
            disease_match_score = 0.3
        elif pattern_disease in disease_name:
            # 决策树疾病名包含在患者描述中
            disease_match_score = 0.25

        total_score += disease_match_score

        # 2. 症状匹配度 (权重: 0.5，提高权重以支持症状驱动的匹配)
        symptom_score = 0.0
        if symptoms:
            symptom_score = self._calculate_symptom_match(
                pattern['thinking_process'],
                pattern['clinical_patterns'],
                symptoms
            )
            total_score += symptom_score * 0.5

            # 🔑 关键优化：如果疾病名称匹配度低，但症状匹配度高，仍然给予较高总分
            # 例如：AI提取"发热"，决策树是"风热感冒"，但症状高度吻合
            if disease_match_score < 0.3 and symptom_score >= 0.6:
                logger.info(f"⚡ 症状驱动匹配: 疾病'{disease_name}'→'{pattern_disease}', 症状匹配度={symptom_score:.2f}")
                # 给予额外的疾病匹配分数补偿
                total_score += 0.15

        # 3. 临床模式文本相似度 (权重: 0.2)
        if patient_description:
            text_similarity = self._calculate_text_similarity(
                patient_description,
                pattern['thinking_process'] + " " + pattern['clinical_patterns']
            )
            total_score += text_similarity * 0.2

        return min(total_score, 1.0)

    def _get_disease_priority_bonus(self, disease_name: str) -> float:
        """
        获取疾病优先级加成分数

        分类逻辑：
        1. 外感疾病（感冒、咳嗽等）- 优先级高（0.3）
           - 特征：多症状综合征，有明确病机
        2. 内伤疾病（胃痛、失眠等）- 优先级中（0.2）
           - 特征：慢性病症，症状群相对固定
        3. 单一症状（头痛、腰痛等）- 优先级低（0.0）
           - 特征：可能是其他疾病的伴随症状

        这样当患者是"发热+头痛+咽痛"时，"风热感冒"会优先于"头痛"被选中
        """
        # 外感疾病（最高优先级）
        外感疾病 = ["感冒", "风寒感冒", "风热感冒", "咳嗽", "外感", "时行感冒", "伤寒", "温病"]
        for disease in 外感疾病:
            if disease in disease_name:
                return 0.3

        # 内伤杂病（中等优先级）
        内伤疾病 = ["胃痛", "脾胃", "失眠", "心悸", "眩晕", "腹泻", "便秘", "水肿"]
        for disease in 内伤疾病:
            if disease in disease_name:
                return 0.2

        # 单一症状（低优先级）
        单一症状 = ["头痛", "腰痛", "膝痛", "关节痛", "咽痛", "鼻塞", "流涕"]
        for symptom in 单一症状:
            if symptom == disease_name or disease_name.startswith(symptom):
                return 0.0

        # 默认中等优先级
        return 0.1

    def _is_disease_alias(self, disease1: str, disease2: str) -> bool:
        """
        检查两个疾病名称是否为别名关系

        策略：
        1. 完全匹配同一个别名组
        2. 部分匹配：disease1包含在disease2的别名组中，或反之
        """
        for main_disease, aliases in self.disease_aliases.items():
            # 完全匹配：两个疾病都在同一个别名组中
            if disease1 in aliases and disease2 in aliases:
                return True

            # 部分匹配：disease1在别名组中，且disease2包含别名组中的任意词
            if disease1 in aliases:
                for alias in aliases:
                    if alias in disease2 or disease2 in alias:
                        logger.info(f"🔍 疾病别名匹配: '{disease1}' ↔ '{disease2}' (通过'{alias}')")
                        return True

            # 部分匹配：disease2在别名组中，且disease1包含别名组中的任意词
            if disease2 in aliases:
                for alias in aliases:
                    if alias in disease1 or disease1 in alias:
                        logger.info(f"🔍 疾病别名匹配: '{disease1}' ↔ '{disease2}' (通过'{alias}')")
                        return True

        return False

    def _calculate_symptom_match(
        self,
        thinking_process: str,
        clinical_patterns: str,
        symptoms: List[str]
    ) -> float:
        """计算症状匹配度"""
        if not symptoms:
            return 0.0

        combined_text = thinking_process + " " + clinical_patterns
        matched_count = 0

        for symptom in symptoms:
            if symptom in combined_text:
                matched_count += 1

        return matched_count / len(symptoms) if symptoms else 0.0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度(基于关键词重叠)"""
        # 分词
        words1 = set(jieba.cut(text1))
        words2 = set(jieba.cut(text2))

        # 过滤停用词
        stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
        words1 = words1 - stopwords
        words2 = words2 - stopwords

        if not words1 or not words2:
            return 0.0

        # Jaccard相似度
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    async def get_pattern_by_id(self, pattern_id: str) -> Optional[DecisionTreeMatch]:
        """根据ID获取决策树"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM doctor_clinical_patterns WHERE id = ?
            """, (pattern_id,))

            pattern = cursor.fetchone()
            conn.close()

            if not pattern:
                return None

            try:
                tree_structure = json.loads(pattern['tree_structure'])
            except:
                tree_structure = {}

            usage = pattern['usage_count']
            success = pattern['success_count']
            confidence = (success / usage) if usage > 0 else 0.5

            return DecisionTreeMatch(
                pattern_id=pattern['id'],
                doctor_id=pattern['doctor_id'],
                disease_name=pattern['disease_name'],
                match_score=1.0,
                thinking_process=pattern['thinking_process'],
                tree_structure=tree_structure,
                clinical_patterns=pattern['clinical_patterns'],
                usage_count=usage,
                success_count=success,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"获取决策树失败: {e}")
            return None

    async def record_pattern_usage(
        self,
        pattern_id: str,
        success: bool = False,
        feedback: Optional[str] = None
    ):
        """记录决策树使用情况"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if success:
                cursor.execute("""
                    UPDATE doctor_clinical_patterns
                    SET usage_count = usage_count + 1,
                        success_count = success_count + 1,
                        last_used_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), pattern_id))
            else:
                cursor.execute("""
                    UPDATE doctor_clinical_patterns
                    SET usage_count = usage_count + 1,
                        last_used_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), pattern_id))

            conn.commit()
            conn.close()

            logger.info(f"✅ 记录决策树使用: {pattern_id}, 成功: {success}")

        except Exception as e:
            logger.error(f"记录决策树使用失败: {e}")

    def extract_symptoms_from_text(self, text: str) -> List[str]:
        """从文本中提取症状关键词"""
        symptoms = []

        # 常见症状关键词
        symptom_keywords = [
            "头痛", "头疼", "发热", "发烧", "咳嗽", "失眠", "多梦",
            "胃痛", "腹痛", "腹泻", "便秘", "心悸", "心慌", "乏力",
            "食欲不振", "恶心", "呕吐", "胸闷", "气短", "眩晕",
            "耳鸣", "怕冷", "怕热", "出汗", "盗汗", "口干", "口苦",
            "咽痛", "鼻塞", "流涕", "腰痛", "膝痛", "关节痛"
        ]

        for keyword in symptom_keywords:
            if keyword in text:
                symptoms.append(keyword)

        return list(set(symptoms))  # 去重

    def extract_disease_from_text(self, text: str) -> Optional[str]:
        """
        从文本中提取疾病名称

        策略：找到所有匹配的疾病，优先选择在文本中最早出现的（主要症状）
        例如："胃脘隐痛...大便溏薄" → 优先返回"胃痛"而不是"腹泻"
        """
        matched_diseases = []

        for main_disease, aliases in self.disease_aliases.items():
            for alias in aliases:
                if alias in text:
                    # 记录疾病名称和在文本中的位置
                    position = text.find(alias)
                    matched_diseases.append((main_disease, position, alias))
                    break  # 找到一个别名就跳出，避免重复

        if not matched_diseases:
            return None

        # 按照在文本中的位置排序，选择最早出现的疾病
        matched_diseases.sort(key=lambda x: x[1])

        selected_disease = matched_diseases[0][0]
        logger.info(f"🔍 疾病提取: 找到 {len(matched_diseases)} 个候选疾病，选择最早出现的 '{selected_disease}'")

        return selected_disease

# 全局单例
_matcher_instance = None

def get_decision_tree_matcher() -> DecisionTreeMatcher:
    """获取决策树匹配器单例"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = DecisionTreeMatcher()
    return _matcher_instance
