#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗安全处理模块
从chat_with_ai_endpoint函数中提取的医疗安全验证相关功能
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..utils.common_utils import safe_execute, get_current_timestamp_iso
from ..utils.text_utils import extract_herb_names, has_medical_keywords, validate_prescription_format

logger = logging.getLogger(__name__)

class MedicalSafetyProcessor:
    """医疗安全处理器"""
    
    def __init__(self, db_manager, config_manager):
        self.db_manager = db_manager
        self.config = config_manager
        
        # 安全检查配置
        self.safety_config = {
            'enable_drug_interaction_check': True,
            'enable_contraindication_check': True,
            'enable_dosage_check': True,
            'enable_pregnancy_check': True,
            'max_daily_herbs': 15,
            'max_herb_dosage': {'单味': 30, '有毒': 10, '峻烈': 15},
            'forbidden_combinations': self._load_forbidden_combinations(),
            'high_risk_herbs': self._load_high_risk_herbs()
        }
        
        # 风险等级定义
        self.risk_levels = {
            'low': {'score': 1, 'color': 'green', 'action': '可以使用'},
            'medium': {'score': 2, 'color': 'yellow', 'action': '谨慎使用'},
            'high': {'score': 3, 'color': 'orange', 'action': '需要监控'},
            'critical': {'score': 4, 'color': 'red', 'action': '禁止使用'}
        }
        
        # 特殊人群标识
        self.special_populations = {
            'pregnant': '孕妇',
            'lactating': '哺乳期',
            'pediatric': '儿童',
            'elderly': '老年人',
            'chronic_disease': '慢性病患者'
        }
    
    def perform_comprehensive_safety_check(self, prescription_text: str, 
                                         user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行综合安全检查"""
        safety_result = {
            'overall_risk_level': 'low',
            'overall_risk_score': 0,
            'safety_passed': True,
            'checks_performed': [],
            'warnings': [],
            'contraindications': [],
            'recommendations': [],
            'prescription_analysis': {},
            'user_specific_risks': []
        }
        
        try:
            # 处方格式验证
            format_check = self._check_prescription_format(prescription_text)
            safety_result['checks_performed'].append('处方格式检查')
            
            if not format_check['valid']:
                safety_result['warnings'].append(f"处方格式问题: {format_check['error']}")
                safety_result['overall_risk_score'] += 1
            
            # 提取处方成分
            prescription_analysis = self._analyze_prescription_components(prescription_text)
            safety_result['prescription_analysis'] = prescription_analysis
            
            # 药物相互作用检查
            if self.safety_config['enable_drug_interaction_check']:
                interaction_check = self._check_drug_interactions(prescription_analysis['herbs'])
                safety_result['checks_performed'].append('药物相互作用检查')
                
                if interaction_check['has_interactions']:
                    safety_result['warnings'].extend(interaction_check['warnings'])
                    safety_result['overall_risk_score'] += interaction_check['risk_score']
            
            # 禁忌检查
            if self.safety_config['enable_contraindication_check']:
                contraindication_check = self._check_contraindications(
                    prescription_analysis['herbs'], 
                    user_profile
                )
                safety_result['checks_performed'].append('禁忌症检查')
                
                if contraindication_check['has_contraindications']:
                    safety_result['contraindications'].extend(contraindication_check['contraindications'])
                    safety_result['overall_risk_score'] += contraindication_check['risk_score']
            
            # 剂量安全检查
            if self.safety_config['enable_dosage_check']:
                dosage_check = self._check_dosage_safety(prescription_analysis['herbs'])
                safety_result['checks_performed'].append('剂量安全检查')
                
                if dosage_check['has_issues']:
                    safety_result['warnings'].extend(dosage_check['warnings'])
                    safety_result['overall_risk_score'] += dosage_check['risk_score']
            
            # 孕妇安全检查
            if user_profile and user_profile.get('is_pregnant') and self.safety_config['enable_pregnancy_check']:
                pregnancy_check = self._check_pregnancy_safety(prescription_analysis['herbs'])
                safety_result['checks_performed'].append('妊娠期安全检查')
                
                if pregnancy_check['has_risks']:
                    safety_result['contraindications'].extend(pregnancy_check['contraindications'])
                    safety_result['overall_risk_score'] += pregnancy_check['risk_score']
            
            # 特殊人群风险评估
            if user_profile:
                special_risks = self._assess_special_population_risks(
                    prescription_analysis['herbs'], 
                    user_profile
                )
                safety_result['user_specific_risks'] = special_risks
                safety_result['overall_risk_score'] += sum(r['risk_score'] for r in special_risks)
            
            # 确定整体风险等级
            safety_result['overall_risk_level'] = self._determine_risk_level(safety_result['overall_risk_score'])
            
            # 判断是否通过安全检查
            if safety_result['overall_risk_level'] in ['critical']:
                safety_result['safety_passed'] = False
            elif safety_result['overall_risk_level'] in ['high'] and len(safety_result['contraindications']) > 0:
                safety_result['safety_passed'] = False
            
            # 生成安全建议
            safety_result['recommendations'] = self._generate_safety_recommendations(safety_result)
            
        except Exception as e:
            logger.error(f"安全检查失败: {e}")
            safety_result['warnings'].append(f"安全检查过程出错: {str(e)}")
            safety_result['overall_risk_level'] = 'high'
            safety_result['safety_passed'] = False
        
        return safety_result
    
    def _check_prescription_format(self, prescription_text: str) -> Dict[str, Any]:
        """检查处方格式"""
        return validate_prescription_format(prescription_text)
    
    def _analyze_prescription_components(self, prescription_text: str) -> Dict[str, Any]:
        """分析处方成分"""
        analysis = {
            'herbs': [],
            'total_herbs': 0,
            'total_daily_dose': 0,
            'herb_categories': {},
            'preparation_methods': []
        }
        
        try:
            # 提取药材和用量
            from ..utils.text_utils import extract_dosage_info
            dosage_info = extract_dosage_info(prescription_text)
            
            analysis['herbs'] = dosage_info['herbs']
            analysis['total_herbs'] = dosage_info['total_herbs']
            
            # 计算总日剂量
            total_dose = sum(herb['dosage'] for herb in analysis['herbs'])
            analysis['total_daily_dose'] = total_dose
            
            # 分类药材
            for herb in analysis['herbs']:
                herb_name = herb['name']
                category = self._get_herb_category(herb_name)
                
                if category not in analysis['herb_categories']:
                    analysis['herb_categories'][category] = []
                analysis['herb_categories'][category].append(herb_name)
                
                # 添加额外的药材信息
                herb.update(self._get_herb_properties(herb_name))
            
            # 提取制法信息
            preparation_methods = re.findall(r'(水煎|冲服|研末|外用)', prescription_text)
            analysis['preparation_methods'] = list(set(preparation_methods))
            
        except Exception as e:
            logger.error(f"处方成分分析失败: {e}")
        
        return analysis
    
    def _check_drug_interactions(self, herbs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查药物相互作用"""
        interaction_result = {
            'has_interactions': False,
            'warnings': [],
            'risk_score': 0,
            'interaction_pairs': []
        }
        
        try:
            # 检查已知的药物配伍禁忌
            herb_names = [herb['name'] for herb in herbs]
            
            for i, herb1 in enumerate(herb_names):
                for j, herb2 in enumerate(herb_names[i+1:], i+1):
                    interaction = self._check_herb_pair_interaction(herb1, herb2)
                    
                    if interaction['has_interaction']:
                        interaction_result['has_interactions'] = True
                        interaction_result['interaction_pairs'].append({
                            'herb1': herb1,
                            'herb2': herb2,
                            'interaction_type': interaction['type'],
                            'severity': interaction['severity'],
                            'description': interaction['description']
                        })
                        
                        warning_msg = f"{herb1}与{herb2}存在{interaction['type']}相互作用: {interaction['description']}"
                        interaction_result['warnings'].append(warning_msg)
                        
                        # 根据严重程度调整风险评分
                        severity_scores = {'轻微': 1, '中度': 2, '严重': 3, '禁用': 4}
                        interaction_result['risk_score'] += severity_scores.get(interaction['severity'], 2)
            
        except Exception as e:
            logger.error(f"药物相互作用检查失败: {e}")
            interaction_result['warnings'].append("药物相互作用检查出现错误")
            interaction_result['risk_score'] += 1
        
        return interaction_result
    
    def _check_herb_pair_interaction(self, herb1: str, herb2: str) -> Dict[str, Any]:
        """检查两味药材的相互作用"""
        # 检查十八反、十九畏等配伍禁忌
        forbidden_pairs = self.safety_config.get('forbidden_combinations', {})
        
        # 标准化药材名称
        herb1_normalized = self._normalize_herb_name(herb1)
        herb2_normalized = self._normalize_herb_name(herb2)
        
        # 检查是否在禁忌组合中
        pair_key1 = f"{herb1_normalized}-{herb2_normalized}"
        pair_key2 = f"{herb2_normalized}-{herb1_normalized}"
        
        if pair_key1 in forbidden_pairs:
            return forbidden_pairs[pair_key1]
        elif pair_key2 in forbidden_pairs:
            return forbidden_pairs[pair_key2]
        
        # 检查药性冲突
        herb1_properties = self._get_herb_properties(herb1)
        herb2_properties = self._get_herb_properties(herb2)
        
        # 寒热冲突检查
        if (herb1_properties.get('nature') == '大寒' and herb2_properties.get('nature') == '大热') or \
           (herb1_properties.get('nature') == '大热' and herb2_properties.get('nature') == '大寒'):
            return {
                'has_interaction': True,
                'type': '药性冲突',
                'severity': '中度',
                'description': '寒热药性相反，可能影响药效'
            }
        
        return {'has_interaction': False}
    
    def _check_contraindications(self, herbs: List[Dict[str, Any]], 
                               user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查禁忌症"""
        contraindication_result = {
            'has_contraindications': False,
            'contraindications': [],
            'risk_score': 0
        }
        
        try:
            for herb in herbs:
                herb_name = herb['name']
                herb_contraindications = self._get_herb_contraindications(herb_name)
                
                # 一般禁忌症
                for contraindication in herb_contraindications.get('general', []):
                    contraindication_result['contraindications'].append({
                        'herb': herb_name,
                        'type': '一般禁忌',
                        'description': contraindication,
                        'severity': '中度'
                    })
                    contraindication_result['risk_score'] += 2
                
                # 特殊人群禁忌
                if user_profile:
                    for population, description in self.special_populations.items():
                        if user_profile.get(population) and herb_contraindications.get(population):
                            contraindication_result['contraindications'].append({
                                'herb': herb_name,
                                'type': f'{description}禁用',
                                'description': herb_contraindications[population],
                                'severity': '严重'
                            })
                            contraindication_result['risk_score'] += 3
                
                # 疾病禁忌
                user_conditions = user_profile.get('medical_conditions', []) if user_profile else []
                for condition in user_conditions:
                    if condition in herb_contraindications.get('conditions', {}):
                        contraindication_result['contraindications'].append({
                            'herb': herb_name,
                            'type': '疾病禁忌',
                            'description': herb_contraindications['conditions'][condition],
                            'severity': '严重'
                        })
                        contraindication_result['risk_score'] += 3
            
            contraindication_result['has_contraindications'] = len(contraindication_result['contraindications']) > 0
            
        except Exception as e:
            logger.error(f"禁忌症检查失败: {e}")
            contraindication_result['contraindications'].append({
                'herb': '未知',
                'type': '检查错误',
                'description': f"禁忌症检查过程出错: {str(e)}",
                'severity': '中度'
            })
            contraindication_result['risk_score'] += 1
        
        return contraindication_result
    
    def _check_dosage_safety(self, herbs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查剂量安全性"""
        dosage_result = {
            'has_issues': False,
            'warnings': [],
            'risk_score': 0
        }
        
        try:
            # 检查单味药材剂量
            for herb in herbs:
                herb_name = herb['name']
                dosage = herb['dosage']
                
                # 获取药材安全剂量范围
                safe_range = self._get_herb_safe_dosage(herb_name)
                
                if dosage > safe_range['max']:
                    dosage_result['warnings'].append(
                        f"{herb_name} 用量{dosage}g超过安全上限({safe_range['max']}g)"
                    )
                    dosage_result['risk_score'] += 2
                    dosage_result['has_issues'] = True
                
                elif dosage < safe_range['min']:
                    dosage_result['warnings'].append(
                        f"{herb_name} 用量{dosage}g低于有效剂量({safe_range['min']}g)"
                    )
                    dosage_result['risk_score'] += 1
                    dosage_result['has_issues'] = True
                
                # 特殊药材剂量检查
                if herb_name in self.safety_config['high_risk_herbs']:
                    risk_info = self.safety_config['high_risk_herbs'][herb_name]
                    if dosage > risk_info.get('max_dosage', 10):
                        dosage_result['warnings'].append(
                            f"{herb_name} 为{risk_info['risk_type']}药材，用量{dosage}g超过安全限制"
                        )
                        dosage_result['risk_score'] += 3
                        dosage_result['has_issues'] = True
            
            # 检查总剂量
            total_herbs = len(herbs)
            if total_herbs > self.safety_config['max_daily_herbs']:
                dosage_result['warnings'].append(
                    f"处方药味过多({total_herbs}味)，超过建议上限({self.safety_config['max_daily_herbs']}味)"
                )
                dosage_result['risk_score'] += 1
                dosage_result['has_issues'] = True
            
        except Exception as e:
            logger.error(f"剂量安全检查失败: {e}")
            dosage_result['warnings'].append("剂量安全检查出现错误")
            dosage_result['risk_score'] += 1
            dosage_result['has_issues'] = True
        
        return dosage_result
    
    def _check_pregnancy_safety(self, herbs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查妊娠期安全性"""
        pregnancy_result = {
            'has_risks': False,
            'contraindications': [],
            'risk_score': 0
        }
        
        # 妊娠禁用药材列表
        pregnancy_forbidden = [
            '附子', '川乌', '草乌', '巴豆', '大戟', '芫花', '甘遂',
            '商陆', '斑蝥', '蜈蚣', '水蛭', '虻虫', '干漆', '麝香',
            '红花', '桃仁', '牛膝', '薏苡仁', '王不留行'
        ]
        
        # 妊娠慎用药材列表
        pregnancy_caution = [
            '当归尾', '川芎', '桃仁', '红花', '牛膝', '薏苡仁',
            '厚朴', '枳壳', '大黄', '芒硝'
        ]
        
        try:
            for herb in herbs:
                herb_name = self._normalize_herb_name(herb['name'])
                
                if herb_name in pregnancy_forbidden:
                    pregnancy_result['contraindications'].append({
                        'herb': herb['name'],
                        'type': '妊娠禁用',
                        'description': '该药材妊娠期绝对禁用，可能导致流产或胎儿畸形',
                        'severity': '禁用'
                    })
                    pregnancy_result['risk_score'] += 4
                    pregnancy_result['has_risks'] = True
                
                elif herb_name in pregnancy_caution:
                    pregnancy_result['contraindications'].append({
                        'herb': herb['name'],
                        'type': '妊娠慎用',
                        'description': '该药材妊娠期需谨慎使用，建议在医师指导下使用',
                        'severity': '严重'
                    })
                    pregnancy_result['risk_score'] += 2
                    pregnancy_result['has_risks'] = True
            
        except Exception as e:
            logger.error(f"妊娠安全检查失败: {e}")
            pregnancy_result['contraindications'].append({
                'herb': '未知',
                'type': '检查错误',
                'description': '妊娠安全检查出现错误',
                'severity': '中度'
            })
            pregnancy_result['risk_score'] += 1
            pregnancy_result['has_risks'] = True
        
        return pregnancy_result
    
    def _assess_special_population_risks(self, herbs: List[Dict[str, Any]], 
                                       user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估特殊人群风险"""
        risks = []
        
        try:
            # 老年人用药风险
            if user_profile.get('age', 0) >= 65:
                for herb in herbs:
                    if herb['dosage'] > 15:  # 老年人一般需要减量
                        risks.append({
                            'population': '老年人',
                            'herb': herb['name'],
                            'risk_type': '剂量风险',
                            'description': '老年人代谢能力下降，建议减量使用',
                            'risk_score': 1
                        })
            
            # 儿童用药风险
            if user_profile.get('age', 0) < 12:
                for herb in herbs:
                    herb_properties = self._get_herb_properties(herb['name'])
                    if herb_properties.get('toxicity', 'low') in ['medium', 'high']:
                        risks.append({
                            'population': '儿童',
                            'herb': herb['name'],
                            'risk_type': '毒性风险',
                            'description': '儿童对该药材较敏感，需严格控制剂量',
                            'risk_score': 2
                        })
            
            # 慢性病患者用药风险
            chronic_conditions = user_profile.get('medical_conditions', [])
            for condition in chronic_conditions:
                condition_risks = self._get_condition_specific_risks(herbs, condition)
                risks.extend(condition_risks)
            
        except Exception as e:
            logger.error(f"特殊人群风险评估失败: {e}")
        
        return risks
    
    def _determine_risk_level(self, risk_score: int) -> str:
        """确定风险等级"""
        if risk_score >= 10:
            return 'critical'
        elif risk_score >= 6:
            return 'high'
        elif risk_score >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _generate_safety_recommendations(self, safety_result: Dict[str, Any]) -> List[str]:
        """生成安全建议"""
        recommendations = []
        
        risk_level = safety_result['overall_risk_level']
        
        if risk_level == 'critical':
            recommendations.append("该处方存在严重安全风险，建议重新调整处方")
            recommendations.append("请在专业医师指导下用药")
        
        elif risk_level == 'high':
            recommendations.append("该处方存在较高风险，需要密切监控")
            recommendations.append("建议定期复诊，观察用药反应")
        
        elif risk_level == 'medium':
            recommendations.append("该处方整体安全，但需注意相关警告")
            recommendations.append("如出现不适症状，请及时就医")
        
        else:
            recommendations.append("该处方安全性良好")
            recommendations.append("请按医嘱正确服用")
        
        # 针对性建议
        if safety_result.get('contraindications'):
            recommendations.append("特别注意处方中的禁忌药材")
        
        if safety_result.get('warnings'):
            recommendations.append("请关注剂量和用药方法")
        
        # 添加通用建议
        recommendations.extend([
            "服药期间避免辛辣、生冷食物",
            "如有过敏史，请提前告知医师",
            "保持处方药材的质量和来源可靠"
        ])
        
        return recommendations[:5]  # 限制建议数量
    
    # 辅助方法
    def _normalize_herb_name(self, herb_name: str) -> str:
        """标准化药材名称"""
        # 移除常见的修饰词
        modifiers = ['生', '炒', '蜜炙', '酒制', '醋制', '盐制', '制']
        normalized = herb_name
        for modifier in modifiers:
            normalized = normalized.replace(modifier, '')
        return normalized.strip()
    
    def _get_herb_category(self, herb_name: str) -> str:
        """获取药材分类"""
        # 简化的分类逻辑，实际应该查询数据库
        herb_categories = {
            '补益': ['人参', '黄芪', '当归', '熟地黄', '枸杞子'],
            '清热': ['黄连', '黄芩', '栀子', '连翘', '金银花'],
            '理气': ['陈皮', '木香', '香附', '柴胡', '枳壳'],
            '活血': ['川芎', '红花', '桃仁', '丹参', '牛膝'],
            '化痰': ['半夏', '陈皮', '茯苓', '白术', '苍术']
        }
        
        for category, herbs in herb_categories.items():
            if any(h in herb_name for h in herbs):
                return category
        return '其他'
    
    def _get_herb_properties(self, herb_name: str) -> Dict[str, Any]:
        """获取药材属性"""
        # 简化实现，实际应该查询完整的药材数据库
        return {
            'nature': '平',
            'flavor': '甘',
            'meridian': '脾胃',
            'toxicity': 'low',
            'category': self._get_herb_category(herb_name)
        }
    
    def _get_herb_contraindications(self, herb_name: str) -> Dict[str, Any]:
        """获取药材禁忌症"""
        # 简化实现，实际应该查询完整的禁忌症数据库
        return {
            'general': [],
            'pregnant': None,
            'lactating': None,
            'pediatric': None,
            'elderly': None,
            'conditions': {}
        }
    
    def _get_herb_safe_dosage(self, herb_name: str) -> Dict[str, int]:
        """获取药材安全剂量范围"""
        # 简化实现，实际应该查询完整的剂量数据库
        return {'min': 3, 'max': 15}
    
    def _get_condition_specific_risks(self, herbs: List[Dict[str, Any]], 
                                    condition: str) -> List[Dict[str, Any]]:
        """获取疾病特异性风险"""
        risks = []
        # 简化实现，实际应该有完整的疾病-药材风险数据库
        return risks
    
    def _load_forbidden_combinations(self) -> Dict[str, Dict[str, Any]]:
        """加载禁忌配伍组合"""
        # 十八反配伍禁忌
        forbidden_combinations = {
            '甘草-甘遂': {
                'has_interaction': True,
                'type': '十八反',
                'severity': '禁用',
                'description': '甘草反甘遂，禁忌配伍'
            },
            '乌头-半夏': {
                'has_interaction': True,
                'type': '十八反',
                'severity': '禁用',
                'description': '乌头反半夏，禁忌配伍'
            }
            # 实际应该包含完整的十八反、十九畏配伍禁忌
        }
        return forbidden_combinations
    
    def _load_high_risk_herbs(self) -> Dict[str, Dict[str, Any]]:
        """加载高风险药材列表"""
        high_risk_herbs = {
            '附子': {
                'risk_type': '有毒',
                'max_dosage': 10,
                'special_preparation': '需要炮制',
                'monitoring_required': True
            },
            '川乌': {
                'risk_type': '有毒',
                'max_dosage': 6,
                'special_preparation': '需要炮制',
                'monitoring_required': True
            }
            # 实际应该包含完整的有毒、峻烈药材列表
        }
        return high_risk_herbs