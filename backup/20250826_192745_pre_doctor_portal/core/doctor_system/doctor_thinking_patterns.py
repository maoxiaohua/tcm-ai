# doctor_thinking_patterns.py - 医生思维决策树系统

import json
import pickle
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import logging
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """决策树节点类型"""
    SYMPTOM_CHECK = "symptom_check"      # 症状检查
    SYNDROME_ANALYSIS = "syndrome_analysis"  # 证候分析
    FORMULA_SELECTION = "formula_selection"  # 方剂选择
    HERB_DOSAGE = "herb_dosage"         # 药物剂量
    MODIFICATION = "modification"        # 加减化裁
    FINAL_PRESCRIPTION = "final_prescription"  # 最终处方

class ConditionOperator(Enum):
    """条件操作符"""
    HAS = "has"           # 具有某症状
    NOT_HAS = "not_has"   # 不具有某症状
    SEVERITY = "severity" # 严重程度
    DURATION = "duration" # 持续时间
    FREQUENCY = "frequency" # 频率
    PULSE_TYPE = "pulse_type" # 脉象类型
    TONGUE_TYPE = "tongue_type" # 舌象类型

@dataclass
class DecisionCondition:
    """决策条件"""
    attribute: str  # 属性名（如"头痛", "舌红", "脉浮"）
    operator: ConditionOperator  # 操作符
    value: Any  # 期望值
    weight: float = 1.0  # 条件权重

@dataclass
class DecisionAction:
    """决策行动"""
    action_type: str  # 行动类型（如"选择方剂", "调整剂量"）
    content: Dict[str, Any]  # 行动内容
    confidence: float = 1.0  # 信心度
    reasoning: str = ""  # 推理过程

@dataclass
class DecisionTreeNode:
    """决策树节点"""
    node_id: str
    node_type: NodeType
    name: str  # 节点名称
    description: str  # 节点描述
    conditions: List[DecisionCondition]  # 进入此节点的条件
    actions: List[DecisionAction]  # 该节点的行动
    children: Dict[str, 'DecisionTreeNode']  # 子节点
    success_rate: float = 0.0  # 历史成功率
    usage_count: int = 0  # 使用次数
    
    def evaluate_conditions(self, patient_data: Dict[str, Any]) -> Tuple[bool, float]:
        """评估是否满足进入条件"""
        if not self.conditions:
            return True, 1.0
            
        total_weight = sum(c.weight for c in self.conditions)
        satisfied_weight = 0.0
        
        for condition in self.conditions:
            if self._check_condition(condition, patient_data):
                satisfied_weight += condition.weight
        
        satisfaction_rate = satisfied_weight / total_weight if total_weight > 0 else 0.0
        is_satisfied = satisfaction_rate >= 0.6  # 60%的条件满足即可进入
        
        return is_satisfied, satisfaction_rate
    
    def _check_condition(self, condition: DecisionCondition, patient_data: Dict[str, Any]) -> bool:
        """检查单个条件"""
        attribute_value = patient_data.get(condition.attribute)
        
        if condition.operator == ConditionOperator.HAS:
            return bool(attribute_value)
        elif condition.operator == ConditionOperator.NOT_HAS:
            return not bool(attribute_value)
        elif condition.operator == ConditionOperator.SEVERITY:
            return attribute_value and attribute_value >= condition.value
        elif condition.operator == ConditionOperator.DURATION:
            return attribute_value and attribute_value >= condition.value
        elif condition.operator == ConditionOperator.FREQUENCY:
            return attribute_value and attribute_value >= condition.value
        elif condition.operator == ConditionOperator.PULSE_TYPE:
            return attribute_value == condition.value
        elif condition.operator == ConditionOperator.TONGUE_TYPE:
            return attribute_value == condition.value
        
        return False

@dataclass
class CaseExample:
    """案例样本"""
    case_id: str
    patient_symptoms: Dict[str, Any]  # 患者症状
    doctor_reasoning: List[str]  # 医生推理过程
    final_prescription: Dict[str, Any]  # 最终处方
    treatment_outcome: str  # 治疗结果
    success_rating: float  # 成功评分 (0-1)
    doctor_id: str
    disease_category: str
    timestamp: datetime

@dataclass
class DoctorThinkingPattern:
    """医生思维模式"""
    doctor_id: str
    doctor_name: str
    disease_category: str  # 疾病类别
    specialty_area: str  # 专业领域
    decision_tree: DecisionTreeNode  # 决策树根节点
    pattern_accuracy: float = 0.0  # 模式准确率
    case_count: int = 0  # 学习案例数
    last_updated: datetime = None
    
    def predict_prescription(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于患者数据预测处方"""
        reasoning_path = []
        current_node = self.decision_tree
        prescription_components = {}
        
        # 沿着决策树推理
        while current_node:
            # 评估当前节点条件
            is_satisfied, confidence = current_node.evaluate_conditions(patient_data)
            
            if is_satisfied:
                reasoning_path.append({
                    "node": current_node.name,
                    "description": current_node.description,
                    "confidence": confidence,
                    "actions": [asdict(action) for action in current_node.actions]
                })
                
                # 执行节点行动
                for action in current_node.actions:
                    self._execute_action(action, prescription_components, patient_data)
                
                # 寻找下一个最适合的子节点
                next_node = self._find_best_child_node(current_node, patient_data)
                current_node = next_node
            else:
                break
        
        return {
            "prescription": prescription_components,
            "reasoning_path": reasoning_path,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "disease_category": self.disease_category,
            "confidence_score": np.mean([step["confidence"] for step in reasoning_path]) if reasoning_path else 0.0
        }
    
    def _execute_action(self, action: DecisionAction, prescription: Dict[str, Any], patient_data: Dict[str, Any]):
        """执行决策行动"""
        if action.action_type == "select_formula":
            prescription["base_formula"] = action.content.get("formula_name")
            prescription["formula_dosage"] = action.content.get("dosage", {})
            
        elif action.action_type == "add_herb":
            if "additional_herbs" not in prescription:
                prescription["additional_herbs"] = []
            prescription["additional_herbs"].append(action.content)
            
        elif action.action_type == "modify_dosage":
            if "dosage_modifications" not in prescription:
                prescription["dosage_modifications"] = {}
            herb_name = action.content.get("herb")
            new_dosage = action.content.get("dosage")
            prescription["dosage_modifications"][herb_name] = new_dosage
            
        elif action.action_type == "set_preparation":
            prescription["preparation_method"] = action.content.get("method")
            prescription["administration"] = action.content.get("administration")
            
        elif action.action_type == "add_caution":
            if "cautions" not in prescription:
                prescription["cautions"] = []
            prescription["cautions"].append(action.content.get("caution"))
    
    def _find_best_child_node(self, current_node: DecisionTreeNode, patient_data: Dict[str, Any]) -> Optional[DecisionTreeNode]:
        """找到最适合的子节点"""
        if not current_node.children:
            return None
        
        best_node = None
        best_score = 0.0
        
        for child_node in current_node.children.values():
            is_satisfied, confidence = child_node.evaluate_conditions(patient_data)
            if is_satisfied and confidence > best_score:
                best_score = confidence
                best_node = child_node
        
        return best_node

class ThinkingPatternLearner:
    """思维模式学习器"""
    
    def __init__(self):
        self.min_cases_required = 3  # 学习一个模式需要的最少案例数（降低要求以便测试）
        
    def learn_pattern_from_cases(self, doctor_id: str, doctor_name: str, 
                                disease_category: str, cases: List[CaseExample]) -> DoctorThinkingPattern:
        """从案例中学习医生思维模式"""
        if len(cases) < self.min_cases_required:
            logger.warning(f"案例数不足({len(cases)}<{self.min_cases_required})，无法学习 {doctor_name} 关于 {disease_category} 的思维模式")
            return None
        
        logger.info(f"开始学习 {doctor_name} 关于 {disease_category} 的思维模式，共 {len(cases)} 个案例")
        
        # 分析案例，提取决策模式
        decision_tree = self._build_decision_tree_from_cases(cases)
        
        if not decision_tree:
            logger.error(f"决策树构建失败，无法为 {doctor_name} 创建 {disease_category} 的思维模式")
            return None
        
        # 计算模式准确率
        accuracy = self._calculate_pattern_accuracy(cases)
        
        pattern = DoctorThinkingPattern(
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            disease_category=disease_category,
            specialty_area=self._infer_specialty_area(cases),
            decision_tree=decision_tree,
            pattern_accuracy=accuracy,
            case_count=len(cases),
            last_updated=datetime.now()
        )
        
        logger.info(f"学习完成，准确率: {accuracy:.2%}，决策树根节点有 {len(decision_tree.children)} 个子节点")
        return pattern
    
    def _build_decision_tree_from_cases(self, cases: List[CaseExample]) -> DecisionTreeNode:
        """从案例中构建决策树"""
        if not cases:
            logger.warning("没有案例数据，无法构建决策树")
            return None
            
        logger.info(f"正在从 {len(cases)} 个案例构建决策树...")
        
        # 分析症状模式
        symptom_patterns = self._analyze_symptom_patterns(cases)
        
        # 分析推理步骤
        reasoning_patterns = self._analyze_reasoning_patterns(cases)
        
        # 分析处方选择模式
        prescription_patterns = self._analyze_prescription_patterns(cases)
        
        logger.info(f"症状模式: {len(symptom_patterns.get('individual_symptoms', {}))}")
        logger.info(f"推理模式: {len(reasoning_patterns.get('common_patterns', {}))}")
        logger.info(f"处方模式: {len(prescription_patterns.get('formula_preferences', {}))}")
        
        # 构建根节点 - 初始症状评估
        root_node = DecisionTreeNode(
            node_id="root",
            node_type=NodeType.SYMPTOM_CHECK,
            name="初始症状评估",
            description="评估患者主要症状",
            conditions=[],  # 根节点无进入条件
            actions=[DecisionAction(
                action_type="start_evaluation",
                content={"message": "开始症状评估"},
                confidence=1.0,
                reasoning="根节点启动评估流程"
            )],
            children={}
        )
        
        # 构建症状检查子节点
        symptom_nodes = self._build_symptom_nodes(symptom_patterns)
        logger.info(f"构建了 {len(symptom_nodes)} 个症状节点")
        
        # 构建证候分析子节点
        syndrome_nodes = self._build_syndrome_nodes(reasoning_patterns)
        logger.info(f"构建了 {len(syndrome_nodes)} 个证候节点")
        
        # 构建方剂选择子节点
        formula_nodes = self._build_formula_nodes(prescription_patterns)
        logger.info(f"构建了 {len(formula_nodes)} 个方剂节点")
        
        # 连接节点，形成决策树
        if symptom_nodes:
            root_node.children = symptom_nodes
            self._connect_tree_nodes(symptom_nodes, syndrome_nodes, formula_nodes)
            logger.info("决策树节点连接完成")
        else:
            logger.warning("没有生成症状节点，决策树可能为空")
        
        return root_node
    
    def _analyze_symptom_patterns(self, cases: List[CaseExample]) -> Dict[str, Any]:
        """分析症状模式"""
        symptom_counter = Counter()
        symptom_combinations = defaultdict(list)
        
        for case in cases:
            symptoms = case.patient_symptoms
            symptom_list = list(symptoms.keys())
            
            # 统计单个症状频率
            for symptom in symptom_list:
                if symptoms[symptom]:  # 存在该症状
                    symptom_counter[symptom] += 1
            
            # 统计症状组合
            for i, symptom1 in enumerate(symptom_list):
                for symptom2 in symptom_list[i+1:]:
                    if symptoms[symptom1] and symptoms[symptom2]:
                        combo = tuple(sorted([symptom1, symptom2]))
                        symptom_combinations[combo].append(case.case_id)
        
        return {
            "individual_symptoms": dict(symptom_counter),
            "symptom_combinations": dict(symptom_combinations),
            "total_cases": len(cases)
        }
    
    def _analyze_reasoning_patterns(self, cases: List[CaseExample]) -> Dict[str, Any]:
        """分析推理模式"""
        reasoning_steps = defaultdict(list)
        
        for case in cases:
            for i, step in enumerate(case.doctor_reasoning):
                reasoning_steps[f"step_{i}"].append(step)
        
        # 提取常见的推理模式
        common_patterns = {}
        for step_key, steps in reasoning_steps.items():
            step_counter = Counter(steps)
            common_patterns[step_key] = step_counter.most_common(3)
        
        return {
            "reasoning_steps": dict(reasoning_steps),
            "common_patterns": common_patterns
        }
    
    def _analyze_prescription_patterns(self, cases: List[CaseExample]) -> Dict[str, Any]:
        """分析处方模式"""
        formula_counter = Counter()
        herb_usage = defaultdict(list)
        dosage_patterns = defaultdict(list)
        
        for case in cases:
            prescription = case.final_prescription
            
            # 统计方剂使用频率
            if "formula" in prescription:
                formula_counter[prescription["formula"]] += 1
            
            # 统计药物使用
            if "herbs" in prescription:
                for herb, dosage in prescription["herbs"].items():
                    herb_usage[herb].append(dosage)
                    dosage_patterns[herb].append((dosage, case.success_rating))
        
        return {
            "formula_preferences": dict(formula_counter),
            "herb_usage": dict(herb_usage),
            "dosage_patterns": dict(dosage_patterns)
        }
    
    def _build_symptom_nodes(self, symptom_patterns: Dict[str, Any]) -> Dict[str, DecisionTreeNode]:
        """构建症状检查节点"""
        nodes = {}
        
        # 按症状频率排序，构建主要症状检查节点
        sorted_symptoms = sorted(
            symptom_patterns["individual_symptoms"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for i, (symptom, frequency) in enumerate(sorted_symptoms[:5]):  # 只取前5个最常见症状
            node_id = f"symptom_{i}"
            
            node = DecisionTreeNode(
                node_id=node_id,
                node_type=NodeType.SYMPTOM_CHECK,
                name=f"{symptom}检查",
                description=f"检查是否存在{symptom}症状",
                conditions=[DecisionCondition(
                    attribute=symptom,
                    operator=ConditionOperator.HAS,
                    value=True,
                    weight=frequency / symptom_patterns["total_cases"]
                )],
                actions=[DecisionAction(
                    action_type="record_symptom",
                    content={"symptom": symptom, "importance": "high"},
                    confidence=frequency / symptom_patterns["total_cases"]
                )],
                children={}
            )
            
            nodes[node_id] = node
        
        return nodes
    
    def _build_syndrome_nodes(self, reasoning_patterns: Dict[str, Any]) -> Dict[str, DecisionTreeNode]:
        """构建证候分析节点"""
        nodes = {}
        
        # 从推理模式中提取证候分析步骤
        common_patterns = reasoning_patterns.get("common_patterns", {})
        
        for step_key, patterns in common_patterns.items():
            for i, (pattern_text, frequency) in enumerate(patterns):
                if "证" in pattern_text or "虚" in pattern_text or "实" in pattern_text or "寒" in pattern_text or "热" in pattern_text:
                    node_id = f"syndrome_{step_key}_{i}"
                    
                    # 计算相对频率
                    total_freq = sum(freq for _, freq in patterns)
                    relative_freq = frequency / total_freq if total_freq > 0 else 0.5
                    
                    node = DecisionTreeNode(
                        node_id=node_id,
                        node_type=NodeType.SYNDROME_ANALYSIS,
                        name=f"证候分析-{pattern_text[:10]}",
                        description=pattern_text,
                        conditions=[],  # 基于症状节点的输出来确定条件
                        actions=[DecisionAction(
                            action_type="analyze_syndrome",
                            content={"analysis": pattern_text, "syndrome_type": "中医辨证"},
                            confidence=relative_freq,
                            reasoning=f"根据 {frequency} 次案例经验进行证候分析"
                        )],
                        children={}
                    )
                    
                    nodes[node_id] = node
        
        # 如果没有找到证候相关的推理，创建通用证候分析节点
        if not nodes:
            logger.info("未找到具体证候模式，创建通用证候分析节点")
            default_node = DecisionTreeNode(
                node_id="syndrome_default",
                node_type=NodeType.SYNDROME_ANALYSIS,
                name="通用证候分析",
                description="基于症状进行综合证候分析",
                conditions=[],
                actions=[DecisionAction(
                    action_type="analyze_syndrome",
                    content={"analysis": "综合症状分析证候", "syndrome_type": "通用辨证"},
                    confidence=0.7,
                    reasoning="基于通用中医理论进行证候分析"
                )],
                children={}
            )
            nodes["syndrome_default"] = default_node
        
        return nodes
    
    def _build_formula_nodes(self, prescription_patterns: Dict[str, Any]) -> Dict[str, DecisionTreeNode]:
        """构建方剂选择节点"""
        nodes = {}
        
        formula_preferences = prescription_patterns.get("formula_preferences", {})
        herb_usage = prescription_patterns.get("herb_usage", {})
        
        # 基于方剂偏好构建节点
        if formula_preferences:
            total_formula_usage = sum(formula_preferences.values())
            
            for i, (formula, frequency) in enumerate(formula_preferences.items()):
                node_id = f"formula_{i}"
                
                # 计算方剂选择的信心度
                confidence = frequency / total_formula_usage if total_formula_usage > 0 else 0.5
                
                # 分析该方剂的适用条件（基于使用该方剂的案例）
                actions = [
                    DecisionAction(
                        action_type="select_formula",
                        content={"formula_name": formula, "usage_frequency": frequency},
                        confidence=confidence,
                        reasoning=f"基于 {frequency} 次成功案例选择{formula}"
                    )
                ]
                
                # 添加相关的药物剂量信息
                if herb_usage:
                    for herb, dosages in herb_usage.items():
                        if len(dosages) > 0:
                            # 计算平均剂量
                            if isinstance(dosages[0], str):
                                # 如果是字符串格式的剂量，取第一个作为默认
                                avg_dosage = dosages[0]
                            else:
                                avg_dosage = np.mean([float(d) for d in dosages if isinstance(d, (int, float))])
                            
                            actions.append(DecisionAction(
                                action_type="set_dosage",
                                content={"herb": herb, "dosage": avg_dosage},
                                confidence=0.8,
                                reasoning=f"基于历史用药经验设定{herb}剂量"
                            ))
                
                node = DecisionTreeNode(
                    node_id=node_id,
                    node_type=NodeType.FORMULA_SELECTION,
                    name=f"选择{formula}",
                    description=f"基于证候选择{formula}方剂，使用频率{frequency}次",
                    conditions=[],  # 基于证候分析的结果确定
                    actions=actions,
                    children={}
                )
                
                nodes[node_id] = node
        
        # 如果没有找到具体的方剂偏好，创建通用方剂选择节点
        if not nodes:
            logger.info("未找到具体方剂模式，创建通用方剂选择节点")
            default_node = DecisionTreeNode(
                node_id="formula_default",
                node_type=NodeType.FORMULA_SELECTION,
                name="通用方剂选择",
                description="基于证候选择适合的方剂",
                conditions=[],
                actions=[DecisionAction(
                    action_type="select_formula",
                    content={"formula_name": "辨证选方", "method": "通用选方"},
                    confidence=0.6,
                    reasoning="基于中医理论进行辨证选方"
                )],
                children={}
            )
            nodes["formula_default"] = default_node
        
        return nodes
    
    def _connect_tree_nodes(self, symptom_nodes: Dict, syndrome_nodes: Dict, formula_nodes: Dict):
        """连接决策树节点"""
        # 简化的连接逻辑：症状 -> 证候 -> 方剂
        symptom_keys = list(symptom_nodes.keys())
        syndrome_keys = list(syndrome_nodes.keys())
        formula_keys = list(formula_nodes.keys())
        
        # 症状节点连接到证候节点
        for i, symptom_key in enumerate(symptom_keys):
            if i < len(syndrome_keys):
                symptom_nodes[symptom_key].children[syndrome_keys[i]] = syndrome_nodes[syndrome_keys[i]]
        
        # 证候节点连接到方剂节点
        for i, syndrome_key in enumerate(syndrome_keys):
            if i < len(formula_keys):
                syndrome_nodes[syndrome_key].children[formula_keys[i]] = formula_nodes[formula_keys[i]]
    
    def _calculate_pattern_accuracy(self, cases: List[CaseExample]) -> float:
        """计算模式准确率"""
        successful_cases = sum(1 for case in cases if case.success_rating >= 0.7)
        return successful_cases / len(cases) if cases else 0.0
    
    def _infer_specialty_area(self, cases: List[CaseExample]) -> str:
        """推断专业领域"""
        disease_counter = Counter(case.disease_category for case in cases)
        most_common_disease = disease_counter.most_common(1)[0][0] if disease_counter else "通科"
        return most_common_disease

class DoctorMindDatabase:
    """医生思维数据库"""
    
    def __init__(self, db_path: str = "./doctor_minds.pkl"):
        self.db_path = db_path
        self.thinking_patterns: Dict[str, Dict[str, DoctorThinkingPattern]] = defaultdict(dict)
        self.case_database: List[CaseExample] = []
        self.load_database()
    
    def add_thinking_pattern(self, pattern: DoctorThinkingPattern):
        """添加思维模式"""
        self.thinking_patterns[pattern.doctor_id][pattern.disease_category] = pattern
        self.save_database()
        logger.info(f"添加了 {pattern.doctor_name} 关于 {pattern.disease_category} 的思维模式")
    
    def get_thinking_pattern(self, doctor_id: str, disease_category: str) -> Optional[DoctorThinkingPattern]:
        """获取思维模式"""
        return self.thinking_patterns.get(doctor_id, {}).get(disease_category)
    
    def get_doctor_patterns(self, doctor_id: str) -> Dict[str, DoctorThinkingPattern]:
        """获取医生的所有思维模式"""
        return self.thinking_patterns.get(doctor_id, {})
    
    def add_case_example(self, case: CaseExample):
        """添加案例样本"""
        self.case_database.append(case)
        self.save_database()
    
    def get_cases_by_doctor_and_disease(self, doctor_id: str, disease_category: str) -> List[CaseExample]:
        """获取特定医生和疾病的案例"""
        return [
            case for case in self.case_database
            if case.doctor_id == doctor_id and case.disease_category == disease_category
        ]
    
    def learn_new_patterns(self, doctor_id: str, doctor_name: str):
        """学习新的思维模式"""
        learner = ThinkingPatternLearner()
        
        # 按疾病类别分组案例
        disease_cases = defaultdict(list)
        for case in self.case_database:
            if case.doctor_id == doctor_id:
                disease_cases[case.disease_category].append(case)
        
        # 为每个疾病类别学习思维模式
        for disease_category, cases in disease_cases.items():
            pattern = learner.learn_pattern_from_cases(
                doctor_id, doctor_name, disease_category, cases
            )
            if pattern:
                self.add_thinking_pattern(pattern)
    
    def save_database(self):
        """保存数据库"""
        try:
            with open(self.db_path, 'wb') as f:
                pickle.dump({
                    'thinking_patterns': dict(self.thinking_patterns),
                    'case_database': self.case_database
                }, f)
        except Exception as e:
            logger.error(f"保存数据库失败: {e}")
    
    def load_database(self):
        """加载数据库"""
        try:
            with open(self.db_path, 'rb') as f:
                data = pickle.load(f)
                self.thinking_patterns = defaultdict(dict, data.get('thinking_patterns', {}))
                self.case_database = data.get('case_database', [])
            logger.info("数据库加载成功")
        except FileNotFoundError:
            logger.info("数据库文件不存在，创建新数据库")
        except Exception as e:
            logger.error(f"加载数据库失败: {e}")

class PrescriptionLogicEngine:
    """处方逻辑推理引擎"""
    
    def __init__(self, mind_database: DoctorMindDatabase):
        self.mind_db = mind_database
    
    def recommend_doctor(self, patient_data: Dict[str, Any], disease_category: str) -> List[Tuple[str, float]]:
        """推荐最适合的医生"""
        recommendations = []
        
        for doctor_id, patterns in self.mind_db.thinking_patterns.items():
            if disease_category in patterns:
                pattern = patterns[disease_category]
                
                # 评估医生的适合度
                suitability_score = self._calculate_doctor_suitability(pattern, patient_data)
                recommendations.append((doctor_id, suitability_score))
        
        # 按适合度排序
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:3]  # 返回前3名
    
    def generate_prescription(self, patient_data: Dict[str, Any], doctor_id: str, disease_category: str) -> Dict[str, Any]:
        """生成处方"""
        pattern = self.mind_db.get_thinking_pattern(doctor_id, disease_category)
        
        if not pattern:
            return {"error": f"未找到 {doctor_id} 关于 {disease_category} 的思维模式"}
        
        # 使用医生的思维模式生成处方
        prescription = pattern.predict_prescription(patient_data)
        
        return prescription
    
    def _calculate_doctor_suitability(self, pattern: DoctorThinkingPattern, patient_data: Dict[str, Any]) -> float:
        """计算医生适合度"""
        # 基于历史准确率和症状匹配度计算
        accuracy_score = pattern.pattern_accuracy
        
        # 计算症状匹配度
        symptom_match_score = 0.0
        root_node = pattern.decision_tree
        
        if root_node.children:
            total_matches = 0
            satisfied_matches = 0
            
            for child_node in root_node.children.values():
                total_matches += 1
                is_satisfied, confidence = child_node.evaluate_conditions(patient_data)
                if is_satisfied:
                    satisfied_matches += confidence
            
            symptom_match_score = satisfied_matches / total_matches if total_matches > 0 else 0.0
        
        # 综合评分
        suitability = (accuracy_score * 0.6 + symptom_match_score * 0.4)
        return suitability

# 使用示例和测试函数
def create_sample_data():
    """创建示例数据"""
    mind_db = DoctorMindDatabase("./sample_doctor_minds.pkl")
    
    # 创建示例案例
    sample_cases = [
        CaseExample(
            case_id="case_001",
            patient_symptoms={
                "头痛": True,
                "发热": True,
                "恶寒": True,
                "脉浮": True,
                "舌苔薄白": True
            },
            doctor_reasoning=[
                "患者头痛发热，恶寒，脉浮，舌苔薄白",
                "辨证为太阳表证",
                "治以解表散寒"
            ],
            final_prescription={
                "formula": "麻黄汤",
                "herbs": {
                    "麻黄": "6g",
                    "桂枝": "9g", 
                    "杏仁": "9g",
                    "甘草": "3g"
                }
            },
            treatment_outcome="症状缓解",
            success_rating=0.9,
            doctor_id="zhang_zhongjing_001",
            disease_category="外感病",
            timestamp=datetime.now()
        ),
        # 可以添加更多案例...
    ]
    
    # 添加案例到数据库
    for case in sample_cases:
        mind_db.add_case_example(case)
    
    # 学习思维模式
    mind_db.learn_new_patterns("zhang_zhongjing_001", "张仲景传人甲")
    
    return mind_db

def demo_prescription_logic():
    """演示处方逻辑"""
    mind_db = create_sample_data()
    logic_engine = PrescriptionLogicEngine(mind_db)
    
    # 模拟患者数据
    patient_data = {
        "头痛": True,
        "发热": True,
        "恶寒": True,
        "脉浮": True,
        "舌苔薄白": True
    }
    
    # 推荐医生
    recommendations = logic_engine.recommend_doctor(patient_data, "外感病")
    print(f"推荐医生: {recommendations}")
    
    # 生成处方
    if recommendations:
        best_doctor = recommendations[0][0]
        prescription = logic_engine.generate_prescription(patient_data, best_doctor, "外感病")
        print(f"处方建议: {json.dumps(prescription, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    demo_prescription_logic()