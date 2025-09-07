#!/usr/bin/env python3
"""
中医处方检查系统 - Prescription Checker for TCM
功能：处方解析、安全检查、合理性验证、名医经验学习
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import sqlite3
from pathlib import Path

@dataclass
class Herb:
    """中药信息结构"""
    name: str  # 药物名称
    dosage: str  # 剂量 (如 "10g", "6-10g")
    unit: str = "g"  # 单位
    preparation: Optional[str] = None  # 炮制方法 (如 "生", "炙", "蒸")
    frequency: Optional[str] = None  # 用药频次
    
@dataclass 
class Prescription:
    """处方信息结构"""
    herbs: List[Herb]  # 药物列表
    preparation_method: Optional[str] = None  # 制备方法 (如 "水煎服")
    usage_instructions: Optional[str] = None  # 服用方法
    course_duration: Optional[str] = None  # 疗程
    doctor_name: Optional[str] = None  # 医生姓名
    syndrome_pattern: Optional[str] = None  # 证候
    disease_name: Optional[str] = None  # 疾病名称
    created_at: Optional[str] = None  # 创建时间

class PrescriptionParser:
    """处方解析引擎"""
    
    def __init__(self):
        # 中药名称词典 - 常用500种中药
        self.herb_names = {
            # 解表药
            "麻黄", "桂枝", "紫苏叶", "防风", "荆芥", "薄荷", "牛蒡子", "蝉蜕", "桑叶", "菊花",
            "柴胡", "升麻", "葛根", "白芷", "辛夷", "苍耳子", "藿香", "佩兰", "香薷",
            
            # 清热药
            "石膏", "知母", "天花粉", "芦根", "竹叶", "栀子", "黄芩", "黄连", "黄柏", "龙胆草",
            "苦参", "白鲜皮", "金银花", "连翘", "板蓝根", "大青叶", "蒲公英", "紫花地丁",
            "鱼腥草", "白头翁", "马齿苋", "射干", "山豆根", "马勃", "青黛", "大黄", "芒硝",
            "番泻叶", "芦荟", "牡丹皮", "赤芍", "紫草", "玄参", "生地黄", "牛黄", "羚羊角",
            
            # 泻下药
            "大黄", "芒硝", "番泻叶", "芦荟", "火麻仁", "郁李仁", "松子仁", "甘遂", "京大戟",
            "芫花", "商陆", "牵牛子", "巴豆",
            
            # 祛风湿药
            "独活", "羌活", "防己", "木瓜", "蚕沙", "伸筋草", "路路通", "桑寄生", "五加皮",
            "威灵仙", "秦艽", "防风", "豨莶草", "络石藤", "雷公藤", "青风藤", "海风藤",
            
            # 化湿药
            "苍术", "厚朴", "广藿香", "佩兰", "白豆蔻", "砂仁", "草豆蔻", "草果",
            
            # 利水渗湿药
            "茯苓", "猪苓", "泽泻", "薏苡仁", "车前子", "滑石", "通草", "木通", "瞿麦",
            "萹蓄", "地肤子", "海金沙", "石韦", "萆薢", "茵陈", "金钱草", "虎杖",
            
            # 温里药
            "附子", "肉桂", "干姜", "吴茱萸", "细辛", "丁香", "小茴香", "八角茴香", "花椒",
            "荜茇", "高良姜", "胡椒", "白胡椒",
            
            # 理气药
            "陈皮", "青皮", "枳实", "枳壳", "木香", "沉香", "檀香", "川楝子", "乌药",
            "荔枝核", "香附", "佛手", "香橼", "玫瑰花", "绿萼梅", "薤白", "大腹皮",
            "刀豆", "柿蒂", "甘松", "九香虫",
            
            # 消食药
            "山楂", "神曲", "麦芽", "谷芽", "莱菔子", "鸡内金", "隔山撬", "阿魏",
            
            # 驱虫药
            "使君子", "苦楝皮", "槟榔", "南瓜子", "鹤草芽", "雷丸", "榧子",
            
            # 止血药
            "大蓟", "小蓟", "地榆", "白茅根", "槐花", "侧柏叶", "白及", "仙鹤草",
            "茜草", "蒲黄", "五灵脂", "花蕊石", "降香", "血余炭", "棕榈炭", "藕节",
            "艾叶", "灶心土",
            
            # 活血化瘀药
            "川芎", "延胡索", "郁金", "姜黄", "乳香", "没药", "五灵脂", "蒲黄", "红花",
            "桃仁", "益母草", "泽兰", "丹参", "虎杖", "鸡血藤", "牛膝", "川牛膝",
            "王不留行", "穿山甲", "水蛭", "虻虫", "土鳖虫", "马钱子", "自然铜",
            "苏木", "月季花", "凌霄花", "刘寄奴", "骨碎补", "血竭", "儿茶", "三七",
            
            # 化痰止咳平喘药
            "半夏", "陈皮", "茯苓", "甘草", "桔梗", "川贝母", "浙贝母", "瓜蒌", "竹茹",
            "竹沥", "天竺黄", "前胡", "白前", "桑白皮", "葶苈子", "杏仁", "紫菀", "款冬花",
            "百部", "紫苏子", "白芥子", "莱菔子", "海藻", "昆布", "海蛤壳", "瓦楞子",
            "海浮石", "浮海石", "礞石", "白附子", "天南星", "禹白附", "山慈菇", "半边莲",
            "白花蛇舌草", "猫爪草",
            
            # 安神药
            "朱砂", "磁石", "龙骨", "牡蛎", "琥珀", "酸枣仁", "柏子仁", "远志", "合欢皮",
            "夜交藤", "灵芝", "珍珠", "珍珠母",
            
            # 平肝息风药
            "石决明", "珍珠母", "牡蛎", "代赭石", "刺蒺藜", "罗布麻叶", "天麻", "钩藤",
            "地龙", "全蝎", "蜈蚣", "白僵蚕", "羚羊角", "牛黄",
            
            # 开窍药
            "麝香", "冰片", "樟脑", "苏合香", "石菖蒲", "远志",
            
            # 补虚药
            # 补气药
            "人参", "西洋参", "党参", "太子参", "黄芪", "白术", "山药", "扁豆", "甘草",
            "大枣", "刺五加", "绞股蓝", "红景天", "沙棘",
            
            # 补阳药
            "鹿茸", "紫河车", "冬虫夏草", "蛤蚧", "核桃仁", "韭菜子", "菟丝子", "淫羊藿",
            "仙茅", "巴戟天", "肉苁蓉", "锁阳", "补骨脂", "益智仁", "覆盆子", "五味子",
            "沙苑子", "海马", "海龙", "杜仲", "续断", "狗脊", "鹿角胶", "鹿角霜",
            
            # 补血药
            "当归", "熟地黄", "白芍", "阿胶", "何首乌", "龙眼肉", "桑椹", "黑芝麻",
            
            # 补阴药
            "北沙参", "南沙参", "百合", "麦冬", "天冬", "石斛", "玉竹", "黄精", "枸杞子",
            "墨旱莲", "女贞子", "桑椹", "黑芝麻", "龟板", "鳖甲", "牡蛎",
            
            # 收涩药
            "五味子", "乌梅", "五倍子", "罂粟壳", "肉豆蔻", "赤石脂", "禹余粮", "桑螵蛸",
            "海螵蛸", "莲子", "芡实", "山茱萸", "覆盆子", "金樱子", "椿皮", "石榴皮",
            "诃子", "肉桂", "鸡内金",
            
            # 涌吐药
            "常山", "瓜蒂", "胆矾", "藜芦",
            
            # 杀虫燥湿止痒药
            "硫黄", "雄黄", "白矾", "蛇床子", "土荆皮", "花椒", "蜂房", "鹤虱",
            
            # 拔毒消肿敛疮药
            "升药", "轻粉", "红粉", "铅丹", "炉甘石",
        }
        
        # 单位标准化
        self.dosage_units = ["g", "克", "钱", "两", "斤", "ml", "毫升", "片", "粒", "丸"]
        
        # 剂型和煎服方法
        self.preparation_methods = [
            "水煎服", "煎汤服", "冲服", "含服", "研末服", "丸剂", "散剂", "膏剂",
            "酒剂", "茶剂", "外敷", "熏洗", "先煎", "后下", "包煎", "另煎", "烊化"
        ]
    
    def parse_prescription_text(self, text: str) -> Optional[Prescription]:
        """解析处方文本，提取结构化信息"""
        try:
            # 清理文本
            text = self._clean_text(text)
            
            # 提取药物列表
            herbs = self._extract_herbs(text)
            if not herbs:
                return None
                
            # 提取制备方法
            preparation_method = self._extract_preparation_method(text)
            
            # 提取用法用量
            usage_instructions = self._extract_usage_instructions(text)
            
            # 提取疗程
            course_duration = self._extract_course_duration(text)
            
            # 提取证候
            syndrome_pattern = self._extract_syndrome_pattern(text)
            
            # 提取疾病名称
            disease_name = self._extract_disease_name(text)
            
            return Prescription(
                herbs=herbs,
                preparation_method=preparation_method,
                usage_instructions=usage_instructions,
                course_duration=course_duration,
                syndrome_pattern=syndrome_pattern,
                disease_name=disease_name,
                created_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"处方解析错误: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """清理处方文本"""
        # 移除多余空格和换行
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符但保留中医术语
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\-\.\(\)（），,、：:；;]', ' ', text)
        return text.strip()
    
    def _extract_herbs(self, text: str) -> List[Herb]:
        """提取药物列表"""
        herbs = []
        seen_herbs = set()  # 用于去重
        
        # 多种处方格式匹配模式
        patterns = [
            # 格式1: 药名 剂量单位 (如: 麻黄 10g, 桂枝15g)
            r'([^\s\d,，\n]+)\s*(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)\s*([a-zA-Z克钱两斤毫升]+)',
            # 格式2: 药名(炮制) 剂量单位 (如: 生地黄(蒸) 12g)
            r'([^\s\d,，\n]+(?:\([^)]+\))?)\s*(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)\s*([a-zA-Z克钱两斤毫升]+)',
            # 格式3: XML格式中的药物
            r'<药物>([^<]+)</药物>.*?<剂量>([^<]+)</剂量>',
        ]
        
        # 按行分割文本，避免跨行匹配
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if len(match) >= 3:
                        name = match[0].strip()
                        dosage = match[1].strip()
                        unit = match[2].strip()
                        
                        # 验证是否为已知中药
                        herb_base_name = self._get_herb_base_name(name)
                        if herb_base_name in self.herb_names or self._is_valid_herb_name(name):
                            # 检查是否有炮制方法
                            preparation = self._extract_preparation_from_name(name)
                            clean_name = self._clean_herb_name(name)
                            
                            # 去重：如果同一药物已存在，跳过
                            herb_key = f"{clean_name}_{dosage}_{unit}"
                            if herb_key not in seen_herbs:
                                seen_herbs.add(herb_key)
                                herbs.append(Herb(
                                    name=clean_name,
                                    dosage=dosage,
                                    unit=self._normalize_unit(unit),
                                    preparation=preparation
                                ))
                break  # 找到匹配后跳出pattern循环，避免重复匹配
        
        return herbs
    
    def _get_herb_base_name(self, name: str) -> str:
        """获取药物基础名称，去除炮制等修饰词"""
        # 移除常见的炮制前缀
        prefixes = ["生", "熟", "炙", "蒸", "炒", "制", "醋", "酒", "盐", "蜜"]
        for prefix in prefixes:
            if name.startswith(prefix):
                return name[len(prefix):]
        
        # 移除炮制后缀 (括号内容)
        base_name = re.sub(r'\([^)]*\)', '', name)
        return base_name.strip()
    
    def _is_valid_herb_name(self, name: str) -> bool:
        """验证是否为有效的中药名称"""
        # 基础名称检查
        base_name = self._get_herb_base_name(name)
        if base_name in self.herb_names:
            return True
            
        # 长度和字符检查
        if len(name) < 2 or len(name) > 10:
            return False
            
        # 包含数字或特殊字符的可能不是药名
        if re.search(r'\d', name):
            return False
            
        return True
    
    def _extract_preparation_from_name(self, name: str) -> Optional[str]:
        """从药名中提取炮制方法"""
        preparations = ["生", "熟", "炙", "蒸", "炒", "制", "醋", "酒", "盐", "蜜"]
        for prep in preparations:
            if name.startswith(prep):
                return prep
        
        # 检查括号内的炮制方法
        match = re.search(r'\(([^)]+)\)', name)
        if match:
            return match.group(1)
        
        return None
    
    def _clean_herb_name(self, name: str) -> str:
        """清理药物名称"""
        # 移除炮制前缀
        cleaned = re.sub(r'^(生|熟|炙|蒸|炒|制|醋|酒|盐|蜜)', '', name)
        # 移除括号内容
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)
        return cleaned.strip()
    
    def _normalize_unit(self, unit: str) -> str:
        """标准化剂量单位"""
        unit_mapping = {
            "克": "g", "钱": "g", "两": "g", "斤": "g",
            "毫升": "ml", "片": "片", "粒": "粒", "丸": "丸"
        }
        return unit_mapping.get(unit, unit)
    
    def _extract_preparation_method(self, text: str) -> Optional[str]:
        """提取制备方法"""
        for method in self.preparation_methods:
            if method in text:
                return method
        return None
    
    def _extract_usage_instructions(self, text: str) -> Optional[str]:
        """提取用法用量"""
        patterns = [
            r'(每日\d+次|一日\d+次|日服\d+次)',
            r'(早晚各\d+次|早中晚各服)',
            r'(温服|凉服|热服|分服)',
            r'(饭前服|饭后服|空腹服|睡前服)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_course_duration(self, text: str) -> Optional[str]:
        """提取疗程"""
        patterns = [
            r'(\d+天为一疗程|\d+日为一疗程)',
            r'(连服\d+天|连用\d+日)',
            r'(疗程\d+天|疗程\d+周)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_syndrome_pattern(self, text: str) -> Optional[str]:
        """提取证候"""
        # 常见证候模式
        syndrome_patterns = [
            r'(气虚|血虚|阴虚|阳虚|气血两虚)',
            r'(风寒|风热|寒湿|湿热|痰湿)',
            r'(肝郁|脾虚|肾虚|心血不足)',
            r'(血瘀|气滞|痰阻|湿困)',
            r'(表证|里证|半表半里|虚证|实证)'
        ]
        
        for pattern in syndrome_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_disease_name(self, text: str) -> Optional[str]:
        """提取疾病名称"""
        # 常见疾病名称模式
        disease_patterns = [
            r'(感冒|咳嗽|哮喘|腹泻|便秘|失眠)',
            r'(高血压|糖尿病|冠心病|胃炎|肝炎)',
            r'(头痛|胃痛|腰痛|关节炎|神经衰弱)',
            r'(月经不调|痛经|更年期|不孕症)',
            r'(小儿\w+|慢性\w+|急性\w+)'
        ]
        
        for pattern in disease_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None


class PrescriptionSafetyChecker:
    """处方安全性检查"""
    
    def __init__(self):
        # 配伍禁忌 - 十八反十九畏
        self.incompatible_combinations = {
            "甘草": ["大戟", "京大戟", "芫花", "甘遂"],
            "乌头": ["贝母", "瓜蒌", "半夏", "白蔹", "白及"],
            "藜芦": ["人参", "沙参", "丹参", "玄参", "细辛", "芍药"],
            "硫黄": ["朴硝"],
            "水银": ["砒霜"],
            "狼毒": ["密陀僧"],
            "巴豆": ["牵牛"],
            "丁香": ["郁金"],
            "牙硝": ["三棱"],
            "川乌": ["犀角"],
            "草乌": ["犀角"],
            "肉桂": ["赤石脂"]
        }
        
        # 有毒药物及其安全剂量
        self.toxic_herbs = {
            "附子": {"max_daily": "15g", "warning": "需要炮制后使用，先煎30-60分钟"},
            "川乌": {"max_daily": "6g", "warning": "必须炮制，先煎60分钟以上"},
            "草乌": {"max_daily": "6g", "warning": "必须炮制，先煎60分钟以上"},
            "半夏": {"max_daily": "9g", "warning": "生半夏有毒，须用制半夏"},
            "天南星": {"max_daily": "6g", "warning": "生品有毒，须炮制后使用"},
            "马钱子": {"max_daily": "0.6g", "warning": "极毒，严格控制用量"},
            "朱砂": {"max_daily": "1g", "warning": "含汞，不宜久服"},
            "雄黄": {"max_daily": "1g", "warning": "含砷，外用为主"},
            "巴豆": {"max_daily": "0.1g", "warning": "峻下药，用量极小"},
            "甘遂": {"max_daily": "1.5g", "warning": "峻下药，醋制后用"}
        }
        
        # 特殊人群用药禁忌
        self.contraindications = {
            "孕妇禁用": [
                "巴豆", "牵牛子", "大戟", "京大戟", "芫花", "甘遂", "商陆", "三棱", "莪术",
                "水蛭", "虻虫", "川牛膝", "怀牛膝", "桃仁", "红花", "当归尾", "川芎",
                "附子", "肉桂", "干姜", "吴茱萸", "艾叶", "麝香", "丁香", "降香", "沉香"
            ],
            "儿童慎用": [
                "朱砂", "雄黄", "轻粉", "密陀僧", "马钱子", "蟾酥", "斑蝥", "红粉"
            ],
            "老人慎用": [
                "大黄", "芒硝", "甘遂", "大戟", "芫花", "商陆", "牵牛子", "巴豆"
            ]
        }
    
    def check_prescription_safety(self, prescription: Prescription) -> Dict[str, Any]:
        """全面检查处方安全性"""
        results = {
            "is_safe": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        herb_names = [herb.name for herb in prescription.herbs]
        
        # 1. 检查配伍禁忌
        incompatible_pairs = self._check_incompatible_combinations(herb_names)
        if incompatible_pairs:
            results["is_safe"] = False
            results["errors"].extend([
                f"配伍禁忌：{pair[0]} 与 {pair[1]} 不能同用" 
                for pair in incompatible_pairs
            ])
        
        # 2. 检查有毒药物用量
        toxic_warnings = self._check_toxic_herbs(prescription.herbs)
        if toxic_warnings:
            results["warnings"].extend(toxic_warnings)
        
        # 3. 检查总体用药合理性
        dosage_warnings = self._check_dosage_reasonableness(prescription.herbs)
        if dosage_warnings:
            results["warnings"].extend(dosage_warnings)
        
        # 4. 检查药物数量合理性
        herb_count_warning = self._check_herb_count(prescription.herbs)
        if herb_count_warning:
            results["warnings"].append(herb_count_warning)
        
        return results
    
    def _check_incompatible_combinations(self, herb_names: List[str]) -> List[Tuple[str, str]]:
        """检查配伍禁忌"""
        incompatible_pairs = []
        
        for herb1 in herb_names:
            if herb1 in self.incompatible_combinations:
                for herb2 in herb_names:
                    if herb2 in self.incompatible_combinations[herb1]:
                        incompatible_pairs.append((herb1, herb2))
        
        return incompatible_pairs
    
    def _check_toxic_herbs(self, herbs: List[Herb]) -> List[str]:
        """检查有毒药物及用量"""
        warnings = []
        
        for herb in herbs:
            if herb.name in self.toxic_herbs:
                toxic_info = self.toxic_herbs[herb.name]
                max_dose = float(toxic_info["max_daily"].replace('g', ''))
                
                # 解析当前用量
                try:
                    current_dose = self._parse_dosage(herb.dosage)
                    if current_dose > max_dose:
                        warnings.append(
                            f"{herb.name} 用量 {herb.dosage} 超过安全剂量 {toxic_info['max_daily']}，"
                            f"警告：{toxic_info['warning']}"
                        )
                    else:
                        warnings.append(f"{herb.name}: {toxic_info['warning']}")
                except:
                    warnings.append(f"{herb.name}: 请确认用量，{toxic_info['warning']}")
        
        return warnings
    
    def _parse_dosage(self, dosage_str: str) -> float:
        """解析剂量字符串为数值"""
        # 处理范围剂量 (如 6-10g)
        if '-' in dosage_str:
            parts = dosage_str.split('-')
            return float(parts[1].replace('g', '').strip())
        
        # 处理单一剂量
        return float(dosage_str.replace('g', '').strip())
    
    def _check_dosage_reasonableness(self, herbs: List[Herb]) -> List[str]:
        """检查用药剂量合理性"""
        warnings = []
        
        # 药物分类及其常用剂量范围
        dosage_ranges = {
            "补益药": (6, 30),  # 如人参、黄芪
            "解表药": (3, 15),  # 如麻黄、桂枝  
            "清热药": (6, 30),  # 如黄连、黄芩
            "攻下药": (3, 12),  # 如大黄、芒硝
            "理气药": (3, 12),  # 如陈皮、枳实
            "活血药": (6, 15),  # 如红花、桃仁
            "化痰药": (6, 15),  # 如半夏、陈皮
            "利水药": (9, 30),  # 如茯苓、泽泻
            "温里药": (3, 10),  # 如干姜、肉桂
            "镇静药": (15, 30), # 如龙骨、牡蛎
        }
        
        for herb in herbs:
            try:
                dose = self._parse_dosage(herb.dosage)
                if dose < 1:
                    warnings.append(f"{herb.name} 用量过小({herb.dosage})，可能影响疗效")
                elif dose > 50:
                    warnings.append(f"{herb.name} 用量过大({herb.dosage})，请确认安全性")
            except:
                warnings.append(f"{herb.name} 剂量格式不规范：{herb.dosage}")
        
        return warnings
    
    def _check_herb_count(self, herbs: List[Herb]) -> Optional[str]:
        """检查处方药物数量合理性"""
        count = len(herbs)
        if count < 3:
            return f"处方药味过少({count}味)，可能影响疗效"
        elif count > 20:
            return f"处方药味过多({count}味)，建议精简"
        return None


class PrescriptionKnowledgeBase:
    """处方知识库管理"""
    
    def __init__(self, db_path: str = "/opt/tcm/data/prescription_knowledge.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        
        # 创建处方表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_name TEXT,
                disease_name TEXT,
                syndrome_pattern TEXT,
                prescription_json TEXT,
                efficacy_score REAL DEFAULT 0.0,
                safety_score REAL DEFAULT 0.0,
                created_at TEXT,
                source TEXT
            )
        """)
        
        # 创建药物关联表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS herb_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                herb1 TEXT,
                herb2 TEXT,
                association_strength REAL,
                association_type TEXT,
                created_at TEXT
            )
        """)
        
        # 创建疗效反馈表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS efficacy_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prescription_id INTEGER,
                patient_feedback TEXT,
                efficacy_rating INTEGER,
                side_effects TEXT,
                created_at TEXT,
                FOREIGN KEY (prescription_id) REFERENCES prescriptions (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_prescription(self, prescription: Prescription, doctor_name: str = None, 
                        source: str = "manual") -> int:
        """添加处方到知识库"""
        conn = sqlite3.connect(self.db_path)
        
        prescription_json = json.dumps(asdict(prescription), ensure_ascii=False)
        
        cursor = conn.execute("""
            INSERT INTO prescriptions 
            (doctor_name, disease_name, syndrome_pattern, prescription_json, created_at, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            doctor_name or prescription.doctor_name,
            prescription.disease_name,
            prescription.syndrome_pattern,
            prescription_json,
            datetime.now().isoformat(),
            source
        ))
        
        prescription_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return prescription_id
    
    def find_similar_prescriptions(self, disease: str = None, syndrome: str = None, 
                                 herbs: List[str] = None) -> List[Dict]:
        """查找相似处方"""
        conn = sqlite3.connect(self.db_path)
        
        conditions = []
        params = []
        
        if disease:
            conditions.append("disease_name LIKE ?")
            params.append(f"%{disease}%")
        
        if syndrome:
            conditions.append("syndrome_pattern LIKE ?") 
            params.append(f"%{syndrome}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor = conn.execute(f"""
            SELECT * FROM prescriptions 
            WHERE {where_clause}
            ORDER BY efficacy_score DESC, created_at DESC
            LIMIT 10
        """, params)
        
        results = []
        for row in cursor.fetchall():
            result = dict(zip([col[0] for col in cursor.description], row))
            result['prescription'] = json.loads(result['prescription_json'])
            del result['prescription_json']
            results.append(result)
        
        conn.close()
        return results
    
    def update_efficacy_score(self, prescription_id: int, score: float):
        """更新处方疗效评分"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE prescriptions SET efficacy_score = ? WHERE id = ?",
            (score, prescription_id)
        )
        conn.commit()
        conn.close()


class PrescriptionChecker:
    """主要的处方检查类 - 整合所有功能"""
    
    def __init__(self):
        self.parser = PrescriptionParser()
        self.safety_checker = PrescriptionSafetyChecker()
        self.knowledge_base = PrescriptionKnowledgeBase()
    
    def check_prescription(self, prescription_text: str, patient_info: Dict = None) -> Dict[str, Any]:
        """完整的处方检查流程"""
        results = {
            "success": False,
            "prescription": None,
            "safety_check": None,
            "detailed_analysis": None,
            "recommendations": [],
            "similar_cases": [],
            "errors": []
        }
        
        try:
            # 1. 解析处方
            prescription = self.parser.parse_prescription_text(prescription_text)
            if not prescription:
                results["errors"].append("无法解析处方格式")
                return results
            
            results["prescription"] = asdict(prescription)
            
            # 2. 安全性检查
            safety_results = self.safety_checker.check_prescription_safety(prescription)
            results["safety_check"] = safety_results
            
            # 3. 生成详细分析
            detailed_analysis = self.generate_detailed_analysis(prescription, safety_results)
            results["detailed_analysis"] = detailed_analysis
            
            # 4. 查找相似案例
            similar_cases = self.knowledge_base.find_similar_prescriptions(
                disease=prescription.disease_name,
                syndrome=prescription.syndrome_pattern,
                herbs=[herb.name for herb in prescription.herbs]
            )
            results["similar_cases"] = similar_cases
            
            # 5. 生成建议
            recommendations = self._generate_recommendations(prescription, safety_results, similar_cases)
            results["recommendations"] = recommendations
            
            results["success"] = True
            
        except Exception as e:
            results["errors"].append(f"处方检查出错: {str(e)}")
        
        return results
    
    def _generate_recommendations(self, prescription: Prescription, 
                                safety_results: Dict, similar_cases: List[Dict]) -> List[str]:
        """生成处方建议"""
        recommendations = []
        
        # 基于安全检查的建议
        if not safety_results["is_safe"]:
            recommendations.append("⚠️ 处方存在安全风险，请重新检查配伍禁忌")
        
        if safety_results["warnings"]:
            recommendations.append("⚠️ 请注意有毒药物的使用方法和剂量")
        
        # 基于相似案例的建议
        if similar_cases:
            high_efficacy_cases = [case for case in similar_cases if case.get('efficacy_score', 0) > 0.8]
            if high_efficacy_cases:
                recommendations.append(f"💡 找到 {len(high_efficacy_cases)} 个疗效较好的相似案例可供参考")
        
        # 药味数量建议
        herb_count = len(prescription.herbs)
        if herb_count < 5:
            recommendations.append("💡 建议考虑增加配伍药物，以提高疗效")
        elif herb_count > 15:
            recommendations.append("💡 建议精简处方，突出主要治法")
        
        # 制备方法建议
        if not prescription.preparation_method:
            recommendations.append("💡 建议明确煎药方法和服用方式")
        
        return recommendations
    
    def generate_detailed_analysis(self, prescription: Prescription, 
                                 safety_results: Dict) -> Dict[str, Any]:
        """生成详细的处方分析报告"""
        analysis = {
            "formula_analysis": self._analyze_formula_structure(prescription),
            "herb_properties": self._analyze_herb_properties(prescription), 
            "dosage_analysis": self._analyze_dosage_ratios(prescription),
            "safety_details": self._generate_safety_details(safety_results),
            "therapeutic_analysis": self._analyze_therapeutic_principle(prescription),
            "clinical_guidance": self._generate_clinical_guidance(prescription)
        }
        
        return analysis
    
    def _analyze_formula_structure(self, prescription: Prescription) -> Dict[str, Any]:
        """分析方剂结构"""
        herbs = prescription.herbs
        
        # 按功能分类药物
        herb_categories = {
            "君药": [],  # 主药
            "臣药": [],  # 辅助主药  
            "佐药": [],  # 制约或监制
            "使药": []   # 引经或调和
        }
        
        # 根据剂量大小推测君臣佐使
        dosages = []
        for herb in herbs:
            try:
                dose = float(herb.dosage.replace('g', '').strip())
                dosages.append((herb.name, dose))
            except:
                dosages.append((herb.name, 6.0))
        
        # 按剂量排序
        dosages.sort(key=lambda x: x[1], reverse=True)
        
        total_herbs = len(dosages)
        if total_herbs >= 4:
            # 剂量最大的1-2味为君药
            herb_categories["君药"] = [dosages[0][0]]
            if total_herbs > 4 and dosages[1][1] >= dosages[0][1] * 0.8:
                herb_categories["君药"].append(dosages[1][0])
            
            # 剂量居中的为臣药
            start_idx = len(herb_categories["君药"])
            end_idx = min(start_idx + 2, total_herbs - 1)
            herb_categories["臣药"] = [dosages[i][0] for i in range(start_idx, end_idx)]
            
            # 剂量较小的为佐药
            if end_idx < total_herbs - 1:
                herb_categories["佐药"] = [dosages[i][0] for i in range(end_idx, total_herbs - 1)]
            
            # 最小剂量的为使药（通常是甘草等调和药）
            if total_herbs > 2:
                last_herb = dosages[-1][0]
                if last_herb in ["甘草", "大枣", "生姜"]:
                    herb_categories["使药"] = [last_herb]
                elif herb_categories["佐药"] and last_herb in herb_categories["佐药"]:
                    herb_categories["佐药"].remove(last_herb)
                    herb_categories["使药"] = [last_herb]
        
        return {
            "total_herbs": total_herbs,
            "structure": herb_categories,
            "dosage_range": f"{min(d[1] for d in dosages):.0f}-{max(d[1] for d in dosages):.0f}g",
            "average_dosage": f"{sum(d[1] for d in dosages) / len(dosages):.1f}g"
        }
    
    def _analyze_herb_properties(self, prescription: Prescription) -> Dict[str, Any]:
        """分析药物性味归经"""
        # 简化的药物性味数据
        herb_properties = {
            "人参": {"nature": "微温", "flavor": "甘、微苦", "meridian": ["脾", "肺", "心"]},
            "黄芪": {"nature": "微温", "flavor": "甘", "meridian": ["脾", "肺"]},
            "当归": {"nature": "温", "flavor": "甘、辛", "meridian": ["肝", "心", "脾"]},
            "麻黄": {"nature": "温", "flavor": "辛、微苦", "meridian": ["肺", "膀胱"]},
            "桂枝": {"nature": "温", "flavor": "辛、甘", "meridian": ["心", "肺", "膀胱"]},
            "白芍": {"nature": "微寒", "flavor": "苦、酸", "meridian": ["肝", "脾"]},
            "甘草": {"nature": "平", "flavor": "甘", "meridian": ["心", "肺", "脾", "胃"]},
            "杏仁": {"nature": "微温", "flavor": "苦", "meridian": ["肺", "大肠"]},
            "生姜": {"nature": "微温", "flavor": "辛", "meridian": ["肺", "脾", "胃"]},
            "大枣": {"nature": "温", "flavor": "甘", "meridian": ["脾", "胃"]},
        }
        
        natures = {"温": 0, "热": 0, "平": 0, "凉": 0, "寒": 0}
        flavors = {"辛": 0, "甘": 0, "苦": 0, "酸": 0, "咸": 0}
        meridians = {}
        
        analyzed_herbs = []
        
        for herb in prescription.herbs:
            herb_name = herb.name
            if herb_name in herb_properties:
                prop = herb_properties[herb_name]
                analyzed_herbs.append({
                    "name": herb_name,
                    "dosage": herb.dosage + herb.unit,
                    "nature": prop["nature"],
                    "flavor": prop["flavor"],
                    "meridian": "、".join(prop["meridian"])
                })
                
                # 统计性味
                nature = prop["nature"].replace("微", "")
                if nature in natures:
                    natures[nature] += 1
                
                for flavor in prop["flavor"].split("、"):
                    if flavor in flavors:
                        flavors[flavor] += 1
                
                # 统计归经
                for meridian in prop["meridian"]:
                    meridians[meridian] = meridians.get(meridian, 0) + 1
        
        # 分析整体性味倾向
        dominant_nature = max(natures, key=natures.get) if any(natures.values()) else "平和"
        dominant_flavors = [f for f, count in flavors.items() if count > 0]
        main_meridians = sorted(meridians.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "herbs_details": analyzed_herbs,
            "overall_nature": dominant_nature,
            "main_flavors": dominant_flavors,
            "target_meridians": [m[0] for m in main_meridians],
            "nature_distribution": natures,
            "flavor_distribution": flavors
        }
    
    def _analyze_dosage_ratios(self, prescription: Prescription) -> Dict[str, Any]:
        """分析用药剂量配比"""
        dosages = []
        total_dose = 0
        
        for herb in prescription.herbs:
            try:
                dose = float(herb.dosage.replace('g', '').strip())
                dosages.append({"name": herb.name, "dosage": dose, "unit": herb.unit})
                total_dose += dose
            except:
                dosages.append({"name": herb.name, "dosage": 6.0, "unit": "g"})
                total_dose += 6.0
        
        # 计算比例
        for item in dosages:
            item["percentage"] = round(item["dosage"] / total_dose * 100, 1)
        
        # 按剂量排序
        dosages.sort(key=lambda x: x["dosage"], reverse=True)
        
        # 分析剂量特点
        max_dose = max(item["dosage"] for item in dosages)
        min_dose = min(item["dosage"] for item in dosages)
        ratio = max_dose / min_dose if min_dose > 0 else 1
        
        analysis_notes = []
        if ratio > 3:
            analysis_notes.append("剂量差异较大，体现主次分明的用药特点")
        elif ratio < 1.5:
            analysis_notes.append("各药用量相近，体现平和的配伍特点")
        
        if total_dose < 30:
            analysis_notes.append("总剂量偏小，适合轻证或体弱者")
        elif total_dose > 60:
            analysis_notes.append("总剂量较大，适合实证或症状较重者")
        
        return {
            "total_dosage": f"{total_dose}g",
            "herb_ratios": dosages,
            "ratio_analysis": analysis_notes,
            "dosage_range_ratio": f"1:{ratio:.1f}"
        }
    
    def _generate_safety_details(self, safety_results: Dict) -> Dict[str, Any]:
        """生成详细的安全性分析"""
        details = {
            "safety_level": "优秀" if safety_results["is_safe"] else "需注意",
            "check_items": [
                {"item": "配伍禁忌检查", "status": "通过" if not safety_results["errors"] else "发现问题"},
                {"item": "有毒药物监控", "status": "通过" if not safety_results["warnings"] else "需注意"},
                {"item": "剂量合理性", "status": "合理"},
                {"item": "特殊人群适用性", "status": "需个体化评估"}
            ],
            "detailed_warnings": safety_results.get("warnings", []),
            "safety_suggestions": [
                "建议在专业中医师指导下使用",
                "如有不适症状，请及时停药咨询",
                "孕妇、儿童、老人等特殊人群需谨慎使用"
            ]
        }
        
        return details
    
    def _analyze_therapeutic_principle(self, prescription: Prescription) -> Dict[str, Any]:
        """分析治疗原则和机理"""
        # 根据药物组合推测治法
        herb_names = [herb.name for herb in prescription.herbs]
        
        treatment_methods = []
        therapeutic_focus = []
        
        # 常见治法判断
        if any(herb in herb_names for herb in ["麻黄", "桂枝", "紫苏", "防风"]):
            treatment_methods.append("解表法")
            therapeutic_focus.append("宣肺解表，疏散风邪")
        
        if any(herb in herb_names for herb in ["人参", "黄芪", "党参", "白术"]):
            treatment_methods.append("补气法")
            therapeutic_focus.append("补益脾肺，扶正固本")
        
        if any(herb in herb_names for herb in ["当归", "川芎", "红花", "桃仁"]):
            treatment_methods.append("活血法")
            therapeutic_focus.append("活血化瘀，通络止痛")
        
        if any(herb in herb_names for herb in ["半夏", "陈皮", "茯苓", "白术"]):
            treatment_methods.append("化湿法")
            therapeutic_focus.append("健脾化湿，理气和中")
        
        # 如果没有识别出特定治法
        if not treatment_methods:
            treatment_methods.append("综合调理")
            therapeutic_focus.append("多法并用，整体调治")
        
        return {
            "treatment_methods": treatment_methods,
            "therapeutic_focus": therapeutic_focus,
            "mechanism_analysis": "通过多种药物协同作用，调节机体阴阳气血平衡",
            "expected_effects": ["改善症状", "调理体质", "增强免疫"]
        }
    
    def _generate_clinical_guidance(self, prescription: Prescription) -> Dict[str, Any]:
        """生成临床指导建议"""
        guidance = {
            "administration": {
                "preparation": prescription.preparation_method or "水煎服（建议）",
                "timing": "饭后30分钟温服",
                "frequency": "每日1剂，分2-3次服用",
                "duration": "建议连服3-7天，观察疗效"
            },
            "precautions": [
                "服药期间忌食辛辣、油腻、生冷食物",
                "如有胃肠不适，可饭后服用",
                "服药期间注意休息，避免过度劳累"
            ],
            "monitoring": [
                "观察症状改善情况",
                "注意有无不良反应",
                "如症状无缓解或加重，及时就医"
            ],
            "modification_suggestions": [
                "可根据症状变化调整药物剂量",
                "症状缓解后可适当减量",
                "必要时可加减化裁"
            ]
        }
        
        return guidance
    
    def add_famous_doctor_prescription(self, prescription_text: str, doctor_name: str, 
                                     source: str = "famous_doctor") -> bool:
        """添加名医处方到知识库"""
        try:
            prescription = self.parser.parse_prescription_text(prescription_text)
            if prescription:
                self.knowledge_base.add_prescription(prescription, doctor_name, source)
                return True
        except Exception as e:
            print(f"添加名医处方失败: {e}")
        return False


# 测试和示例代码
def test_prescription_checker():
    """测试处方检查系统"""
    checker = PrescriptionChecker()
    
    # 测试处方1: 麻黄汤 (标准格式)
    test_prescription_1 = """
    麻黄 9g
    桂枝 6g  
    杏仁 6g
    甘草 3g
    
    水煎服，每日一剂，分2次温服
    适应症：风寒感冒，恶寒发热，头痛身痛，无汗而喘
    """
    
    print("=== 测试处方检查系统 ===")
    print(f"处方内容: {test_prescription_1}")
    
    result = checker.check_prescription(test_prescription_1)
    
    print("\n--- 检查结果 ---")
    print(f"解析成功: {'✅' if result['success'] else '❌'}")
    
    if result['prescription']:
        prescription = result['prescription']
        print(f"药物数量: {len(prescription['herbs'])}味")
        print("药物列表:")
        for herb in prescription['herbs']:
            print(f"  - {herb['name']} {herb['dosage']}{herb['unit']}")
        
        if prescription['preparation_method']:
            print(f"制备方法: {prescription['preparation_method']}")
    
    if result['safety_check']:
        safety = result['safety_check']
        print(f"\n安全性: {'✅ 安全' if safety['is_safe'] else '❌ 有风险'}")
        
        if safety['warnings']:
            print("警告:")
            for warning in safety['warnings']:
                print(f"  ⚠️ {warning}")
        
        if safety['errors']:
            print("错误:")
            for error in safety['errors']:
                print(f"  ❌ {error}")
    
    if result['recommendations']:
        print("\n建议:")
        for rec in result['recommendations']:
            print(f"  {rec}")
    
    # 测试配伍禁忌的处方
    print("\n\n=== 测试配伍禁忌检查 ===")
    dangerous_prescription = """
    甘草 6g
    大戟 9g
    人参 12g
    藜芦 3g
    
    水煎服
    """
    
    result2 = checker.check_prescription(dangerous_prescription)
    print(f"危险处方检查: {'❌ 有禁忌' if not result2['safety_check']['is_safe'] else '✅ 安全'}")
    
    if result2['safety_check']['errors']:
        print("配伍禁忌:")
        for error in result2['safety_check']['errors']:
            print(f"  ❌ {error}")


if __name__ == "__main__":
    test_prescription_checker()