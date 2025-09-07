#!/usr/bin/env python3
"""
名医处方收集和学习系统
收集、分析、学习名医处方经验，提升AI诊断准确性
"""

import json
import sqlite3
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import statistics
from collections import defaultdict, Counter

import sys
sys.path.append('/opt/tcm-ai')
from core.prescription.prescription_checker import Prescription, PrescriptionParser, PrescriptionSafetyChecker
from core.knowledge_retrieval.tcm_knowledge_graph import TCMKnowledgeGraph

@dataclass
class DoctorProfile:
    """名医档案"""
    name: str
    specialty: List[str]  # 专长领域
    school: str  # 学术流派
    experience_years: int  # 临床经验年数
    location: str  # 地域
    famous_formulas: List[str]  # 代表方剂
    treatment_philosophy: str  # 治疗理念
    unique_techniques: List[str]  # 独特技法

@dataclass
class ClinicalCase:
    """临床案例"""
    case_id: str
    doctor_name: str
    patient_info: Dict[str, Any]  # 患者信息 (匿名化)
    chief_complaint: str  # 主诉
    present_illness: str  # 现病史
    tcm_diagnosis: str  # 中医诊断
    syndrome_differentiation: str  # 辨证
    prescription: Prescription  # 处方
    follow_up: List[Dict] = None  # 随访记录
    outcome: str = ""  # 治疗结果
    notes: str = ""  # 医生备注

class FamousDoctorLearningSystem:
    """名医处方学习系统"""
    
    def __init__(self, db_path: str = "/opt/tcm-ai/data/famous_doctors.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.parser = PrescriptionParser()
        self.safety_checker = PrescriptionSafetyChecker()
        self.knowledge_graph = TCMKnowledgeGraph()
        
        self._init_database()
        self._load_famous_doctors()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        
        # 名医档案表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS famous_doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                specialty TEXT,
                school TEXT,
                experience_years INTEGER,
                location TEXT,
                famous_formulas TEXT,
                treatment_philosophy TEXT,
                unique_techniques TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 临床案例表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clinical_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                doctor_name TEXT,
                patient_info TEXT,
                chief_complaint TEXT,
                present_illness TEXT,
                tcm_diagnosis TEXT,
                syndrome_differentiation TEXT,
                prescription_json TEXT,
                follow_up TEXT,
                outcome TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_name) REFERENCES famous_doctors (name)
            )
        """)
        
        # 处方模式表 - 用于学习医生用药规律
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prescription_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_name TEXT,
                disease_name TEXT,
                syndrome_pattern TEXT,
                herb_combination TEXT,  -- JSON格式的药物组合
                frequency INTEGER DEFAULT 1,  -- 使用频次
                success_rate REAL DEFAULT 0.0,  -- 成功率
                avg_dosage TEXT,  -- JSON格式的平均剂量
                notes TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用药经验表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medication_experience (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_name TEXT,
                herb_name TEXT,
                usage_context TEXT,  -- 使用场景
                special_dosage TEXT,  -- 特殊剂量
                preparation_method TEXT,  -- 特殊炮制
                combination_herbs TEXT,  -- 常配伍药物
                contraindications TEXT,  -- 禁忌情况
                clinical_tips TEXT,  -- 临床心得
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_famous_doctors(self):
        """加载著名中医师资料"""
        famous_doctors = [
            DoctorProfile(
                name="张仲景",
                specialty=["伤寒杂病", "内科", "急危重症"],
                school="经方派",
                experience_years=50,
                location="东汉南阳",
                famous_formulas=["麻黄汤", "桂枝汤", "小柴胡汤", "四逆汤", "白虎汤"],
                treatment_philosophy="辨证论治，方证相应，用药精准",
                unique_techniques=["六经辨证", "方证对应", "药量精确"]
            ),
            
            DoctorProfile(
                name="叶天士",
                specialty=["温病", "内科", "妇科"],
                school="温病派",
                experience_years=60,
                location="清代苏州",
                famous_formulas=["银翘散", "桑菊饮", "清营汤", "犀角地黄汤"],
                treatment_philosophy="温病卫气营血辨证，用药轻灵",
                unique_techniques=["卫气营血辨证", "轻清宣透", "甘寒清润"]
            ),
            
            DoctorProfile(
                name="李东垣",
                specialty=["脾胃病", "内伤杂病", "消化系统"],
                school="补土派",
                experience_years=55,
                location="金元时期",
                famous_formulas=["补中益气汤", "升阳散火汤", "清胃散"],
                treatment_philosophy="脾胃为后天之本，重视调理脾胃",
                unique_techniques=["升阳益气", "甘温除热", "调理脾胃"]
            ),
            
            DoctorProfile(
                name="朱丹溪",
                specialty=["滋阴降火", "内科", "妇科"],
                school="滋阴派",
                experience_years=50,
                location="元代",
                famous_formulas=["大补阴丸", "知柏地黄丸", "左归丸"],
                treatment_philosophy="阴常不足，阳常有余，重视滋阴降火",
                unique_techniques=["滋阴降火", "养血柔肝", "清热解毒"]
            ),
            
            DoctorProfile(
                name="刘渡舟",
                specialty=["伤寒论", "经方应用", "内科"],
                school="现代经方派",
                experience_years=60,
                location="现代北京",
                famous_formulas=["小柴胡汤加减", "桂枝汤类方", "麻黄汤类方"],
                treatment_philosophy="经方辨证，师古而不泥古，灵活应用",
                unique_techniques=["经方辨证", "类方应用", "现代应用经方"]
            )
        ]
        
        conn = sqlite3.connect(self.db_path)
        
        for doctor in famous_doctors:
            conn.execute("""
                INSERT OR REPLACE INTO famous_doctors 
                (name, specialty, school, experience_years, location, famous_formulas, 
                 treatment_philosophy, unique_techniques)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doctor.name,
                json.dumps(doctor.specialty, ensure_ascii=False),
                doctor.school,
                doctor.experience_years,
                doctor.location,
                json.dumps(doctor.famous_formulas, ensure_ascii=False),
                doctor.treatment_philosophy,
                json.dumps(doctor.unique_techniques, ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
    
    def add_clinical_case(self, case: ClinicalCase) -> bool:
        """添加临床案例"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            conn.execute("""
                INSERT OR REPLACE INTO clinical_cases 
                (case_id, doctor_name, patient_info, chief_complaint, present_illness, 
                 tcm_diagnosis, syndrome_differentiation, prescription_json, 
                 follow_up, outcome, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case.case_id,
                case.doctor_name,
                json.dumps(case.patient_info, ensure_ascii=False),
                case.chief_complaint,
                case.present_illness,
                case.tcm_diagnosis,
                case.syndrome_differentiation,
                json.dumps(asdict(case.prescription), ensure_ascii=False),
                json.dumps(case.follow_up or [], ensure_ascii=False),
                case.outcome,
                case.notes
            ))
            
            conn.commit()
            conn.close()
            
            # 更新处方模式
            self._update_prescription_patterns(case)
            
            return True
            
        except Exception as e:
            print(f"添加临床案例失败: {e}")
            return False
    
    def _update_prescription_patterns(self, case: ClinicalCase):
        """更新处方模式统计"""
        conn = sqlite3.connect(self.db_path)
        
        # 提取药物组合
        herb_names = [herb.name for herb in case.prescription.herbs]
        herb_combination = json.dumps(sorted(herb_names), ensure_ascii=False)
        
        # 计算平均剂量
        avg_dosages = {}
        for herb in case.prescription.herbs:
            try:
                dosage = float(herb.dosage.replace('g', '').strip())
                avg_dosages[herb.name] = dosage
            except:
                pass
        
        # 检查是否已存在该模式
        cursor = conn.execute("""
            SELECT id, frequency, avg_dosage FROM prescription_patterns 
            WHERE doctor_name = ? AND disease_name = ? AND syndrome_pattern = ? 
            AND herb_combination = ?
        """, (
            case.doctor_name,
            case.tcm_diagnosis,
            case.syndrome_differentiation,
            herb_combination
        ))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            pattern_id, frequency, existing_dosages_str = existing
            
            # 合并平均剂量
            try:
                existing_dosages = json.loads(existing_dosages_str) if existing_dosages_str else {}
            except:
                existing_dosages = {}
            
            # 计算新的平均值
            for herb, dosage in avg_dosages.items():
                if herb in existing_dosages:
                    existing_dosages[herb] = (existing_dosages[herb] * frequency + dosage) / (frequency + 1)
                else:
                    existing_dosages[herb] = dosage
            
            conn.execute("""
                UPDATE prescription_patterns 
                SET frequency = frequency + 1, 
                    avg_dosage = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                json.dumps(existing_dosages, ensure_ascii=False),
                pattern_id
            ))
        else:
            # 插入新记录
            conn.execute("""
                INSERT INTO prescription_patterns 
                (doctor_name, disease_name, syndrome_pattern, herb_combination, 
                 frequency, avg_dosage)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (
                case.doctor_name,
                case.tcm_diagnosis,
                case.syndrome_differentiation,
                herb_combination,
                json.dumps(avg_dosages, ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
    
    def learn_doctor_prescription_patterns(self, doctor_name: str) -> Dict[str, Any]:
        """学习特定医生的处方规律"""
        conn = sqlite3.connect(self.db_path)
        
        # 获取该医生的所有处方模式
        cursor = conn.execute("""
            SELECT disease_name, syndrome_pattern, herb_combination, 
                   frequency, avg_dosage, success_rate
            FROM prescription_patterns 
            WHERE doctor_name = ?
            ORDER BY frequency DESC
        """, (doctor_name,))
        
        patterns = cursor.fetchall()
        
        analysis = {
            "doctor_name": doctor_name,
            "total_patterns": len(patterns),
            "common_diseases": {},
            "frequent_herb_combinations": [],
            "dosage_preferences": {},
            "treatment_characteristics": []
        }
        
        # 统计常见疾病
        disease_count = defaultdict(int)
        for pattern in patterns:
            disease_name, syndrome, herbs_json, freq, dosage_json, success_rate = pattern
            disease_count[disease_name] += freq
        
        analysis["common_diseases"] = dict(sorted(disease_count.items(), 
                                                key=lambda x: x[1], reverse=True))
        
        # 统计频繁药物组合
        for pattern in patterns[:10]:  # 取前10个最频繁的模式
            disease_name, syndrome, herbs_json, freq, dosage_json, success_rate = pattern
            try:
                herbs = json.loads(herbs_json)
                analysis["frequent_herb_combinations"].append({
                    "herbs": herbs,
                    "disease": disease_name,
                    "syndrome": syndrome,
                    "frequency": freq,
                    "success_rate": success_rate or 0.0
                })
            except:
                pass
        
        # 统计用药偏好
        all_herb_dosages = defaultdict(list)
        for pattern in patterns:
            try:
                dosage_json = pattern[4]
                if dosage_json:
                    dosages = json.loads(dosage_json)
                    for herb, dosage in dosages.items():
                        all_herb_dosages[herb].append(dosage)
            except:
                pass
        
        # 计算每个药物的平均用量和用量范围
        for herb, dosage_list in all_herb_dosages.items():
            if dosage_list:
                analysis["dosage_preferences"][herb] = {
                    "avg_dosage": round(statistics.mean(dosage_list), 1),
                    "min_dosage": min(dosage_list),
                    "max_dosage": max(dosage_list),
                    "usage_count": len(dosage_list)
                }
        
        conn.close()
        return analysis
    
    def recommend_prescription_by_doctor_style(self, disease: str, syndrome: str, 
                                             doctor_name: str) -> Dict[str, Any]:
        """基于特定医生风格推荐处方"""
        conn = sqlite3.connect(self.db_path)
        
        # 查找该医生针对相同疾病和证型的处方模式
        cursor = conn.execute("""
            SELECT herb_combination, avg_dosage, frequency, success_rate
            FROM prescription_patterns 
            WHERE doctor_name = ? AND disease_name = ? AND syndrome_pattern = ?
            ORDER BY frequency DESC, success_rate DESC
        """, (doctor_name, disease, syndrome))
        
        exact_matches = cursor.fetchall()
        
        # 如果没有完全匹配，查找相似疾病
        if not exact_matches:
            cursor = conn.execute("""
                SELECT disease_name, syndrome_pattern, herb_combination, avg_dosage, 
                       frequency, success_rate
                FROM prescription_patterns 
                WHERE doctor_name = ? AND (disease_name LIKE ? OR syndrome_pattern LIKE ?)
                ORDER BY frequency DESC, success_rate DESC
                LIMIT 5
            """, (doctor_name, f"%{disease}%", f"%{syndrome}%"))
            
            similar_matches = cursor.fetchall()
        else:
            similar_matches = []
        
        recommendation = {
            "doctor_name": doctor_name,
            "target_disease": disease,
            "target_syndrome": syndrome,
            "exact_matches": [],
            "similar_cases": [],
            "confidence": 0.0
        }
        
        # 处理精确匹配
        for match in exact_matches:
            herbs_json, dosage_json, frequency, success_rate = match
            try:
                herbs = json.loads(herbs_json)
                dosages = json.loads(dosage_json) if dosage_json else {}
                
                prescription_herbs = []
                for herb_name in herbs:
                    dosage = dosages.get(herb_name, 6.0)  # 默认6g
                    prescription_herbs.append({
                        "name": herb_name,
                        "dosage": f"{dosage}g"
                    })
                
                recommendation["exact_matches"].append({
                    "herbs": prescription_herbs,
                    "frequency": frequency,
                    "success_rate": success_rate or 0.0,
                    "confidence": min(0.9, frequency * 0.1 + (success_rate or 0) * 0.5)
                })
            except:
                pass
        
        # 处理相似案例
        for match in similar_matches:
            disease_name, syndrome_pattern, herbs_json, dosage_json, frequency, success_rate = match
            try:
                herbs = json.loads(herbs_json)
                dosages = json.loads(dosage_json) if dosage_json else {}
                
                prescription_herbs = []
                for herb_name in herbs:
                    dosage = dosages.get(herb_name, 6.0)
                    prescription_herbs.append({
                        "name": herb_name,
                        "dosage": f"{dosage}g"
                    })
                
                recommendation["similar_cases"].append({
                    "disease": disease_name,
                    "syndrome": syndrome_pattern,
                    "herbs": prescription_herbs,
                    "frequency": frequency,
                    "success_rate": success_rate or 0.0,
                    "confidence": min(0.7, frequency * 0.05 + (success_rate or 0) * 0.3)
                })
            except:
                pass
        
        # 计算总体置信度
        if exact_matches:
            recommendation["confidence"] = max([m.get("confidence", 0) for m in recommendation["exact_matches"]])
        elif similar_matches:
            recommendation["confidence"] = max([m.get("confidence", 0) for m in recommendation["similar_cases"]]) * 0.7
        
        conn.close()
        return recommendation
    
    def get_doctor_profile(self, doctor_name: str) -> Optional[Dict]:
        """获取医生档案"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("SELECT * FROM famous_doctors WHERE name = ?", (doctor_name,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        columns = [description[0] for description in cursor.description]
        profile = dict(zip(columns, row))
        
        # 解析JSON字段
        json_fields = ['specialty', 'famous_formulas', 'unique_techniques']
        for field in json_fields:
            if profile.get(field):
                try:
                    profile[field] = json.loads(profile[field])
                except:
                    profile[field] = []
        
        # 添加统计信息
        cursor = conn.execute("""
            SELECT COUNT(*) as case_count, 
                   COUNT(DISTINCT tcm_diagnosis) as disease_count
            FROM clinical_cases WHERE doctor_name = ?
        """, (doctor_name,))
        
        stats = cursor.fetchone()
        if stats:
            profile["case_count"] = stats[0]
            profile["disease_count"] = stats[1]
        
        conn.close()
        return profile
    
    async def generate_decision_paths(self, disease_name: str, thinking_process: str, path_prompt: str) -> Dict[str, Any]:
        """
        生成分支路径结构的决策树
        
        Args:
            disease_name: 疾病名称
            thinking_process: 医生思维过程
            path_prompt: 路径生成提示词
            
        Returns:
            分支路径数据结构
        """
        try:
            # 这里应该调用AI服务生成路径，目前使用规则生成
            # 实际部署时应该集成阿里云Dashscope或其他AI服务
            
            # 分析医生思维过程，提取关键信息
            extracted_info = self._extract_thinking_elements(disease_name, thinking_process)
            
            # 生成分支路径
            paths = self._generate_clinical_paths(extracted_info)
            
            return {
                "paths": paths
            }
            
        except Exception as e:
            print(f"生成决策路径失败: {e}")
            # 返回默认路径结构
            return self._create_default_paths(disease_name)
    
    def _extract_thinking_elements(self, disease_name: str, thinking_process: str) -> Dict[str, Any]:
        """
        从医生思维描述中提取诊疗要素
        
        Args:
            disease_name: 疾病名称
            thinking_process: 思维过程描述
            
        Returns:
            提取的诊疗要素
        """
        # 使用简单的关键词提取（实际应该用NLP）
        symptoms = []
        conditions = []
        diagnoses = []
        treatments = []
        formulas = []
        
        # 症状关键词
        symptom_keywords = ['失眠', '头痛', '胃痛', '腹泻', '咳嗽', '发热', '乏力', '心悸']
        for keyword in symptom_keywords:
            if keyword in thinking_process:
                symptoms.append(keyword)
        
        # 判断条件关键词
        condition_keywords = ['舌红', '舌淡', '苔厚', '苔薄', '脉滑', '脉数', '脉沉', '脉细', '面色萎黄', '面红']
        for keyword in condition_keywords:
            if keyword in thinking_process:
                conditions.append(keyword)
        
        # 证型关键词
        diagnosis_keywords = ['心火', '脾虚', '肾虚', '肝郁', '痰湿', '血瘀', '气滞', '阳虚', '阴虚']
        for keyword in diagnosis_keywords:
            if keyword in thinking_process:
                diagnoses.append(keyword)
        
        # 方剂关键词
        formula_keywords = ['黄连阿胶汤', '归脾汤', '逍遥散', '补中益气汤', '六味地黄丸', '金匮肾气丸']
        for keyword in formula_keywords:
            if keyword in thinking_process:
                formulas.append(keyword)
        
        return {
            "disease": disease_name,
            "symptoms": symptoms or [disease_name],
            "conditions": conditions or ["症状明显", "症状隐隐"],
            "diagnoses": diagnoses or ["实证", "虚证"],
            "treatments": ["对症治疗"] if not diagnoses else [f"治疗{d}" for d in diagnoses[:2]],
            "formulas": formulas or ["对症方剂"]
        }
    
    def _generate_clinical_paths(self, extracted_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据提取的要素生成临床路径
        
        Args:
            extracted_info: 提取的诊疗要素
            
        Returns:
            临床路径列表
        """
        paths = []
        disease = extracted_info["disease"]
        
        # 生成实证路径
        if extracted_info["conditions"] and extracted_info["diagnoses"]:
            for i, (condition, diagnosis) in enumerate(zip(extracted_info["conditions"][:2], extracted_info["diagnoses"][:2])):
                formula = extracted_info["formulas"][i] if i < len(extracted_info["formulas"]) else "对症方剂"
                treatment = extracted_info["treatments"][i] if i < len(extracted_info["treatments"]) else "对症治疗"
                
                path = {
                    "id": f"path_{i+1}",
                    "steps": [
                        {"type": "symptom", "content": disease},
                        {"type": "condition", "content": condition, "result": True},
                        {"type": "diagnosis", "content": diagnosis},
                        {"type": "treatment", "content": treatment},
                        {"type": "formula", "content": formula}
                    ],
                    "keywords": [disease] + extracted_info["symptoms"][:3] + [condition],
                    "created_by": "AI生成"
                }
                paths.append(path)
        
        # 如果没有提取到足够信息，生成默认路径
        if not paths:
            paths = self._create_default_paths(disease)["paths"]
        
        return paths
    
    def _create_default_paths(self, disease_name: str) -> Dict[str, Any]:
        """
        创建默认的分支路径
        
        Args:
            disease_name: 疾病名称
            
        Returns:
            默认路径结构
        """
        return {
            "paths": [
                {
                    "id": f"default_path_1",
                    "steps": [
                        {"type": "symptom", "content": disease_name},
                        {"type": "condition", "content": "症状重", "result": True},
                        {"type": "diagnosis", "content": "实证"},
                        {"type": "treatment", "content": "泻实"},
                        {"type": "formula", "content": "清热方"}
                    ],
                    "keywords": [disease_name, "症状重", "实证"],
                    "created_by": "系统默认"
                },
                {
                    "id": f"default_path_2",
                    "steps": [
                        {"type": "symptom", "content": disease_name},
                        {"type": "condition", "content": "症状轻", "result": True},
                        {"type": "diagnosis", "content": "虚证"},
                        {"type": "treatment", "content": "补虚"},
                        {"type": "formula", "content": "补益方"}
                    ],
                    "keywords": [disease_name, "症状轻", "虚证"],
                    "created_by": "系统默认"
                }
            ]
        }
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习系统统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 获取总案例数
            cursor = conn.execute("SELECT COUNT(*) FROM clinical_cases")
            total_cases = cursor.fetchone()[0]
            
            # 获取总医生数
            cursor = conn.execute("SELECT COUNT(DISTINCT doctor_name) FROM clinical_cases")
            total_doctors = cursor.fetchone()[0]
            
            # 获取最近案例时间
            cursor = conn.execute("SELECT MAX(created_at) FROM clinical_cases")
            latest_case = cursor.fetchone()[0]
            
            # 获取按来源分类的统计
            cursor = conn.execute("""
                SELECT SUBSTR(case_id, 1, 6) as source_type, COUNT(*) as count 
                FROM clinical_cases 
                GROUP BY SUBSTR(case_id, 1, 6)
            """)
            source_stats = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                "total_cases": total_cases,
                "total_doctors": total_doctors,
                "latest_case_time": latest_case,
                "source_statistics": source_stats,
                "database_path": str(self.db_path),
                "system_status": "operational"
            }
            
        except Exception as e:
            logger.error(f"获取学习统计失败: {e}")
            return {
                "total_cases": 0,
                "total_doctors": 0,
                "latest_case_time": None,
                "source_statistics": {},
                "database_path": str(self.db_path),
                "system_status": "error",
                "error": str(e)
            }

    def add_medication_experience(self, doctor_name: str, herb_name: str, 
                                experience_data: Dict[str, str]) -> bool:
        """添加用药经验"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            conn.execute("""
                INSERT OR REPLACE INTO medication_experience 
                (doctor_name, herb_name, usage_context, special_dosage, 
                 preparation_method, combination_herbs, contraindications, clinical_tips)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doctor_name,
                herb_name,
                experience_data.get("usage_context", ""),
                experience_data.get("special_dosage", ""),
                experience_data.get("preparation_method", ""),
                experience_data.get("combination_herbs", ""),
                experience_data.get("contraindications", ""),
                experience_data.get("clinical_tips", "")
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"添加用药经验失败: {e}")
            return False
    
    async def analyze_doctor_thinking(self, thinking_process: str, disease_name: str, analysis_prompt: str) -> Dict[str, Any]:
        """
        分析医生的诊疗思维过程
        
        Args:
            thinking_process: 医生的思维描述
            disease_name: 疾病名称
            analysis_prompt: 分析提示词
            
        Returns:
            分析结果
        """
        try:
            # 这里应该调用AI服务进行分析，目前使用模拟分析
            # 实际部署时应该集成阿里云Dashscope或其他AI服务
            
            # 提取关键信息
            key_points = self._extract_key_points(thinking_process, disease_name)
            missing_considerations = self._identify_missing_considerations(thinking_process, disease_name)
            suggested_workflow = self._suggest_workflow(thinking_process, disease_name)
            
            return {
                "key_points": key_points,
                "missing_considerations": missing_considerations,
                "suggested_workflow": suggested_workflow
            }
            
        except Exception as e:
            print(f"分析医生思维失败: {e}")
            # 返回默认分析结果
            return {
                "key_points": [
                    f"医生对{disease_name}有基本的认识和治疗思路",
                    "考虑了主要症状和治疗方案",
                    "体现了中医辨证论治思维"
                ],
                "missing_considerations": [
                    "建议补充四诊合参的详细描述",
                    "可以考虑更多的鉴别诊断",
                    "注意个体差异和体质因素",
                    "加强随访和疗效评估"
                ],
                "suggested_workflow": "1. 详细四诊收集 → 2. 综合辨证分析 → 3. 确定治则治法 → 4. 方药选择 → 5. 疗效观察与调整"
            }
    
    async def generate_decision_tree(self, disease_name: str, thinking_process: str, schools: List[str], tree_prompt: str) -> Dict[str, Any]:
        """
        生成诊疗决策树
        
        Args:
            disease_name: 疾病名称
            thinking_process: 医生思维过程
            schools: 选择的中医流派
            tree_prompt: 决策树生成提示词
            
        Returns:
            决策树数据结构
        """
        try:
            # 这里应该调用AI服务生成决策树，目前使用规则生成
            # 实际部署时应该集成阿里云Dashscope或其他AI服务
            
            # 生成基础决策树结构
            tree_levels = self._generate_tree_levels(disease_name, thinking_process)
            
            # 生成流派建议
            school_suggestions = self._generate_school_suggestions(disease_name, thinking_process, schools)
            
            return {
                "tree": {
                    "levels": tree_levels
                },
                "school_suggestions": school_suggestions
            }
            
        except Exception as e:
            print(f"生成决策树失败: {e}")
            # 返回默认决策树结构
            return {
                "tree": {
                    "levels": [
                        {
                            "title": "症状观察",
                            "type": "symptom",
                            "nodes": [
                                {"name": f"{disease_name}典型症状", "description": "主要临床表现"},
                                {"name": "伴随症状", "description": "次要症状表现"},
                                {"name": "诱发因素", "description": "病因病机分析"}
                            ]
                        },
                        {
                            "title": "辨证分析",
                            "type": "diagnosis",
                            "nodes": [
                                {"name": "主要证型", "description": "常见证候类型"},
                                {"name": "兼夹证", "description": "复合证候分析"},
                                {"name": "体质评估", "description": "个体差异考虑"}
                            ]
                        },
                        {
                            "title": "治疗方案",
                            "type": "treatment",
                            "nodes": [
                                {"name": "主治法", "description": "核心治疗原则"},
                                {"name": "辅助治疗", "description": "配合治疗方法"},
                                {"name": "预防调护", "description": "日常调养建议"}
                            ]
                        }
                    ]
                },
                "school_suggestions": school_suggestions
            }
    
    def _extract_key_points(self, thinking_process: str, disease_name: str) -> List[str]:
        """从思维过程中提取关键诊断要点"""
        key_points = []
        
        # 基于关键词提取
        if "症状" in thinking_process:
            key_points.append(f"识别了{disease_name}的相关症状")
        if "舌" in thinking_process or "脉" in thinking_process:
            key_points.append("考虑了舌脉诊查要点")
        if "方" in thinking_process or "药" in thinking_process:
            key_points.append("制定了具体的方药治疗方案")
        if "证" in thinking_process or "辨" in thinking_process:
            key_points.append("运用了辨证论治思维")
        
        # 默认要点
        if not key_points:
            key_points = [
                f"对{disease_name}有基本认识",
                "具备中医诊疗思维",
                "考虑了治疗方案"
            ]
        
        return key_points
    
    def _identify_missing_considerations(self, thinking_process: str, disease_name: str) -> List[str]:
        """识别可能遗漏的考虑点"""
        missing = []
        
        # 检查是否遗漏重要方面
        if "四诊" not in thinking_process:
            missing.append("建议补充完整的四诊信息")
        if "体质" not in thinking_process:
            missing.append("考虑患者个体体质差异")
        if "鉴别" not in thinking_process:
            missing.append("加强与相似疾病的鉴别诊断")
        if "随访" not in thinking_process:
            missing.append("制定随访观察计划")
        if "禁忌" not in thinking_process:
            missing.append("注意用药禁忌和注意事项")
        
        # 默认建议
        if not missing:
            missing = [
                "建议结合现代医学检查结果",
                "注意药物配伍禁忌",
                "考虑季节气候因素影响"
            ]
        
        return missing
    
    def _suggest_workflow(self, thinking_process: str, disease_name: str) -> str:
        """建议标准化的诊疗流程"""
        return f"针对{disease_name}的标准诊疗流程：1. 详细问诊收集病史 → 2. 四诊合参全面检查 → 3. 辨证分型确定证候 → 4. 制定治则选择方药 → 5. 观察疗效及时调整"
    
    def _generate_tree_levels(self, disease_name: str, thinking_process: str) -> List[Dict[str, Any]]:
        """生成决策树层级结构"""
        # 基础的三层结构：症状-证型-治疗
        return [
            {
                "title": "症状识别",
                "type": "symptom",
                "nodes": [
                    {"name": f"{disease_name}主症", "description": "核心临床表现"},
                    {"name": "次要症状", "description": "伴随症状表现"},
                    {"name": "体征观察", "description": "客观体征检查"}
                ]
            },
            {
                "title": "证候辨识",
                "type": "diagnosis", 
                "nodes": [
                    {"name": "主要证型", "description": "最常见证候类型"},
                    {"name": "兼证分析", "description": "复合证候判断"},
                    {"name": "病位病性", "description": "病变部位和性质"}
                ]
            },
            {
                "title": "治疗决策",
                "type": "treatment",
                "nodes": [
                    {"name": "治疗原则", "description": "核心治疗策略"},
                    {"name": "方药选择", "description": "具体处方方案"},
                    {"name": "调护建议", "description": "日常调养指导"}
                ]
            }
        ]
    
    def _generate_school_suggestions(self, disease_name: str, thinking_process: str, schools: List[str]) -> List[Dict[str, str]]:
        """生成各流派的补充建议"""
        suggestions = []
        
        school_advice_map = {
            "张仲景经方派": f"从经方角度看{disease_name}，建议严格按照条文进行辨证，注重方证对应，考虑原方的适应证和禁忌症",
            "叶天士温病派": f"温病学派认为{disease_name}需要重视卫气营血辨证，注意病邪的传变规律，用药宜清灵活泼",
            "李东垣脾胃派": f"脾胃学派强调{disease_name}的治疗要重视脾胃功能，注意升清降浊，慎用苦寒药物",
            "朱丹溪滋阴派": f"丹溪学派认为{disease_name}需要重视阴液的保护，注意养阴清热，避免过用温燥之品",
            "郑钦安火神派": f"火神派观点认为{disease_name}需要重视阳气的作用，适当温阳扶正，但需防止助火",
            "刘渡舟经方派": f"现代经方应用认为{disease_name}需要灵活运用经方，结合现代临床实践，注重个体化治疗"
        }
        
        for school in schools:
            if school in school_advice_map:
                suggestions.append({
                    "school": school,
                    "advice": school_advice_map[school]
                })
        
        # 如果没有匹配的流派，提供通用建议
        if not suggestions:
            suggestions.append({
                "school": "综合观点",
                "advice": f"针对{disease_name}，建议综合运用各家经验，因人制宜，辨证论治，注重整体调理"
            })
        
        return suggestions

    async def generate_decision_paths(self, disease_name: str, include_tcm_analysis: bool = True, 
                                    complexity_level: str = "standard", generation_prompt: str = "") -> Dict[str, Any]:
        """
        为可视化构建器生成决策路径
        
        Args:
            disease_name: 疾病名称
            include_tcm_analysis: 是否包含中医理论分析
            complexity_level: 复杂度级别
            generation_prompt: 生成提示词
            
        Returns:
            决策路径数据
        """
        try:
            # 根据疾病名称生成默认路径
            paths = self._generate_default_paths_for_disease(disease_name, complexity_level)
            
            # 如果包含TCM分析，添加理论依据
            if include_tcm_analysis:
                for path in paths:
                    path["tcm_theory"] = self._get_tcm_theory_for_path(path, disease_name)
            
            return {
                "paths": paths,
                "suggested_layout": {
                    "auto_arrange": True,
                    "spacing": {"horizontal": 300, "vertical": 150}
                }
            }
            
        except Exception as e:
            print(f"生成决策路径失败: {e}")
            # 返回基础路径 - 包含具体方剂
            default_paths = self._generate_default_paths_for_disease(disease_name, complexity_level)
            if not default_paths:
                # 通用备用路径
                default_paths = [
                    {
                        "id": f"{disease_name}_basic_path",
                        "title": f"{disease_name}基础诊疗路径",
                        "steps": [
                            {"type": "symptom", "content": disease_name},
                            {"type": "condition", "content": "症状明显", "options": ["是", "否"]},
                            {"type": "diagnosis", "content": "基础证型"},
                            {"type": "treatment", "content": "对症治疗"},
                            {"type": "formula", "content": "甘草干姜汤"}
                        ],
                        "keywords": [disease_name],
                        "tcm_theory": "基础中医理论应用"
                    }
                ]
            
            return {
                "paths": default_paths,
                "suggested_layout": {
                    "auto_arrange": True,
                    "spacing": {"horizontal": 300, "vertical": 150}
                }
            }

    async def analyze_tcm_theory(self, tree_data: Dict[str, Any], disease_name: str, analysis_prompt: str) -> Dict[str, Any]:
        """
        基于中医理论分析决策树
        
        Args:
            tree_data: 决策树数据
            disease_name: 疾病名称  
            analysis_prompt: 分析提示词
            
        Returns:
            理论分析结果
        """
        try:
            # 分析决策树的理论合理性
            theory_score = self._calculate_theory_score(tree_data, disease_name)
            strengths = self._identify_theory_strengths(tree_data, disease_name)
            weaknesses = self._identify_theory_weaknesses(tree_data, disease_name)
            
            result = {
                "theory_analysis": {
                    "overall_score": theory_score,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "theoretical_basis": f"基于中医{disease_name}的传统理论体系分析"
                },
                "improvement_suggestions": self._get_improvement_suggestions(tree_data, disease_name),
                "knowledge_supplements": self._get_knowledge_supplements(disease_name)
            }
            
            # 确保返回有效结果
            return result
            
        except Exception as e:
            print(f"TCM理论分析失败: {e}")
            # 返回默认分析
            return {
                "theory_analysis": {
                    "overall_score": 75,
                    "strengths": ["基本辨证思路清晰"],
                    "weaknesses": ["可进一步完善"],
                    "theoretical_basis": f"中医{disease_name}理论应用"
                },
                "improvement_suggestions": [
                    {
                        "type": "theory_enhancement",
                        "description": "建议加强理论依据",
                        "priority": "medium"
                    }
                ],
                "knowledge_supplements": [
                    {
                        "topic": "基础理论",
                        "content": f"{disease_name}的基本理论",
                        "source": "中医内科学"
                    }
                ]
            }

    async def detect_missing_logic(self, current_tree: Dict[str, Any], disease_name: str, detection_prompt: str) -> Dict[str, Any]:
        """
        检测决策树遗漏的诊疗逻辑
        
        Args:
            current_tree: 当前决策树数据
            disease_name: 疾病名称
            detection_prompt: 检测提示词
            
        Returns:
            遗漏逻辑检测结果
        """
        try:
            # 直接返回遗漏逻辑分析，避免调用可能有问题的辅助方法
            return self._create_missing_logic_analysis_direct(current_tree, disease_name)
            
        except Exception as e:
            print(f"遗漏逻辑检测失败: {e}")
            # 返回默认检测结果
            return {
                "missing_analyses": [
                    {
                        "category": "基础检测",
                        "items": [
                            {
                                "type": "general_check",
                                "content": "建议补充更多诊疗细节",
                                "description": "决策树可能需要更多细化",
                                "importance": "medium",
                                "suggested_addition": {
                                    "step_type": "condition",
                                    "step_content": "补充判断条件"
                                }
                            }
                        ]
                    }
                ],
                "quick_additions": [
                    {
                        "title": "补充基础路径",
                        "path_data": {
                            "steps": [
                                {"type": "condition", "content": "症状是否典型"},
                                {"type": "diagnosis", "content": "确认诊断"}
                            ]
                        }
                    }
                ]
            }

    def _generate_default_paths_for_disease(self, disease_name: str, complexity_level: str) -> List[Dict[str, Any]]:
        """为特定疾病生成默认诊疗路径"""
        paths = []
        
        # 基于疾病名称的专门路径生成
        if disease_name == "失眠":
            paths = [
                {
                    "id": "insomnia_heart_fire",
                    "title": "心火旺盛型失眠",
                    "steps": [
                        {"type": "symptom", "content": "失眠"},
                        {"type": "condition", "content": "舌红苔黄，心烦口干", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "心火旺盛证"},
                        {"type": "treatment", "content": "清心火，安神志"},
                        {"type": "formula", "content": "黄连阿胶汤"}
                    ],
                    "keywords": ["失眠", "多梦", "心烦", "口干", "舌红", "苔黄"],
                    "tcm_theory": "心主神明，心火亢盛则神不安"
                },
                {
                    "id": "insomnia_heart_spleen_deficiency",
                    "title": "心脾两虚型失眠",
                    "steps": [
                        {"type": "symptom", "content": "失眠"},
                        {"type": "condition", "content": "面色萎黄，健忘心悸", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "心脾两虚证"},
                        {"type": "treatment", "content": "补益心脾，养血安神"},
                        {"type": "formula", "content": "归脾汤"}
                    ],
                    "keywords": ["失眠", "健忘", "心悸", "面色萎黄", "舌淡", "脉弱"],
                    "tcm_theory": "心脾同源，脾虚不生血，心虚失神明"
                },
                {
                    "id": "insomnia_liver_qi_stagnation",
                    "title": "肝郁化火型失眠",
                    "steps": [
                        {"type": "symptom", "content": "失眠"},
                        {"type": "condition", "content": "易怒，胸胁胀满", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "肝郁化火证"},
                        {"type": "treatment", "content": "疏肝解郁，清热安神"},
                        {"type": "formula", "content": "逍遥散合甘麦大枣汤"}
                    ],
                    "keywords": ["失眠", "易怒", "胸胁胀满", "口苦", "脉弦"],
                    "tcm_theory": "肝主疏泄，肝郁化火，扰动心神"
                }
            ]
        elif disease_name == "胃痛":
            paths = [
                {
                    "id": "stomach_pain_spleen_cold",
                    "title": "脾胃虚寒型胃痛",
                    "steps": [
                        {"type": "symptom", "content": "胃痛"},
                        {"type": "condition", "content": "喜温喜按，遇冷加重", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "脾胃虚寒证"},
                        {"type": "treatment", "content": "温中健脾，和胃止痛"},
                        {"type": "formula", "content": "理中汤"}
                    ],
                    "keywords": ["胃痛", "隐隐", "喜温", "喜按", "舌淡", "苔白"],
                    "tcm_theory": "脾胃为后天之本，虚寒则痛"
                },
                {
                    "id": "stomach_pain_liver_qi",
                    "title": "肝气犯胃型胃痛",
                    "steps": [
                        {"type": "symptom", "content": "胃痛"},
                        {"type": "condition", "content": "胀痛，情绪波动时加重", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "肝气犯胃证"},
                        {"type": "treatment", "content": "疏肝理气，和胃止痛"},
                        {"type": "formula", "content": "柴胡疏肝散"}
                    ],
                    "keywords": ["胃痛", "胀痛", "情绪", "嗳气", "脉弦"],
                    "tcm_theory": "肝主疏泄，肝气不舒则横逆犯胃"
                }
            ]
        else:
            # 通用疾病路径模板 - 增强版
            paths = [
                {
                    "id": f"{disease_name}_heat_syndrome",
                    "title": f"{disease_name}实热证型",
                    "steps": [
                        {"type": "symptom", "content": disease_name},
                        {"type": "condition", "content": "舌红苔黄，脉数有力", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "实热证"},
                        {"type": "treatment", "content": "清热泻火"},
                        {"type": "formula", "content": "黄连解毒汤加减"}
                    ],
                    "keywords": [disease_name, "舌红", "苔黄", "脉数", "实热"],
                    "tcm_theory": "实则泻之，热者清之，以苦寒直折热邪"
                },
                {
                    "id": f"{disease_name}_deficiency_cold",
                    "title": f"{disease_name}虚寒证型",
                    "steps": [
                        {"type": "symptom", "content": disease_name},
                        {"type": "condition", "content": "舌淡苔白，脉沉细弱", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "虚寒证"},
                        {"type": "treatment", "content": "温阳益气"},
                        {"type": "formula", "content": "理中汤合四君子汤"}
                    ],
                    "keywords": [disease_name, "舌淡", "苔白", "脉弱", "虚寒"],
                    "tcm_theory": "虚则补之，寒者热之，以甘温补中焦阳气"
                },
                {
                    "id": f"{disease_name}_qi_stagnation",
                    "title": f"{disease_name}气滞证型",
                    "steps": [
                        {"type": "symptom", "content": disease_name},
                        {"type": "condition", "content": "胸闷不舒，情志不畅", "options": ["是", "否"]},
                        {"type": "diagnosis", "content": "气机郁滞证"},
                        {"type": "treatment", "content": "疏肝理气"},
                        {"type": "formula", "content": "逍遥散加减"}
                    ],
                    "keywords": [disease_name, "胸闷", "情志", "气滞", "脉弦"],
                    "tcm_theory": "气为血之帅，气行则血行，通则不痛"
                }
            ]
        
        return paths

    def _create_missing_logic_analysis_direct(self, current_tree: Dict[str, Any], disease_name: str) -> Dict[str, Any]:
        """直接创建遗漏逻辑分析，避免复杂的检测逻辑"""
        try:
            # 获取当前已有的证型和条件
            existing_diagnoses = set()
            existing_conditions = set()
            
            if "paths" in current_tree:
                for path in current_tree["paths"]:
                    for step in path.get("steps", []):
                        if step.get("type") == "diagnosis":
                            existing_diagnoses.add(step.get("content", ""))
                        elif step.get("type") == "condition":
                            existing_conditions.add(step.get("content", ""))
            
            # 定义常见证型和条件
            common_data = {
                "失眠": {
                    "syndromes": ["心火旺盛证", "心脾两虚证", "肝郁化火证", "心肾不交证", "痰热扰心证"],
                    "conditions": ["舌红苔黄", "舌淡苔白", "胸胁胀满", "五心烦热", "痰多"],
                    "formulas": ["黄连阿胶汤", "归脾汤", "逍遥散", "天王补心丹", "温胆汤"]
                },
                "胃痛": {
                    "syndromes": ["脾胃虚寒证", "肝气犯胃证", "胃阴不足证", "湿热中阻证", "瘀血阻络证"],
                    "conditions": ["喜温喜按", "胀痛拒按", "口干咽燥", "口苦黏腻", "刺痛固定"],
                    "formulas": ["理中汤", "柴胡疏肝散", "麦门冬汤", "黄芩汤", "失笑散"]
                }
            }
            
            disease_data = common_data.get(disease_name, {
                "syndromes": [f"{disease_name}虚证", f"{disease_name}实证", f"{disease_name}虚实夹杂证"],
                "conditions": ["舌红苔黄", "舌淡苔白", "脉象变化"],
                "formulas": ["补益方剂", "清热方剂", "调和方剂"]
            })
            
            # 找出遗漏的证型
            missing_syndromes = [s for s in disease_data["syndromes"] if s not in existing_diagnoses]
            missing_conditions = [c for c in disease_data["conditions"] if c not in existing_conditions]
            
            missing_analyses = []
            
            if missing_syndromes:
                missing_analyses.append({
                    "category": "证型分析",
                    "items": [
                        {
                            "type": "missing_syndrome",
                            "content": syndrome,
                            "description": f"{disease_name}的{syndrome}是重要证型",
                            "importance": "high",
                            "suggested_addition": {
                                "step_type": "diagnosis",
                                "step_content": syndrome
                            }
                        } for syndrome in missing_syndromes[:3]
                    ]
                })
            
            if missing_conditions:
                missing_analyses.append({
                    "category": "判断条件",
                    "items": [
                        {
                            "type": "missing_condition",
                            "content": condition,
                            "description": f"建议增加{condition}的判断",
                            "importance": "medium",
                            "suggested_addition": {
                                "step_type": "condition",
                                "step_content": condition
                            }
                        } for condition in missing_conditions[:3]
                    ]
                })
            
            quick_additions = [
                {
                    "title": "补充鉴别诊断路径",
                    "path_data": {
                        "steps": [
                            {"type": "condition", "content": "是否符合典型特征"},
                            {"type": "diagnosis", "content": f"确诊{disease_name}"}
                        ]
                    }
                }
            ]
            
            return {
                "missing_analyses": missing_analyses,
                "quick_additions": quick_additions
            }
            
        except Exception as e:
            print(f"直接分析失败: {e}")
            # 返回最简单的默认结果
            return {
                "missing_analyses": [
                    {
                        "category": "基础分析",
                        "items": [
                            {
                                "type": "general_suggestion",
                                "content": "建议完善决策树",
                                "description": "当前决策树可以进一步细化",
                                "importance": "medium"
                            }
                        ]
                    }
                ],
                "quick_additions": [
                    {
                        "title": "基础补充",
                        "path_data": {"steps": [{"type": "condition", "content": "补充判断条件"}]}
                    }
                ]
            }

    def _get_tcm_theory_for_path(self, path: Dict[str, Any], disease_name: str) -> str:
        """为路径获取中医理论依据"""
        try:
            # 根据诊断和治疗方法生成理论依据
            diagnosis_step = next((step for step in path.get("steps", []) if step.get("type") == "diagnosis"), None)
            treatment_step = next((step for step in path.get("steps", []) if step.get("type") == "treatment"), None)
            
            if diagnosis_step and treatment_step:
                diagnosis = diagnosis_step.get("content", "")
                treatment = treatment_step.get("content", "")
                
                # 基于关键词匹配理论
                if "虚" in diagnosis:
                    return f"{disease_name}属虚证范畴，治疗以{treatment}为主，体现'虚则补之'的治疗原则"
                elif "实" in diagnosis or "热" in diagnosis:
                    return f"{disease_name}属实热证范畴，治疗以{treatment}为主，体现'实则泻之，热者清之'的治疗原则"
                elif "气滞" in diagnosis or "肝郁" in diagnosis:
                    return f"{disease_name}多因气机不利所致，治疗以{treatment}为主，体现'通则不痛'的治疗理念"
                else:
                    return f"{disease_name}的治疗遵循{treatment}原则，符合中医辨证论治精神"
            
            return f"基于中医{disease_name}的传统理论指导治疗"
            
        except Exception as e:
            print(f"获取TCM理论失败: {e}")
            return "基于中医传统理论"

    def _calculate_theory_score(self, tree_data: Dict[str, Any], disease_name: str) -> int:
        """计算理论合理性评分"""
        try:
            score = 60  # 基础分
            
            # 检查是否有完整的辨证过程
            if "paths" in tree_data:
                for path in tree_data["paths"]:
                    steps = path.get("steps", [])
                    step_types = [step.get("type") for step in steps]
                    
                    # 完整的诊疗流程加分
                    if all(t in step_types for t in ["symptom", "condition", "diagnosis", "treatment", "formula"]):
                        score += 15
                    
                    # 有中医理论依据加分
                    if path.get("tcm_theory"):
                        score += 10
                    
                    # 关键词丰富加分
                    if len(path.get("keywords", [])) >= 4:
                        score += 5
            
            return min(score, 100)  # 最高100分
            
        except Exception as e:
            print(f"计算理论评分失败: {e}")
            return 70

    def _identify_theory_strengths(self, tree_data: Dict[str, Any], disease_name: str) -> List[str]:
        """识别理论优势"""
        strengths = []
        
        try:
            if "paths" in tree_data and tree_data["paths"]:
                path_count = len(tree_data["paths"])
                if path_count >= 3:
                    strengths.append("覆盖了该疾病的主要证型")
                
                # 检查是否有完整的诊疗流程
                for path in tree_data["paths"]:
                    steps = path.get("steps", [])
                    if len(steps) >= 5:
                        strengths.append("诊疗流程完整，层次清晰")
                        break
                
                # 检查是否有理论依据
                if any(path.get("tcm_theory") for path in tree_data["paths"]):
                    strengths.append("具备中医理论依据")
            
            # 默认优势
            if not strengths:
                strengths = ["基本框架合理", "符合中医思维"]
                
        except Exception as e:
            print(f"识别理论优势失败: {e}")
            strengths = ["基本结构清晰"]
        
        return strengths

    def _identify_theory_weaknesses(self, tree_data: Dict[str, Any], disease_name: str) -> List[str]:
        """识别理论不足"""
        weaknesses = []
        
        try:
            if "paths" in tree_data and tree_data["paths"]:
                # 检查路径数量
                if len(tree_data["paths"]) < 3:
                    weaknesses.append("可增加更多证型路径")
                
                # 检查判断条件的具体性
                vague_conditions = 0
                for path in tree_data["paths"]:
                    for step in path.get("steps", []):
                        if step.get("type") == "condition":
                            content = step.get("content", "")
                            if len(content) < 6 or "症状" in content:
                                vague_conditions += 1
                
                if vague_conditions > 0:
                    weaknesses.append("部分判断条件可以更加具体化")
                
                # 检查是否缺少鉴别诊断
                has_differential = any(
                    "鉴别" in step.get("content", "") 
                    for path in tree_data["paths"] 
                    for step in path.get("steps", [])
                )
                if not has_differential:
                    weaknesses.append("建议补充鉴别诊断要点")
            
            # 默认不足
            if not weaknesses:
                weaknesses = ["可进一步细化诊疗细节"]
                
        except Exception as e:
            print(f"识别理论不足失败: {e}")
            weaknesses = ["需要进一步完善"]
        
        return weaknesses

    def _get_improvement_suggestions(self, tree_data: Dict[str, Any], disease_name: str) -> List[Dict[str, str]]:
        """获取改进建议"""
        suggestions = [
            {
                "type": "theory_enhancement",
                "description": "建议增加更详细的四诊信息收集",
                "priority": "high"
            },
            {
                "type": "differential_diagnosis",
                "description": "补充与相关疾病的鉴别要点",
                "priority": "medium"
            },
            {
                "type": "individualization",
                "description": "增加个体化治疗的考虑因素",
                "priority": "medium"
            }
        ]
        
        return suggestions

    def _get_knowledge_supplements(self, disease_name: str) -> List[Dict[str, str]]:
        """获取知识补充建议"""
        supplements = [
            {
                "topic": "病机理论",
                "content": f"{disease_name}的基本病机和病理生理",
                "source": "中医内科学"
            },
            {
                "topic": "方剂配伍",
                "content": f"治疗{disease_name}的经典方剂及其配伍原理",
                "source": "方剂学"
            },
            {
                "topic": "临床经验",
                "content": f"名医治疗{disease_name}的特色经验",
                "source": "临床实践"
            }
        ]
        
        return supplements

    def _detect_missing_syndromes(self, current_tree: Dict[str, Any], disease_name: str) -> List[Dict[str, Any]]:
        """检测可能遗漏的证型"""
        missing_analyses = []
        
        try:
            # 获取当前已有的证型
            existing_syndromes = set()
            if "paths" in current_tree:
                for path in current_tree["paths"]:
                    for step in path.get("steps", []):
                        if step.get("type") == "diagnosis":
                            existing_syndromes.add(step.get("content", ""))
            
            # 根据疾病检查常见遗漏证型
            common_syndromes = self._get_common_syndromes_for_disease(disease_name)
            missing_syndromes = [s for s in common_syndromes if s not in existing_syndromes]
            
            if missing_syndromes:
                missing_analyses.append({
                    "category": "证型分析",
                    "items": [
                        {
                            "type": "missing_syndrome",
                            "content": syndrome,
                            "description": f"{disease_name}的{syndrome}是常见证型，建议补充",
                            "importance": "high",
                            "suggested_addition": {
                                "step_type": "diagnosis",
                                "step_content": syndrome
                            }
                        } for syndrome in missing_syndromes[:3]  # 最多建议3个
                    ]
                })
            
        except Exception as e:
            print(f"检测遗漏证型失败: {e}")
        
        return missing_analyses

    def _get_common_syndromes_for_disease(self, disease_name: str) -> List[str]:
        """获取疾病的常见证型"""
        syndrome_map = {
            "失眠": ["心火旺盛证", "心脾两虚证", "肝郁化火证", "心肾不交证", "痰热扰心证"],
            "胃痛": ["脾胃虚寒证", "肝气犯胃证", "胃阴不足证", "湿热中阻证", "瘀血阻络证"],
            "头痛": ["风寒头痛", "风热头痛", "肝阳上亢", "痰浊头痛", "血瘀头痛"],
            "咳嗽": ["风寒咳嗽", "风热咳嗽", "痰湿咳嗽", "痰热咳嗽", "肺阴虚咳嗽"]
        }
        
        return syndrome_map.get(disease_name, [f"{disease_name}常见证型"])

    def _suggest_quick_additions(self, current_tree: Dict[str, Any], disease_name: str) -> List[Dict[str, Any]]:
        """建议快速添加的内容"""
        additions = []
        
        # 检查是否缺少鉴别诊断
        has_differential = False
        if "paths" in current_tree:
            for path in current_tree["paths"]:
                for step in path.get("steps", []):
                    if "鉴别" in step.get("content", ""):
                        has_differential = True
                        break
        
        if not has_differential:
            additions.append({
                "title": "添加鉴别诊断路径",
                "path_data": {
                    "steps": [
                        {"type": "condition", "content": "是否伴有典型特征"},
                        {"type": "diagnosis", "content": f"排除相关疾病，确诊{disease_name}"}
                    ]
                }
            })
        
        # 检查是否缺少预后评估
        has_prognosis = False
        if "paths" in current_tree:
            for path in current_tree["paths"]:
                for step in path.get("steps", []):
                    if "预后" in step.get("content", "") or "随访" in step.get("content", ""):
                        has_prognosis = True
                        break
        
        if not has_prognosis:
            additions.append({
                "title": "添加预后评估",
                "path_data": {
                    "steps": [
                        {"type": "condition", "content": "治疗效果评估"},
                        {"type": "treatment", "content": "调整治疗方案"}
                    ]
                }
            })
        
        return additions


# 测试和演示功能
def test_famous_doctor_system():
    """测试名医学习系统"""
    system = FamousDoctorLearningSystem()
    
    print("=== 名医处方学习系统测试 ===")
    
    # 1. 测试添加临床案例
    print("\n--- 测试添加临床案例 ---")
    
    # 创建示例处方
    sample_prescription = Prescription(
        herbs=[
            {"name": "麻黄", "dosage": "9", "unit": "g"},
            {"name": "桂枝", "dosage": "6", "unit": "g"},
            {"name": "杏仁", "dosage": "6", "unit": "g"},
            {"name": "甘草", "dosage": "3", "unit": "g"}
        ],
        preparation_method="水煎服",
        usage_instructions="每日1剂，分2次温服",
        syndrome_pattern="风寒表实证",
        disease_name="感冒"
    )
    
    # 转换为正确的Prescription对象格式
    from prescription_checker import Herb
    sample_prescription = Prescription(
        herbs=[
            Herb("麻黄", "9", "g"),
            Herb("桂枝", "6", "g"), 
            Herb("杏仁", "6", "g"),
            Herb("甘草", "3", "g")
        ],
        preparation_method="水煎服",
        usage_instructions="每日1剂，分2次温服",
        syndrome_pattern="风寒表实证",
        disease_name="感冒"
    )
    
    sample_case = ClinicalCase(
        case_id="case_001",
        doctor_name="张仲景",
        patient_info={"age": 35, "gender": "男", "constitution": "平和质"},
        chief_complaint="发热恶寒1天",
        present_illness="患者昨日受凉后出现发热恶寒，头痛身痛，无汗，微喘",
        tcm_diagnosis="感冒",
        syndrome_differentiation="风寒表实证",
        prescription=sample_prescription,
        outcome="服药2剂后症状明显缓解，3剂后痊愈",
        notes="典型的麻黄汤证"
    )
    
    success = system.add_clinical_case(sample_case)
    print(f"添加案例: {'成功' if success else '失败'}")
    
    # 2. 测试学习医生处方规律
    print("\n--- 测试学习处方规律 ---")
    patterns = system.learn_doctor_prescription_patterns("张仲景")
    print(f"张仲景的处方模式分析:")
    print(f"  总模式数: {patterns['total_patterns']}")
    print(f"  常见疾病: {list(patterns['common_diseases'].keys())}")
    if patterns['frequent_herb_combinations']:
        print(f"  常用药物组合: {patterns['frequent_herb_combinations'][0]['herbs']}")
    
    # 3. 测试基于医生风格的处方推荐
    print("\n--- 测试处方推荐 ---")
    recommendation = system.recommend_prescription_by_doctor_style("感冒", "风寒表实证", "张仲景")
    print(f"张仲景风格的感冒风寒表实证处方推荐:")
    print(f"  置信度: {recommendation['confidence']:.2f}")
    if recommendation['exact_matches']:
        herbs = recommendation['exact_matches'][0]['herbs']
        herb_list = [f"{h['name']} {h['dosage']}" for h in herbs]
        print(f"  推荐处方: {herb_list}")
    
    # 4. 测试获取医生档案
    print("\n--- 测试医生档案 ---")
    profile = system.get_doctor_profile("张仲景")
    if profile:
        print(f"医生: {profile['name']}")
        print(f"学派: {profile['school']}")
        print(f"专长: {profile.get('specialty', [])}")
        print(f"代表方剂: {profile.get('famous_formulas', [])}")
        print(f"治疗理念: {profile.get('treatment_philosophy', '')}")


if __name__ == "__main__":
    test_famous_doctor_system()