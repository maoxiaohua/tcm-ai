#!/usr/bin/env python3
"""
智能中医处方分析系统 - 基于中医师临床思维
重新设计：只要能识别出足够的中药信息，就进行专业的中医辨证分析
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ChineseHerb:
    """中药信息（完整版）"""
    name: str
    dosage: float
    unit: str
    raw_text: str
    category: str  # 药物分类
    properties: Dict[str, str]  # 性味归经
    functions: List[str]  # 主要功效
    confidence: float

@dataclass
class PrescriptionAnalysis:
    """处方分析结果"""
    herbs: List[ChineseHerb]
    total_herbs: int
    prescription_pattern: str  # 方证模式
    syndrome_analysis: Dict[str, Any]  # 证候分析
    herb_classification: Dict[str, List[str]]  # 药物分类统计
    clinical_assessment: Dict[str, Any]  # 临床评估
    professional_comments: List[str]  # 专业点评

class ChineseMedicineDatabase:
    """中医药数据库 - 统一版本(358种药材)"""
    
    def __init__(self):
        # 加载统一的358种中药数据库
        self.herbs_database = self._load_unified_herb_database()
        
        # 初始化经典方剂模式识别数据库
        self.classic_formulas = {
            "银翘散": ["金银花", "连翘", "桔梗", "薄荷", "竹叶", "甘草", "荆芥", "牛蒡子"],
            "麻黄汤": ["麻黄", "桂枝", "杏仁", "甘草"],
            "小柴胡汤": ["柴胡", "黄芩", "人参", "半夏", "甘草", "生姜", "大枣"],
            "止咳散": ["桔梗", "百部", "荆芥", "甘草", "白前"],
            "二陈汤": ["半夏", "陈皮", "茯苓", "甘草"],
            "四君子汤": ["人参", "白术", "茯苓", "甘草"],
            "四物汤": ["当归", "川芎", "白芍", "熟地黄"],
            "补中益气汤": ["黄芪", "人参", "白术", "甘草", "当归", "陈皮", "升麻", "柴胡"],
            "桂枝汤": ["桂枝", "白芍", "甘草", "生姜", "大枣"],
            "六君子汤": ["人参", "白术", "茯苓", "甘草", "陈皮", "半夏"]
        }
        
    def _load_unified_herb_database(self) -> Dict:
        """加载统一的中药数据库"""
        import json
        import os
        
        # 首先尝试加载统一数据库文件
        unified_db_path = "/opt/tcm/unified_herb_database.json"
        if os.path.exists(unified_db_path):
            try:
                with open(unified_db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载统一数据库失败: {e}")
        
        # 如果文件不存在，从tcm_formula_analyzer中动态加载
        try:
            import sys
            sys.path.append('/home/ute/tcm-ai')
            from core.prescription.tcm_formula_analyzer import TCMFormulaAnalyzer
            
            analyzer = TCMFormulaAnalyzer()
            herb_db = analyzer.herb_database
            
            # 转换格式以保持兼容性
            unified_db = {}
            for herb_name, herb_info in herb_db.items():
                properties = herb_info.get('properties', {})
                nature = properties.get('性味', '未知')
                meridian = properties.get('归经', '未知')
                functions = herb_info.get('functions', [])
                category = herb_info.get('category', '其他')
                
                unified_db[herb_name] = {
                    'category': category,
                    'nature': nature,
                    'meridian': meridian, 
                    'functions': functions,
                    'typical_roles': herb_info.get('typical_roles', []),
                    'typical_dosage': herb_info.get('typical_dosage', [6, 12])
                }
            
            # 保存统一数据库文件供下次使用
            with open(unified_db_path, 'w', encoding='utf-8') as f:
                json.dump(unified_db, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功加载并保存统一药材数据库: {len(unified_db)}种药材")
            return unified_db
            
        except Exception as e:
            logger.error(f"动态加载药材数据库失败: {e}")
            # 返回基础数据库作为后备
            return self._get_fallback_database()
    
    def _get_fallback_database(self) -> Dict:
        """后备数据库 - 基础药材"""
        return {
            "甘草": {"category": "补气药", "nature": "甘平", "meridian": "心、肺、脾、胃", "functions": ["补脾益气", "清热解毒", "祛痰止咳", "调和诸药"]},
            "人参": {"category": "补气药", "nature": "甘微苦微温", "meridian": "肺、脾、心、肾", "functions": ["大补元气", "复脉固脱", "补脾益肺", "生津止渴", "安神益智"]},
            "黄芪": {"category": "补气药", "nature": "甘微温", "meridian": "肺、脾", "functions": ["补气升阳", "固表止汗", "利水消肿", "生肌"]},
            "当归": {"category": "补血药", "nature": "甘辛温", "meridian": "肝、心、脾", "functions": ["补血", "活血", "调经止痛", "润燥滑肠"]},
            "川芎": {"category": "活血化瘀药", "nature": "辛温", "meridian": "肝、胆、心包", "functions": ["活血行气", "祛风止痛"]},
            "白芍": {"category": "补血药", "nature": "苦酸微寒", "meridian": "肝、脾", "functions": ["养血调经", "敛阴止汗", "柔肝止痛", "平抑肝阳"]},
            "熟地黄": {"category": "补血药", "nature": "甘微温", "meridian": "肝、肾", "functions": ["滋阴补血", "益精填髓"]},
            "白术": {"category": "补气药", "nature": "甘、苦，温", "meridian": "脾、胃", "functions": ["补脾益气", "燥湿利水", "止汗", "安胎"]},
            "茯苓": {"category": "利水渗湿药", "nature": "甘淡平", "meridian": "心、肺、脾、肾", "functions": ["利水渗湿", "健脾", "宁心"]},
            "陈皮": {"category": "理气药", "nature": "苦辛温", "meridian": "肺、脾", "functions": ["理气健脾", "燥湿化痰"]}
        }

class IntelligentPrescriptionAnalyzer:
    """智能处方分析器 - 基于中医临床思维"""
    
    def __init__(self):
        self.herb_db = ChineseMedicineDatabase()
        
        # 药物识别的置信度阈值（优化以提高识别率）
        self.min_herbs_for_analysis = 3  # 最少3味药才进行分析
        self.confidence_threshold = 0.01  # 置信度阈值（适配低置信度OCR）
        
        # 扩展中药名称数据库 - 添加更多常见中药
        self._extend_herb_database()
        
    def analyze_prescription(self, text: str) -> Dict[str, Any]:
        """智能处方分析 - 主入口"""
        try:
            # 1. 提取中药信息
            herbs = self._extract_chinese_herbs(text)
            
            # 2. 基础验证
            valid_herbs = [h for h in herbs if h.confidence >= self.confidence_threshold]
            
            if len(valid_herbs) < self.min_herbs_for_analysis:
                return {
                    "success": False,
                    "error": f"识别到的有效中药不足{self.min_herbs_for_analysis}味（当前{len(valid_herbs)}味），无法进行中医辨证分析",
                    "extracted_herbs": len(herbs),
                    "valid_herbs": len(valid_herbs),
                    "suggestion": "请确保上传的是包含完整中药处方的文档"
                }
            
            # 3. 专业中医分析
            analysis = self._perform_tcm_analysis(valid_herbs, text)
            
            return {
                "success": True,
                "analysis_type": "中医辨证论治分析",
                "prescription_analysis": analysis,
                "herbs_summary": {
                    "total_extracted": len(herbs),
                    "valid_for_analysis": len(valid_herbs),
                    "analysis_confidence": self._calculate_overall_confidence(valid_herbs)
                }
            }
            
        except Exception as e:
            logger.error(f"智能处方分析失败: {e}")
            return {
                "success": False,
                "error": f"分析过程出现异常: {str(e)}"
            }
    
    def _extract_chinese_herbs(self, text: str) -> List[ChineseHerb]:
        """提取中药信息"""
        herbs = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # 多种中药识别模式（修复版 - 移除危险的宽松模式）
            patterns = [
                # 模式1: 药名（规格）剂量*帖数 价格
                r'([一-龯]{2,8})(?:\（[^）]*\）)?\s*(?:\([^)]*\))?\s*(\d+(?:\.\d+)?)\s*(?:\([克g]\))?\s*(?:\*\s*\d+[帖剂]?)?',
                # 模式2: 标准格式 药名 剂量单位
                r'([一-龯]{2,8})\s+(\d+(?:\.\d+)?)\s*([克g钱两])',
                # 模式3: 简单格式
                r'([一-龯]{2,8})\s*[:：]\s*(\d+(?:\.\d+)?)',
                # 模式4: 中文数字格式
                r'([一-龯]{2,8})\s*([一二三四五六七八九十百]+)\s*[克钱两g]',
                # 模式5: 表格格式
                r'([一-龯]{2,8})\s*(?:\（[^）]*\）)?\s+(\d+(?:\.\d+)?)\s*g\s+\d+帖',
                # 模式6: 带序号格式
                r'\d+\.\s*([一-龯]{2,8})\s*(?:\([^)]*\))?\s*(\d+(?:\.\d+)?)\s*g',
                # 模式7: 逗号分隔格式
                r'([一-龯]{2,8})\s*(\d+(?:\.\d+)?)\s*g\s*[,，]',
                # 模式8: 安全的克重匹配（必须有克/g标识）
                r'([一-龯]{2,8})\s*(?:\（[^）]*\）)?\s*(\d+(?:\.\d+)?)\s*[克g]',
                # 🚨 已删除模式9：危险的宽松匹配 - 会把"小火煎煮 20"当成药材
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if len(match) >= 2:
                        herb_name = match[0].strip()
                        dosage_str = match[1].strip()
                        
                        # 🚨 关键修复：黑名单过滤，排除明显不是药材的词汇
                        non_herb_blacklist = [
                            "小火煎煮", "大火煮沸", "后下", "先煎", "包煎", "另煎", "冲服", 
                            "可加", "若", "如", "若见", "若有", "可用", "煎制", "服用",
                            "浸泡", "煎煮", "药材", "所有", "清水", "分钟", "时间", "方法",
                            "若痰多", "若咽痛", "若怕冷", "若烦躁", "明显", "黏稠", "不安",
                            "先用", "煮沸后", "最后", "即在"
                        ]
                        
                        # 如果是黑名单词汇，跳过
                        if any(blacklisted in herb_name for blacklisted in non_herb_blacklist):
                            continue
                        
                        # 验证是否为中药
                        confidence = self._calculate_herb_recognition_confidence(herb_name, line, dosage_str)
                        
                        if confidence > 0.2:  # 基础筛选（降低阈值）
                            try:
                                # 处理中文数字转换
                                if re.match(r'[一二三四五六七八九十百]+', dosage_str):
                                    dosage = self._chinese_number_to_float(dosage_str)
                                else:
                                    dosage = float(dosage_str)
                                
                                herb = ChineseHerb(
                                    name=herb_name,
                                    dosage=dosage,
                                    unit="g",
                                    raw_text=line,
                                    category=self._get_herb_category(herb_name),
                                    properties=self._get_herb_properties(herb_name),
                                    functions=self._get_herb_functions(herb_name),
                                    confidence=confidence
                                )
                                herbs.append(herb)
                            except (ValueError, TypeError):
                                continue
        
        return self._deduplicate_and_rank_herbs(herbs)
    
    def _calculate_herb_recognition_confidence(self, name: str, context: str, dosage: str) -> float:
        """计算中药识别置信度"""
        confidence = 0.3  # 基础分
        
        # 1. 在中药数据库中
        if name in self.herb_db.herbs_database:
            confidence += 0.5
        
        # 2. 炮制品识别
        processed_names = ["生", "熟", "炙", "炒", "制", "姜", "醋", "酒", "盐", "蜜"]
        for prefix in processed_names:
            clean_name = name.replace(prefix, "") if name.startswith(prefix) else name
            if clean_name in self.herb_db.herbs_database:
                confidence += 0.4
                break
        
        # 3. 剂量合理性
        try:
            dose = float(dosage)
            if 3 <= dose <= 30:  # 常规剂量
                confidence += 0.2
            elif 1 <= dose <= 50:  # 可接受范围
                confidence += 0.1
            else:
                confidence -= 0.1
        except:
            confidence -= 0.1
        
        # 4. 上下文医学特征
        medical_keywords = ["克", "g", "帖", "剂", "煎", "服", "日", "次", "净", "炒"]
        if any(kw in context for kw in medical_keywords):
            confidence += 0.15
        
        # 5. 中药名称特征
        if 2 <= len(name) <= 6 and all('\u4e00' <= c <= '\u9fff' for c in name):
            confidence += 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def _chinese_number_to_float(self, chinese_num: str) -> float:
        """中文数字转换为阿拉伯数字"""
        # 基础中文数字映射
        chinese_digits = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '百': 100
        }
        
        # 简单转换逻辑
        if chinese_num in chinese_digits:
            return float(chinese_digits[chinese_num])
        
        # 处理十几的数字 (如 "十二")
        if chinese_num.startswith('十') and len(chinese_num) == 2:
            return 10.0 + chinese_digits.get(chinese_num[1], 0)
        
        # 处理二十几的数字 (如 "二十")
        if '十' in chinese_num and len(chinese_num) <= 3:
            parts = chinese_num.split('十')
            tens = chinese_digits.get(parts[0], 0) * 10 if parts[0] else 10
            units = chinese_digits.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return float(tens + units)
        
        # 其他复杂情况，返回默认值
        return 10.0
    
    def _extend_herb_database(self):
        """扩展中药数据库 - 添加更多常用中药"""
        additional_herbs = {
            # 补充常用中药（提取自实际处方）
            "白芍": {"category": "补血药", "nature": "苦酸微寒", "meridian": "肝、脾", "functions": ["养血调经", "敛阴止汗", "柔肝止痛", "平抑肝阳"]},
            "当归": {"category": "补血药", "nature": "甘辛温", "meridian": "肝、心、脾", "functions": ["补血", "活血", "调经止痛", "润燥滑肠"]},
            "川芎": {"category": "活血药", "nature": "辛温", "meridian": "肝、胆、心包", "functions": ["活血行气", "祛风止痛"]},
            "红花": {"category": "活血药", "nature": "辛温", "meridian": "心、肝", "functions": ["活血通经", "散瘀止痛"]},
            "桃仁": {"category": "活血药", "nature": "苦甘平", "meridian": "心、肝、肺、大肠", "functions": ["破血行瘀", "润燥滑肠"]},
            "枸杞子": {"category": "补阴药", "nature": "甘平", "meridian": "肝、肾", "functions": ["滋补肝肾", "益精明目"]},
            "菊花": {"category": "清热药", "nature": "甘苦微寒", "meridian": "肺、肝", "functions": ["疏散风热", "平抑肝阳", "清肝明目", "清热解毒"]},
            "薄荷": {"category": "解表药", "nature": "辛凉", "meridian": "肺、肝", "functions": ["疏散风热", "清利头目", "利咽透疹", "疏肝行气"]},
            "地黄": {"category": "补阴药", "nature": "甘微温", "meridian": "肝、肾", "functions": ["滋阴补血", "填精益髓"]},
            "山药": {"category": "补气药", "nature": "甘平", "meridian": "肺、脾、肾", "functions": ["益气养阴", "补脾肺肾", "固精止带"]},
            "白术": {"category": "补气药", "nature": "甘苦温", "meridian": "脾、胃", "functions": ["补气健脾", "燥湿利水", "止汗", "安胎"]},
            "党参": {"category": "补气药", "nature": "甘平", "meridian": "肺、脾", "functions": ["补脾益肺", "养血生津"]},
            "大枣": {"category": "补气药", "nature": "甘温", "meridian": "脾、胃", "functions": ["补中益气", "养血安神", "缓和药性"]},
            "生姜": {"category": "解表药", "nature": "辛微温", "meridian": "肺、脾、胃", "functions": ["解表散寒", "温中止呕", "化痰止咳"]},
            "柴胡": {"category": "解表药", "nature": "苦微寒", "meridian": "肝、胆", "functions": ["疏散退热", "疏肝解郁", "升举阳气"]},
            "黄连": {"category": "清热药", "nature": "苦寒", "meridian": "心、肝、胃、大肠", "functions": ["清热燥湿", "泻火解毒"]},
            "黄芩": {"category": "清热药", "nature": "苦寒", "meridian": "肺、胆、脾、大肠", "functions": ["清热燥湿", "泻火解毒", "止血", "安胎"]},
            "板蓝根": {"category": "清热药", "nature": "苦寒", "meridian": "心、胃", "functions": ["清热解毒", "凉血利咽"]},
            
            # 添加一些可能OCR识别错误但实际是中药的名称
            "丹参": {"category": "活血药", "nature": "苦微寒", "meridian": "心、肝", "functions": ["活血祛瘀", "通经止痛", "清心除烦", "凉血消痈"]},
            "三七": {"category": "活血药", "nature": "甘微苦温", "meridian": "肝、胃", "functions": ["散瘀止血", "消肿定痛"]},
            "天麻": {"category": "平肝药", "nature": "甘平", "meridian": "肝", "functions": ["息风止痉", "平抑肝阳", "祛风通络"]},
            "决明子": {"category": "清热药", "nature": "甘苦咸微寒", "meridian": "肝、肾、大肠", "functions": ["清热明目", "润肠通便"]},
            
            # 地方用药和现代用药
            "罗汉果": {"category": "清热药", "nature": "甘凉", "meridian": "肺、脾", "functions": ["清热润肺", "利咽开音", "滑肠通便"]},
            "胖大海": {"category": "清热药", "nature": "甘寒", "meridian": "肺、大肠", "functions": ["清热润肺", "利咽解毒", "润肠通便"]},
        }
        
        # 合并到主数据库
        self.herb_db.herbs_database.update(additional_herbs)
    
    def _get_herb_category(self, name: str) -> str:
        """获取药物分类"""
        if name in self.herb_db.herbs_database:
            return self.herb_db.herbs_database[name]["category"]
        
        # 基于名称推测分类
        if any(prefix in name for prefix in ["炒", "制", "蜜"]):
            base_name = re.sub(r'^[炒制蜜姜醋酒盐]', '', name)
            if base_name in self.herb_db.herbs_database:
                return self.herb_db.herbs_database[base_name]["category"]
        
        return "其他"
    
    def _get_herb_properties(self, name: str) -> Dict[str, str]:
        """获取药物性味归经"""
        if name in self.herb_db.herbs_database:
            data = self.herb_db.herbs_database[name]
            return {
                "nature": data.get("nature", "未知"),
                "meridian": data.get("meridian", "未知")
            }
        return {"nature": "未知", "meridian": "未知"}
    
    def _get_herb_functions(self, name: str) -> List[str]:
        """获取药物功效"""
        if name in self.herb_db.herbs_database:
            return self.herb_db.herbs_database[name].get("functions", [])
        return []
    
    def _perform_tcm_analysis(self, herbs: List[ChineseHerb], original_text: str) -> PrescriptionAnalysis:
        """执行中医辨证分析"""
        
        # 1. 药物分类统计
        herb_classification = self._classify_herbs(herbs)
        
        # 2. 方证模式识别
        prescription_pattern = self._identify_prescription_pattern(herbs)
        
        # 3. 证候分析
        syndrome_analysis = self._analyze_syndrome(herbs, herb_classification)
        
        # 4. 临床评估
        clinical_assessment = self._clinical_assessment(herbs, herb_classification)
        
        # 5. 专业点评 (传入君臣佐使分析结果)
        professional_comments = self._generate_professional_comments(herbs, herb_classification, syndrome_analysis, clinical_assessment["herb_roles"])
        
        return {
            "herbs": [self._herb_to_dict(herb) for herb in herbs],
            "total_herbs": len(herbs),
            "prescription_pattern": prescription_pattern,
            "syndrome_analysis": syndrome_analysis,
            "herb_classification": herb_classification,
            "clinical_assessment": clinical_assessment,
            "professional_comments": professional_comments
        }
    
    def _classify_herbs(self, herbs: List[ChineseHerb]) -> Dict[str, List[str]]:
        """药物分类统计"""
        classification = {}
        
        for herb in herbs:
            category = herb.category
            if category not in classification:
                classification[category] = []
            classification[category].append(f"{herb.name} {herb.dosage}g")
        
        return classification
    
    def _identify_prescription_pattern(self, herbs: List[ChineseHerb]) -> str:
        """识别方证模式"""
        herb_names = {herb.name for herb in herbs}
        
        # 检查是否匹配经典方剂
        for formula_name, formula_herbs in self.herb_db.classic_formulas.items():
            match_count = len([h for h in formula_herbs if h in herb_names])
            match_ratio = match_count / len(formula_herbs)
            
            if match_ratio >= 0.6:  # 60%匹配度
                return f"疑似{formula_name}加减方（匹配度{match_ratio:.1%}）"
        
        # 基于主要药物功效分析
        categories = [herb.category for herb in herbs]
        if categories.count("清热药") >= 3:
            return "清热类方剂"
        elif categories.count("补气药") >= 2:
            return "补益类方剂"
        elif categories.count("化痰药") >= 2 and categories.count("止咳药") >= 1:
            return "止咳化痰类方剂"
        else:
            return "复合型方剂"
    
    def _analyze_syndrome(self, herbs: List[ChineseHerb], classification: Dict) -> Dict[str, Any]:
        """证候分析"""
        syndrome_clues = []
        primary_syndrome = ""
        
        # 基于药物组合分析证候
        if "清热药" in classification and len(classification["清热药"]) >= 2:
            syndrome_clues.append("热证")
            if "化痰药" in classification:
                primary_syndrome = "痰热证"
            else:
                primary_syndrome = "热证"
        
        if "化痰药" in classification and "止咳药" in classification:
            syndrome_clues.append("痰湿证")
            if not primary_syndrome:
                primary_syndrome = "痰湿蕴肺证"
        
        if "补气药" in classification:
            syndrome_clues.append("气虚证")
            if not primary_syndrome:
                primary_syndrome = "脾肺气虚证"
        
        return {
            "primary_syndrome": primary_syndrome or "复合证候",
            "syndrome_clues": syndrome_clues,
            "confidence": 0.7 if primary_syndrome else 0.5
        }
    
    def _clinical_assessment(self, herbs: List[ChineseHerb], classification: Dict) -> Dict[str, Any]:
        """临床评估"""
        assessment = {
            "prescription_reasonableness": "合理",
            "dosage_assessment": [],
            "safety_notes": [],
            "efficacy_prediction": "",
            "herb_roles": self._analyze_herb_roles(herbs, classification)  # 新增：君臣佐使分析
        }
        
        # 剂量评估
        assessment["dosage_notes"] = []
        for herb in herbs:
            if herb.dosage > 30:
                assessment["dosage_notes"].append(f"{herb.name}剂量偏大({herb.dosage}g)，请注意安全性")
            elif herb.dosage < 3:
                assessment["dosage_notes"].append(f"{herb.name}剂量偏小({herb.dosage}g)，可能影响疗效")
        
        # 安全性提示
        toxic_herbs = ["半夏", "附子", "乌头"]  # 示例有毒药物
        for herb in herbs:
            if herb.name in toxic_herbs:
                assessment["safety_notes"].append(f"{herb.name}为有毒药物，需严格控制用量")
        
        return assessment
    
    def _analyze_herb_roles(self, herbs: List[ChineseHerb], classification: Dict) -> Dict[str, List[Dict]]:
        """分析药材的君臣佐使角色"""
        
        # 君臣佐使分析规则
        herb_roles = {
            "君药": [],  # 主治药物，剂量通常较大
            "臣药": [],  # 辅助君药或主治兼证
            "佐药": [],  # 佐助或制约
            "使药": []   # 引经或调和
        }
        
        # 按剂量排序（君药通常剂量大）
        sorted_herbs = sorted(herbs, key=lambda x: x.dosage, reverse=True)
        total_herbs = len(sorted_herbs)
        
        for i, herb in enumerate(sorted_herbs):
            herb_info = {
                "name": herb.name,
                "dosage": f"{herb.dosage}g",
                "category": herb.category,
                "functions": herb.functions,
                "role_reason": ""
            }
            
            # 君药判定（通常是剂量最大的1-2味主要药物）
            if i < max(1, total_herbs // 4) and herb.dosage >= 10:
                # 基于药物功效判断是否为君药
                if any(func in ["清热解毒", "补气", "养血", "温阳", "滋阴"] for func in herb.functions):
                    herb_info["role_reason"] = f"剂量较大({herb.dosage}g)，功效针对主证"
                    herb_roles["君药"].append(herb_info)
                    continue
            
            # 臣药判定（协助君药或治疗兼证）
            if herb.dosage >= 6 and len(herb_roles["君药"]) > 0:
                # 检查是否与君药协同
                jun_categories = [jun["category"] for jun in herb_roles["君药"]]
                if herb.category in jun_categories or any(cat in jun_categories for cat in [herb.category]):
                    herb_info["role_reason"] = f"协助君药发挥作用，同属{herb.category}"
                    herb_roles["臣药"].append(herb_info)
                    continue
            
            # 佐药判定（剂量适中，有特殊作用）
            if 3 <= herb.dosage < 12:
                # 常见佐药功效
                zuo_functions = ["理气", "化痰", "止咳", "安神", "开胃", "消食"]
                if any(func in zuo_functions for func in herb.functions):
                    herb_info["role_reason"] = f"调理气机或化解副作用"
                    herb_roles["佐药"].append(herb_info)
                    continue
            
            # 使药判定（剂量通常较小）
            if herb.dosage <= 6:
                # 常见使药
                shi_herbs = ["甘草", "生姜", "大枣", "蜂蜜", "薄荷"]
                if herb.name in shi_herbs:
                    herb_info["role_reason"] = f"调和诸药或引经"
                    herb_roles["使药"].append(herb_info)
                    continue
                # 根据功效判断
                elif "调和" in herb.functions or "引经" in herb.functions:
                    herb_info["role_reason"] = f"引经报使或调和药性"
                    herb_roles["使药"].append(herb_info)
                    continue
            
            # 如果未能明确分类，根据剂量和位置分配
            if len(herb_roles["臣药"]) < total_herbs // 3:
                herb_info["role_reason"] = f"辅助治疗，剂量{herb.dosage}g"
                herb_roles["臣药"].append(herb_info)
            else:
                herb_info["role_reason"] = f"调理配伍，剂量{herb.dosage}g"
                herb_roles["佐药"].append(herb_info)
        
        return herb_roles
    
    def _generate_professional_comments(self, herbs: List[ChineseHerb], classification: Dict, syndrome: Dict, herb_roles: Dict) -> List[str]:
        """生成专业点评"""
        comments = []
        
        # 1. 处方结构分析
        comments.append(f"处方共{len(herbs)}味药，药物配伍层次分明")
        
        # 2. 药物分类点评
        for category, herb_list in classification.items():
            comments.append(f"【{category}】: {', '.join(herb_list)}")
        
        # 3. 配伍特点
        if "清热药" in classification and "化痰药" in classification:
            comments.append("清热化痰并用，体现了热痰同治的配伍思想")
        
        if "补气药" in classification and len([h for h in herbs if h.category == "补气药"]) >= 2:
            comments.append("重用补气药物，符合'虚者补之'的治疗原则")
        
        # 4. 君臣佐使分析 (使用统一的分析结果)
        if herb_roles.get("君药"):
            jun_herbs = herb_roles["君药"]
            jun_herb_names = ', '.join([f"{herb['name']}({herb['dosage']})" for herb in jun_herbs])
            comments.append(f"君药为: {jun_herb_names}")
        
        if herb_roles.get("臣药"):
            chen_herbs = herb_roles["臣药"]  
            chen_count = len(chen_herbs)
            comments.append(f"臣药{chen_count}味，辅助君药发挥主要功效")
        
        # 5. 证候相符性
        if syndrome["primary_syndrome"]:
            comments.append(f"整体配伍针对'{syndrome['primary_syndrome']}'，方证相符")
        
        return comments
    
    def _deduplicate_and_rank_herbs(self, herbs: List[ChineseHerb]) -> List[ChineseHerb]:
        """去重并按置信度排序"""
        seen = set()
        unique_herbs = []
        
        # 按置信度排序
        herbs.sort(key=lambda x: x.confidence, reverse=True)
        
        for herb in herbs:
            key = f"{herb.name}_{herb.dosage}"
            if key not in seen:
                seen.add(key)
                unique_herbs.append(herb)
        
        return unique_herbs
    
    def _calculate_overall_confidence(self, herbs: List[ChineseHerb]) -> float:
        """计算整体分析置信度"""
        if not herbs:
            return 0.0
        
        avg_confidence = sum(h.confidence for h in herbs) / len(herbs)
        
        # 基于药物数量调整
        if len(herbs) >= 8:
            avg_confidence += 0.1
        elif len(herbs) >= 5:
            avg_confidence += 0.05
        
        return min(avg_confidence, 1.0)
    
    def _herb_to_dict(self, herb: ChineseHerb) -> Dict[str, Any]:
        """中药信息转字典格式"""
        return {
            "name": herb.name,
            "dosage": herb.dosage,
            "unit": herb.unit,
            "category": herb.category,
            "properties": herb.properties,
            "functions": herb.functions,
            "confidence": round(herb.confidence, 3),
            "raw_text": herb.raw_text
        }

# 全局实例
intelligent_analyzer = None

def get_intelligent_prescription_analyzer():
    """获取智能处方分析器实例"""
    global intelligent_analyzer
    if intelligent_analyzer is None:
        intelligent_analyzer = IntelligentPrescriptionAnalyzer()
    return intelligent_analyzer

# 测试函数
def test_intelligent_analyzer():
    """测试智能分析器"""
    test_text = """
    桔梗（净）10(克)*7帖 12.11
    荆芥（净）10(克)*7帖 5.04
    百部（净）10(克)*7帖 7.7
    甘草（净）6(克)*7帖 4.24
    陈皮（净）10(克)*7帖 2.45
    百合（净）10(克)*7帖 9.66
    炒莱菔子（净）15(克)*7帖 4.52
    炒紫苏子（净）15(克)*7帖 10.92
    姜半夏（净）6(克)*7帖 18.65
    茯苓（净）15(克)*7帖 11.87
    蝉蜕（净）6(克)*7帖 101.68
    浙贝母（净）10(克)*7帖 14.42
    """
    
    analyzer = get_intelligent_prescription_analyzer()
    result = analyzer.analyze_prescription(test_text)
    print("=== 智能处方分析结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    test_intelligent_analyzer()