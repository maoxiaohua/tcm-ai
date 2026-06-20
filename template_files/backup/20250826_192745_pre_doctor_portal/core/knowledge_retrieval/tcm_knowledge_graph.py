#!/usr/bin/env python3
"""
中医药物知识图谱系统
构建药物-疾病-证候-方剂的关联网络
"""

import json
import sqlite3
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import networkx as nx
from collections import defaultdict

@dataclass
class HerbInfo:
    """药物基本信息"""
    name: str
    category: str  # 药物分类
    nature: str    # 性味 (寒、热、温、凉、平)
    flavor: str    # 五味 (酸、苦、甘、辛、咸)
    meridian: List[str]  # 归经
    effects: List[str]   # 功效
    indications: List[str]  # 主治
    dosage_range: Tuple[float, float]  # 常用剂量范围
    contraindications: List[str]  # 禁忌
    toxicity_level: int = 0  # 毒性等级 0-无毒 1-小毒 2-有毒 3-大毒

@dataclass
class FormulaInfo:
    """方剂信息"""
    name: str
    category: str  # 方剂分类
    composition: Dict[str, str]  # 组成 {药名: 剂量}
    functions: List[str]  # 功能
    indications: List[str]  # 主治
    syndrome_pattern: str  # 主要证型
    source: str  # 出处
    modifications: Dict[str, str] = None  # 加减变化

class TCMKnowledgeGraph:
    """中医知识图谱"""
    
    def __init__(self, db_path: str = "/opt/tcm/data/tcm_knowledge_graph.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        # 创建图结构
        self.graph = nx.MultiDiGraph()
        
        # 初始化数据库
        self._init_database()
        
        # 加载基础知识
        self._load_basic_knowledge()
    
    def _init_database(self):
        """初始化知识图谱数据库"""
        conn = sqlite3.connect(self.db_path)
        
        # 药物信息表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS herbs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT,
                nature TEXT,
                flavor TEXT,
                meridian TEXT,
                effects TEXT,
                indications TEXT,
                dosage_min REAL,
                dosage_max REAL,
                contraindications TEXT,
                toxicity_level INTEGER DEFAULT 0
            )
        """)
        
        # 方剂信息表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS formulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT,
                composition TEXT,
                functions TEXT,
                indications TEXT,
                syndrome_pattern TEXT,
                source TEXT,
                modifications TEXT
            )
        """)
        
        # 疾病信息表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS diseases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT,
                symptoms TEXT,
                common_syndromes TEXT,
                treatment_principles TEXT
            )
        """)
        
        # 关系表 - 存储所有类型的关联关系
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT,  -- herb/formula/disease/syndrome
                source_name TEXT,
                relation_type TEXT,  -- treats/contains/causes/synergistic/antagonistic
                target_type TEXT,
                target_name TEXT,
                strength REAL DEFAULT 1.0,  -- 关系强度
                evidence TEXT,  -- 证据来源
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_basic_knowledge(self):
        """加载基础中医知识"""
        
        # 1. 基础药物信息
        basic_herbs = [
            HerbInfo("人参", "补虚药", "微温", "甘、微苦", ["脾", "肺", "心", "肾"], 
                    ["大补元气", "复脉固脱", "补脾益肺", "生津止渴", "安神益智"],
                    ["元气虚脱", "肢冷脉微", "脾虚食少", "肺虚喘咳", "津伤口渴", "内热消渴", "心神不安", "失眠多梦"],
                    (3, 9), ["实热证", "湿热证"]),
            
            HerbInfo("黄芪", "补虚药", "微温", "甘", ["脾", "肺"], 
                    ["补气升阳", "固表止汗", "利水消肿", "生肌敛疮"],
                    ["气虚乏力", "中气下陷", "久泻脱肛", "表虚自汗", "气虚水肿", "痈疽难溃", "久溃不敛"],
                    (9, 30), ["表实邪盛", "疮疡阳盛"]),
            
            HerbInfo("当归", "补虚药", "温", "甘、辛", ["肝", "心", "脾"], 
                    ["补血调经", "活血止痛", "润肠通便"],
                    ["血虚萎黄", "眩晕心悸", "月经不调", "经闭痛经", "虚寒腹痛", "痿痹", "肌肤麻木", "肠燥便秘", "赤痢后重"],
                    (6, 12), ["湿盛中满", "大便溏泄"]),
            
            HerbInfo("麻黄", "解表药", "温", "辛、微苦", ["肺", "膀胱"], 
                    ["发汗解表", "宣肺平喘", "利水消肿"],
                    ["风寒感冒", "胸闷喘咳", "风水浮肿", "风湿痹痛", "阴疽", "痰核"],
                    (2, 9), ["表虚自汗", "阴虚阳亢", "失眠症"]),
            
            HerbInfo("桂枝", "解表药", "温", "辛、甘", ["心", "肺", "膀胱"], 
                    ["发汗解肌", "温通经脉", "助阳化气", "平冲降逆"],
                    ["风寒感冒", "脘腹冷痛", "血寒经闭", "关节痹痛", "痰饮", "水肿", "心悸", "奔豚"],
                    (3, 9), ["温热病", "阴虚火旺", "出血证"]),
        ]
        
        # 2. 经典方剂
        classic_formulas = [
            FormulaInfo("麻黄汤", "解表剂", 
                       {"麻黄": "9g", "桂枝": "6g", "杏仁": "6g", "甘草": "3g"},
                       ["发汗解表", "宣肺平喘"],
                       ["风寒感冒", "恶寒发热", "头痛身痛", "无汗而喘", "舌苔薄白", "脉浮紧"],
                       "风寒表实证", "《伤寒杂病论》"),
            
            FormulaInfo("桂枝汤", "解表剂",
                       {"桂枝": "9g", "白芍": "9g", "生姜": "9g", "大枣": "12枚", "甘草": "6g"},
                       ["解肌发表", "调和营卫"],
                       ["风寒感冒", "头痛发热", "汗出恶风", "鼻鸣干呕", "苔白不渴", "脉浮缓或浮弱"],
                       "风寒表虚证", "《伤寒杂病论》"),
            
            FormulaInfo("四君子汤", "补益剂",
                       {"人参": "9g", "白术": "9g", "茯苓": "9g", "甘草": "6g"},
                       ["益气健脾"],
                       ["脾胃气虚", "面色萎白", "语声低微", "气短乏力", "食少便溏", "舌淡苔白", "脉虚缓"],
                       "脾胃气虚证", "《太平惠民和剂局方》"),
            
            FormulaInfo("四物汤", "补益剂",
                       {"当归": "10g", "川芎": "8g", "白芍": "12g", "熟地黄": "12g"},
                       ["补血调血"],
                       ["营血虚滞", "心悸失眠", "头晕目眩", "面色无华", "妇人月经不调", "量少或经闭", "脐腹作痛", "舌淡", "脉细弦或细涩"],
                       "血虚证", "《太平惠民和剂局方》"),
        ]
        
        # 3. 常见疾病
        common_diseases = [
            {"name": "感冒", "category": "外感病", 
             "symptoms": ["发热", "恶寒", "头痛", "鼻塞", "流涕", "咳嗽", "咽痛"],
             "common_syndromes": ["风寒感冒", "风热感冒", "暑湿感冒"],
             "treatment_principles": ["疏风解表", "宣肺止咳"]},
            
            {"name": "咳嗽", "category": "肺系病证",
             "symptoms": ["咳嗽", "咳痰", "胸闷", "气短"],
             "common_syndromes": ["风寒咳嗽", "风热咳嗽", "燥邪伤肺", "痰湿咳嗽", "痰热咳嗽", "肺阴亏耗"],
             "treatment_principles": ["宣肺止咳", "化痰平喘"]},
            
            {"name": "失眠", "category": "神志病",
             "symptoms": ["入睡困难", "睡眠浅", "易醒", "多梦", "早醒"],
             "common_syndromes": ["心肾不交", "肝郁化火", "痰热内扰", "心脾两虚", "心胆气虚"],
             "treatment_principles": ["养心安神", "清热化痰", "疏肝解郁"]},
        ]
        
        # 将数据保存到数据库
        self._save_herbs_to_db(basic_herbs)
        self._save_formulas_to_db(classic_formulas)
        self._save_diseases_to_db(common_diseases)
        
        # 构建图结构
        self._build_graph()
    
    def _save_herbs_to_db(self, herbs: List[HerbInfo]):
        """保存药物信息到数据库"""
        conn = sqlite3.connect(self.db_path)
        
        for herb in herbs:
            conn.execute("""
                INSERT OR REPLACE INTO herbs 
                (name, category, nature, flavor, meridian, effects, indications, 
                 dosage_min, dosage_max, contraindications, toxicity_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                herb.name, herb.category, herb.nature, herb.flavor,
                json.dumps(herb.meridian, ensure_ascii=False),
                json.dumps(herb.effects, ensure_ascii=False),
                json.dumps(herb.indications, ensure_ascii=False),
                herb.dosage_range[0], herb.dosage_range[1],
                json.dumps(herb.contraindications, ensure_ascii=False),
                herb.toxicity_level
            ))
        
        conn.commit()
        conn.close()
    
    def _save_formulas_to_db(self, formulas: List[FormulaInfo]):
        """保存方剂信息到数据库"""
        conn = sqlite3.connect(self.db_path)
        
        for formula in formulas:
            conn.execute("""
                INSERT OR REPLACE INTO formulas 
                (name, category, composition, functions, indications, syndrome_pattern, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                formula.name, formula.category,
                json.dumps(formula.composition, ensure_ascii=False),
                json.dumps(formula.functions, ensure_ascii=False),
                json.dumps(formula.indications, ensure_ascii=False),
                formula.syndrome_pattern, formula.source
            ))
        
        conn.commit()
        conn.close()
    
    def _save_diseases_to_db(self, diseases: List[Dict]):
        """保存疾病信息到数据库"""
        conn = sqlite3.connect(self.db_path)
        
        for disease in diseases:
            conn.execute("""
                INSERT OR REPLACE INTO diseases 
                (name, category, symptoms, common_syndromes, treatment_principles)
                VALUES (?, ?, ?, ?, ?)
            """, (
                disease["name"], disease["category"],
                json.dumps(disease["symptoms"], ensure_ascii=False),
                json.dumps(disease["common_syndromes"], ensure_ascii=False),
                json.dumps(disease["treatment_principles"], ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
    
    def _build_graph(self):
        """构建知识图谱"""
        conn = sqlite3.connect(self.db_path)
        
        # 1. 添加药物节点
        herbs = conn.execute("SELECT name, category, nature FROM herbs").fetchall()
        for name, category, nature in herbs:
            self.graph.add_node(name, type='herb', category=category, nature=nature)
        
        # 2. 添加方剂节点
        formulas = conn.execute("SELECT name, category, composition FROM formulas").fetchall()
        for name, category, composition_str in formulas:
            self.graph.add_node(name, type='formula', category=category)
            
            # 添加方剂-药物关系
            composition = json.loads(composition_str)
            for herb_name, dosage in composition.items():
                if herb_name in self.graph:
                    self.graph.add_edge(name, herb_name, relation='contains', 
                                      weight=self._parse_dosage(dosage))
        
        # 3. 添加疾病节点
        diseases = conn.execute("SELECT name, category FROM diseases").fetchall()
        for name, category in diseases:
            self.graph.add_node(name, type='disease', category=category)
        
        # 4. 建立治疗关系 (简化版)
        treatment_relations = [
            ("麻黄汤", "感冒", "treats", 0.9),
            ("桂枝汤", "感冒", "treats", 0.8),
            ("四君子汤", "脾虚", "treats", 0.9),
            ("四物汤", "血虚", "treats", 0.9),
            ("人参", "气虚", "treats", 0.8),
            ("当归", "血虚", "treats", 0.8),
            ("麻黄", "感冒", "treats", 0.7),
            ("桂枝", "感冒", "treats", 0.6),
        ]
        
        for source, target, relation, weight in treatment_relations:
            if source in self.graph and target in self.graph:
                self.graph.add_edge(source, target, relation=relation, weight=weight)
        
        conn.close()
    
    def _parse_dosage(self, dosage_str: str) -> float:
        """解析剂量字符串为数值"""
        try:
            dosage_str = dosage_str.replace('g', '').replace('枚', '').strip()
            if '-' in dosage_str:
                parts = dosage_str.split('-')
                return (float(parts[0]) + float(parts[1])) / 2
            return float(dosage_str)
        except:
            return 6.0  # 默认剂量
    
    def find_herb_relationships(self, herb_name: str) -> Dict[str, List]:
        """查找药物的所有关系"""
        if herb_name not in self.graph:
            return {"error": f"未找到药物: {herb_name}"}
        
        relationships = {
            "treats": [],      # 治疗的疾病
            "contained_in": [], # 包含在哪些方剂中
            "synergistic": [],  # 协同药物
            "antagonistic": []  # 拮抗药物
        }
        
        # 出边 - 该药物治疗什么
        for target in self.graph.successors(herb_name):
            edge_data = self.graph[herb_name][target]
            for edge in edge_data.values():
                relation = edge.get('relation', 'unknown')
                if relation == 'treats':
                    relationships["treats"].append({
                        "target": target,
                        "weight": edge.get('weight', 0)
                    })
        
        # 入边 - 哪些方剂包含该药物
        for source in self.graph.predecessors(herb_name):
            edge_data = self.graph[source][herb_name]
            for edge in edge_data.values():
                relation = edge.get('relation', 'unknown')
                if relation == 'contains':
                    relationships["contained_in"].append({
                        "formula": source,
                        "dosage": edge.get('weight', 0)
                    })
        
        return relationships
    
    def recommend_herbs_for_disease(self, disease_name: str, limit: int = 10) -> List[Dict]:
        """为疾病推荐相关药物"""
        recommendations = []
        
        if disease_name not in self.graph:
            return [{"error": f"未找到疾病: {disease_name}"}]
        
        # 找到直接治疗该疾病的药物
        for source in self.graph.predecessors(disease_name):
            if self.graph.nodes[source].get('type') == 'herb':
                edge_data = self.graph[source][disease_name]
                for edge in edge_data.values():
                    if edge.get('relation') == 'treats':
                        recommendations.append({
                            "herb": source,
                            "confidence": edge.get('weight', 0),
                            "reason": f"直接治疗{disease_name}"
                        })
        
        # 找到治疗该疾病的方剂中的药物
        for source in self.graph.predecessors(disease_name):
            if self.graph.nodes[source].get('type') == 'formula':
                # 获取方剂中的药物
                for herb in self.graph.successors(source):
                    if self.graph.nodes[herb].get('type') == 'herb':
                        edge_data = self.graph[source][herb]
                        for edge in edge_data.values():
                            if edge.get('relation') == 'contains':
                                recommendations.append({
                                    "herb": herb,
                                    "confidence": edge.get('weight', 0) / 10,  # 权重降低
                                    "reason": f"方剂{source}的组成药物"
                                })
        
        # 按置信度排序并去重
        seen_herbs = set()
        unique_recommendations = []
        
        for rec in sorted(recommendations, key=lambda x: x['confidence'], reverse=True):
            if rec['herb'] not in seen_herbs:
                seen_herbs.add(rec['herb'])
                unique_recommendations.append(rec)
        
        return unique_recommendations[:limit]
    
    def find_herb_combinations(self, herbs: List[str]) -> Dict[str, Any]:
        """分析药物组合的合理性"""
        result = {
            "herbs": herbs,
            "possible_formulas": [],
            "synergistic_pairs": [],
            "potential_conflicts": [],
            "treatment_focus": []
        }
        
        # 1. 检查是否匹配已知方剂
        conn = sqlite3.connect(self.db_path)
        formulas = conn.execute("SELECT name, composition FROM formulas").fetchall()
        
        for formula_name, composition_str in formulas:
            composition = json.loads(composition_str)
            formula_herbs = set(composition.keys())
            input_herbs = set(herbs)
            
            # 计算匹配度
            intersection = formula_herbs.intersection(input_herbs)
            if len(intersection) >= 2:  # 至少匹配2味药
                match_ratio = len(intersection) / len(formula_herbs)
                result["possible_formulas"].append({
                    "name": formula_name,
                    "match_ratio": match_ratio,
                    "matched_herbs": list(intersection),
                    "missing_herbs": list(formula_herbs - input_herbs),
                    "extra_herbs": list(input_herbs - formula_herbs)
                })
        
        # 2. 分析治疗焦点
        disease_votes = defaultdict(float)
        for herb in herbs:
            relationships = self.find_herb_relationships(herb)
            for treat_info in relationships.get("treats", []):
                disease_votes[treat_info["target"]] += treat_info["weight"]
        
        result["treatment_focus"] = [
            {"disease": disease, "confidence": score}
            for disease, score in sorted(disease_votes.items(), key=lambda x: x[1], reverse=True)
        ]
        
        conn.close()
        return result
    
    def get_herb_info(self, herb_name: str) -> Optional[Dict]:
        """获取药物详细信息"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute(
            "SELECT * FROM herbs WHERE name = ?", (herb_name,)
        )
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        columns = [description[0] for description in cursor.description]
        herb_info = dict(zip(columns, row))
        
        # 解析JSON字段
        json_fields = ['meridian', 'effects', 'indications', 'contraindications']
        for field in json_fields:
            if herb_info.get(field):
                try:
                    herb_info[field] = json.loads(herb_info[field])
                except:
                    herb_info[field] = []
        
        conn.close()
        return herb_info


# 测试和示例
def test_tcm_knowledge_graph():
    """测试中医知识图谱功能"""
    kg = TCMKnowledgeGraph()
    
    print("=== 中医知识图谱系统测试 ===")
    print(f"图中节点数: {len(kg.graph.nodes)}")
    print(f"图中边数: {len(kg.graph.edges)}")
    
    # 1. 测试药物关系查找
    print("\n--- 测试药物关系查找 ---")
    herb_relations = kg.find_herb_relationships("人参")
    print(f"人参的治疗关系: {herb_relations}")
    
    # 2. 测试疾病药物推荐
    print("\n--- 测试疾病药物推荐 ---")
    recommendations = kg.recommend_herbs_for_disease("感冒")
    print("感冒的推荐用药:")
    for rec in recommendations[:5]:
        if "error" not in rec:
            print(f"  - {rec['herb']} (置信度: {rec['confidence']:.2f}) - {rec['reason']}")
    
    # 3. 测试药物组合分析
    print("\n--- 测试药物组合分析 ---")
    test_herbs = ["麻黄", "桂枝", "杏仁", "甘草"]
    combination_analysis = kg.find_herb_combinations(test_herbs)
    
    print(f"输入药物: {test_herbs}")
    print("可能的方剂:")
    for formula in combination_analysis["possible_formulas"]:
        print(f"  - {formula['name']} (匹配度: {formula['match_ratio']:.2f})")
        print(f"    匹配: {formula['matched_herbs']}")
        if formula['missing_herbs']:
            print(f"    缺少: {formula['missing_herbs']}")
    
    print("\n治疗焦点:")
    for focus in combination_analysis["treatment_focus"][:3]:
        print(f"  - {focus['disease']} (置信度: {focus['confidence']:.2f})")
    
    # 4. 测试药物详情
    print("\n--- 测试药物详情查询 ---")
    herb_info = kg.get_herb_info("人参")
    if herb_info:
        print(f"药物: {herb_info['name']}")
        print(f"性味: {herb_info['nature']} {herb_info['flavor']}")
        print(f"归经: {herb_info.get('meridian', [])}")
        print(f"功效: {herb_info.get('effects', [])}")
        print(f"剂量范围: {herb_info['dosage_min']}-{herb_info['dosage_max']}g")


if __name__ == "__main__":
    test_tcm_knowledge_graph()