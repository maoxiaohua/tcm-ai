#!/usr/bin/env python3
"""
张仲景诊疗决策系统 - 基于《伤寒论》六经辨证理论

设计原则:
1. 严格按照《伤寒论》六经辨证体系
2. 标准化的诊疗流程，避免随意性
3. 明确的开方标准，确保安全
4. 可扩展到其他医生的标准模板
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re


class ImprovedSymptomAnalyzer:
    """改进的症状分析器 - 支持否定词检测"""
    
    def __init__(self):
        # 症状关键词映射
        self.symptom_keywords = {
            "发热": ["发热", "发烧", "热", "体温高", "烧"],
            "发寒": ["发寒", "恶寒", "怕冷", "畏寒", "寒战"], 
            "出汗": ["出汗", "汗出", "多汗", "盗汗", "自汗"],
            "头痛": ["头痛", "头疼", "头胀", "头晕"],
            "口渴": ["口渴", "渴", "口干", "想喝水"],
            "腹痛": ["腹痛", "肚子痛", "胃痛", "肚疼"],
            "腹泻": ["腹泻", "拉肚子", "泄泻", "大便稀"],
            "便秘": ["便秘", "大便难", "排便困难"]
        }
    
    def detect_negated_symptoms(self, patient_input: str) -> List[str]:
        """检测被否定的症状"""
        negated_symptoms = []
        
        # 精确的否定检测模式
        negation_patterns = [
            (r"没有.*?(发热|发烧)", "发热"),
            (r"没有.*?(发寒|恶寒|怕冷|畏寒|寒战)", "发寒"), 
            (r"没有.*?(出汗|汗出|多汗)", "出汗"),
            (r"没有.*?(头痛|头疼|头胀|头晕)", "头痛"),
            (r"没有.*?(口渴|渴|口干)", "口渴"),
            (r"没有.*?(腹痛|肚子痛|胃痛|肚疼)", "腹痛"),
            (r"没有.*?(腹泻|拉肚子|泄泻|大便稀)", "腹泻"),
            (r"没有.*?(便秘|大便难|排便困难)", "便秘"),
            (r"不.*?(发热|发烧)", "发热"),
            (r"不.*?(发寒|怕冷|畏寒)", "发寒"),
            (r"不.*?(出汗)", "出汗"),
            (r"无.*?(发热|发烧)", "发热"),
            (r"无.*?(发寒|恶寒|怕冷)", "发寒")
        ]
        
        for pattern, symptom in negation_patterns:
            if re.search(pattern, patient_input):
                if symptom not in negated_symptoms:
                    negated_symptoms.append(symptom)
        
        return negated_symptoms
    
    def detect_present_symptoms(self, patient_input: str, negated_symptoms: List[str]) -> List[Tuple[str, float]]:
        """检测存在的症状"""
        present_symptoms = []
        
        for symptom, keywords in self.symptom_keywords.items():
            if symptom in negated_symptoms:
                continue  # 跳过已否定的症状
                
            confidence = 0.0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in patient_input:
                    # 检查是否在否定语境中
                    is_in_negation_context = False
                    
                    # 检查否定词前后15个字符
                    keyword_pos = patient_input.find(keyword)
                    for neg_word in ["没有", "没", "无", "不"]:
                        neg_pos = patient_input.find(neg_word)
                        if neg_pos >= 0 and abs(keyword_pos - neg_pos) <= 15:
                            is_in_negation_context = True
                            break
                    
                    if not is_in_negation_context:
                        matched_keywords.append(keyword)
                        confidence += 1.0
            
            if matched_keywords:
                normalized_confidence = min(confidence / len(keywords), 1.0) * 0.8
                present_symptoms.append((symptom, normalized_confidence))
        
        return present_symptoms


class SixMeridians(Enum):
    """六经分类"""
    TAI_YANG = "太阳病"        # 太阳病：表证，恶寒发热
    YANG_MING = "阳明病"       # 阳明病：里热实证
    SHAO_YANG = "少阳病"       # 少阳病：半表半里证
    TAI_YIN = "太阴病"         # 太阴病：里虚寒证
    SHAO_YIN = "少阴病"        # 少阴病：肾阳虚证
    JUE_YIN = "厥阴病"         # 厥阴病：寒热错杂证

class DiagnosisStage(Enum):
    """诊断阶段"""
    INITIAL = "初诊问询"       # 收集主诉
    SYMPTOM_ANALYSIS = "症状分析"  # 分析症状组合
    SIX_MERIDIAN = "六经辨证"    # 确定所属六经
    PRESCRIPTION = "方证相应"     # 选择对应方剂
    DOSAGE_ADJUST = "剂量调整"   # 根据体质调整

@dataclass
class SymptomPattern:
    """症状模式"""
    name: str                    # 症状组合名称
    keywords: List[str]          # 关键症状词
    meridian: SixMeridians      # 对应六经
    confidence: float            # 匹配信心度
    contraindications: List[str] # 禁忌症

@dataclass 
class PrescriptionRule:
    """处方规则"""
    name: str                    # 方剂名称
    meridian: SixMeridians      # 适用六经
    main_symptoms: List[str]     # 主要适应症
    herbs: List[Tuple[str, int]] # 药材和剂量 (药名, 克数)
    modifications: Dict[str, Tuple[str, int]] # 加减法则
    contraindications: List[str] # 禁忌症
    preparation: str             # 制法
    
class ZhangZhongjingDecisionSystem:
    """张仲景诊疗决策系统"""
    
    def __init__(self):
        """初始化决策系统"""
        self.symptom_patterns = self._init_symptom_patterns()
        self.prescriptions = self._init_prescriptions()
        self.current_stage = DiagnosisStage.INITIAL
        
    def _init_symptom_patterns(self) -> List[SymptomPattern]:
        """初始化症状模式库"""
        return [
            # 太阳病症状模式
            SymptomPattern(
                name="太阳表实证",
                keywords=["恶寒", "发热", "无汗", "头痛", "项强", "脉浮紧"],
                meridian=SixMeridians.TAI_YANG,
                confidence=0.9,
                contraindications=["汗出", "口渴"]
            ),
            SymptomPattern(
                name="太阳表虚证", 
                keywords=["恶寒", "发热", "汗出", "头痛", "脉浮缓"],
                meridian=SixMeridians.TAI_YANG,
                confidence=0.85,
                contraindications=["无汗", "口渴甚"]
            ),
            
            # 阳明病症状模式
            SymptomPattern(
                name="阳明气分热证",
                keywords=["大热", "大汗", "大渴", "脉洪大", "烦躁"],
                meridian=SixMeridians.YANG_MING,
                confidence=0.9,
                contraindications=["恶寒", "无汗"]
            ),
            SymptomPattern(
                name="阳明腑实证",
                keywords=["潮热", "腹满", "便秘", "谵语", "脉沉实"],
                meridian=SixMeridians.YANG_MING, 
                confidence=0.85,
                contraindications=["腹泻", "脉虚"]
            ),
            
            # 少阳病症状模式
            SymptomPattern(
                name="少阳枢机不利",
                keywords=["往来寒热", "胸胁苦满", "默默不欲饮食", "心烦喜呕", "口苦", "咽干", "目眩", "脉弦"],
                meridian=SixMeridians.SHAO_YANG,
                confidence=0.95,
                contraindications=["大汗", "大下"]
            ),
            
            # 太阴病症状模式  
            SymptomPattern(
                name="太阴脾虚证",
                keywords=["腹满", "吐", "食不下", "自利", "时腹自痛", "脉缓"],
                meridian=SixMeridians.TAI_YIN,
                confidence=0.8,
                contraindications=["大热", "口渴"]
            ),
            
            # 少阴病症状模式
            SymptomPattern(
                name="少阴肾阳虚证",
                keywords=["脉微细", "但欲寐", "四肢厥冷", "下利清谷", "小便清长"],
                meridian=SixMeridians.SHAO_YIN,
                confidence=0.85, 
                contraindications=["发热", "口渴"]
            ),
            
            # 厥阴病症状模式
            SymptomPattern(
                name="厥阴寒热错杂",
                keywords=["消渴", "气上撞心", "心中疼热", "饥不欲食", "吐蛔", "手足厥冷"],
                meridian=SixMeridians.JUE_YIN,
                confidence=0.8,
                contraindications=["单纯热证", "单纯寒证"]
            )
        ]
    
    def _init_prescriptions(self) -> List[PrescriptionRule]:
        """初始化处方规则库"""
        return [
            # 太阳病方剂
            PrescriptionRule(
                name="麻黄汤",
                meridian=SixMeridians.TAI_YANG,
                main_symptoms=["恶寒", "发热", "无汗", "喘"],
                herbs=[("麻黄", 9), ("桂枝", 6), ("杏仁", 6), ("炙甘草", 3)],
                modifications={
                    "咳嗽重": ("杏仁", 9),
                    "头痛重": ("川芎", 6)
                },
                contraindications=["汗出", "脉虚", "年老体弱"],
                preparation="先煎麻黄，去上沫，内诸药，煮取二升半，去滓，温服八合"
            ),
            PrescriptionRule(
                name="桂枝汤", 
                meridian=SixMeridians.TAI_YANG,
                main_symptoms=["恶寒", "发热", "汗出", "恶风"],
                herbs=[("桂枝", 9), ("芍药", 9), ("炙甘草", 6), ("生姜", 9), ("大枣", 3)],
                modifications={
                    "项背强": ("葛根", 12),
                    "咳嗽": ("厚朴", 6)
                },
                contraindications=["无汗", "口渴甚", "脉洪数"],
                preparation="水煎温服，服已须臾，啜热稀粥一升余，以助药力"
            ),
            
            # 阳明病方剂
            PrescriptionRule(
                name="白虎汤",
                meridian=SixMeridians.YANG_MING,
                main_symptoms=["大热", "大汗", "大渴", "脉洪大"],
                herbs=[("石膏", 50), ("知母", 18), ("炙甘草", 6), ("粳米", 9)],
                modifications={
                    "烦躁": ("石膏", 60),
                    "渴甚": ("天花粉", 12)
                },
                contraindications=["恶寒", "脉虚", "汗出不多"],
                preparation="水煎服，石膏先煎"
            ),
            PrescriptionRule(
                name="大承气汤",
                meridian=SixMeridians.YANG_MING,
                main_symptoms=["大便秘结", "腹满硬痛", "潮热", "谵语"],
                herbs=[("大黄", 12), ("厚朴", 24), ("枳实", 12), ("芒硝", 9)],
                modifications={
                    "腹痛甚": ("厚朴", 30),
                    "燥屎不下": ("大黄", 15)
                },
                contraindications=["孕妇", "体虚", "无实热"],
                preparation="水煎，大黄后下，芒硝溶服"
            ),
            
            # 少阳病方剂
            PrescriptionRule(
                name="小柴胡汤",
                meridian=SixMeridians.SHAO_YANG,
                main_symptoms=["往来寒热", "胸胁苦满", "默默不欲饮食", "心烦喜呕"],
                herbs=[("柴胡", 24), ("黄芩", 9), ("人参", 9), ("半夏", 9), ("炙甘草", 9), ("生姜", 9), ("大枣", 4)],
                modifications={
                    "胸满": ("去人参、大枣", 0), 
                    "渴": ("去半夏", 0),
                    "腹中痛": ("芍药", 9)
                },
                contraindications=["大汗", "大下后"],
                preparation="水煎服，分三次温服"
            ),
            
            # 太阴病方剂
            PrescriptionRule(
                name="理中汤",
                meridian=SixMeridians.TAI_YIN,
                main_symptoms=["腹满", "吐利", "手足厥冷", "脉沉迟"],
                herbs=[("人参", 9), ("白术", 9), ("干姜", 9), ("炙甘草", 9)],
                modifications={
                    "利多": ("白术", 12),
                    "吐多": ("生姜", 12),
                    "寒甚": ("附子", 6)
                },
                contraindications=["阴虚内热", "实热证"],
                preparation="水煎温服"
            ),
            
            # 少阴病方剂
            PrescriptionRule(
                name="四逆汤", 
                meridian=SixMeridians.SHAO_YIN,
                main_symptoms=["四肢厥逆", "恶寒蜷卧", "脉微细", "下利清谷"],
                herbs=[("炙甘草", 6), ("干姜", 9), ("生附子", 15)],
                modifications={
                    "利止脉不出": ("人参", 9),
                    "呕": ("生姜", 9)
                },
                contraindications=["阴虚火旺", "实热证"],
                preparation="水煎温服，附子先煎1小时"
            ),
            
            # 厥阴病方剂
            PrescriptionRule(
                name="乌梅丸",
                meridian=SixMeridians.JUE_YIN,
                main_symptoms=["消渴", "气上撞心", "心中疼热", "饥不欲食", "吐蛔"],
                herbs=[("乌梅", 300), ("细辛", 6), ("干姜", 10), ("黄连", 16), ("当归", 4), ("附子", 6), ("蜀椒", 4), ("桂枝", 6), ("人参", 6), ("黄柏", 6)],
                modifications={
                    "寒重": ("附子", 9),
                    "热重": ("黄连", 20)
                },
                contraindications=["单纯寒证", "单纯热证"],
                preparation="细末，蜂蜜为丸，温服"
            )
        ]
    
    
    def analyze_symptoms(self, patient_description: str) -> Tuple[SixMeridians, float, str]:
        """改进的症状分析 - 支持否定词检测"""
        # 创建症状分析器
        analyzer = ImprovedSymptomAnalyzer()
        
        # 检测否定和存在的症状
        negated_symptoms = analyzer.detect_negated_symptoms(patient_description)
        present_symptoms = analyzer.detect_present_symptoms(patient_description, negated_symptoms)
        
        # 文本预处理
        description = patient_description.lower()
        
        best_match = None
        best_confidence = 0.0
        analysis_detail = ""
        
        for pattern in self.symptom_patterns:
            # 计算匹配度（考虑否定）
            matched_keywords = []
            total_score = 0.0
            negation_penalty = 0.0
            
            for keyword in pattern.keywords:
                # 检查关键词是否在描述中
                if keyword in description:
                    # 检查是否被否定
                    is_negated = False
                    for negated in negated_symptoms:
                        if keyword in analyzer.symptom_keywords.get(negated, []):
                            is_negated = True
                            negation_penalty += 2.0  # 重度扣分
                            break
                    
                    if not is_negated:
                        matched_keywords.append(keyword)
                        total_score += 1.0
            
            # 检查禁忌症
            contraindication_found = False
            for contra in pattern.contraindications:
                if contra in description:
                    # 检查禁忌症是否也被否定
                    contra_negated = False
                    for negated in negated_symptoms:
                        if contra in analyzer.symptom_keywords.get(negated, []):
                            contra_negated = True
                            break
                    
                    if not contra_negated:
                        contraindication_found = True
                        total_score -= 0.5
                        break
            
            # 计算最终信心度
            if len(pattern.keywords) > 0:
                keyword_ratio = len(matched_keywords) / len(pattern.keywords)
                final_confidence = keyword_ratio * pattern.confidence
                
                # 应用否定惩罚
                final_confidence = max(0, final_confidence - negation_penalty * 0.1)
                
                if contraindication_found:
                    final_confidence *= 0.5
                
                if final_confidence > best_confidence:
                    best_confidence = final_confidence
                    best_match = pattern
                    
                    # 生成详细分析
                    analysis_parts = []
                    if matched_keywords:
                        analysis_parts.append(f"匹配症状: {matched_keywords}")
                    if negated_symptoms:
                        analysis_parts.append(f"否定症状: {negated_symptoms}")
                    analysis_parts.append(f"信心度: {final_confidence:.2f}")
                    analysis_detail = ", ".join(analysis_parts)
        
        if best_match and best_confidence > 0.05:  # 提高最低信心度要求
            return best_match.meridian, best_confidence, analysis_detail
        else:
            # 如果没有好的匹配，生成详细说明
            if negated_symptoms:
                analysis_detail = f"患者明确否认: {negated_symptoms}，症状不典型，按太阴病处理"
            else:
                analysis_detail = "症状描述不充分，按太阴病处理"
            return SixMeridians.TAI_YIN, 0.1, analysis_detail

    def select_prescription(self, meridian: SixMeridians, symptoms: str) -> Optional[PrescriptionRule]:
        """根据六经选择最适合的处方"""
        candidates = [p for p in self.prescriptions if p.meridian == meridian]
        
        if not candidates:
            return None
            
        # 选择最匹配的处方
        best_prescription = None
        best_score = 0.0
        
        for prescription in candidates:
            score = 0.0
            for main_symptom in prescription.main_symptoms:
                if main_symptom in symptoms:
                    score += 1.0
            
            # 检查禁忌症
            for contra in prescription.contraindications:
                if contra in symptoms:
                    score -= 2.0  # 禁忌症严重扣分
            
            if score > best_score:
                best_score = score
                best_prescription = prescription
        
        return best_prescription if best_score > 0 else candidates[0]  # 至少返回一个
    
    def generate_diagnosis_response(self, patient_input: str) -> str:
        """生成完整的诊断回复 - 增强版本（含加减用药）"""
        # 分析症状
        meridian, confidence, analysis = self.analyze_symptoms(patient_input)
        
        # 选择处方
        prescription = self.select_prescription(meridian, patient_input)
        
        if not prescription:
            return self._generate_inquiry_response(patient_input)
        
        # 检查症状描述是否足够详细来开方
        if not self._is_information_sufficient_for_prescription(patient_input):
            return self._generate_inquiry_response(patient_input)
        
        # 生成加减方案
        modifications = self._generate_modifications(prescription, patient_input)
        
        # 生成标准化诊断回复
        response = f"""基于《伤寒论》六经辨证分析：

### 一、症状分析
{analysis}
**症状匹配度**: {confidence:.1%}

### 二、六经辨证
**证型**: {meridian.value}
**辨证要点**: {self._get_meridian_description(meridian)}
**经络受邪**: {self._get_meridian_pathology(meridian)}

### 三、方证相应
**主方**: {prescription.name}（《伤寒论》经方）
**适应证**: {', '.join(prescription.main_symptoms)}
**方义**: {self._get_formula_meaning(prescription.name)}

### 四、处方组成

**【处方】**

"""
        
        # 添加基础药物列表（增强显示）
        for herb_name, dosage in prescription.herbs:
            herb_function = self._get_herb_function(herb_name, prescription.name)
            response += f"{herb_name} {dosage}g  # {herb_function}\n"
        
        # 添加加减方案
        if modifications:
            response += f"\n**【加减用药】**\n\n"
            for condition, (herb, dosage) in modifications.items():
                response += f"若见{condition}：加 {herb} {dosage}g\n"
        
        # 添加剂量调整建议
        dosage_adjustments = self._get_dosage_adjustments(prescription, patient_input)
        if dosage_adjustments:
            response += f"\n**【剂量调整】**\n\n"
            for adjustment in dosage_adjustments:
                response += f"- {adjustment}\n"
        
        response += f"""
**【制法】** {prescription.preparation}

**【用法】** 水煎服，日1剂，分2-3次温服

### 五、服药指导
**服药方法**：
- 温服效果最佳，忌冷饮
- 服药后避风寒，适当保暖
- 观察汗出情况，微汗即可

**疗程建议**：
- 急性期：连服3-5剂
- 症状缓解后可减量或停药
- 病情变化时及时调整方药

### 六、注意事项
- 严格按照张仲景原方用药
- 禁忌：{', '.join(prescription.contraindications)}
- 如有不适反应，立即停药就医
- 孕妇、儿童、老人需减量使用

**重要声明**: 本方案基于《伤寒论》六经辨证理论，仅供参考，请在专业中医师指导下使用。"""
        
        return response
    
    def _get_meridian_description(self, meridian: SixMeridians) -> str:
        """获取六经的描述"""
        descriptions = {
            SixMeridians.TAI_YANG: "表证，邪在肌表，当发汗解表",
            SixMeridians.YANG_MING: "里热证，热盛津伤，当清热泻火", 
            SixMeridians.SHAO_YANG: "半表半里证，邪在少阳，当和解",
            SixMeridians.TAI_YIN: "里虚寒证，脾阳不足，当温中健脾",
            SixMeridians.SHAO_YIN: "肾阳虚证，命门火衰，当温肾助阳",
            SixMeridians.JUE_YIN: "寒热错杂证，当寒热并治"
        }
        return descriptions.get(meridian, "")
    
    def _generate_modifications(self, prescription: PrescriptionRule, patient_input: str) -> Dict[str, Tuple[str, int]]:
        """生成加减方案"""
        modifications = {}
        
        # 基于处方的预设加减方案
        if prescription.modifications:
            for condition, modification in prescription.modifications.items():
                if isinstance(modification, tuple):
                    herb_name, dosage = modification
                    if dosage > 0:  # 正常加药
                        modifications[condition] = (herb_name, dosage)
        
        # 基于症状的动态加减
        patient_lower = patient_input.lower()
        
        if "咳嗽" in patient_input or "痰" in patient_input:
            if prescription.name == "麻黄汤":
                modifications["咳嗽痰多"] = ("桔梗", 6)
            elif prescription.name == "桂枝汤":
                modifications["咳嗽"] = ("杏仁", 9)
                
        if "便秘" in patient_input:
            modifications["大便秘结"] = ("大黄", 3)
            
        if "失眠" in patient_input or "心烦" in patient_input:
            modifications["心烦不眠"] = ("酸枣仁", 15)
            
        if "腰痛" in patient_input or "关节痛" in patient_input:
            modifications["肢体疼痛"] = ("独活", 9)
        
        return modifications
    
    def _get_dosage_adjustments(self, prescription: PrescriptionRule, patient_input: str) -> List[str]:
        """获取剂量调整建议"""
        adjustments = []
        
        # 体质调整
        if "体虚" in patient_input or "老人" in patient_input:
            adjustments.append("体质虚弱者：各药减量1/3")
            
        if "小儿" in patient_input or "儿童" in patient_input:
            adjustments.append("小儿用量：按体重计算，一般为成人量的1/3-1/2")
            
        # 症状强度调整
        if "剧烈" in patient_input or "严重" in patient_input:
            adjustments.append("症状较重者：主药可酌量增加")
            
        # 特殊药物调整
        if prescription.name == "四逆汤":
            adjustments.append("附子：先从小量开始，逐渐加量，必须先煎1-2小时")
            
        if prescription.name == "大承气汤":
            adjustments.append("大黄：后下15分钟，芒硝：溶化后兑服")
            
        return adjustments
    
    def _get_meridian_pathology(self, meridian: SixMeridians) -> str:
        """获取六经病机"""
        pathologies = {
            SixMeridians.TAI_YANG: "风寒束表，卫气不宣",
            SixMeridians.YANG_MING: "热盛津伤，胃肠燥结", 
            SixMeridians.SHAO_YANG: "邪在半表半里，枢机不利",
            SixMeridians.TAI_YIN: "脾阳虚衰，寒湿内盛",
            SixMeridians.SHAO_YIN: "肾阳虚衰，命门火微",
            SixMeridians.JUE_YIN: "阴阳错杂，寒热并见"
        }
        return pathologies.get(meridian, "")
    
    def _get_formula_meaning(self, formula_name: str) -> str:
        """获取方剂方义"""
        meanings = {
            "麻黄汤": "麻黄开腠发汗，桂枝温通血脉，杏仁宣肺平喘，甘草调和诸药",
            "桂枝汤": "桂枝温通阳气，芍药敛阴和营，生姜助发汗，大枣益气养血，甘草调中",
            "小柴胡汤": "柴胡疏肝解郁，黄芩清热，人参扶正，半夏降逆，姜枣调营卫",
            "白虎汤": "石膏清热泻火，知母滋阴润燥，甘草调中，粳米保胃气",
            "理中汤": "人参大补元气，白术健脾燥湿，干姜温中散寒，甘草调和药性",
            "四逆汤": "附子回阳救逆，干姜温中散寒，甘草调和诸药，共奏回阳救逆之功",
            "乌梅丸": "乌梅敛肝安蛔，黄连清热，附子温阳，寒热并用，治寒热错杂证"
        }
        return meanings.get(formula_name, "方证相应，药证合拍")
    
    def _get_herb_function(self, herb_name: str, formula_name: str) -> str:
        """获取药物在方中的功效"""
        herb_functions = {
            # 麻黄汤
            "麻黄": "发汗解表，宣肺平喘",
            "桂枝": "温通阳气，助麻黄发汗",
            "杏仁": "宣肺降气，平喘止咳", 
            "炙甘草": "调和诸药，缓和峻性",
            
            # 桂枝汤
            "芍药": "敛阴和营，调和营卫",
            "生姜": "温胃散寒，助药力",
            "大枣": "益气养血，调和营卫",
            
            # 小柴胡汤
            "柴胡": "疏肝解郁，和解少阳",
            "黄芩": "清热燥湿，泻火解毒",
            "人参": "大补元气，扶正祛邪",
            "半夏": "降逆止呕，燥湿化痰",
            
            # 四逆汤
            "生附子": "回阳救逆，温肾壮阳", 
            "干姜": "温中散寒，回阳通脉",
            
            # 其他常用药
            "石膏": "清热泻火，除烦止渴",
            "知母": "清热润燥，滋阴降火",
            "白术": "健脾燥湿，益气固表",
            "人参": "大补元气，生津止渴"
        }
        return herb_functions.get(herb_name, "归经入药，各司其职")
    
    def _is_information_sufficient_for_prescription(self, patient_input: str) -> bool:
        """检查患者信息是否足够详细来开具处方"""
        # 基本症状描述长度检查（过于简短不开方）
        if len(patient_input) < 8:
            return False
            
        # 检查是否包含足够的四诊信息
        required_info_count = 0
        
        # 1. 主要症状信息
        main_symptoms = ['头痛', '发热', '恶寒', '咳嗽', '腹痛', '腹泻', '便秘', '呕吐', '胸闷', '心悸']
        if any(symptom in patient_input for symptom in main_symptoms):
            required_info_count += 1
            
        # 2. 伴随症状或病程信息
        accompanying_info = ['天', '次', '小时', '周', '月', '昨天', '今天', '最近', '一直', '经常', 
                           '时候', '之后', '以来', '开始', '伴有', '同时', '另外', '还有']
        if any(info in patient_input for info in accompanying_info):
            required_info_count += 1
            
        # 3. 程度或性质描述
        quality_descriptions = ['严重', '轻微', '很', '非常', '特别', '明显', '剧烈', '隐隐', 
                              '阵阵', '持续', '间断', '偶尔', '频繁']
        if any(desc in patient_input for desc in quality_descriptions):
            required_info_count += 1
            
        # 4. 诱因或相关情况
        context_info = ['吃', '喝', '睡', '工作', '运动', '天气', '情绪', '压力', '劳累', 
                       '受凉', '着急', '生气', '因为', '由于', '可能']
        if any(context in patient_input for context in context_info):
            required_info_count += 1
            
        # 暂时总是要求更多信息，直到系统稳定
        # 需要非常详细的信息才考虑开方（至少40字符且包含4种以上信息类型）
        if len(patient_input) > 40 and required_info_count >= 4:
            return True
            
        # 对于其他情况，都需要问诊
        return False
    
    def _generate_inquiry_response(self, patient_input: str) -> str:
        """生成进一步问诊的回复 - 针对性智能问诊"""
        # 根据主要症状生成针对性问诊
        main_symptom = self._identify_main_symptom(patient_input)
        
        base_response = f"根据您提到的{main_symptom}，按照《伤寒论》六经辨证的要求，我需要进一步了解以下情况：\n\n"
        
        # 针对不同症状的专门问诊
        if "胸" in patient_input or "心" in patient_input:
            specific_questions = """**针对胸痛的具体问诊：**
1. **疼痛性质** - 是刺痛、闷痛、胀痛还是压痛？疼痛是否向肩背或臂部放射？
2. **发作规律** - 疼痛是持续性还是阵发性？什么情况下加重或缓解？
3. **伴随症状** - 是否伴有心悸、气短、胸闷、出汗？
4. **寒热情况** - 是否怕冷或发热？喜欢热敷还是冷敷？"""
        
        elif "头" in patient_input or "痛" in patient_input and "头" in patient_input:
            specific_questions = """**针对头痛的具体问诊：**
1. **疼痛部位** - 前额、两侧、后脑还是巅顶？是否固定位置？
2. **疼痛性质** - 胀痛、跳痛、刺痛还是空痛？
3. **诱发因素** - 劳累、情绪、天气变化、饮食后是否加重？
4. **伴随症状** - 是否恶心呕吐、怕光怕声、眼花？"""
        
        elif "拉" in patient_input or "泻" in patient_input or "肚" in patient_input:
            specific_questions = """**针对腹泻的具体问诊：**
1. **大便性状** - 水样、糊状还是有形？颜色如何？是否有黏液或血丝？
2. **腹痛情况** - 是否腹痛？疼痛在脐周、上腹还是下腹？
3. **伴随症状** - 是否恶心呕吐、腹胀、肠鸣？
4. **寒热倾向** - 喜热饮还是冷饮？腹部喜按还是拒按？"""
        
        elif "咳" in patient_input or "嗽" in patient_input:
            specific_questions = """**针对咳嗽的具体问诊：**
1. **咳嗽性质** - 干咳还是有痰？痰的颜色和性状如何？
2. **发作时间** - 晨起、夜间还是全天？劳累后是否加重？
3. **伴随症状** - 是否胸闷气短、喉痒、声嘶？
4. **寒热表现** - 是否恶寒发热？咽痛咽干？"""
        
        else:
            # 通用问诊（当无法识别具体症状时）
            specific_questions = """**六经辨证必要信息：**
1. **寒热表现** - 是否恶寒或发热？出汗情况如何？
2. **饮食睡眠** - 食欲、睡眠、二便情况？
3. **精神状态** - 精神是否疲倦？烦躁还是安静？
4. **四肢感觉** - 手足是否温凉？有无酸痛？"""
        
        # 添加通用的六经辨证问诊
        common_questions = """
**六经辨证关键信息：**
5. **舌脉情况** - 如有条件，请描述舌苔颜色厚薄、脉象情况（或自觉脉跳快慢强弱）

请根据您的实际情况如实回答，这些信息对准确的六经辨证和选方用药至关重要。"""
        
        return base_response + specific_questions + common_questions
    
    def _identify_main_symptom(self, patient_input: str) -> str:
        """识别患者的主要症状"""
        symptom_keywords = {
            "胸痛": ["胸", "心"],
            "头痛": ["头痛", "头疼"],  
            "腹泻": ["拉", "泻", "肚"],
            "咳嗽": ["咳", "嗽"],
            "发热": ["发烧", "发热", "热"],
            "腹痛": ["腹痛", "肚子痛"],
            "不适": ["不舒服", "难受"]
        }
        
        for symptom, keywords in symptom_keywords.items():
            if any(keyword in patient_input for keyword in keywords):
                return symptom
                
        return "症状"

# 测试函数
def test_zhang_zhongjing_system():
    """测试张仲景决策系统"""
    system = ZhangZhongjingDecisionSystem()
    
    test_cases = [
        "我恶寒发热，无汗，头痛，项背强直，脉浮紧",  # 太阳病麻黄汤证
        "往来寒热，胸胁苦满，不想吃饭，心烦想吐，口苦",  # 少阳病小柴胡汤证
        "腹满，吐，不想吃饭，腹泻，手脚冷，脉缓慢",  # 太阴病理中汤证
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"患者描述: {case}")
        print("-" * 50)
        
        response = system.generate_diagnosis_response(case)
        print(response)
        print("=" * 50)

if __name__ == "__main__":
    test_zhang_zhongjing_system()