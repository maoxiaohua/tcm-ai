#!/usr/bin/env python3
"""
决策树智能匹配服务
在患者问诊时,自动匹配医生保存的决策树,实现个性化诊疗
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import jieba

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

class DecisionTreeMatcher:
    """决策树智能匹配服务"""

    def __init__(self, db_path: str = "/opt/tcm-ai/data/user_history.sqlite"):
        """初始化决策树匹配服务"""
        self.db_path = db_path

        # 疾病别名映射（扩展版，包含更多中医常用术语）
        self.disease_aliases = {
            "失眠": ["失眠", "不寐", "睡眠障碍", "睡不着", "多梦", "难入睡", "易醒"],
            "便秘": ["便秘", "大便干", "大便难", "排便困难", "大便秘结", "大便不通"],
            "腹泻": ["腹泻", "拉肚子", "泄泻", "便溏"],  # 移除"大便溏"，避免误匹配
            "胃痛": ["胃痛", "胃疼", "胃脘痛", "胃部不适", "胃脘隐痛", "胃脘胀痛", "胃脘灼痛", "脘痛", "脘腹痛"],
            "头痛": ["头痛", "头疼", "偏头痛", "头胀痛", "巅顶痛"],
            "咳嗽": ["咳嗽", "咳", "干咳", "咳痰", "咳喘"],
            "感冒": ["感冒", "风寒", "风热", "外感", "伤风"],
            "发热": ["发热", "发烧", "身热", "壮热", "潮热"],
            "心悸": ["心悸", "心慌", "怔忡", "心跳", "心动悸"]
        }

        logger.info(f"✅ 决策树匹配服务初始化完成: {db_path}")

    async def find_matching_patterns(
        self,
        disease_name: str,
        symptoms: List[str],
        patient_description: str = "",
        doctor_id: Optional[str] = None,
        min_match_score: float = 0.3
    ) -> List[DecisionTreeMatch]:
        """
        查找匹配的决策树

        Args:
            disease_name: 疾病名称
            symptoms: 患者症状列表
            patient_description: 患者完整描述
            doctor_id: 指定医生ID(可选)
            min_match_score: 最小匹配分数阈值

        Returns:
            匹配的决策树列表,按匹配分数排序
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 🔧 查询决策树（支持doctor_id=None查询所有医生的决策树）
            if doctor_id:
                logger.info(f"🔍 查询医生 {doctor_id} 的决策树")
                cursor.execute("""
                    SELECT * FROM doctor_clinical_patterns
                    WHERE doctor_id = ?
                    ORDER BY usage_count DESC, success_count DESC
                """, (doctor_id,))
            else:
                logger.info(f"🔍 查询所有医生的决策树")
                cursor.execute("""
                    SELECT * FROM doctor_clinical_patterns
                    ORDER BY usage_count DESC, success_count DESC
                """)

            patterns = cursor.fetchall()
            conn.close()

            if not patterns:
                logger.info("未找到任何医生决策树")
                return []

            # 计算匹配分数
            matches = []
            for pattern in patterns:
                match_score = self._calculate_match_score(
                    pattern,
                    disease_name,
                    symptoms,
                    patient_description
                )

                if match_score >= min_match_score:
                    try:
                        tree_structure = json.loads(pattern['tree_structure'])
                    except:
                        tree_structure = {}

                    # 计算置信度(基于历史成功率和使用次数)
                    usage = pattern['usage_count']
                    success = pattern['success_count']
                    confidence = (success / usage * 0.7 + match_score * 0.3) if usage > 0 else match_score

                    match = DecisionTreeMatch(
                        pattern_id=pattern['id'],
                        doctor_id=pattern['doctor_id'],
                        disease_name=pattern['disease_name'],
                        match_score=match_score,
                        thinking_process=pattern['thinking_process'],
                        tree_structure=tree_structure,
                        clinical_patterns=pattern['clinical_patterns'],
                        usage_count=usage,
                        success_count=success,
                        confidence=confidence
                    )
                    matches.append(match)

            # 按匹配分数和置信度排序
            matches.sort(key=lambda x: (x.match_score * 0.6 + x.confidence * 0.4), reverse=True)

            logger.info(f"找到 {len(matches)} 个匹配的决策树(疾病:{disease_name}, 症状数:{len(symptoms)})")
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
        4. 症状匹配度: 0.4分
        5. 临床模式文本相似度: 0.2分
        """
        total_score = 0.0

        # 1. 疾病名称匹配 (权重: 0.4)
        pattern_disease = pattern['disease_name']
        if disease_name == pattern_disease:
            # 完全匹配
            total_score += 0.4
        elif self._is_disease_alias(disease_name, pattern_disease):
            # 别名匹配
            total_score += 0.35
        elif disease_name in pattern_disease:
            # 患者描述的疾病名包含在决策树疾病名中 (如"胃痛" in "脾胃虚寒型胃痛")
            # 这种情况应该给较高分数,因为是核心疾病词匹配
            total_score += 0.3
        elif pattern_disease in disease_name:
            # 决策树疾病名包含在患者描述中
            total_score += 0.25

        # 2. 症状匹配度 (权重: 0.4)
        if symptoms:
            symptom_score = self._calculate_symptom_match(
                pattern['thinking_process'],
                pattern['clinical_patterns'],
                symptoms
            )
            total_score += symptom_score * 0.4

        # 3. 临床模式文本相似度 (权重: 0.2)
        if patient_description:
            text_similarity = self._calculate_text_similarity(
                patient_description,
                pattern['thinking_process'] + " " + pattern['clinical_patterns']
            )
            total_score += text_similarity * 0.2

        return min(total_score, 1.0)

    def _is_disease_alias(self, disease1: str, disease2: str) -> bool:
        """检查两个疾病名称是否为别名关系"""
        for main_disease, aliases in self.disease_aliases.items():
            if disease1 in aliases and disease2 in aliases:
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
