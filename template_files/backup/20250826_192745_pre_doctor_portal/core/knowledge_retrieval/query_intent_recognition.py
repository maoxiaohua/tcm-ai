# query_intent_recognition.py - 查询意图识别与症状关联图谱系统

import re
import jieba
import numpy as np
from typing import List, Dict, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

class QueryIntent(Enum):
    """查询意图类型"""
    DISEASE_NAME = "disease_name"           # 疾病名称查询
    SYMPTOM_DESCRIPTION = "symptom"         # 症状描述查询
    TREATMENT_METHOD = "treatment"          # 治疗方法查询
    MEDICINE_FORMULA = "formula"            # 方剂药物查询
    SYNDROME_PATTERN = "syndrome"           # 证候模式查询
    PREVENTION = "prevention"               # 预防保健查询
    EXAMINATION = "examination"             # 检查诊断查询
    COMPLEX_QUERY = "complex"               # 复合查询
    GENERAL_QUESTION = "general"            # 一般性问题

@dataclass
class IntentMatch:
    """意图匹配结果"""
    intent: QueryIntent
    confidence: float
    keywords: List[str]
    patterns: List[str]

class SymptomGraphNode:
    """症状图谱节点"""
    def __init__(self, symptom: str, category: str = "symptom"):
        self.symptom = symptom
        self.category = category  # symptom, disease, syndrome, treatment
        self.related_symptoms: Set[str] = set()
        self.related_diseases: Set[str] = set()
        self.related_syndromes: Set[str] = set()
        self.weight = 1.0
        self.frequency = 0

class QueryIntentRecognizer:
    """查询意图识别器"""
    
    def __init__(self):
        self.intent_patterns = self._build_intent_patterns()
        self.symptom_graph = SymptomGraph()
        self.chinese_medicine_terms = self._load_tcm_terms()
        
    def _build_intent_patterns(self) -> Dict[QueryIntent, List[Dict]]:
        """构建意图识别模式"""
        return {
            QueryIntent.DISEASE_NAME: [
                {"keywords": ["什么是", "什么叫", "如何定义"], "weight": 0.9},
                {"keywords": ["病", "症", "综合征", "疾病"], "weight": 0.8},
                {"patterns": [r"(.+)病$", r"(.+)症$", r"(.+)综合征$"], "weight": 0.85},
                {"keywords": ["高血压", "糖尿病", "冠心病", "肝硬化", "肾炎"], "weight": 1.0},
            ],
            
            QueryIntent.SYMPTOM_DESCRIPTION: [
                {"keywords": ["疼痛", "头痛", "腹痛", "胸痛", "咳嗽", "发热"], "weight": 0.9},
                {"keywords": ["感觉", "症状", "不舒服", "难受"], "weight": 0.8},
                {"patterns": [r"我(.+)", r"患者(.+)", r"总是(.+)", r"经常(.+)"], "weight": 0.7},
                {"keywords": ["痰", "汗", "便", "尿", "眠", "食", "口", "舌", "脉"], "weight": 0.85},
            ],
            
            QueryIntent.TREATMENT_METHOD: [
                {"keywords": ["怎么治", "如何治疗", "治疗方法", "怎么办"], "weight": 0.95},
                {"keywords": ["针灸", "按摩", "推拿", "刮痧", "拔罐"], "weight": 0.9},
                {"keywords": ["调理", "养生", "保养"], "weight": 0.8},
                {"patterns": [r"(.+)怎么治", r"如何治(.+)", r"(.+)的治疗"], "weight": 0.9},
            ],
            
            QueryIntent.MEDICINE_FORMULA: [
                {"keywords": ["方剂", "中药", "药方", "处方", "汤剂"], "weight": 0.95},
                {"keywords": ["吃什么药", "用什么药", "服用"], "weight": 0.9},
                {"patterns": [r"(.+)汤$", r"(.+)散$", r"(.+)丸$", r"(.+)膏$"], "weight": 0.9},
                {"keywords": ["四物汤", "六味地黄丸", "逍遥散", "补中益气汤"], "weight": 1.0},
            ],
            
            QueryIntent.SYNDROME_PATTERN: [
                {"keywords": ["证候", "辨证", "证型", "病机"], "weight": 0.95},
                {"keywords": ["气虚", "血瘀", "痰湿", "阴虚", "阳虚"], "weight": 0.9},
                {"keywords": ["寒证", "热证", "虚证", "实证"], "weight": 0.85},
                {"patterns": [r"(.+)证$", r"(.+)型$"], "weight": 0.8},
            ],
            
            QueryIntent.PREVENTION: [
                {"keywords": ["预防", "防治", "避免", "注意事项"], "weight": 0.95},
                {"keywords": ["养生", "保健", "调养", "护理"], "weight": 0.9},
                {"keywords": ["饮食", "运动", "作息", "生活习惯"], "weight": 0.8},
            ],
            
            QueryIntent.EXAMINATION: [
                {"keywords": ["检查", "诊断", "化验", "B超", "CT"], "weight": 0.95},
                {"keywords": ["舌诊", "脉诊", "望诊", "闻诊"], "weight": 0.9},
                {"keywords": ["四诊", "辨证诊断"], "weight": 0.85},
            ]
        }
    
    def _load_tcm_terms(self) -> Dict[str, List[str]]:
        """加载中医术语词典"""
        return {
            "body_parts": ["头", "颈", "胸", "腹", "腰", "背", "四肢", "手", "足", "心", "肝", "脾", "肺", "肾"],
            "symptoms": ["痛", "胀", "闷", "麻", "酸", "重", "冷", "热", "干", "湿", "痒", "肿"],
            "qualities": ["隐痛", "刺痛", "胀痛", "绞痛", "酸痛", "冷痛", "灼痛", "固定", "游走"],
            "time_patterns": ["晨起", "午后", "夜间", "饭前", "饭后", "劳累后", "休息时"],
            "tcm_syndromes": ["气虚", "血虚", "阴虚", "阳虚", "气滞", "血瘀", "痰湿", "湿热", "寒湿"]
        }
    
    def recognize_intent(self, query: str) -> List[IntentMatch]:
        """识别查询意图"""
        query_clean = self._preprocess_query(query)
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = self._calculate_intent_score(query_clean, patterns)
            if score > 0.1:  # 最低阈值
                keywords = self._extract_keywords(query_clean, patterns)
                intent_scores[intent] = IntentMatch(
                    intent=intent,
                    confidence=score,
                    keywords=keywords,
                    patterns=self._get_matched_patterns(query_clean, patterns)
                )
        
        # 按置信度排序
        return sorted(intent_scores.values(), key=lambda x: x.confidence, reverse=True)
    
    def _preprocess_query(self, query: str) -> str:
        """预处理查询文本"""
        # 移除标点符号和多余空格
        query = re.sub(r'[^\w\s]', '', query)
        query = re.sub(r'\s+', ' ', query).strip()
        return query
    
    def _calculate_intent_score(self, query: str, patterns: List[Dict]) -> float:
        """计算意图匹配分数"""
        max_score = 0.0
        
        for pattern in patterns:
            score = 0.0
            
            # 关键词匹配
            if "keywords" in pattern:
                for keyword in pattern["keywords"]:
                    if keyword in query:
                        score = max(score, pattern["weight"])
            
            # 正则模式匹配
            if "patterns" in pattern:
                for regex_pattern in pattern["patterns"]:
                    if re.search(regex_pattern, query):
                        score = max(score, pattern["weight"])
            
            max_score = max(max_score, score)
        
        return max_score
    
    def _extract_keywords(self, query: str, patterns: List[Dict]) -> List[str]:
        """提取匹配的关键词"""
        keywords = []
        
        for pattern in patterns:
            if "keywords" in pattern:
                for keyword in pattern["keywords"]:
                    if keyword in query:
                        keywords.append(keyword)
        
        return keywords
    
    def _get_matched_patterns(self, query: str, patterns: List[Dict]) -> List[str]:
        """获取匹配的模式"""
        matched = []
        
        for pattern in patterns:
            if "patterns" in pattern:
                for regex_pattern in pattern["patterns"]:
                    if re.search(regex_pattern, query):
                        matched.append(regex_pattern)
        
        return matched

class SymptomGraph:
    """症状关联图谱"""
    
    def __init__(self):
        self.nodes: Dict[str, SymptomGraphNode] = {}
        self.symptom_disease_map = self._build_symptom_disease_map()
        self.syndrome_symptom_map = self._build_syndrome_symptom_map()
        self._build_graph()
    
    def _build_symptom_disease_map(self) -> Dict[str, List[str]]:
        """构建症状-疾病映射"""
        return {
            # 呼吸系统症状
            "咳嗽": ["感冒", "慢性气管炎", "肺结核", "哮喘", "肺炎"],
            "咳痰": ["慢性气管炎", "肺脓肿", "肺结核", "哮喘"],
            "气短": ["心脏病", "哮喘", "肺心病", "贫血"],
            "胸闷": ["冠心病", "哮喘", "肺心病", "神经官能症"],
            
            # 消化系统症状
            "腹痛": ["消化性溃疡", "胃炎", "肠炎", "胆石症", "胰腺炎"],
            "腹胀": ["消化不良", "肠梗阻", "肝硬化", "慢性胃炎"],
            "恶心": ["胃炎", "妊娠反应", "肝炎", "胆囊炎"],
            "呕吐": ["胃炎", "食物中毒", "妊娠反应", "脑血管病"],
            "便秘": ["习惯性便秘", "肠梗阻", "甲状腺功能减退"],
            "腹泻": ["肠炎", "消化不良", "克罗恩病", "肠易激综合征"],
            
            # 循环系统症状
            "心悸": ["心律不齐", "甲亢", "贫血", "神经症"],
            "胸痛": ["冠心病", "心绞痛", "肋间神经痛", "胸膜炎"],
            "水肿": ["心力衰竭", "肾炎", "肝硬化", "营养不良"],
            
            # 神经系统症状
            "头痛": ["偏头痛", "紧张性头痛", "高血压", "脑血管病"],
            "头晕": ["高血压", "低血压", "贫血", "颈椎病"],
            "失眠": ["神经衰弱", "焦虑症", "更年期综合征"],
            "健忘": ["神经衰弱", "老年痴呆", "抑郁症"],
            
            # 泌尿生殖系统症状
            "尿频": ["泌尿系感染", "前列腺疾病", "糖尿病"],
            "尿急": ["膀胱炎", "前列腺炎", "神经性膀胱"],
            "尿痛": ["泌尿系感染", "尿道结石", "前列腺炎"],
            "血尿": ["肾炎", "泌尿系结石", "膀胱癌"],
            
            # 妇科症状
            "月经不调": ["多囊卵巢", "甲状腺疾病", "子宫肌瘤"],
            "痛经": ["子宫内膜异位症", "子宫肌瘤", "盆腔炎"],
            "白带异常": ["阴道炎", "宫颈炎", "盆腔炎"],
            
            # 全身症状
            "乏力": ["贫血", "甲减", "慢性疲劳综合征", "肝病"],
            "发热": ["感染", "肿瘤", "风湿病", "甲亢"],
            "盗汗": ["结核", "甲亢", "更年期综合征", "肿瘤"],
            "消瘦": ["糖尿病", "甲亢", "肿瘤", "慢性消耗性疾病"]
        }
    
    def _build_syndrome_symptom_map(self) -> Dict[str, List[str]]:
        """构建证候-症状映射"""
        return {
            # 气虚证
            "气虚": ["乏力", "气短", "声低", "懒言", "自汗", "易感冒"],
            "脾气虚": ["腹胀", "便溏", "食少", "乏力", "面色萎黄"],
            "肺气虚": ["咳嗽", "气短", "声低", "易感冒", "自汗"],
            "心气虚": ["心悸", "气短", "胸闷", "乏力", "自汗"],
            "肾气虚": ["腰酸", "尿频", "夜尿多", "畏寒", "四肢冷"],
            
            # 血虚证
            "血虚": ["面色苍白", "头晕", "心悸", "失眠", "健忘"],
            "心血虚": ["心悸", "失眠", "多梦", "健忘", "面色无华"],
            "肝血虚": ["眩晕", "视物模糊", "面色萎黄", "月经量少"],
            
            # 阴虚证  
            "阴虚": ["五心烦热", "盗汗", "口干", "咽燥", "便秘"],
            "肺阴虚": ["干咳少痰", "咽干", "声嘶", "潮热", "盗汗"],
            "胃阴虚": ["口干", "食少", "便秘", "舌红少苔"],
            "肾阴虚": ["腰酸", "膝软", "五心烦热", "盗汗", "遗精"],
            
            # 阳虚证
            "阳虚": ["畏寒", "四肢冷", "乏力", "便溏", "尿清长"],
            "脾阳虚": ["腹胀", "便溏", "四肢冷", "水肿", "面色苍白"],
            "肾阳虚": ["腰膝酸冷", "畏寒", "四肢冷", "阳痿", "早泄"],
            
            # 气滞证
            "肝气郁结": ["胸胁胀痛", "情志抑郁", "易怒", "月经不调"],
            "胃气郁结": ["胃脘胀痛", "嗳气", "食少", "情绪波动加重"],
            
            # 血瘀证
            "血瘀": ["疼痛固定", "痛如针刺", "面色晦暗", "舌质紫暗"],
            "心血瘀阻": ["胸痛", "心悸", "唇甲青紫", "舌质紫暗"],
            
            # 痰湿证
            "痰湿": ["胸闷", "腹胀", "头重", "身重", "苔腻"],
            "脾虚痰湿": ["腹胀", "便溏", "头重", "身重", "苔白腻"],
            
            # 湿热证
            "湿热": ["身热不扬", "头重", "胸闷", "苔黄腻", "小便黄"],
            "脾胃湿热": ["腹胀", "恶心", "口苦", "苔黄腻", "大便粘滞"]
        }
    
    def _build_graph(self):
        """构建症状关联图谱"""
        # 添加症状节点
        for symptom, diseases in self.symptom_disease_map.items():
            if symptom not in self.nodes:
                self.nodes[symptom] = SymptomGraphNode(symptom, "symptom")
            
            # 关联疾病
            self.nodes[symptom].related_diseases.update(diseases)
        
        # 添加证候节点和关联
        for syndrome, symptoms in self.syndrome_symptom_map.items():
            if syndrome not in self.nodes:
                self.nodes[syndrome] = SymptomGraphNode(syndrome, "syndrome")
            
            # 关联症状
            for symptom in symptoms:
                if symptom not in self.nodes:
                    self.nodes[symptom] = SymptomGraphNode(symptom, "symptom")
                
                # 建立双向关联
                self.nodes[syndrome].related_symptoms.add(symptom)
                self.nodes[symptom].related_syndromes.add(syndrome)
        
        # 计算症状间关联
        self._calculate_symptom_correlations()
    
    def _calculate_symptom_correlations(self):
        """计算症状间相关性"""
        symptoms = [node for node in self.nodes.values() if node.category == "symptom"]
        
        for i, symptom1 in enumerate(symptoms):
            for symptom2 in symptoms[i+1:]:
                # 基于共同疾病计算相关性
                common_diseases = symptom1.related_diseases & symptom2.related_diseases
                if common_diseases:
                    correlation = len(common_diseases) / (len(symptom1.related_diseases) + len(symptom2.related_diseases) - len(common_diseases))
                    if correlation > 0.3:  # 相关性阈值
                        symptom1.related_symptoms.add(symptom2.symptom)
                        symptom2.related_symptoms.add(symptom1.symptom)
    
    def get_related_symptoms(self, symptom: str, max_results: int = 5) -> List[Tuple[str, float]]:
        """获取相关症状"""
        if symptom not in self.nodes:
            return []
        
        node = self.nodes[symptom]
        related = []
        
        # 直接相关症状
        for related_symptom in node.related_symptoms:
            if related_symptom in self.nodes:
                weight = 0.8  # 直接相关权重
                related.append((related_symptom, weight))
        
        # 通过证候相关的症状
        for syndrome in node.related_syndromes:
            if syndrome in self.nodes:
                syndrome_node = self.nodes[syndrome]
                for syndrome_symptom in syndrome_node.related_symptoms:
                    if syndrome_symptom != symptom and syndrome_symptom not in [r[0] for r in related]:
                        weight = 0.6  # 证候相关权重
                        related.append((syndrome_symptom, weight))
        
        # 按权重排序并返回前N个
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:max_results]
    
    def get_possible_diseases(self, symptoms: List[str]) -> List[Tuple[str, float]]:
        """根据症状组合推测可能疾病"""
        disease_scores = defaultdict(float)
        
        for symptom in symptoms:
            if symptom in self.nodes:
                node = self.nodes[symptom]
                for disease in node.related_diseases:
                    disease_scores[disease] += 1.0
        
        # 计算匹配度
        total_symptoms = len(symptoms)
        disease_matches = []
        
        for disease, score in disease_scores.items():
            confidence = score / total_symptoms
            disease_matches.append((disease, confidence))
        
        # 按置信度排序
        disease_matches.sort(key=lambda x: x[1], reverse=True)
        return disease_matches[:10]  # 返回前10个可能疾病

class EnhancedQueryProcessor:
    """增强查询处理器"""
    
    def __init__(self):
        self.intent_recognizer = QueryIntentRecognizer()
        
    def process_query(self, query: str) -> Dict:
        """处理查询并返回增强信息"""
        # 意图识别
        intents = self.intent_recognizer.recognize_intent(query)
        primary_intent = intents[0] if intents else None
        
        # 提取症状
        symptoms = self._extract_symptoms(query)
        
        # 获取相关信息
        result = {
            "original_query": query,
            "primary_intent": primary_intent.intent.value if primary_intent else "general",
            "confidence": primary_intent.confidence if primary_intent else 0.0,
            "keywords": primary_intent.keywords if primary_intent else [],
            "extracted_symptoms": symptoms,
            "related_symptoms": [],
            "possible_diseases": [],
            "search_enhancement": {}
        }
        
        # 症状关联分析
        if symptoms:
            # 获取相关症状
            all_related = set()
            for symptom in symptoms:
                related = self.intent_recognizer.symptom_graph.get_related_symptoms(symptom)
                all_related.update([r[0] for r in related])
            result["related_symptoms"] = list(all_related)
            
            # 推测可能疾病
            possible_diseases = self.intent_recognizer.symptom_graph.get_possible_diseases(symptoms)
            result["possible_diseases"] = [{"disease": d[0], "confidence": d[1]} for d in possible_diseases]
        
        # 搜索增强策略
        result["search_enhancement"] = self._generate_search_enhancement(result)
        
        return result
    
    def _extract_symptoms(self, query: str) -> List[str]:
        """从查询中提取症状"""
        symptoms = []
        symptom_graph = self.intent_recognizer.symptom_graph
        
        # 直接匹配已知症状
        for symptom in symptom_graph.nodes:
            if symptom in query and symptom_graph.nodes[symptom].category == "symptom":
                symptoms.append(symptom)
        
        return symptoms
    
    def _generate_search_enhancement(self, analysis: Dict) -> Dict:
        """生成搜索增强策略"""
        enhancement = {
            "expand_terms": [],
            "boost_categories": [],
            "filter_types": [],
            "weight_adjustments": {}
        }
        
        intent = analysis["primary_intent"]
        
        # 根据意图调整搜索策略
        if intent == "disease_name":
            enhancement["boost_categories"] = ["disease", "diagnosis"]
            enhancement["weight_adjustments"]["exact_match"] = 2.0
            
        elif intent == "symptom":
            enhancement["boost_categories"] = ["symptom", "syndrome"]
            enhancement["expand_terms"] = analysis["related_symptoms"]
            
        elif intent == "treatment":
            enhancement["boost_categories"] = ["treatment", "formula"]
            enhancement["filter_types"] = ["therapy", "medicine"]
            
        elif intent == "formula":
            enhancement["boost_categories"] = ["formula", "medicine"]
            enhancement["weight_adjustments"]["formula_match"] = 1.8
        
        # 添加相关症状到扩展词条
        if analysis["related_symptoms"]:
            enhancement["expand_terms"].extend(analysis["related_symptoms"][:5])
        
        return enhancement

# 测试代码
if __name__ == "__main__":
    processor = EnhancedQueryProcessor()
    
    test_queries = [
        "我最近总是咳嗽，有痰，该怎么办？",
        "什么是高血压？",
        "头痛头晕怎么治疗？",
        "四物汤的组成是什么？",
        "气虚的症状有哪些？"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        result = processor.process_query(query)
        print(f"意图: {result['primary_intent']} (置信度: {result['confidence']:.2f})")
        print(f"关键词: {result['keywords']}")
        print(f"提取症状: {result['extracted_symptoms']}")
        print(f"相关症状: {result['related_symptoms'][:3]}")
        if result['possible_diseases']:
            print(f"可能疾病: {[d['disease'] for d in result['possible_diseases'][:3]]}")
        print("=" * 50)