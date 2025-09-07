#!/usr/bin/env python3
"""
集成版增强处方解析器 - 修复药材识别问题
合并了OCR识别结果处理和智能药材提取功能
现在集成了模糊药材提取器
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
import logging

# 导入模糊提取器
try:
    from fuzzy_herb_extractor import FuzzyHerbExtractor
    fuzzy_extractor_available = True
except ImportError:
    fuzzy_extractor_available = False
    print("警告: 模糊药材提取器不可用")

logger = logging.getLogger(__name__)

@dataclass
class ExtractedHerb:
    """提取的药材信息"""
    name: str
    dosage: float
    unit: str
    confidence: float
    source_line: str
    line_number: int
    extraction_method: str

class IntegratedPrescriptionParser:
    """集成版处方解析器 - 修复版"""
    
    def __init__(self):
        # 初始化模糊提取器
        if fuzzy_extractor_available:
            self.fuzzy_extractor = FuzzyHerbExtractor()
            logger.info("模糊药材提取器初始化成功")
        else:
            self.fuzzy_extractor = None
            logger.warning("模糊药材提取器不可用")
        
        # 扩展的中药名称库
        self.known_herbs = {
            # OCR实测识别的药材
            "桔梗", "荆芥", "百部", "甘草", "陈皮", "百合", "茯苓", "浙贝母", 
            "蝉蜕", "炒莱菔子", "炒紫苏子", "姜半夏", "扯根菜", "甜叶菊",
            
            # 常用中药补充
            "当归", "白芍", "川芎", "熟地", "人参", "黄芪", "白术", "党参",
            "麦冬", "五味子", "枸杞子", "菊花", "金银花", "连翘", "黄芩", 
            "黄连", "黄柏", "板蓝根", "大青叶", "蒲公英", "车前草", "半夏",
            "生姜", "大枣", "桂枝", "柴胡", "麻黄", "杏仁", "石膏", "芍药",
            "丹参", "三七", "天麻", "决明子", "罗汉果", "胖大海", "山药",
            "枸杞", "红枣", "桂圆", "莲子", "百合", "银耳", "薏米", "红豆"
        }
        
        # 文档类型检测关键词
        self.billing_keywords = {
            "结算", "告知单", "门诊号", "总金额", "医保", "支付", "浙里办", 
            "服务热线", "收费", "发票", "智慧医疗", "费用清单", "报销"
        }
        
        self.prescription_keywords = {
            "处方", "方剂", "药方", "中药", "汤剂", "煎服", "水煎", 
            "每日", "分服", "温服", "饭前", "饭后", "早晚"
        }
        
        # 排除关键词（避免误识别）
        self.exclude_keywords = {
            "服务", "热线", "电话", "联系", "咨询", "扫码", "网址", "地址",
            "微信", "支付宝", "银行", "医保", "发票", "收据", "门诊", "号码",
            "总金额", "报销", "自费", "现金", "浙里办", "智慧医疗", "结算",
            "清单", "项目", "数量", "金额", "元", "次", "人次"
        }
    
    def parse_prescription_with_validation(self, text: str) -> Dict[str, Any]:
        """增强版处方解析，包含文档类型验证和修复的药材提取"""
        
        try:
            # 1. 文档类型检测
            doc_type_result = self._detect_document_type(text)
            
            # 2. 药材提取（即使是费用单，也可能包含药材信息）
            herbs = self._extract_herbs_enhanced(text)
            
            if len(herbs) == 0:
                return {
                    "success": False,
                    "error": "未能从文档中识别到有效的中药信息",
                    "document_type": doc_type_result["type"],
                    "detection_confidence": doc_type_result["confidence"],
                    "suggestion": "请确保上传的文档包含清晰的中药处方信息"
                }
            
            # 3. 如果是费用单但包含药材信息，给出特殊提示
            if doc_type_result["type"] == "billing" and len(herbs) >= 3:
                return {
                    "success": True,
                    "document_type": "billing_with_prescription",  # 特殊类型
                    "detection_confidence": doc_type_result["confidence"],
                    "herbs": [self._herb_to_dict(herb) for herb in herbs],
                    "total_herbs": len(herbs),
                    "special_note": "检测到这是医疗费用单，但成功从中提取了处方药材信息",
                    "validation": self._validate_prescription(herbs, text),
                    "parsing_notes": [
                        f"从费用单中识别到{len(herbs)}味中药",
                        "费用单中的处方信息仅供参考，建议参考原始处方单"
                    ]
                }
            
            # 4. 标准处方结果
            return {
                "success": True,
                "document_type": doc_type_result["type"],
                "detection_confidence": doc_type_result["confidence"],
                "herbs": [self._herb_to_dict(herb) for herb in herbs],
                "total_herbs": len(herbs),
                "validation": self._validate_prescription(herbs, text),
                "parsing_notes": self._generate_parsing_notes(herbs, text)
            }
            
        except Exception as e:
            logger.error(f"集成版处方解析失败: {e}")
            return {
                "success": False,
                "error": f"处方解析异常: {str(e)}"
            }
    
    def _detect_document_type(self, text: str) -> Dict[str, Any]:
        """检测文档类型"""
        
        billing_score = 0
        prescription_score = 0
        
        # 统计关键词
        for keyword in self.billing_keywords:
            if keyword in text:
                billing_score += 2
        
        for keyword in self.prescription_keywords:
            if keyword in text:
                prescription_score += 2
        
        # 特殊模式检测
        if re.search(r'智慧医疗结算.*告知单', text):
            billing_score += 10
        
        if re.search(r'门诊号码?\s*[:：]\s*\d+', text):
            billing_score += 5
        
        if re.search(r'总金额\s*[:：]\s*\d+\.?\d*', text):
            billing_score += 5
        
        # 判断文档类型
        if billing_score > prescription_score:
            return {
                "type": "billing",
                "confidence": min(billing_score / 15.0, 1.0)
            }
        else:
            return {
                "type": "prescription",
                "confidence": min(prescription_score / 10.0, 0.8)
            }
    
    
    def _handle_separated_herbs_dosages(self, lines: List[str]) -> List[ExtractedHerb]:
        """处理药名和剂量分离的情况 - 新增功能"""
        
        herbs = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # 检查这行是否是单独的药名（没有剂量）
            herb_match = self._is_single_herb_name(line)
            if herb_match:
                herb_name = herb_match
                
                # 在后续行中查找对应的剂量
                dosage_found = False
                for j in range(i + 1, min(i + 3, len(lines))):  # 查找后面2行
                    next_line = lines[j].strip()
                    dosage_match = self._extract_standalone_dosage(next_line)
                    
                    if dosage_match:
                        dosage, unit = dosage_match
                        
                        herbs.append(ExtractedHerb(
                            name=herb_name,
                            dosage=dosage,
                            unit=unit,
                            confidence=0.8,  # 分离匹配置信度较低
                            source_line=f"{line} + {next_line}",
                            line_number=i + 1,
                            extraction_method="separated_herb_dosage"
                        ))
                        
                        dosage_found = True
                        break
                
                # 如果没找到剂量，记录为无剂量药材
                if not dosage_found:
                    herbs.append(ExtractedHerb(
                        name=herb_name,
                        dosage=0.0,
                        unit="",
                        confidence=0.5,
                        source_line=line,
                        line_number=i + 1,
                        extraction_method="herb_name_only"
                    ))
            
            i += 1
        
        return herbs
    
    def _is_single_herb_name(self, line: str) -> Optional[str]:
        """判断是否是单独的药名行"""
        
        line_clean = line.strip()
        
        # 排除包含数字的行（可能已经包含剂量）
        if re.search(r'\d', line_clean):
            return None
        
        # 排除过短或过长的行
        if len(line_clean) < 2 or len(line_clean) > 6:
            return None
        
        # 检查是否是已知药材
        for herb in self.known_herbs:
            if herb in line_clean:
                return herb
        
        # 使用模糊匹配
        if self.fuzzy_extractor:
            try:
                fuzzy_result = self.fuzzy_extractor.extract_herbs_from_noisy_text(line_clean)
                if fuzzy_result:
                    return fuzzy_result[0]['name']
            except:
                pass  # 模糊匹配失败时继续
        
        return None
    
    def _extract_standalone_dosage(self, line: str) -> Optional[Tuple[float, str]]:
        """提取单独的剂量行"""
        
        line_clean = line.strip()
        
        # 匹配各种剂量格式
        dosage_patterns = [
            r'^(\d+(?:\.\d+)?)\s*([gG克])\s*$',     # "15g"
            r'^(\d+(?:\.\d+)?)\s*(克)\s*$',         # "15克"
            r'^(\d+(?:\.\d+)?)\s*([片粒颗])\s*$',    # "3片"
            r'^(\d+(?:\.\d+)?)\s*(毫升|[mM][lL])\s*$', # "10ml"
            r'^(\d+(?:\.\d+)?)\s*(枚|个|支)\s*$'     # "12枚"
        ]
        
        for pattern in dosage_patterns:
            match = re.match(pattern, line_clean)
            if match:
                dosage = float(match.group(1))
                unit = match.group(2)
                return dosage, unit
        
        return None

    def _extract_herbs_enhanced(self, text: str) -> List[ExtractedHerb]:
        """增强版药材提取 - 修复版，集成模糊提取器"""
        
        herbs = []
        lines = text.split('\n')
        
        # 首先尝试处理分离的药名和剂量
        separated_herbs = self._handle_separated_herbs_dosages(lines)
        if separated_herbs:
            herbs.extend(separated_herbs)
            logger.info(f"分离处理找到 {len(separated_herbs)} 味药材")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # 跳过明显的非药材行
            if any(keyword in line for keyword in self.exclude_keywords):
                continue
            
            # 多模式药材提取
            herb_results = self._extract_herbs_from_line(line, line_num)
            herbs.extend(herb_results)
        
        # 如果标准提取结果很少且模糊提取器可用，使用模糊提取器作为后备
        if len(herbs) < 2 and self.fuzzy_extractor is not None:
            logger.info("标准提取结果较少，启用模糊提取器作为后备")
            try:
                fuzzy_results = self.fuzzy_extractor.extract_herbs_from_noisy_text(text)
                for fuzzy_herb in fuzzy_results:
                    # 转换格式
                    herb = ExtractedHerb(
                        name=fuzzy_herb['name'],
                        dosage=fuzzy_herb['dosage'],
                        unit=fuzzy_herb['unit'],
                        confidence=fuzzy_herb['confidence'],
                        source_line=fuzzy_herb['source_line'],
                        line_number=fuzzy_herb['line_number'],
                        extraction_method=f"fuzzy_{fuzzy_herb['extraction_method']}"
                    )
                    herbs.append(herb)
                logger.info(f"模糊提取器补充了 {len(fuzzy_results)} 味药材")
            except Exception as e:
                logger.error(f"模糊提取器运行错误: {e}")
        
        # 去重和排序
        herbs = self._deduplicate_herbs(herbs)
        herbs.sort(key=lambda x: x.confidence, reverse=True)
        
        return herbs
    
    def _extract_herbs_from_line(self, line: str, line_num: int) -> List[ExtractedHerb]:
        """从单行提取药材"""
        
        results = []
        
        # 针对OCR费用单格式的精确模式
        patterns = [
            {
                "name": "ocr_billing_format",
                "pattern": r'^([^\s\(（]+)（净）\([^)]*\)\s*(\d+(?:\.\d+)?)\([克g]\)\*\d+帖\s+[\d.]+$',
                "priority": 1.0
            },
            {
                "name": "ocr_simple_format", 
                "pattern": r'([^\s\(（]+)（净）.*?(\d+(?:\.\d+)?)[克g]',
                "priority": 0.9
            },
            {
                "name": "standard_prescription",
                "pattern": r'([一-龯\u4e00-\u9fff]{2,6})\s+(\d+(?:\.\d+)?)\s*[克g]',
                "priority": 0.8
            },
            {
                "name": "loose_match",
                "pattern": r'([一-龯\u4e00-\u9fff]{2,6})[^一-龯\u4e00-\u9fff]*?(\d+(?:\.\d+)?)',
                "priority": 0.6
            }
        ]
        
        for pattern_info in patterns:
            matches = re.findall(pattern_info["pattern"], line)
            
            for match in matches:
                if len(match) >= 2:
                    herb_name = match[0].strip()
                    dosage_str = match[1].strip()
                    
                    # 验证药材有效性
                    if self._is_valid_herb(herb_name, line):
                        try:
                            dosage = float(dosage_str)
                            if 0.5 <= dosage <= 100:  # 合理剂量范围
                                confidence = self._calculate_confidence(
                                    herb_name, dosage, line, pattern_info["priority"]
                                )
                                
                                if confidence >= 0.3:
                                    results.append(ExtractedHerb(
                                        name=herb_name,
                                        dosage=dosage,
                                        unit="g",
                                        confidence=confidence,
                                        source_line=line,
                                        line_number=line_num,
                                        extraction_method=pattern_info["name"]
                                    ))
                        except ValueError:
                            continue
        
        return results
    
    def _is_valid_herb(self, name: str, context: str) -> bool:
        """验证是否为有效药材名称"""
        
        # 基础验证
        if len(name) < 2 or len(name) > 8:
            return False
        
        # 必须是中文字符
        if not all('\u4e00' <= c <= '\u9fff' for c in name):
            return False
        
        # 在已知药材库中
        if name in self.known_herbs:
            return True
        
        # 检查去炮制后的名称
        clean_name = re.sub(r'^[生熟炙蒸炒制醋酒盐蜜]+', '', name)
        if clean_name in self.known_herbs:
            return True
        
        return False
    
    def _calculate_confidence(self, name: str, dosage: float, context: str, pattern_priority: float) -> float:
        """计算识别置信度"""
        
        confidence = 0.3 + pattern_priority * 0.2
        
        # 在已知药材库中
        if name in self.known_herbs:
            confidence += 0.4
        else:
            clean_name = re.sub(r'^[生熟炙蒸炒制醋酒盐蜜]+', '', name)
            if clean_name in self.known_herbs:
                confidence += 0.3
        
        # 剂量合理性
        if 3 <= dosage <= 30:
            confidence += 0.2
        elif 1 <= dosage <= 50:
            confidence += 0.1
        
        # 上下文特征
        if "（净）" in context:
            confidence += 0.15
        if "帖" in context:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _deduplicate_herbs(self, herbs: List[ExtractedHerb]) -> List[ExtractedHerb]:
        """药材去重，保留置信度最高的"""
        
        herb_dict = {}
        
        for herb in herbs:
            key = f"{herb.name}_{herb.dosage}"
            
            if key not in herb_dict or herb.confidence > herb_dict[key].confidence:
                herb_dict[key] = herb
        
        return list(herb_dict.values())
    
    def _validate_prescription(self, herbs: List[ExtractedHerb], text: str) -> Dict[str, Any]:
        """处方合理性验证"""
        
        issues = []
        warnings = []
        
        if len(herbs) < 3:
            warnings.append(f"处方药味较少({len(herbs)}味)，请确认是否完整")
        
        if len(herbs) > 20:
            warnings.append(f"处方药味较多({len(herbs)}味)，请检查是否重复识别")
        
        # 置信度检查
        low_confidence_herbs = [h for h in herbs if h.confidence < 0.7]
        if low_confidence_herbs:
            warnings.append(f"有{len(low_confidence_herbs)}味药物识别置信度较低，请核实")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "confidence_summary": {
                "average": sum(h.confidence for h in herbs) / len(herbs) if herbs else 0,
                "lowest": min(h.confidence for h in herbs) if herbs else 0,
                "highest": max(h.confidence for h in herbs) if herbs else 0
            }
        }
    
    def _herb_to_dict(self, herb: ExtractedHerb) -> Dict[str, Any]:
        """药材信息转字典"""
        
        return {
            "name": herb.name,
            "dosage": herb.dosage,
            "unit": herb.unit,
            "confidence": round(herb.confidence, 3),
            "source_line": herb.source_line,
            "line_number": herb.line_number,
            "extraction_method": herb.extraction_method
        }
    
    def _generate_parsing_notes(self, herbs: List[ExtractedHerb], text: str) -> List[str]:
        """生成解析说明"""
        
        notes = []
        notes.append(f"成功识别{len(herbs)}味中药")
        
        high_conf = len([h for h in herbs if h.confidence >= 0.8])
        if high_conf > 0:
            notes.append(f"其中{high_conf}味药物高置信度识别")
        
        # 按提取方法统计
        method_count = {}
        for herb in herbs:
            method = herb.extraction_method
            method_count[method] = method_count.get(method, 0) + 1
        
        if "ocr_billing_format" in method_count:
            notes.append(f"使用OCR费用单格式识别了{method_count['ocr_billing_format']}味药物")
        
        return notes

# 全局实例
integrated_parser = None

def get_integrated_prescription_parser():
    """获取集成版处方解析器实例"""
    global integrated_parser
    if integrated_parser is None:
        integrated_parser = IntegratedPrescriptionParser()
    return integrated_parser

def parse_prescription_text(text: str) -> Dict[str, Any]:
    """解析处方文本 - 主入口函数"""
    parser = get_integrated_prescription_parser()
    return parser.parse_prescription_with_validation(text)

if __name__ == "__main__":
    # 测试代码
    test_text = """
丁兰街道社区卫生服务中心
智慧医疗结算告知单
门诊号码：208514374
桔梗（净）(k克) 10(克)*7帖 12.11
荆芥（净）(k克) 10(克)*7帖 5.04
百部（净）(k克) 10(克)*7帖 7.7
甘草（净）(k克) 6(克)*7帖 4.24
陈皮（净）(k克) 10(克)*7帖 2.45
百合（净）(k克) 10(克)*7帖 9.66
炒莱菔子（净）(k克) 15(克)*7帖 4.52
炒紫苏子（净）(k克) 15(克)*7帖 10.92
姜半夏（净）(k克) 6(克)*7帖 18.65
茯苓（净）(k克) 15(克)*7帖 11.87
蝉蜕（净）(k克) 6(克)*7帖 101.68
浙贝母（净）(k克) 10(克)*7帖 14.42
总金额：344.72
浙里办服务热线0571-8808880
"""
    
    result = parse_prescription_text(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
