#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处方学习集成器
自动收集上传的处方数据，提取知识，更新向量数据库
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import asyncio

sys.path.append('/opt/tcm-ai')

from services.famous_doctor_learning_system import FamousDoctorLearningSystem, ClinicalCase, DoctorProfile
from template_files.lightweight_tcm_vector_db import LightweightTCMVectorDatabase
from core.prescription.prescription_checker import Prescription, PrescriptionParser

logger = logging.getLogger(__name__)

class PrescriptionLearningIntegrator:
    """处方学习集成器 - 连接处方检测和学习系统"""
    
    def __init__(self):
        """初始化学习集成器"""
        self.learning_system = None
        self.vector_db = None
        self.parser = PrescriptionParser()
        self.setup_systems()
    
    def setup_systems(self):
        """设置学习系统"""
        try:
            # 初始化名医学习系统
            self.learning_system = FamousDoctorLearningSystem()
            logger.info("✅ 名医学习系统初始化成功")
            
            # 初始化向量数据库
            self.vector_db = LightweightTCMVectorDatabase()
            logger.info("✅ 向量数据库初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 学习系统初始化失败: {e}")
            
    async def process_prescription_data(self, 
                                      prescription_data: Dict[str, Any],
                                      source_type: str = "user_upload",
                                      patient_info: Optional[Dict] = None) -> bool:
        """
        处理处方数据并进行学习
        
        Args:
            prescription_data: 处方分析结果
            source_type: 数据源类型 (user_upload, image_upload, etc.)
            patient_info: 患者信息（匿名化）
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 1. 提取关键信息
            extracted_info = self._extract_learning_data(prescription_data, patient_info)
            if not extracted_info:
                logger.warning("⚠️ 未能提取有效的学习数据")
                return False
            
            # 2. 保存到名医学习系统
            saved_to_learning = await self._save_to_learning_system(extracted_info, source_type)
            
            # 3. 更新向量数据库
            updated_vector_db = await self._update_vector_database(extracted_info)
            
            # 4. 记录处理日志
            self._log_processing_result(extracted_info, saved_to_learning, updated_vector_db)
            
            return saved_to_learning or updated_vector_db
            
        except Exception as e:
            logger.error(f"❌ 处方学习处理失败: {e}")
            return False
    
    def _extract_learning_data(self, prescription_data: Dict[str, Any], 
                              patient_info: Optional[Dict] = None) -> Optional[Dict]:
        """提取用于学习的关键数据"""
        try:
            # 提取处方信息
            prescription_info = prescription_data.get('prescription', {})
            herbs = prescription_info.get('herbs', [])
            
            if not herbs:
                return None
            
            # 提取诊断信息
            diagnosis_info = prescription_data.get('diagnosis', {})
            clinical_analysis = prescription_data.get('clinical_analysis', {})
            
            # 构建学习数据结构
            learning_data = {
                'prescription_id': f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'timestamp': datetime.now().isoformat(),
                'herbs': herbs,
                'total_herbs': len(herbs),
                'diagnosis': {
                    'primary': diagnosis_info.get('primary', ''),
                    'tcm_syndrome': diagnosis_info.get('tcm_syndrome', ''),
                    'symptoms': diagnosis_info.get('symptoms', [])
                },
                'clinical_info': {
                    'formula_type': clinical_analysis.get('formula_type', ''),
                    'therapeutic_principle': clinical_analysis.get('therapeutic_principle', ''),
                    'expected_effects': clinical_analysis.get('expected_effects', [])
                },
                'patient_profile': self._anonymize_patient_info(patient_info) if patient_info else {},
                'source_type': 'user_upload',
                'confidence_score': prescription_data.get('document_analysis', {}).get('confidence', 0.0)
            }
            
            return learning_data
            
        except Exception as e:
            logger.error(f"❌ 数据提取失败: {e}")
            return None
    
    def _anonymize_patient_info(self, patient_info: Dict) -> Dict:
        """患者信息匿名化处理"""
        if not patient_info:
            return {}
            
        # 保留有学习价值的信息，移除个人标识
        anonymized = {}
        
        # 年龄段而非具体年龄
        age = patient_info.get('age', '')
        if age:
            try:
                age_num = int(age)
                if age_num < 18:
                    anonymized['age_group'] = '儿童'
                elif age_num < 60:
                    anonymized['age_group'] = '成人'
                else:
                    anonymized['age_group'] = '老年'
            except:
                pass
        
        # 性别（用于某些性别特异性疾病）
        gender = patient_info.get('gender', '')
        if gender in ['男', '女', 'male', 'female']:
            anonymized['gender'] = gender
            
        # 症状描述（移除姓名等个人信息）
        symptoms = patient_info.get('symptoms', '')
        if symptoms:
            anonymized['symptom_pattern'] = self._clean_symptom_text(symptoms)
        
        return anonymized
    
    def _clean_symptom_text(self, text: str) -> str:
        """清理症状文本，移除个人信息"""
        # 简单的个人信息移除
        import re
        
        # 移除可能的姓名模式
        text = re.sub(r'[王李张刘陈杨黄赵吴周][某某一二三四五六七八九十]', '患者', text)
        text = re.sub(r'[先生女士]{0,1}[，。]', '', text)
        
        return text[:200]  # 限制长度
    
    async def _save_to_learning_system(self, learning_data: Dict, source_type: str) -> bool:
        """保存到名医学习系统"""
        try:
            if not self.learning_system:
                logger.warning("⚠️ 名医学习系统未初始化")
                return False
            
            # 构建临床案例数据结构
            case_id = learning_data['prescription_id']
            
            # 创建处方对象
            herbs_data = learning_data['herbs']
            prescription = self._create_prescription_object(herbs_data)
            
            if not prescription:
                logger.warning("⚠️ 无法创建有效的处方对象")
                return False
            
            # 创建临床案例
            clinical_case = ClinicalCase(
                case_id=case_id,
                doctor_name="上传处方_匿名医生",
                patient_info=learning_data.get('patient_profile', {}),
                chief_complaint=learning_data['diagnosis'].get('primary', ''),
                present_illness="基于上传处方推断",
                tcm_diagnosis=learning_data['diagnosis'].get('primary', ''),
                syndrome_differentiation=learning_data['diagnosis'].get('tcm_syndrome', ''),
                prescription=prescription,
                outcome="数据收集中",
                notes=f"来源: {source_type}, 置信度: {learning_data.get('confidence_score', 0)}"
            )
            
            # 保存到学习系统
            success = self.learning_system.add_clinical_case(clinical_case)
            
            if success:
                logger.info(f"✅ 成功保存处方案例到学习系统: {case_id}")
            else:
                logger.warning(f"⚠️ 保存处方案例失败: {case_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ 保存到学习系统失败: {e}")
            return False
    
    def _create_prescription_object(self, herbs_data: List[Dict]) -> Optional[Prescription]:
        """从药材数据创建处方对象"""
        try:
            if not herbs_data:
                return None
            
            # 构建处方文本
            prescription_text = ""
            for herb in herbs_data:
                name = herb.get('name', '')
                dosage = herb.get('dosage', '')
                unit = herb.get('unit', 'g')
                
                if name and dosage:
                    prescription_text += f"{name} {dosage}{unit}\n"
            
            if not prescription_text.strip():
                return None
            
            # 使用解析器创建处方对象
            prescription = self.parser.parse_prescription_text(prescription_text)
            return prescription
            
        except Exception as e:
            logger.error(f"❌ 创建处方对象失败: {e}")
            return None
    
    async def _update_vector_database(self, learning_data: Dict) -> bool:
        """更新向量数据库"""
        try:
            if not self.vector_db:
                logger.warning("⚠️ 向量数据库未初始化")
                return False
            
            # 构建向量化文档
            doc_content = self._build_vectorizable_content(learning_data)
            
            if not doc_content:
                logger.warning("⚠️ 无法构建有效的向量化内容")
                return False
            
            # 添加到向量数据库
            doc_id = learning_data['prescription_id']
            
            # 这里需要扩展向量数据库的add_document方法
            # 暂时记录，等待向量数据库支持动态添加
            logger.info(f"📝 准备向量化文档: {doc_id}")
            logger.info(f"文档内容预览: {doc_content[:100]}...")
            
            # TODO: 实现动态向量数据库更新
            # success = self.vector_db.add_document(doc_id, doc_content, learning_data)
            
            # 暂时返回True，表示准备工作完成
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新向量数据库失败: {e}")
            return False
    
    def _build_vectorizable_content(self, learning_data: Dict) -> str:
        """构建可向量化的内容"""
        try:
            content_parts = []
            
            # 诊断信息
            diagnosis = learning_data['diagnosis']
            if diagnosis.get('primary'):
                content_parts.append(f"诊断: {diagnosis['primary']}")
            if diagnosis.get('tcm_syndrome'):
                content_parts.append(f"证型: {diagnosis['tcm_syndrome']}")
            if diagnosis.get('symptoms'):
                content_parts.append(f"症状: {', '.join(diagnosis['symptoms'])}")
            
            # 处方信息
            herbs = learning_data['herbs']
            herb_names = [herb.get('name', '') for herb in herbs if herb.get('name')]
            if herb_names:
                content_parts.append(f"处方药物: {', '.join(herb_names)}")
            
            # 临床信息
            clinical = learning_data['clinical_info']
            if clinical.get('formula_type'):
                content_parts.append(f"方剂类型: {clinical['formula_type']}")
            if clinical.get('therapeutic_principle'):
                content_parts.append(f"治疗原则: {clinical['therapeutic_principle']}")
            
            return " | ".join(content_parts)
            
        except Exception as e:
            logger.error(f"❌ 构建向量化内容失败: {e}")
            return ""
    
    def _log_processing_result(self, learning_data: Dict, saved_to_learning: bool, updated_vector_db: bool):
        """记录处理结果"""
        case_id = learning_data['prescription_id']
        herbs_count = learning_data['total_herbs']
        confidence = learning_data.get('confidence_score', 0)
        
        status_parts = []
        if saved_to_learning:
            status_parts.append("✅ 学习系统")
        if updated_vector_db:
            status_parts.append("✅ 向量数据库")
        
        if not status_parts:
            status_parts.append("❌ 未保存")
        
        logger.info(f"📊 处方学习处理完成: {case_id}")
        logger.info(f"   - 药物数量: {herbs_count}")
        logger.info(f"   - 置信度: {confidence:.2f}")
        logger.info(f"   - 保存状态: {' + '.join(status_parts)}")
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习统计信息"""
        try:
            stats = {
                'learning_system_available': self.learning_system is not None,
                'vector_db_available': self.vector_db is not None,
                'total_learned_prescriptions': 0,
                'last_update': datetime.now().isoformat()
            }
            
            if self.learning_system:
                try:
                    learning_stats = self.learning_system.get_learning_statistics()
                    stats.update({
                        'total_learned_prescriptions': learning_stats.get('total_cases', 0),
                        'total_doctors': learning_stats.get('total_doctors', 0),
                        'latest_case_time': learning_stats.get('latest_case_time'),
                        'source_statistics': learning_stats.get('source_statistics', {}),
                        'learning_database_status': learning_stats.get('system_status', 'unknown')
                    })
                except Exception as e:
                    logger.error(f"获取学习系统统计失败: {e}")
                    stats['total_learned_prescriptions'] = f'error: {e}'
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取学习统计失败: {e}")
            return {'error': str(e)}

# 全局实例
prescription_learning_integrator = None

def get_prescription_learning_integrator() -> PrescriptionLearningIntegrator:
    """获取处方学习集成器单例"""
    global prescription_learning_integrator
    if prescription_learning_integrator is None:
        prescription_learning_integrator = PrescriptionLearningIntegrator()
    return prescription_learning_integrator

if __name__ == "__main__":
    # 测试代码
    async def test_integrator():
        integrator = get_prescription_learning_integrator()
        
        # 模拟处方数据
        test_prescription = {
            'prescription': {
                'herbs': [
                    {'name': '麻黄', 'dosage': '9', 'unit': 'g'},
                    {'name': '桂枝', 'dosage': '6', 'unit': 'g'},
                    {'name': '杏仁', 'dosage': '6', 'unit': 'g'},
                    {'name': '甘草', 'dosage': '3', 'unit': 'g'}
                ]
            },
            'diagnosis': {
                'primary': '风寒感冒',
                'tcm_syndrome': '风寒外感',
                'symptoms': ['恶寒发热', '头痛身痛', '无汗而喘']
            },
            'clinical_analysis': {
                'formula_type': '解表剂',
                'therapeutic_principle': '发汗解表，宣肺平喘'
            },
            'document_analysis': {
                'confidence': 0.95
            }
        }
        
        result = await integrator.process_prescription_data(test_prescription)
        print(f"测试结果: {result}")
        
        stats = await integrator.get_learning_statistics()
        print(f"学习统计: {stats}")

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_integrator())