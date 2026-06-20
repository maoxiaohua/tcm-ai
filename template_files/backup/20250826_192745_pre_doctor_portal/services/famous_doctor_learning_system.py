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
    
    def __init__(self, db_path: str = "/opt/tcm/data/famous_doctors.sqlite"):
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