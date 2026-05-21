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

# AI配置导入
try:
    import dashscope
    import asyncio
    from config.settings import AI_CONFIG
    DASHSCOPE_AVAILABLE = True
except ImportError:
    dashscope = None
    AI_CONFIG = {}
    DASHSCOPE_AVAILABLE = False

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
        
        # 配置Dashscope AI
        if DASHSCOPE_AVAILABLE:
            try:
                dashscope.api_key = AI_CONFIG.get('dashscope_api_key', '')
                self.ai_model = AI_CONFIG.get('decision_tree_model', 'qwen3.5-omni-plus-2026-03-15')
                self.ai_enabled = bool(dashscope.api_key)
                if self.ai_enabled:
                    print(f"✅ AI功能已启用，模型: {self.ai_model}")
                else:
                    print("⚠️ 未配置Dashscope API密钥，使用模板模式")
            except Exception as e:
                print(f"❌ AI配置失败: {e}，使用模板模式")
                self.ai_enabled = False
        else:
            self.ai_enabled = False
            
        # 学习机制配置
        self.learning_enabled = True
        self.user_feedback_weight = 0.3
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        self._init_database()
        self._load_famous_doctors()
        self._setup_learning_database()
    
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
    
    # 旧的generate_decision_paths方法已删除，使用新的AI支持版本
    
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

    def _get_disease_specific_content(self, disease_name: str):
        """
        获取疾病特定的诊疗内容

        Args:
            disease_name: 疾病名称

        Returns:
            包含症状问题、辨证要点、治疗原则的字典
        """
        # 常见疾病知识库
        disease_knowledge = {
            "感冒": {
                "cold": {
                    "symptoms": [f"{disease_name}时是否怕冷明显？", f"{disease_name}时是否流清鼻涕？", "是否打喷嚏？", "是否咽喉不痛？"],
                    "diagnosis": [f"{disease_name}风寒程度", "表证轻重", "有无兼证"],
                    "treatment": "辛温解表，发散风寒",
                    "prescription_hint": f"针对{disease_name}风寒证，可考虑辛温解表之剂"
                },
                "heat": {
                    "symptoms": [f"{disease_name}时是否发热明显？", f"{disease_name}时是否咽喉肿痛？", "是否口渴喜饮？", "鼻涕是否黄稠？"],
                    "diagnosis": [f"{disease_name}风热程度", "热象轻重", "有无化燥"],
                    "treatment": "辛凉解表，清热解毒",
                    "prescription_hint": f"针对{disease_name}风热证，可考虑辛凉清热之品"
                }
            },
            "头痛": {
                "cold": {
                    "symptoms": [f"{disease_name}时是否遇寒加重？", f"{disease_name}时是否喜温？", "疼痛是否紧束感？", "是否伴有怕冷？"],
                    "diagnosis": [f"{disease_name}病位（前额/后头/偏侧）", "寒邪程度", "有无血瘀"],
                    "treatment": "温经散寒，通络止痛",
                    "prescription_hint": f"针对{disease_name}寒证，可考虑温通止痛之法"
                },
                "heat": {
                    "symptoms": [f"{disease_name}时是否跳痛灼痛？", f"{disease_name}是否口苦？", "是否目赤？", "是否烦躁易怒？"],
                    "diagnosis": [f"{disease_name}病位及性质", "肝阳亢盛程度", "有无痰火"],
                    "treatment": "清热平肝，息风止痛",
                    "prescription_hint": f"针对{disease_name}热证，可考虑清肝泻火之品"
                }
            },
            "咳嗽": {
                "cold": {
                    "symptoms": [f"{disease_name}时痰是否清稀？", f"{disease_name}时是否怕冷？", "是否咽痒？", "是否鼻塞流涕？"],
                    "diagnosis": [f"{disease_name}风寒程度", "肺气闭束情况", "痰液性质"],
                    "treatment": "疏风散寒，宣肺止咳",
                    "prescription_hint": f"针对{disease_name}风寒证，宜温化寒痰"
                },
                "heat": {
                    "symptoms": [f"{disease_name}时痰是否黄稠？", f"{disease_name}时咽喉是否疼痛？", "是否发热？", "是否口干？"],
                    "diagnosis": [f"{disease_name}热邪程度", "痰热壅肺情况", "津液耗损"],
                    "treatment": "清热宣肺，化痰止咳",
                    "prescription_hint": f"针对{disease_name}痰热证，宜清肺化痰"
                }
            },
            "腹泻": {
                "cold": {
                    "symptoms": [f"{disease_name}时是否腹痛喜按？", f"{disease_name}时是否得温痛减？", "是否肠鸣漉漉？", "大便是否清稀？"],
                    "diagnosis": [f"{disease_name}寒湿程度", "脾阳虚损情况", "病程久暂"],
                    "treatment": "温中散寒，健脾止泻",
                    "prescription_hint": f"针对{disease_name}寒证，宜温脾散寒"
                },
                "heat": {
                    "symptoms": [f"{disease_name}时大便是否臭秽？", f"{disease_name}时是否肛门灼热？", "是否口渴？", "是否腹痛拒按？"],
                    "diagnosis": [f"{disease_name}湿热程度", "肠道热象", "正气强弱"],
                    "treatment": "清热利湿，调理肠腑",
                    "prescription_hint": f"针对{disease_name}湿热证，宜清肠化湿"
                }
            },
            "胃痛": {
                "cold": {
                    "symptoms": [f"{disease_name}时是否得温痛减？", f"{disease_name}时是否喜热饮？", "是否畏寒肢冷？", "呕吐物是否清稀？"],
                    "diagnosis": [f"{disease_name}虚实寒热", "中焦虚寒程度", "气机阻滞"],
                    "treatment": "温中散寒，和胃止痛",
                    "prescription_hint": f"针对{disease_name}寒证，宜温胃散寒"
                },
                "heat": {
                    "symptoms": [f"{disease_name}时是否灼痛？", f"{disease_name}时是否喜冷饮？", "是否口苦？", "是否烦躁？"],
                    "diagnosis": [f"{disease_name}郁热程度", "胃阴耗损情况", "肝胃不和"],
                    "treatment": "清热和胃，降逆止痛",
                    "prescription_hint": f"针对{disease_name}热证，宜清胃泻火"
                }
            }
        }

        # 如果是已知疾病，返回特定内容；否则返回通用内容
        if disease_name in disease_knowledge:
            return disease_knowledge[disease_name]
        else:
            # 通用内容（但包含疾病名称）
            return {
                "cold": {
                    "symptoms": [f"{disease_name}时是否怕冷？", f"{disease_name}时是否喜温？", f"{disease_name}症状遇寒是否加重？", "是否肢体不温？"],
                    "diagnosis": [f"{disease_name}的寒证程度", "病位深浅", "虚实夹杂"],
                    "treatment": "温阳散寒",
                    "prescription_hint": f"针对{disease_name}的寒证特点选方用药"
                },
                "heat": {
                    "symptoms": [f"{disease_name}时是否发热？", f"{disease_name}时是否口渴？", f"{disease_name}症状遇热是否加重？", "是否尿黄便干？"],
                    "diagnosis": [f"{disease_name}的热证性质", "病位层次", "实热虚热"],
                    "treatment": "清热泻火",
                    "prescription_hint": f"针对{disease_name}的热证特点选方用药"
                }
            }

    def _generate_standard_template(self, disease_name: str, complexity_level: str = "standard") -> List[Dict[str, Any]]:
        """
        生成标准决策树模板（根据疾病提供针对性内容）

        Args:
            disease_name: 疾病名称
            complexity_level: 复杂度级别 (simple, standard, complex)

        Returns:
            标准决策路径列表
        """
        print(f"📋 生成标准模板: {disease_name} (复杂度: {complexity_level})")

        # 获取疾病特定内容
        disease_content = self._get_disease_specific_content(disease_name)

        # 基础模板结构
        if complexity_level == "simple":
            # 简单模板：单一路径（使用寒证作为示例）
            cold_content = disease_content.get("cold", {})
            template_paths = [
                {
                    "id": f"{disease_name}_standard",
                    "title": f"{disease_name}标准诊疗流程",
                    "path_name": f"{disease_name}标准诊疗流程",
                    "description": f"针对{disease_name}的标准诊疗流程（以寒证为例）",
                    "steps": [
                        {
                            "step_number": 1,
                            "title": f"{disease_name}症状收集",
                            "content": f"详细询问{disease_name}的症状特点",
                            "questions": cold_content.get("symptoms", [f"{disease_name}的主要症状？", "症状持续多久？", "伴随症状？"]),
                            "node_type": "inquiry"
                        },
                        {
                            "step_number": 2,
                            "title": f"{disease_name}辨证分析",
                            "content": f"综合四诊信息对{disease_name}进行辨证",
                            "key_points": cold_content.get("diagnosis", [f"{disease_name}证型", "病位病性", "病因病机"]),
                            "node_type": "diagnosis"
                        },
                        {
                            "step_number": 3,
                            "title": f"{disease_name}治疗方案",
                            "content": f"制定{disease_name}的个体化治疗方案",
                            "treatment_principle": cold_content.get("treatment", "辨证施治"),
                            "prescription": cold_content.get("prescription_hint", "根据辨证选方用药"),
                            "node_type": "treatment"
                        }
                    ]
                }
            ]
        elif complexity_level == "complex":
            # 复杂模板：多路径分支
            template_paths = [
                {
                    "id": f"{disease_name}_deficiency",
                    "title": f"{disease_name}虚证诊疗路径",
                    "path_name": f"{disease_name}虚证诊疗路径",
                    "description": "虚证类型的诊疗流程（请根据实际填写）",
                    "steps": [
                        {
                            "step_number": 1,
                            "title": "虚证症状识别",
                            "content": "识别虚证特征性症状（请根据实际填写）",
                            "questions": ["是否乏力疲劳？", "是否气短懒言？", "舌质是否淡？"],
                            "node_type": "inquiry"
                        },
                        {
                            "step_number": 2,
                            "title": "虚证辨证分型",
                            "content": "区分气虚、血虚、阴虚、阳虚（请根据实际填写）",
                            "key_points": ["虚证类型", "虚损程度", "兼夹证候"],
                            "node_type": "diagnosis"
                        },
                        {
                            "step_number": 3,
                            "title": "补虚治疗",
                            "content": "根据虚证类型选择补法（请根据实际填写）",
                            "treatment_principle": "虚则补之",
                            "node_type": "treatment"
                        }
                    ]
                },
                {
                    "id": f"{disease_name}_excess",
                    "title": f"{disease_name}实证诊疗路径",
                    "path_name": f"{disease_name}实证诊疗路径",
                    "description": "实证类型的诊疗流程（请根据实际填写）",
                    "steps": [
                        {
                            "step_number": 1,
                            "title": "实证症状识别",
                            "content": "识别实证特征性症状（请根据实际填写）",
                            "questions": ["是否胀痛拒按？", "是否便秘？", "舌苔是否厚腻？"],
                            "node_type": "inquiry"
                        },
                        {
                            "step_number": 2,
                            "title": "实证辨证分型",
                            "content": "区分气滞、血瘀、痰湿、食积等（请根据实际填写）",
                            "key_points": ["实证类型", "病邪性质", "病位深浅"],
                            "node_type": "diagnosis"
                        },
                        {
                            "step_number": 3,
                            "title": "祛邪治疗",
                            "content": "根据实证类型选择泻法（请根据实际填写）",
                            "treatment_principle": "实则泻之",
                            "node_type": "treatment"
                        }
                    ]
                }
            ]
        else:
            # 标准模板：双路径（寒热辨证） - 使用疾病特定内容
            cold_content = disease_content.get("cold", {})
            heat_content = disease_content.get("heat", {})

            template_paths = [
                {
                    "id": f"{disease_name}_cold",
                    "title": f"{disease_name}寒证诊疗路径",
                    "path_name": f"{disease_name}寒证诊疗路径",
                    "description": f"针对{disease_name}寒证类型的诊疗流程",
                    "steps": [
                        {
                            "step_number": 1,
                            "title": f"{disease_name}寒证症状询问",
                            "content": f"询问{disease_name}寒证的特征性症状",
                            "questions": cold_content.get("symptoms", [f"{disease_name}时是否怕冷？", "是否喜温？"]),
                            "node_type": "inquiry"
                        },
                        {
                            "step_number": 2,
                            "title": f"{disease_name}寒证辨证",
                            "content": f"对{disease_name}寒证进行辨证分析",
                            "key_points": cold_content.get("diagnosis", [f"{disease_name}寒证程度", "病位深浅"]),
                            "node_type": "diagnosis"
                        },
                        {
                            "step_number": 3,
                            "title": f"{disease_name}寒证治疗",
                            "content": f"制定{disease_name}寒证的治疗方案",
                            "treatment_principle": cold_content.get("treatment", "温阳散寒"),
                            "prescription": cold_content.get("prescription_hint", f"针对{disease_name}寒证选方用药"),
                            "node_type": "treatment"
                        }
                    ]
                },
                {
                    "id": f"{disease_name}_heat",
                    "title": f"{disease_name}热证诊疗路径",
                    "path_name": f"{disease_name}热证诊疗路径",
                    "description": f"针对{disease_name}热证类型的诊疗流程",
                    "steps": [
                        {
                            "step_number": 1,
                            "title": f"{disease_name}热证症状询问",
                            "content": f"询问{disease_name}热证的特征性症状",
                            "questions": heat_content.get("symptoms", [f"{disease_name}时是否发热？", "是否口渴？"]),
                            "node_type": "inquiry"
                        },
                        {
                            "step_number": 2,
                            "title": f"{disease_name}热证辨证",
                            "content": f"对{disease_name}热证进行辨证分析",
                            "key_points": heat_content.get("diagnosis", [f"{disease_name}热证性质", "病位层次"]),
                            "node_type": "diagnosis"
                        },
                        {
                            "step_number": 3,
                            "title": f"{disease_name}热证治疗",
                            "content": f"制定{disease_name}热证的治疗方案",
                            "treatment_principle": heat_content.get("treatment", "清热泻火"),
                            "prescription": heat_content.get("prescription_hint", f"针对{disease_name}热证选方用药"),
                            "node_type": "treatment"
                        }
                    ]
                }
            ]

        return template_paths

    async def generate_decision_paths(self, disease_name: str, thinking_process: str = "", 
                                    use_ai: bool = None, include_tcm_analysis: bool = True, 
                                    complexity_level: str = "standard", enable_smart_branching: bool = False) -> Dict[str, Any]:
        """
        智能生成决策路径（混合模式：AI + 模板）
        
        Args:
            disease_name: 疾病名称
            thinking_process: 用户输入的诊疗思路
            use_ai: 是否使用AI，默认依据系统配置判断
            include_tcm_analysis: 是否包含中医理论分析
            complexity_level: 复杂度级别
            
        Returns:
            决策路径数据（包含数据来源标识）
        """
        # 自动判断使用AI还是模板
        if use_ai is None:
            use_ai = self.ai_enabled and bool(thinking_process.strip())
        
        # 🔍 添加详细调试信息
        print(f"🔍 AI决策判断调试:")
        print(f"  - use_ai参数: {use_ai}")  
        print(f"  - self.ai_enabled: {self.ai_enabled}")
        print(f"  - thinking_process长度: {len(thinking_process.strip()) if thinking_process else 0}")
        print(f"  - 最终使用AI: {use_ai and self.ai_enabled and bool(thinking_process.strip())}")
        
        result = {
            "source": "ai" if use_ai else "template",
            "ai_generated": use_ai,
            "user_thinking_used": bool(thinking_process.strip()),
            "paths": [],
            "suggested_layout": {
                "auto_arrange": True,
                "spacing": {"horizontal": 300, "vertical": 150}
            }
        }
        
        try:
            # 详细的AI条件调试
            print(f"🔍 AI生成条件检查:")
            print(f"  - use_ai: {use_ai} (类型: {type(use_ai)})")
            print(f"  - self.ai_enabled: {self.ai_enabled} (类型: {type(self.ai_enabled)})")
            print(f"  - thinking_process.strip(): '{thinking_process.strip()}' (长度: {len(thinking_process.strip())})")
            print(f"  - bool(thinking_process.strip()): {bool(thinking_process.strip())}")
            print(f"  - 综合条件: {use_ai and self.ai_enabled and thinking_process.strip()}")
            
            if use_ai and self.ai_enabled and thinking_process.strip():
                # 使用真实AI生成
                print(f"🤖 使用AI智能生成: {disease_name}")
                ai_paths = await self._generate_ai_decision_paths(disease_name, thinking_process, complexity_level)
                result["paths"] = ai_paths
                result["generation_time"] = "10-15秒"
                
                # 记录AI生成的学习数据
                await self._record_ai_learning(disease_name, thinking_process, ai_paths)
                
            else:
                # 📋 使用标准模板
                print(f"📋 使用标准模板生成: {disease_name}")
                template_paths = self._generate_standard_template(disease_name, complexity_level)
                result["paths"] = template_paths
                result["generation_time"] = "即时"
                result["source"] = "template"
            
            # 添加中医理论分析
            if include_tcm_analysis:
                for path in result["paths"]:
                    if "tcm_theory" not in path:
                        path["tcm_theory"] = self._get_tcm_theory_for_path(path, disease_name)
            
            # 🎯 智能年龄分支生成
            if enable_smart_branching and result["paths"]:
                print(f"🎯 启用智能年龄分支生成: {disease_name}")
                try:
                    result["paths"] = self._add_age_branches_to_paths(result["paths"], disease_name)
                    result["smart_branching_enabled"] = True
                except Exception as e:
                    print(f"⚠️ 智能分支生成失败，跳过: {e}")
                    result["smart_branching_enabled"] = False
            else:
                result["smart_branching_enabled"] = False
            
            return result
            
        except Exception as e:
            print(f"❌ 决策路径生成失败: {e}")
            print(f"📋 降级使用标准模板作为备用方案")
            # 使用标准模板作为备用
            try:
                template_paths = self._generate_standard_template(disease_name, complexity_level)
                result["paths"] = template_paths
                result["generation_time"] = "即时"
                result["source"] = "template_fallback"
                result["error_message"] = str(e)
                return result
            except Exception as fallback_error:
                print(f"❌ 模板备用方案也失败: {fallback_error}")
                raise e

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
    
    def _setup_learning_database(self):
        """设置学习数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # AI决策树学习记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_decision_tree_learning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    disease_name TEXT NOT NULL,
                    user_thinking TEXT,
                    ai_response TEXT,
                    user_feedback INTEGER,  -- 1-5星的评分
                    improvement_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 理论分析学习记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_theory_analysis_learning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    disease_name TEXT NOT NULL,
                    tree_data TEXT,
                    ai_analysis TEXT,
                    expert_corrections TEXT,
                    accuracy_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 用户偏好记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    ai_mode_preferred BOOLEAN DEFAULT 1,
                    complexity_level TEXT DEFAULT 'standard',
                    favorite_schools TEXT,
                    custom_templates TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            print("✅ 学习数据库设置完成")
            
        except Exception as e:
            print(f"❌ 学习数据库设置失败: {e}")

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

    async def _generate_ai_decision_paths(self, disease_name: str, thinking_process: str, complexity_level: str) -> List[Dict[str, Any]]:
        """
        使用Dashscope AI真实生成决策路径
        """
        if not DASHSCOPE_AVAILABLE or not self.ai_enabled:
            raise Exception("AI服务不可用")
        
        # 构建简化的AI提示词 - 专注于核心信息
        prompt = f"""
从以下中医诊疗思路中提取关键信息，按照：病种→病情描述→具体处方的流程。

疾病：{disease_name}
医生思路：{thinking_process}

要求：
1. 只提取医生明确提到的信息，不添加任何额外内容
2. 处方必须包含具体药材和克数
3. 考虑成人和儿童用药差异

返回JSON（不要任何其他文字）：
{{
    "paths": [
        {{
            "id": "path1",
            "title": "{disease_name}诊疗路径",
            "steps": [
                {{"type": "disease", "content": "{disease_name}"}},
                {{"type": "symptom", "content": "医生描述的病情症状"}},
                {{"type": "prescription", "content": "方剂名称：药材1 Xg，药材2 Yg，药材3 Zg"}}
            ]
        }}
    ]
}}"""
        
        # 智能分析诊疗流程完整性并增强提示词
        try:
            completeness_analysis = await self._analyze_diagnostic_completeness(disease_name, thinking_process)
            if completeness_analysis.get("missing_items"):
                prompt = self._enhance_prompt_with_missing_items(prompt, completeness_analysis, disease_name)
                print(f"🔍 诊疗流程分析：发现{len(completeness_analysis['missing_items'])}项缺失，已智能补充")
        except Exception as e:
            print(f"⚠️ 诊疗流程分析失败: {e}")
        
        try:
            response = await asyncio.to_thread(
                dashscope.MultiModalConversation.call,
                model=self.ai_model,
                messages=[{"role": "user", "content": [{"text": prompt}]}]
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content[0]["text"]
                print(f"🔍 AI原始响应内容: {content}")
                
                # 解析JSON响应 - 增强容错版
                try:
                    # 首先尝试直接解析
                    ai_result = json.loads(content)
                    paths = ai_result.get("paths", [])
                    print(f"🔍 JSON解析成功，得到{len(paths)}条路径")
                except json.JSONDecodeError as e:
                    print(f"❌ 直接JSON解析失败: {e}")
                    print(f"🔍 错误位置: 行{e.lineno}, 列{e.colno}, 字符{e.pos}")
                    print(f"🔍 错误附近内容: ...{content[max(0, e.pos-20):e.pos+20]}...")

                    # 如果失败，尝试提取JSON部分 - 支持markdown代码块
                    import re

                    # 🔧 第一步：清理常见的JSON格式错误
                    cleaned_content = content
                    # 移除注释
                    cleaned_content = re.sub(r'//.*?\n', '\n', cleaned_content)
                    cleaned_content = re.sub(r'/\*.*?\*/', '', cleaned_content, flags=re.DOTALL)
                    # 修复尾部逗号
                    cleaned_content = re.sub(r',(\s*[}\]])', r'\1', cleaned_content)
                    # 修复缺失的逗号（在}或]后面应该有逗号但没有的情况）
                    cleaned_content = re.sub(r'([}\]])(\s*)([{"\[])', r'\1,\2\3', cleaned_content)

                    # 尝试用清理后的内容解析
                    try:
                        ai_result = json.loads(cleaned_content)
                        paths = ai_result.get("paths", [])
                        print(f"🔍 清理后JSON解析成功，得到{len(paths)}条路径")
                    except json.JSONDecodeError:
                        # 更精准的JSON提取模式
                        json_patterns = [
                            r'```json\s*(\{[\s\S]*?\})\s*```',  # markdown代码块
                            r'```\s*(\{[\s\S]*?\})\s*```',      # 无语言标识的代码块
                            r'(\{[\s\S]*?\})(?=\s*###|补充|建议|注意|$)',    # JSON后跟其他内容
                            r'(\{(?:[^{}]|\{[^}]*\})*\})'       # 平衡括号匹配
                        ]

                        json_content = None
                        for pattern in json_patterns:
                            json_match = re.search(pattern, cleaned_content)
                            if json_match:
                                # 安全地访问捕获组
                                try:
                                    json_content = json_match.group(1)
                                    print(f"🔍 使用模式提取到JSON内容")
                                    break
                                except IndexError:
                                    json_content = json_match.group(0)
                                    print(f"🔍 使用模式提取到JSON内容（fallback）")
                                    break

                        if json_content:
                            # 再次清理提取的JSON
                            json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
                            json_content = re.sub(r'([}\]])(\s*)([{"\[])', r'\1,\2\3', json_content)

                            try:
                                ai_result = json.loads(json_content)
                                paths = ai_result.get("paths", [])
                                print(f"🔍 从混合内容中提取JSON成功，得到{len(paths)}条路径")
                            except json.JSONDecodeError as e2:
                                print(f"⚠️ JSON提取也失败: {e2}")
                                print(f"提取的内容前500字符: {json_content[:500]}")
                                # 🔧 容错：不抛出异常，返回空路径
                                print(f"⚠️ 使用空路径作为备用方案")
                                paths = []
                                ai_result = {"paths": paths}
                        else:
                            print(f"⚠️ 无法找到JSON内容")
                            print(f"原始响应前500字符: {content[:500]}")
                            # 🔧 容错：不抛出异常，返回空路径
                            print(f"⚠️ 使用空路径作为备用方案")
                            paths = []
                            ai_result = {"paths": paths}
                
                # 验证和清理AI返回的数据
                cleaned_paths = []
                for path in paths:
                    # 修复AI返回的步骤类型
                    fixed_path = self._fix_ai_path_types(path, disease_name)
                    
                    # 清理验证性语言 - 加强版
                    cleaned_path = self._clean_verification_language(fixed_path)
                    
                    # 自动补充缺失的字段
                    if "keywords" not in cleaned_path:
                        cleaned_path["keywords"] = [disease_name]
                    
                    if self._validate_ai_path(cleaned_path, disease_name):
                        cleaned_paths.append(cleaned_path)
                
                if cleaned_paths:
                    print(f"✅ AI成功生成 {len(cleaned_paths)} 条决策路径")
                    return cleaned_paths
                else:
                    # 🔧 如果AI返回的路径为空或验证失败，生成一个基本的备用路径
                    print(f"⚠️ AI返回的路径为空或验证失败，生成基本备用路径")
                    return self._generate_basic_fallback_path(disease_name, thinking_process)
                    
            else:
                raise Exception(f"AI调用失败: {response.message}")
                
        except Exception as e:
            print(f"❌ AI生成失败: {e}")
            raise e

    def _fix_ai_path_types(self, path: Dict[str, Any], disease_name: str) -> Dict[str, Any]:
        """修复AI返回的步骤类型，映射到前端期望的类型"""
        # 类型映射表：AI可能返回的类型 -> 前端期望的类型
        type_mapping = {
            'symptom_verify': 'symptom',
            'examination_check': 'four_diagnosis', 
            'syndrome_confirm': 'syndrome',
            'treatment_review': 'principle',
            'prescription_audit': 'prescription',
            'missing_check': 'modification',
            'pathogenesis_analysis': 'pathogenesis',
            'diagnosis': 'syndrome',
            'treatment': 'principle',
            'formula': 'prescription',
            'herbs': 'modification'
        }
        
        # 复制路径对象以避免修改原始数据
        fixed_path = path.copy()
        fixed_steps = []
        
        for step in path.get("steps", []):
            fixed_step = step.copy()
            original_type = step.get("type", "")
            
            # 如果类型需要映射，则进行映射
            if original_type in type_mapping:
                fixed_step["type"] = type_mapping[original_type]
                print(f"🔧 类型映射: {original_type} -> {fixed_step['type']}")
            elif original_type not in ['disease', 'four_diagnosis', 'symptom', 'pathogenesis', 'syndrome', 'principle', 'prescription', 'modification']:
                # 如果是完全未知的类型，根据内容猜测
                content = step.get("content", "").lower()
                if "症状" in content or "symptom" in content:
                    fixed_step["type"] = "symptom"
                elif "舌" in content or "脉" in content or "四诊" in content:
                    fixed_step["type"] = "four_diagnosis"
                elif "证" in content or "syndrome" in content:
                    fixed_step["type"] = "syndrome"
                elif "治" in content or "principle" in content:
                    fixed_step["type"] = "principle"
                elif "方" in content or "prescription" in content:
                    fixed_step["type"] = "prescription"
                else:
                    fixed_step["type"] = "modification"
                print(f"🔧 智能推断类型: {original_type} -> {fixed_step['type']}")
            
            fixed_steps.append(fixed_step)
        
        fixed_path["steps"] = fixed_steps
        return fixed_path

    def _clean_verification_language(self, path: Dict[str, Any]) -> Dict[str, Any]:
        """清理AI返回内容中的验证性语言"""
        cleaned_path = path.copy()
        cleaned_steps = []
        
        for step in path.get("steps", []):
            cleaned_step = step.copy()
            content = step.get("content", "")
            
            # 清理验证性语言的模式
            content = self._remove_verification_patterns(content, step.get("type", ""))
            
            # 如果清理后内容为空或太短，跳过这个步骤（但疾病名称可以很短）
            step_type = step.get("type", "")
            if len(content.strip()) < 3 and step_type != "disease":
                continue
                
            cleaned_step["content"] = content
            cleaned_steps.append(cleaned_step)
        
        cleaned_path["steps"] = cleaned_steps
        return cleaned_path

    def _remove_verification_patterns(self, content: str, step_type: str = "") -> str:
        """移除验证性语言模式 - 超强版"""
        import re
        
        # 第一步：移除所有符号开头的前缀
        prefix_patterns = [
            r'^✓\s*.*?：',  # 所有✓开头的内容
            r'^⚠️\s*.*?：',  # 所有⚠️开头的内容
            r'^☑\s*.*?：',   # 复选框开头
            r'^▪\s*.*?：',   # 项目符号开头
            r'^•\s*.*?：',   # 圆点开头
            r'^-\s*.*?：',   # 破折号开头
        ]
        
        for pattern in prefix_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # 第二步：移除包含特定关键词的句子段落
        keyword_patterns = [
            r'[^。]*?验证[^。]*?[。？]',
            r'[^。]*?确认[^。]*?[。？]',
            r'[^。]*?检查[^。]*?[。？]',
            r'[^。]*?核实[^。]*?[。？]',
            r'[^。]*?审核[^。]*?[。？]',
            r'[^。]*?是否[^。]*?[。？]',
            r'[^。]*?\？[^。]*?',  # 包含问号的内容
        ]
        
        for pattern in keyword_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # 第三步：移除末尾的验证性内容
        tail_patterns = [
            r'\s*-\s*.*?\？.*$',  # 破折号后的问题
            r'\s*，.*?\？.*$',    # 逗号后的问题  
            r'\s*。.*?\？.*$',    # 句号后的问题
            r'\s*[\-－—]\s*[^。]*$',  # 破折号后的内容
        ]
        
        for pattern in tail_patterns:
            content = re.sub(pattern, '', content)
        
        # 第四步：移除明确的验证性短语
        verification_phrases = [
            '是否准确', '是否适宜', '是否合理', '是否正确',
            '组方合理性检查', '请确保', '需要确认', '需要检查', 
            '需要验证', '需要核实', '请注意', '请考虑',
            '建议', '评估', '分析', '判断', '检验'
        ]
        
        for phrase in verification_phrases:
            # 移除包含这些短语的整个句段
            pattern = f'[^。]*?{phrase}[^。]*?[。？]?'
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # 第五步：清理残留的符号和格式
        content = re.sub(r'[。]+', '。', content)  # 合并多个句号
        content = re.sub(r'\s*。\s*$', '', content)  # 移除末尾句号
        content = re.sub(r'^\s*[，。、]\s*', '', content)  # 移除开头的标点
        content = re.sub(r'\s+', ' ', content)  # 合并多个空格
        content = content.strip()
        
        # 第六步：如果内容太短或只剩标点，返回空字符串（但疾病名称可以很短）
        if step_type == "disease":
            # 疾病名称允许很短，只检查是否为纯标点
            if content in ['。', '，', '、', '：', '；'] or len(content.strip()) == 0:
                return ""
        else:
            # 其他类型需要较长的内容
            if len(content) < 5 or content in ['。', '，', '、', '：', '；']:
                return ""
        
        return content

    def _validate_ai_path(self, path: Dict[str, Any], disease_name: str) -> bool:
        """验证AI生成的路径格式"""
        required_fields = ["id", "title", "steps", "keywords"]
        
        # 详细调试信息
        print(f"🔍 验证路径: {path.keys()}")
        for field in required_fields:
            if field not in path:
                print(f"❌ 缺失字段: {field}")
                return False
            else:
                print(f"✅ 存在字段: {field}")
        
        steps = path.get("steps", [])
        print(f"🔍 步骤数量: {len(steps)}")
        for i, step in enumerate(steps):
            print(f"🔍 步骤{i+1}: type={step.get('type')}, content={step.get('content', '')[:50]}...")
        
        if len(steps) < 3:  # 至少要有症状、诊断、治疗
            print(f"❌ 步骤不足: 需要至少3步，实际{len(steps)}步")
            return False
            
        print("✅ 路径验证通过")
        return True

    def _parse_ai_text_response(self, content: str, disease_name: str) -> List[Dict[str, Any]]:
        """解析AI文本响应，当JSON解析失败时的备用方案"""
        print("🔄 使用备用文本解析方案")
        
        # 尝试从AI内容中提取有用信息
        paths = []
        
        # 简单的关键词提取
        import re
        
        # 首先过滤掉JSON代码块
        content = re.sub(r'\{[^}]*"paths"[^}]*\}.*', '', content, flags=re.DOTALL)
        content = re.sub(r'```json.*?```', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # 改进的信息提取 - 更精准的模式匹配
        # 提取症状信息
        symptoms = []
        symptom_patterns = [
            r'患者([^。，]*(?:恶寒|发热|头痛|身痛|咳嗽|鼻塞|流涕|胸闷|胃痛|失眠|痰白|痰黄)[^。，]*)',
            r'(恶寒发热[^。，]*)',
            r'(头痛身痛[^。，]*)',
            r'(鼻塞流涕[^。，]*)',
            r'(咳嗽[^。，]*)',
            r'(胸闷[^。，]*)',
            r'(胃痛[^。，]*)'
        ]
        
        for pattern in symptom_patterns:
            matches = re.findall(pattern, content)
            symptoms.extend([m for m in matches if m.strip()])
        
        # 提取四诊信息 
        four_diagnosis = []
        four_diag_patterns = [
            r'(舌[^。，]*)',
            r'(脉[^。，]*)',
            r'(面色[^。，]*)',
            r'(声音[^。，]*)'
        ]
        
        for pattern in four_diag_patterns:
            matches = re.findall(pattern, content)
            four_diagnosis.extend([m for m in matches if m.strip()])
        
        # 提取方剂信息  
        prescriptions = []
        prescription_patterns = [
            r'用([^。，]*(?:汤|散|丸|膏)[^。，]*)',
            r'方用([^。，]*(?:汤|散|丸|膏)[^。，]*)',
            r'选用([^。，]*(?:汤|散|丸|膏)[^。，]*)',
            r'([一-龟][^。，]*(?:汤|散|丸|膏)(?:加减)?)'
        ]
        
        for pattern in prescription_patterns:
            matches = re.findall(pattern, content)
            prescriptions.extend([m.strip() for m in matches if m.strip()])
        
        # 提取证型信息
        syndromes = []
        syndrome_patterns = [
            r'辨证为([^。，]*)',
            r'([^。，]*(?:风寒|风热|气虚|血瘀|痰湿|肝郁)[^。，]*(?:证|型))',
            r'诊断为([^。，]*)',
            r'考虑([^。，]*(?:证|型))'
        ]
        
        for pattern in syndrome_patterns:
            matches = re.findall(pattern, content)
            syndromes.extend([m.strip() for m in matches if m.strip()])
        
        # 提取治疗原则
        principles = []
        principle_patterns = [
            r'治宜([^。，]*)',
            r'治以([^。，]*)',
            r'治法([^。，]*)',
            r'(辛温解表[^。，]*)',
            r'(疏风散寒[^。，]*)',
            r'(清热解毒[^。，]*)'
        ]
        
        for pattern in principle_patterns:
            matches = re.findall(pattern, content)
            principles.extend([m.strip() for m in matches if m.strip()])
        
        # 构建步骤 - 按中医诊疗流程顺序
        steps = [{"type": "disease", "content": disease_name}]
        
        # 添加症状信息
        if symptoms:
            symptom_content = "，".join(symptoms[:2])  # 取前2个最相关症状
            steps.append({"type": "symptom", "content": symptom_content})
        
        # 添加四诊信息
        if four_diagnosis:
            four_diag_content = "，".join(four_diagnosis[:2])  # 取前2个四诊信息
            steps.append({"type": "four_diagnosis", "content": four_diag_content})
        
        # 添加证型信息
        if syndromes:
            syndrome_content = syndromes[0].strip()
            steps.append({"type": "syndrome", "content": syndrome_content})
        
        # 添加治疗原则
        if principles:
            principle_content = principles[0].strip()
            steps.append({"type": "principle", "content": principle_content})
        
        # 添加处方信息
        if prescriptions:
            prescription_content = prescriptions[0].strip()
            steps.append({"type": "prescription", "content": prescription_content})
        
        # 确保至少有基本的治疗原则
        if len(steps) == 1:  # 只有疾病名称
            steps.append({"type": "principle", "content": f"{disease_name}的基本治疗原则"})
        
        path = {
            "id": "medical_path",
            "title": f"{disease_name}诊疗路径",
            "steps": steps,
            "keywords": [disease_name],
            "tcm_theory": "基于AI分析的中医理论",
            "confidence": 0.6
        }
        
        paths.append(path)
        print(f"📝 备用解析完成，提取到{len(steps)}个步骤")
        print(f"🔍 提取详情: 症状{len(symptoms)}个, 四诊{len(four_diagnosis)}个, 证型{len(syndromes)}个, 治法{len(principles)}个, 方剂{len(prescriptions)}个")
        if symptoms: print(f"  症状: {symptoms}")
        if four_diagnosis: print(f"  四诊: {four_diagnosis}")
        if syndromes: print(f"  证型: {syndromes}")
        if principles: print(f"  治法: {principles}")
        if prescriptions: print(f"  方剂: {prescriptions}")
        return paths

    async def _record_ai_learning(self, disease_name: str, thinking_process: str, ai_paths: List[Dict[str, Any]]):
        """记录AI生成的学习数据"""
        try:
            # 这里可以记录AI生成的数据用于后续学习
            print(f"📚 记录AI学习数据: {disease_name}, 路径数量: {len(ai_paths)}")
        except Exception as e:
            print(f"⚠️ 记录学习数据失败: {e}")

    async def _analyze_diagnostic_completeness(self, disease_name: str, thinking_process: str) -> Dict[str, Any]:
        """
        分析诊疗流程完整性，识别缺失项目
        
        Args:
            disease_name: 疾病名称
            thinking_process: 医生诊疗思路
            
        Returns:
            完整性分析结果
        """
        # 标准中医诊疗流程清单
        standard_items = {
            "disease_identification": "病种识别：确定疾病的中医病名",
            "four_diagnosis": "四诊收集：望闻问切，收集全面信息", 
            "main_symptoms": "主要症状：主症、兼症的归纳分析",
            "pathogenesis": "病因病机：分析发病原因和病理机制",
            "syndrome_differentiation": "证候判断：辨证分型（支持多种证型）",
            "treatment_principles": "治则治法：确定治疗原则和方法",
            "prescription": "方剂处方：选方用药，君臣佐使",
            "modifications": "随症加减：根据具体症状调整用药",
            "prognosis_care": "预后调理：养生建议和注意事项"
        }
        
        # 分析医生思路中已包含的项目
        present_items = []
        missing_items = []
        
        thinking_lower = thinking_process.lower()
        
        # 关键词匹配规则
        keyword_patterns = {
            "disease_identification": [disease_name, "病名", "诊断"],
            "four_diagnosis": ["舌", "脉", "望", "闻", "问", "切", "四诊"],
            "main_symptoms": ["症状", "主症", "兼症", "表现"],
            "pathogenesis": ["病因", "病机", "发病", "原因", "机制"],
            "syndrome_differentiation": ["证", "型", "辨证", "分型", "证候"],
            "treatment_principles": ["治法", "治则", "原则", "方法"],
            "prescription": ["方", "药", "处方", "方剂", "君臣佐使"],
            "modifications": ["加减", "调整", "变化", "加味"],
            "prognosis_care": ["调理", "养生", "注意", "预后", "护理"]
        }
        
        # 检查每个项目是否存在
        for item_key, item_desc in standard_items.items():
            keywords = keyword_patterns.get(item_key, [])
            found = any(keyword in thinking_lower for keyword in keywords)
            
            if found:
                present_items.append({"key": item_key, "description": item_desc})
            else:
                missing_items.append({"key": item_key, "description": item_desc})
        
        return {
            "present_items": present_items,
            "missing_items": missing_items,
            "completeness_rate": len(present_items) / len(standard_items),
            "recommendations": self._generate_completion_recommendations(missing_items, disease_name)
        }

    def _enhance_prompt_with_missing_items(self, original_prompt: str, completeness_analysis: Dict[str, Any], disease_name: str) -> str:
        """
        基于缺失项目增强AI提示词
        
        Args:
            original_prompt: 原始提示词
            completeness_analysis: 完整性分析结果
            disease_name: 疾病名称
            
        Returns:
            增强后的提示词
        """
        missing_items = completeness_analysis.get("missing_items", [])
        if not missing_items:
            return original_prompt
        
        # 构建补充指导
        missing_guidance = f"\n🔍 请特别关注以下缺失的诊疗要素，并尝试基于常见的{disease_name}诊疗规律进行合理补充：\n"
        
        for item in missing_items:
            missing_guidance += f"- {item['description']}\n"
        
        missing_guidance += "\n💡 补充原则：\n"
        missing_guidance += f"- 基于{disease_name}的中医诊疗常规\n"
        missing_guidance += "- 考虑患者可能的年龄、性别特征\n"
        missing_guidance += "- 提供合理的临床推测，但要标注为'建议补充'\n"
        missing_guidance += "- 如果信息确实无法推测，可以省略该步骤\n"
        
        # 在原始提示词中插入补充指导
        enhanced_prompt = original_prompt.replace(
            "提取规则：",
            f"提取规则：\n{missing_guidance}\n原始提取规则："
        )
        
        return enhanced_prompt

    def _generate_completion_recommendations(self, missing_items: List[Dict[str, Any]], disease_name: str) -> List[str]:
        """
        生成诊疗流程完善建议
        
        Args:
            missing_items: 缺失项目列表
            disease_name: 疾病名称
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if any(item["key"] == "four_diagnosis" for item in missing_items):
            recommendations.append(f"建议补充{disease_name}的典型舌脉象表现")
        
        if any(item["key"] == "pathogenesis" for item in missing_items):
            recommendations.append(f"建议分析{disease_name}的病因病机")
        
        if any(item["key"] == "modifications" for item in missing_items):
            recommendations.append("建议考虑随症加减的具体方案")
        
        if any(item["key"] == "prognosis_care" for item in missing_items):
            recommendations.append("建议添加预后调理和生活指导")
        
        return recommendations


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

    def _add_age_branches_to_paths(self, original_paths: List[Dict[str, Any]], disease_name: str) -> List[Dict[str, Any]]:
        """
        为决策路径添加智能年龄分支
        
        Args:
            original_paths: 原始决策路径
            disease_name: 疾病名称
            
        Returns:
            添加年龄分支后的决策路径
        """
        enhanced_paths = []
        
        for path in original_paths:
            # 如果路径包含处方步骤，创建年龄分支
            prescription_steps = [step for step in path.get("steps", []) 
                                if step.get("type") == "prescription"]
            
            if prescription_steps:
                # 为每个处方步骤创建成人/儿童分支
                adult_path, child_path = self._create_age_specific_paths(path, disease_name)
                enhanced_paths.extend([adult_path, child_path])
            else:
                # 无处方步骤，保持原路径
                enhanced_paths.append(path)
        
        print(f"🎯 智能分支完成: 原始{len(original_paths)}条路径 → 增强后{len(enhanced_paths)}条路径")
        return enhanced_paths

    def _create_age_specific_paths(self, original_path: Dict[str, Any], disease_name: str) -> tuple:
        """
        创建成人和儿童特定的路径分支
        
        Args:
            original_path: 原始路径
            disease_name: 疾病名称
            
        Returns:
            (成人路径, 儿童路径)元组
        """
        # 复制原始路径作为基础
        adult_path = original_path.copy()
        child_path = original_path.copy()
        
        # 成人路径 (18岁以上)
        adult_path.update({
            "id": f"{original_path['id']}_adult",
            "title": f"{original_path['title']} - 成人用药",
            "age_group": "adult",
            "age_range": "18岁以上",
            "dosage_ratio": 1.0,
            "steps": self._adjust_steps_for_age_group(original_path.get("steps", []), "adult"),
            "keywords": original_path.get("keywords", []) + ["成人", "标准剂量"],
            "dosage_note": "成人标准剂量，根据体重和病情适当调整"
        })
        
        # 儿童路径 (3-17岁, 65%剂量)
        child_path.update({
            "id": f"{original_path['id']}_child",
            "title": f"{original_path['title']} - 儿童用药",
            "age_group": "child", 
            "age_range": "3-17岁",
            "dosage_ratio": 0.65,
            "steps": self._adjust_steps_for_age_group(original_path.get("steps", []), "child"),
            "keywords": original_path.get("keywords", []) + ["儿童", "减量65%"],
            "dosage_note": "儿童减量用药(65%)，注意观察反应，必要时调整剂量"
        })
        
        return adult_path, child_path

    def _adjust_steps_for_age_group(self, original_steps: List[Dict[str, Any]], age_group: str) -> List[Dict[str, Any]]:
        """
        根据年龄组调整决策步骤中的处方剂量
        
        Args:
            original_steps: 原始步骤
            age_group: 年龄组 ("adult" 或 "child")
            
        Returns:
            调整后的步骤
        """
        adjusted_steps = []
        
        for step in original_steps:
            new_step = step.copy()
            
            if step.get("type") == "prescription":
                # 调整处方剂量
                new_step["content"] = self._adjust_prescription_dosage(
                    step.get("content", ""), age_group
                )
                
                # 添加年龄特定的用药说明
                if age_group == "child":
                    new_step["age_specific_notes"] = [
                        "儿童用药需密切观察反应",
                        "如有不适请及时就医",
                        "剂量已按儿童标准调整(65%)"
                    ]
                else:
                    new_step["age_specific_notes"] = [
                        "成人标准剂量",
                        "可根据体重适当调整",
                        "注意药物相互作用"
                    ]
            
            adjusted_steps.append(new_step)
        
        return adjusted_steps

    def _adjust_prescription_dosage(self, prescription_content: str, age_group: str) -> str:
        """
        调整处方内容中的药物剂量
        
        Args:
            prescription_content: 原始处方内容
            age_group: 年龄组
            
        Returns:
            调整后的处方内容
        """
        if age_group == "adult":
            # 成人保持标准剂量
            return prescription_content
        
        # 儿童减量65%
        import re
        
        def replace_dosage(match):
            try:
                original_dose = float(match.group(1))
                adjusted_dose = round(original_dose * 0.65, 1)
                # 确保最小剂量不少于1g (除非原始剂量就很小)
                if adjusted_dose < 1 and original_dose >= 3:
                    adjusted_dose = 1
                return f"{adjusted_dose}g"
            except:
                return match.group(0)
        
        # 匹配剂量模式：数字+g
        adjusted_content = re.sub(r'(\d+(?:\.\d+)?)g', replace_dosage, prescription_content)
        
        # 添加儿童用药提示
        if "儿童剂量" not in adjusted_content:
            adjusted_content += " (已调整为儿童安全剂量)"

        return adjusted_content

    def _generate_basic_fallback_path(self, disease_name: str, thinking_process: str) -> List[Dict[str, Any]]:
        """
        生成基本的备用决策路径（当AI解析完全失败时使用）

        Args:
            disease_name: 疾病名称
            thinking_process: 医生的诊疗思路

        Returns:
            基本的决策路径列表
        """
        print(f"🔧 生成基本备用路径: {disease_name}")

        # 从医生思路中提取关键信息
        import re

        # 提取可能的症状
        symptoms = []
        symptom_keywords = ["症状", "表现", "证候", "主症", "兼症"]
        for keyword in symptom_keywords:
            if keyword in thinking_process:
                # 提取该关键词后的内容
                match = re.search(f'{keyword}[:：]?([^。，；]+)', thinking_process)
                if match:
                    symptoms.append(match.group(1).strip())

        # 提取可能的治法
        treatment_principle = ""
        treatment_keywords = ["治法", "治则", "治疗", "方药"]
        for keyword in treatment_keywords:
            if keyword in thinking_process:
                match = re.search(f'{keyword}[:：]?([^。，；]+)', thinking_process)
                if match:
                    treatment_principle = match.group(1).strip()
                    break

        # 构建基本路径
        steps = [
            {
                "type": "disease",
                "title": disease_name,
                "content": disease_name
            }
        ]

        # 添加症状步骤
        if symptoms:
            steps.append({
                "type": "symptom",
                "title": "临床表现",
                "content": "、".join(symptoms[:3])  # 最多取3个症状
            })
        else:
            steps.append({
                "type": "symptom",
                "title": "临床表现",
                "content": thinking_process[:100] if thinking_process else f"{disease_name}的典型症状"
            })

        # 添加治疗步骤
        if treatment_principle:
            steps.append({
                "type": "treatment",
                "title": "治疗原则",
                "content": treatment_principle
            })
        else:
            steps.append({
                "type": "treatment",
                "title": "治疗原则",
                "content": f"{disease_name}的辨证施治"
            })

        # 添加处方步骤（基本模板）
        steps.append({
            "type": "prescription",
            "title": "处方建议",
            "content": f"方剂：请根据具体证型选方用药"
        })

        return [{
            "id": "fallback_path1",
            "title": f"{disease_name}基本诊疗路径",
            "steps": steps,
            "keywords": [disease_name, "基本路径"],
            "source": "fallback",
            "note": "由于AI解析异常，此为基本参考路径，请根据实际情况调整"
        }]

if __name__ == "__main__":
    test_famous_doctor_system()