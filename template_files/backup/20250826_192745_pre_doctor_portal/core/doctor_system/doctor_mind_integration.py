# doctor_mind_integration.py - 医生思维系统集成接口

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict

import sys
sys.path.append('/opt/tcm-ai')
from core.doctor_system.doctor_thinking_patterns import (
    DoctorMindDatabase, 
    PrescriptionLogicEngine,
    ThinkingPatternLearner,
    CaseExample,
    DoctorThinkingPattern
)
from core.doctor_system.tcm_doctor_personas import TCMDoctorPersonas, PersonalizedTreatmentGenerator

logger = logging.getLogger(__name__)

class EnhancedPersonalizedTreatmentGenerator:
    """增强的个性化治疗生成器 - 集成思维决策树"""
    
    def __init__(self, mind_database_path: str = "./doctor_minds.pkl"):
        # 原有的流派系统
        self.traditional_personas = TCMDoctorPersonas()
        self.traditional_generator = PersonalizedTreatmentGenerator()
        
        # 新的思维决策树系统
        self.mind_database = DoctorMindDatabase(mind_database_path)
        self.logic_engine = PrescriptionLogicEngine(self.mind_database)
        
        # 疾病类别映射
        self.disease_mapping = {
            "感冒": "外感病",
            "发热": "外感病", 
            "咳嗽": "肺系病",
            "失眠": "神志病",
            "胃痛": "脾胃病",
            "腹泻": "脾胃病",
            "便秘": "脾胃病",
            "头痛": "头面病",
            "心悸": "心系病"
        }
        
        logger.info("增强个性化治疗生成器初始化完成")
    
    def generate_prescription(self, user_query: str, selected_doctor: str, 
                            patient_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成处方 - 优先使用思维决策树，回退到传统流派"""
        
        # 提取疾病类别
        disease_category = self._extract_disease_category(user_query)
        
        # 尝试获取医生的思维模式
        thinking_pattern = self.mind_database.get_thinking_pattern(selected_doctor, disease_category)
        
        if thinking_pattern and patient_data:
            # 使用思维决策树生成处方
            logger.info(f"使用 {selected_doctor} 的思维决策树生成处方")
            return self._generate_with_decision_tree(thinking_pattern, patient_data, user_query)
        else:
            # 回退到传统流派系统
            logger.info(f"回退到传统流派系统: {selected_doctor}")
            return self._generate_with_traditional_system(selected_doctor, user_query)
    
    def _generate_with_decision_tree(self, pattern: DoctorThinkingPattern, 
                                   patient_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """使用思维决策树生成处方"""
        try:
            # 从用户查询和对话历史中提取症状信息 (已修复性能问题)
            extracted_symptoms = self._extract_symptoms_from_query_with_history(user_query, patient_data)
            
            # 合并症状数据
            combined_data = {**patient_data, **extracted_symptoms}
            
            # 使用思维模式预测处方
            prescription_result = pattern.predict_prescription(combined_data)
            
            # 转换为统一格式
            return {
                "method": "decision_tree",
                "doctor_name": pattern.doctor_name,
                "disease_category": pattern.disease_category,
                "prescription": prescription_result.get("prescription", {}),
                "reasoning_path": prescription_result.get("reasoning_path", []),
                "confidence_score": prescription_result.get("confidence_score", 0.0),
                "formatted_response": self._format_decision_tree_response(prescription_result)
            }
            
        except Exception as e:
            logger.error(f"思维决策树处方生成失败: {e}")
            return self._generate_with_traditional_system(pattern.doctor_id, user_query)
    
    def _generate_with_traditional_system(self, selected_doctor: str, user_query: str) -> Dict[str, Any]:
        """使用传统流派系统生成处方"""
        try:
            # 使用原有的个性化提示词系统
            persona_prompt = self.traditional_generator.generate_persona_prompt(
                selected_doctor, user_query, ""
            )
            
            return {
                "method": "traditional_persona",
                "doctor_id": selected_doctor,
                "persona_prompt": persona_prompt,
                "formatted_response": f"采用{selected_doctor}流派的诊疗思路，请基于以下指导进行诊疗：\n\n{persona_prompt}"
            }
            
        except Exception as e:
            logger.error(f"传统流派系统处方生成失败: {e}")
            return {"error": f"处方生成失败: {str(e)}"}
    
    def _extract_disease_category(self, user_query: str) -> str:
        """从用户查询中提取疾病类别"""
        for keyword, category in self.disease_mapping.items():
            if keyword in user_query:
                return category
        
        # 默认分类逻辑 - 优先级从高到低
        # 温病症状优先检查（避免与外感病混淆）
        if any(word in user_query for word in ["口渴", "咽痛", "温病", "热病", "身热"]) and "发热" in user_query:
            return "温病"
        elif any(word in user_query for word in ["胃痛", "腹痛", "腹泻", "便秘", "食欲不振", "腹胀", "乏力", "脾虚", "胃胀", "消化不良", "大便溏", "便溏"]):
            return "脾胃病"
        elif any(word in user_query for word in ["失眠", "多梦", "健忘", "心悸", "焦虑", "抑郁"]):
            return "神志病"
        elif any(word in user_query for word in ["咳嗽", "气喘", "胸闷", "哮喘", "肺炎"]):
            return "肺系病"
        elif any(word in user_query for word in ["发热", "恶寒", "头痛", "鼻塞", "感冒", "风寒", "风热"]):
            return "外感病"
        else:
            return "其他"
    
    def _extract_symptoms_from_query(self, user_query: str) -> Dict[str, Any]:
        """从用户查询中提取症状 - 严格防止医疗信息幻觉"""
        symptoms = {}
        
        # 常见症状关键词映射
        symptom_keywords = {
            "头痛": ["头痛", "头疼", "脑袋疼"],
            "发热": ["发热", "发烧", "身热", "高热"],
            "恶寒": ["恶寒", "怕冷", "畏寒"],
            "咳嗽": ["咳嗽", "咳", "干咳"],
            "失眠": ["失眠", "睡不着", "不寐", "多梦"],
            "胃痛": ["胃痛", "胃疼", "胃部不适"],
            "腹泻": ["腹泻", "拉肚子", "大便溏"],
            "便秘": ["便秘", "大便干", "排便难"],
            "心悸": ["心悸", "心慌", "心跳快"]
        }
        
        # 脉象和舌象关键词（仅当患者明确提及时才提取）
        pulse_keywords = {
            "脉浮": ["脉浮", "浮脉"],
            "脉沉": ["脉沉", "沉脉"],
            "脉数": ["脉数", "数脉", "脉快"],
            "脉迟": ["脉迟", "迟脉", "脉慢"]
        }
        
        tongue_keywords = {
            "舌红": ["舌红", "舌质红"],
            "舌淡": ["舌淡", "舌质淡"],
            "苔白": ["苔白", "舌苔白"],
            "苔黄": ["苔黄", "舌苔黄"]
        }
        
        # 检查基本症状（始终检查）
        for symptom, keywords in symptom_keywords.items():
            symptoms[symptom] = any(keyword in user_query for keyword in keywords)
        
        # 【关键修复】仅当患者明确提及脉象时才提取脉象信息
        # 避免AI幻觉：不在没有描述的情况下假设脉象特征
        for pulse, keywords in pulse_keywords.items():
            if any(keyword in user_query for keyword in keywords):
                symptoms[pulse] = True
                logger.info(f"检测到患者明确描述的脉象信息: {pulse}")
        
        # 【关键修复】仅当患者明确提及舌象时才提取舌象信息  
        # 避免AI幻觉：不在没有舌象图片或描述的情况下假设舌象特征
        for tongue, keywords in tongue_keywords.items():
            if any(keyword in user_query for keyword in keywords):
                symptoms[tongue] = True
                logger.info(f"检测到患者明确描述的舌象信息: {tongue}")
        
        # 记录提取结果，用于调试
        extracted_count = sum(1 for v in symptoms.values() if v)
        logger.info(f"从用户查询中提取了 {extracted_count} 个症状特征")
        
        return symptoms
    
    def _extract_symptoms_from_query_with_history(self, user_query: str, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """从用户查询和对话历史中提取症状信息 - 优化版本避免调用栈溢出"""
        symptoms = {}
        
        # 1. 从当前查询中提取症状
        current_symptoms = self._extract_symptoms_from_query(user_query)
        symptoms.update(current_symptoms)
        
        # 2. 从对话历史中提取症状信息 (限制处理数量和文本长度)
        conversation_history = patient_data.get("conversation_history", [])
        if conversation_history:
            # 只处理最近的8条消息，进一步减少处理量
            recent_history = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
            logger.info(f"历史症状分析：共 {len(conversation_history)} 条消息，处理最近 {len(recent_history)} 条")
            
            # 简化的历史症状提取
            historical_symptoms = []
            total_length = 0
            max_total_length = 500  # 进一步减少限制，避免超长文本
            
            for message in reversed(recent_history):  # 从最新消息开始处理
                if message.get("role") == "user" and message.get("content"):
                    content = message["content"].strip()
                    if len(content) > 100:  # 跳过过长的单条消息
                        content = content[:100] + "..."
                    
                    if total_length + len(content) <= max_total_length:
                        historical_symptoms.append(content)
                        total_length += len(content)
                    else:
                        break
            
            # 从历史信息中提取关键症状
            if historical_symptoms:
                combined_text = " ".join(reversed(historical_symptoms))  # 恢复时间顺序
                historical_symptom_data = self._simple_symptom_extraction(combined_text)
                
                # 合并历史症状到当前症状中，避免覆盖
                for key, value in historical_symptom_data.items():
                    if key not in symptoms:
                        symptoms[key] = value
                    else:
                        # 如果已有症状，合并信息
                        if isinstance(symptoms[key], list) and isinstance(value, list):
                            symptoms[key] = list(set(symptoms[key] + value))
                
                logger.info(f"成功整合历史症状信息，避免重复询问")
        
        return symptoms
        
    def _simple_symptom_extraction(self, text: str) -> Dict[str, Any]:
        """简化的症状提取，避免复杂处理"""
        simple_symptoms = {}
        
        # 基础症状关键词检测
        symptom_keywords = {
            'pain': ['疼', '痛', '胀痛', '刺痛', '隐痛'],
            'digestive': ['食欲', '胃', '腹', '便秘', '腹泻', '消化'],
            'sleep': ['睡眠', '失眠', '多梦', '易醒'],
            'energy': ['疲劳', '乏力', '无力', '精神'],
            'temperature': ['怕冷', '怕热', '发热', '畏寒'],
            'tongue_pulse': ['舌苔', '舌质', '舌象', '脉象', '脉']
        }
        
        for category, keywords in symptom_keywords.items():
            found_symptoms = []
            for keyword in keywords:
                if keyword in text:
                    found_symptoms.append(keyword)
            if found_symptoms:
                simple_symptoms[category] = found_symptoms
        
        return simple_symptoms
    
    def _format_decision_tree_response(self, prescription_result: Dict[str, Any]) -> str:
        """格式化决策树响应"""
        response_parts = []
        
        # 添加医生信息
        response_parts.append(f"**医生**: {prescription_result.get('doctor_name', '未知')}")
        response_parts.append(f"**专业领域**: {prescription_result.get('disease_category', '通科')}")
        response_parts.append(f"**信心度**: {prescription_result.get('confidence_score', 0.0):.1%}")
        response_parts.append("")
        
        # 添加推理过程
        reasoning_path = prescription_result.get('reasoning_path', [])
        if reasoning_path:
            response_parts.append("**诊疗思路**:")
            for i, step in enumerate(reasoning_path, 1):
                response_parts.append(f"{i}. {step['description']} (信心度: {step['confidence']:.1%})")
                for action in step.get('actions', []):
                    response_parts.append(f"   - {action.get('reasoning', action.get('action_type', ''))}")
            response_parts.append("")
        
        # 添加处方信息
        prescription = prescription_result.get('prescription', {})
        if prescription:
            response_parts.append("**处方建议**:")
            
            if 'base_formula' in prescription:
                response_parts.append(f"- **基础方剂**: {prescription['base_formula']}")
            
            if 'additional_herbs' in prescription:
                response_parts.append("- **加减用药**:")
                for herb in prescription['additional_herbs']:
                    response_parts.append(f"  - {herb}")
            
            if 'dosage_modifications' in prescription:
                response_parts.append("- **剂量调整**:")
                for herb, dosage in prescription['dosage_modifications'].items():
                    response_parts.append(f"  - {herb}: {dosage}")
            
            if 'preparation_method' in prescription:
                response_parts.append(f"- **制备方法**: {prescription['preparation_method']}")
            
            if 'cautions' in prescription:
                response_parts.append("- **注意事项**:")
                for caution in prescription['cautions']:
                    response_parts.append(f"  - {caution}")
        
        return "\n".join(response_parts)
    
    def add_case_example(self, case_data: Dict[str, Any]) -> bool:
        """添加案例样本"""
        try:
            case = CaseExample(
                case_id=case_data.get('case_id', f"case_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                patient_symptoms=case_data.get('patient_symptoms', {}),
                doctor_reasoning=case_data.get('doctor_reasoning', []),
                final_prescription=case_data.get('final_prescription', {}),
                treatment_outcome=case_data.get('treatment_outcome', ''),
                success_rating=case_data.get('success_rating', 0.5),
                doctor_id=case_data.get('doctor_id', ''),
                disease_category=case_data.get('disease_category', ''),
                timestamp=datetime.now()
            )
            
            self.mind_database.add_case_example(case)
            logger.info(f"成功添加案例: {case.case_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加案例失败: {e}")
            return False
    
    def learn_doctor_patterns(self, doctor_id: str, doctor_name: str) -> Dict[str, Any]:
        """学习医生思维模式"""
        try:
            # 获取该医生的所有案例
            all_cases = [case for case in self.mind_database.case_database if case.doctor_id == doctor_id]
            
            if not all_cases:
                return {"success": False, "message": "没有找到该医生的案例"}
            
            # 学习新模式
            self.mind_database.learn_new_patterns(doctor_id, doctor_name)
            
            # 获取学习结果
            learned_patterns = self.mind_database.get_doctor_patterns(doctor_id)
            
            return {
                "success": True,
                "message": f"成功学习 {doctor_name} 的思维模式",
                "patterns_learned": list(learned_patterns.keys()),
                "total_cases": len(all_cases)
            }
            
        except Exception as e:
            logger.error(f"学习医生模式失败: {e}")
            return {"success": False, "message": f"学习失败: {str(e)}"}
    
    def recommend_doctors(self, user_query: str, patient_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """推荐最适合的医生"""
        try:
            disease_category = self._extract_disease_category(user_query)
            
            if not patient_data:
                patient_data = self._extract_symptoms_from_query(user_query)
            
            # 获取推荐
            recommendations = self.logic_engine.recommend_doctor(patient_data, disease_category)
            
            # 格式化推荐结果
            formatted_recommendations = []
            for doctor_id, suitability_score in recommendations:
                pattern = self.mind_database.get_thinking_pattern(doctor_id, disease_category)
                if pattern:
                    formatted_recommendations.append({
                        "doctor_id": doctor_id,
                        "doctor_name": pattern.doctor_name,
                        "disease_category": disease_category,
                        "suitability_score": suitability_score,
                        "pattern_accuracy": pattern.pattern_accuracy,
                        "case_count": pattern.case_count,
                        "specialty_area": pattern.specialty_area
                    })
            
            return formatted_recommendations
            
        except Exception as e:
            logger.error(f"医生推荐失败: {e}")
            return []
    
    def get_doctor_statistics(self) -> Dict[str, Any]:
        """获取医生统计信息"""
        stats = {
            "total_doctors": len(self.mind_database.thinking_patterns),
            "total_patterns": sum(len(patterns) for patterns in self.mind_database.thinking_patterns.values()),
            "total_cases": len(self.mind_database.case_database),
            "doctors_by_specialty": {},
            "patterns_by_disease": {}
        }
        
        # 统计专业分布
        for doctor_id, patterns in self.mind_database.thinking_patterns.items():
            for disease_category, pattern in patterns.items():
                specialty = pattern.specialty_area
                if specialty not in stats["doctors_by_specialty"]:
                    stats["doctors_by_specialty"][specialty] = 0
                stats["doctors_by_specialty"][specialty] += 1
                
                if disease_category not in stats["patterns_by_disease"]:
                    stats["patterns_by_disease"][disease_category] = 0
                stats["patterns_by_disease"][disease_category] += 1
        
        return stats

class DoctorMindAPI:
    """医生思维系统API接口"""
    
    def __init__(self, enhanced_generator: EnhancedPersonalizedTreatmentGenerator):
        self.generator = enhanced_generator
    
    def add_case_api(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """API: 添加案例"""
        success = self.generator.add_case_example(case_data)
        return {
            "success": success,
            "message": "案例添加成功" if success else "案例添加失败"
        }
    
    def learn_patterns_api(self, doctor_id: str, doctor_name: str) -> Dict[str, Any]:
        """API: 学习思维模式"""
        return self.generator.learn_doctor_patterns(doctor_id, doctor_name)
    
    def recommend_doctors_api(self, user_query: str, patient_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """API: 推荐医生"""
        recommendations = self.generator.recommend_doctors(user_query, patient_data)
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    
    def get_statistics_api(self) -> Dict[str, Any]:
        """API: 获取统计信息"""
        stats = self.generator.get_doctor_statistics()
        return {
            "success": True,
            "statistics": stats
        }
    
    def generate_prescription_api(self, user_query: str, selected_doctor: str, 
                                patient_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """API: 生成处方"""
        try:
            result = self.generator.generate_prescription(user_query, selected_doctor, patient_data)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def import_thinking_pattern_api(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """API: 直接导入医生思维模式"""
        try:
            from direct_thinking_import import DirectThinkingImporter
            
            # 创建导入器
            importer = DirectThinkingImporter(self.generator.mind_database)
            
            # 导入思维模式
            success = importer.import_thinking_pattern_from_structure(pattern_data)
            
            if success:
                return {
                    "success": True,
                    "message": f"成功导入 {pattern_data.get('doctor_name', '未知医生')} 关于 {pattern_data.get('disease_category', '未知疾病')} 的思维模式",
                    "doctor_id": pattern_data.get("doctor_id"),
                    "disease_category": pattern_data.get("disease_category")
                }
            else:
                return {
                    "success": False,
                    "message": "思维模式导入失败，请检查数据格式"
                }
                
        except Exception as e:
            logger.error(f"思维模式导入失败: {e}")
            return {
                "success": False,
                "message": f"导入失败: {str(e)}"
            }

# 示例使用
def demo_enhanced_system():
    """演示增强系统"""
    # 初始化系统
    enhanced_generator = EnhancedPersonalizedTreatmentGenerator()
    api = DoctorMindAPI(enhanced_generator)
    
    # 添加示例案例
    sample_case = {
        "case_id": "demo_001",
        "patient_symptoms": {
            "头痛": True,
            "发热": True,
            "恶寒": True,
            "脉浮": True
        },
        "doctor_reasoning": [
            "患者头痛发热，恶寒，脉浮",
            "辨证为太阳表证",
            "治以解表散寒"
        ],
        "final_prescription": {
            "formula": "麻黄汤",
            "herbs": {"麻黄": "6g", "桂枝": "9g", "杏仁": "9g", "甘草": "3g"}
        },
        "treatment_outcome": "症状缓解",
        "success_rating": 0.9,
        "doctor_id": "zhang_zhongjing_demo",
        "disease_category": "外感病"
    }
    
    # 添加案例
    result = api.add_case_api(sample_case)
    print(f"添加案例结果: {result}")
    
    # 学习模式
    learn_result = api.learn_patterns_api("zhang_zhongjing_demo", "张仲景传人(演示)")
    print(f"学习结果: {learn_result}")
    
    # 推荐医生
    recommendations = api.recommend_doctors_api("患者头痛发热，恶寒")
    print(f"医生推荐: {json.dumps(recommendations, ensure_ascii=False, indent=2)}")
    
    # 生成处方
    prescription = api.generate_prescription_api(
        "患者头痛发热，恶寒", 
        "zhang_zhongjing_demo",
        {"头痛": True, "发热": True, "恶寒": True}
    )
    print(f"处方生成: {json.dumps(prescription, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    demo_enhanced_system()