#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医生匹配服务 - 智汇中医工作流核心模块
支持指定医生、系统推荐、导医介绍三种模式
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import sqlite3
from config.settings import PATHS

logger = logging.getLogger(__name__)

@dataclass
class DoctorInfo:
    """医生信息数据类"""
    uuid: str
    name: str
    title: str
    specialties: List[str]
    average_rating: float
    total_reviews: int
    consultation_count: int
    available_hours: Dict[str, Any]
    introduction: str
    avatar_url: str
    commission_rate: float
    is_available: bool

@dataclass
class MatchingCriteria:
    """医生匹配条件数据类"""
    patient_id: str
    symptoms: List[str]
    preferred_specialties: List[str] = None
    preferred_doctor_id: str = None
    avoid_doctor_ids: List[str] = None
    consultation_time: str = None  # morning, afternoon, evening, anytime
    gender_preference: str = None  # male, female, no_preference
    language_preference: str = "zh-CN"
    max_results: int = 5

class DoctorMatchingService:
    """医生匹配服务类"""
    
    def __init__(self):
        self.db_path = PATHS['user_db']
    
    def get_available_doctors(self, criteria: MatchingCriteria) -> List[DoctorInfo]:
        """获取可用医生列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 构建查询条件
                query_parts = [
                    "SELECT d.id, d.name, d.speciality, d.specialties, d.introduction,",
                    "       d.average_rating, d.total_reviews, d.consultation_count, d.available_hours",
                    "FROM doctors d",
                    "WHERE d.status = 'active'"
                ]
                
                params = []
                
                # 排除不想要的医生
                if criteria.avoid_doctor_ids:
                    placeholders = ','.join(['?' for _ in criteria.avoid_doctor_ids])
                    query_parts.append(f"AND d.id NOT IN ({placeholders})")
                    params.extend(criteria.avoid_doctor_ids)
                
                # 专科筛选
                if criteria.preferred_specialties:
                    specialty_conditions = []
                    for specialty in criteria.preferred_specialties:
                        specialty_conditions.append("d.specialties LIKE ?")
                        params.append(f'%"{specialty}"%')
                    query_parts.append(f"AND ({' OR '.join(specialty_conditions)})")
                
                # 按评分和问诊量排序
                query_parts.append("ORDER BY d.average_rating DESC, d.consultation_count DESC")
                query_parts.append(f"LIMIT {criteria.max_results}")
                
                query = " ".join(query_parts)
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                doctors = []
                for row in rows:
                    try:
                        specialties = json.loads(row['specialties'] or '[]')
                        available_hours = json.loads(row['available_hours'] or '{}')
                    except json.JSONDecodeError:
                        specialties = []
                        available_hours = {}
                    
                    doctor = DoctorInfo(
                        uuid=str(row['id']),
                        name=row['name'],
                        title=row['speciality'] or '医师',  # 使用专业作为title
                        specialties=specialties,
                        average_rating=float(row['average_rating'] or 0),
                        total_reviews=int(row['total_reviews'] or 0),
                        consultation_count=int(row['consultation_count'] or 0),
                        available_hours=available_hours,
                        introduction=row['introduction'] or '',
                        avatar_url='',
                        commission_rate=0.30,  # 默认30%分成
                        is_available=True  # 简化处理，默认可用
                    )
                    doctors.append(doctor)
                
                logger.info(f"找到 {len(doctors)} 位可用医生")
                return doctors
                
        except Exception as e:
            logger.error(f"获取可用医生失败: {e}")
            return []
    
    def get_doctor_by_id(self, doctor_id: str) -> Optional[DoctorInfo]:
        """根据ID获取特定医生信息"""
        try:
            criteria = MatchingCriteria(
                patient_id="", 
                symptoms=[],
                preferred_doctor_id=doctor_id,
                max_results=1
            )
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = """
                SELECT d.id, d.name, d.speciality, d.specialties, d.introduction,
                       d.average_rating, d.total_reviews, d.consultation_count, d.available_hours
                FROM doctors d
                WHERE d.id = ? AND d.status = 'active'
                """
                
                cursor = conn.execute(query, (doctor_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                try:
                    specialties = json.loads(row['specialties'] or '[]')
                    available_hours = json.loads(row['available_hours'] or '{}')
                except json.JSONDecodeError:
                    specialties = []
                    available_hours = {}
                
                doctor = DoctorInfo(
                    uuid=str(row['id']),
                    name=row['name'],
                    title=row['speciality'] or '医师',  # 使用专业作为title
                    specialties=specialties,
                    average_rating=float(row['average_rating'] or 0),
                    total_reviews=int(row['total_reviews'] or 0),
                    consultation_count=int(row['consultation_count'] or 0),
                    available_hours=available_hours,
                    introduction=row['introduction'] or '',
                    avatar_url='',
                    commission_rate=0.30,  # 默认30%分成
                    is_available=True  # 简化处理，默认可用
                )
                
                return doctor
                
        except Exception as e:
            logger.error(f"获取医生信息失败 ({doctor_id}): {e}")
            return None
    
    def recommend_doctors_for_symptoms(self, symptoms: List[str], patient_id: str) -> List[DoctorInfo]:
        """根据症状智能推荐医生"""
        try:
            # 扩展的症状到专科映射 - 支持更多专科和症状
            symptom_specialty_mapping = {
                # 内科相关
                '失眠': ['内科', '神志病科'],
                '焦虑': ['内科', '神志病科'],
                '抑郁': ['内科', '神志病科'],
                '头痛': ['内科', '脑病科'],
                '头疼': ['内科', '脑病科'],
                '眩晕': ['内科', '脑病科'],
                '头晕': ['内科', '脑病科'],
                '心悸': ['内科'],
                '胸闷': ['内科'],
                '乏力': ['内科'],
                '发热': ['内科'],
                
                # 脾胃病科
                '胃痛': ['脾胃病科', '内科'],
                '胃疼': ['脾胃病科', '内科'],
                '胃炎': ['脾胃病科', '内科'],
                '腹泻': ['脾胃病科', '内科'],
                '便秘': ['脾胃病科', '内科'],
                '食欲不振': ['脾胃病科', '内科'],
                '消化不良': ['脾胃病科', '内科'],
                
                # 肺病科
                '咳嗽': ['肺病科', '内科'],
                '哮喘': ['肺病科', '内科'],
                '鼻炎': ['肺病科', '内科'],
                '气喘': ['肺病科', '内科'],
                
                # 妇科专业
                '月经不调': ['妇科'],
                '痛经': ['妇科'],
                '白带异常': ['妇科'],
                '不孕': ['妇科'],
                '更年期': ['妇科', '内科'],
                '妇科疾病': ['妇科'],
                '妇科问题': ['妇科'],
                '妇科': ['妇科'],
                '女性疾病': ['妇科'],
                '例假不准': ['妇科'],
                
                # 儿科专业
                '小儿发热': ['儿科'],
                '小儿咳嗽': ['儿科'],
                '小儿腹泻': ['儿科'],
                '儿科疾病': ['儿科'],
                '儿科': ['儿科'],
                '小儿疾病': ['儿科'],
                '孩子生病': ['儿科'],
                '宝宝发烧': ['儿科'],
                
                # 皮肤科
                '湿疹': ['皮肤科', '内科'],
                '痤疮': ['皮肤科', '内科'],
                '皮肤病': ['皮肤科', '内科'],
                '皮肤疾病': ['皮肤科', '内科'],
                '青春痘': ['皮肤科', '内科'],
                
                # 骨伤科
                '腰痛': ['骨伤科', '内科'],
                '关节痛': ['骨伤科', '内科'],
                '颈椎病': ['骨伤科', '内科'],
                '骨科疾病': ['骨伤科', '内科'],
                '骨科': ['骨伤科', '内科'],
                '筋骨疼痛': ['骨伤科', '内科'],
                '膝盖痛': ['骨伤科', '内科'],
                
                # 五官科/耳鼻喉科
                '耳鸣': ['五官科', '内科'],
                '听力下降': ['五官科', '内科'],
                '鼻塞': ['肺病科', '五官科'],
                
                # 肿瘤科
                '肿瘤': ['肿瘤科', '内科'],
                '癌症': ['肿瘤科', '内科']
            }
            
            logger.info(f"开始为症状 {symptoms} 匹配专科...")
            
            # 根据症状确定推荐专科
            recommended_specialties = set()
            for symptom in symptoms:
                for key, specialties in symptom_specialty_mapping.items():
                    if key in symptom:
                        recommended_specialties.update(specialties)
            
            if not recommended_specialties:
                recommended_specialties = ['内科']  # 默认推荐内科
            
            # 获取患者历史偏好
            patient_preferences = self._get_patient_preferences(patient_id)
            if patient_preferences and patient_preferences.get('preferred_specialties'):
                recommended_specialties.update(patient_preferences['preferred_specialties'])
            
            criteria = MatchingCriteria(
                patient_id=patient_id,
                symptoms=symptoms,
                preferred_specialties=list(recommended_specialties),
                avoid_doctor_ids=patient_preferences.get('avoid_doctor_ids', []) if patient_preferences else [],
                consultation_time=patient_preferences.get('preferred_consultation_time') if patient_preferences else None,
                gender_preference=patient_preferences.get('gender_preference') if patient_preferences else None,
                max_results=8
            )
            
            recommended_doctors = self.get_available_doctors(criteria)
            logger.info(f"为症状 {symptoms} 推荐了 {len(recommended_doctors)} 位医生")
            
            return recommended_doctors
            
        except Exception as e:
            logger.error(f"症状匹配推荐失败: {e}")
            return []
    
    def assign_doctor_to_patient(self, patient_id: str, doctor_id: str, 
                                selection_method: str = "specified") -> bool:
        """将医生分配给患者"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 检查是否已存在关系
                existing = conn.execute(
                    "SELECT id FROM doctor_patient_relationships WHERE doctor_id = ? AND patient_id = ?",
                    (doctor_id, patient_id)
                ).fetchone()
                
                if existing:
                    # 更新现有关系
                    conn.execute("""
                        UPDATE doctor_patient_relationships 
                        SET relationship_type = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE doctor_id = ? AND patient_id = ?
                    """, (selection_method, doctor_id, patient_id))
                else:
                    # 创建新关系
                    relationship_uuid = f"rel-{datetime.now().strftime('%Y%m%d')}-{patient_id[:8]}-{doctor_id[:8]}"
                    conn.execute("""
                        INSERT INTO doctor_patient_relationships 
                        (uuid, doctor_id, patient_id, relationship_type, first_consultation_date)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (relationship_uuid, doctor_id, patient_id, selection_method))
                
                conn.commit()
                logger.info(f"医生分配成功: 患者 {patient_id} -> 医生 {doctor_id} ({selection_method})")
                return True
                
        except Exception as e:
            logger.error(f"医生分配失败: {e}")
            return False
    
    def _check_doctor_availability(self, doctor_id: str, consultation_time: str = None) -> bool:
        """检查医生可用性"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now()
                day_of_week = now.weekday() + 1  # SQLite中周一是1
                current_time = now.time()
                
                # 检查医生今天是否有可用时间段
                query = """
                SELECT COUNT(*) as available_slots
                FROM doctor_availability 
                WHERE doctor_id = ? AND day_of_week = ? 
                AND is_available = 1 AND start_time <= ? AND end_time >= ?
                """
                
                result = conn.execute(query, (
                    doctor_id, day_of_week, 
                    current_time.strftime('%H:%M'), 
                    current_time.strftime('%H:%M')
                )).fetchone()
                
                return result[0] > 0 if result else True  # 默认可用
                
        except Exception as e:
            logger.error(f"检查医生可用性失败: {e}")
            return True  # 出错时默认可用
    
    def _get_patient_preferences(self, patient_id: str) -> Optional[Dict]:
        """获取患者偏好设置"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                row = conn.execute("""
                    SELECT preferred_specialties, preferred_doctor_id, avoid_doctor_ids,
                           preferred_consultation_time, gender_preference
                    FROM doctor_selection_preferences
                    WHERE patient_id = ?
                    ORDER BY updated_at DESC LIMIT 1
                """, (patient_id,)).fetchone()
                
                if row:
                    try:
                        return {
                            'preferred_specialties': json.loads(row['preferred_specialties'] or '[]'),
                            'preferred_doctor_id': row['preferred_doctor_id'],
                            'avoid_doctor_ids': json.loads(row['avoid_doctor_ids'] or '[]'),
                            'preferred_consultation_time': row['preferred_consultation_time'],
                            'gender_preference': row['gender_preference']
                        }
                    except json.JSONDecodeError:
                        return None
                
                return None
                
        except Exception as e:
            logger.error(f"获取患者偏好失败: {e}")
            return None
    
    def save_patient_preferences(self, patient_id: str, preferences: Dict) -> bool:
        """保存患者偏好设置"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 检查是否已存在偏好设置
                existing = conn.execute(
                    "SELECT id FROM doctor_selection_preferences WHERE patient_id = ?",
                    (patient_id,)
                ).fetchone()
                
                if existing:
                    # 更新现有偏好
                    conn.execute("""
                        UPDATE doctor_selection_preferences SET
                            preferred_specialties = ?,
                            preferred_doctor_id = ?,
                            avoid_doctor_ids = ?,
                            preferred_consultation_time = ?,
                            gender_preference = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE patient_id = ?
                    """, (
                        json.dumps(preferences.get('preferred_specialties', [])),
                        preferences.get('preferred_doctor_id'),
                        json.dumps(preferences.get('avoid_doctor_ids', [])),
                        preferences.get('preferred_consultation_time'),
                        preferences.get('gender_preference'),
                        patient_id
                    ))
                else:
                    # 创建新偏好设置
                    pref_uuid = f"pref-{datetime.now().strftime('%Y%m%d%H%M%S')}-{patient_id[:8]}"
                    conn.execute("""
                        INSERT INTO doctor_selection_preferences
                        (uuid, patient_id, preferred_specialties, preferred_doctor_id,
                         avoid_doctor_ids, preferred_consultation_time, gender_preference)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pref_uuid, patient_id,
                        json.dumps(preferences.get('preferred_specialties', [])),
                        preferences.get('preferred_doctor_id'),
                        json.dumps(preferences.get('avoid_doctor_ids', [])),
                        preferences.get('preferred_consultation_time'),
                        preferences.get('gender_preference')
                    ))
                
                conn.commit()
                logger.info(f"患者偏好保存成功: {patient_id}")
                return True
                
        except Exception as e:
            logger.error(f"保存患者偏好失败: {e}")
            return False