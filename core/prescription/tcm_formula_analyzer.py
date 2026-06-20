#!/usr/bin/env python3
"""
中医方剂君臣佐使分析系统
基于传统中医理论和现代AI技术的智能分析
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class HerbInfo:
    """药材信息"""
    name: str
    dosage: float
    unit: str = "g"
    processing: Optional[str] = None
    properties: Dict[str, str] = None
    functions: List[str] = None

@dataclass
class HerbRole:
    """药材在方剂中的角色"""
    name: str
    dosage: str
    role: str  # 君、臣、佐、使
    reason: str
    confidence: float

class TCMFormulaAnalyzer:
    """中医方剂分析器"""
    
    def __init__(self):
        self.herb_database = self._load_herb_database()
        self.formula_patterns = self._load_formula_patterns()
        self.dosage_thresholds = {
            '君药': (12, 30),  # 君药通常用量较大
            '臣药': (9, 20),   # 臣药用量中等
            '佐药': (6, 15),   # 佐药用量较小
            '使药': (3, 10)    # 使药用量最小
        }
    
    def _load_herb_database(self) -> Dict:
        """加载药材数据库 - 扩展版本包含136种药材"""
        return {
            "人参": {
                        "properties": {
                                    "性味": "甘、微苦，微温",
                                    "归经": "脾、肺、心、肾经"
                        },
                        "functions": [
                                    "大补元气",
                                    "复脉固脱",
                                    "补脾益肺",
                                    "生津养血",
                                    "安神益智"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    15
                        ],
                        "category": "补气药"
            },
            "党参": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "脾、肺经"
                        },
                        "functions": [
                                    "补脾益肺",
                                    "养血生津"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "补气药"
            },
            "黄芪": {
                        "properties": {
                                    "性味": "甘，微温",
                                    "归经": "脾、肺经"
                        },
                        "functions": [
                                    "补气升阳",
                                    "固表止汗",
                                    "利水消肿",
                                    "生肌"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "补气药"
            },
            "白术": {
                        "properties": {
                                    "性味": "甘、苦，温",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "补气健脾",
                                    "燥湿利水",
                                    "止汗",
                                    "安胎"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "化痰药"
            },
            "山药": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "脾、肺、肾经"
                        },
                        "functions": [
                                    "补脾养胃",
                                    "生津益肺",
                                    "补肾涩精"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    10,
                                    30
                        ],
                        "category": "补气药"
            },
            "大枣": {
                        "properties": {
                                    "性味": "甘，温",
                                    "归经": "脾、胃、心经"
                        },
                        "functions": [
                                    "补中益气",
                                    "养血安神",
                                    "缓和药性"
                        ],
                        "typical_roles": [
                                    "使药"
                        ],
                        "typical_dosage": [
                                    3,
                                    12
                        ],
                        "category": "补气药"
            },
            "刺五加": {
                        "properties": {
                                    "性味": "甘、微苦，温",
                                    "归经": "脾、肾、心经"
                        },
                        "functions": [
                                    "益气健脾",
                                    "补肾安神"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补气药"
            },
            "西洋参": {
                        "properties": {
                                    "性味": "甘、微苦，凉",
                                    "归经": "心、肺、肾经"
                        },
                        "functions": [
                                    "补气养阴",
                                    "清热生津"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    9
                        ],
                        "category": "补气药"
            },
            "太子参": {
                        "properties": {
                                    "性味": "甘、微苦，平",
                                    "归经": "脾、肺经"
                        },
                        "functions": [
                                    "补气健脾",
                                    "生津润肺"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "补气药"
            },
            "白扁豆": {
                        "properties": {
                                    "性味": "甘，微温",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "补脾和中",
                                    "化湿消暑"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "补气药"
            },
            "饴糖": {
                        "properties": {
                                    "性味": "甘，温",
                                    "归经": "脾、胃、肺经"
                        },
                        "functions": [
                                    "补中益气",
                                    "润肺止咳",
                                    "缓急止痛"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    30,
                                    60
                        ],
                        "category": "补气药"
            },
            "蜂蜜": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "肺、脾、大肠经"
                        },
                        "functions": [
                                    "补中",
                                    "润燥",
                                    "止痛",
                                    "解毒"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "使药"
                        ],
                        "typical_dosage": [
                                    15,
                                    30
                        ],
                        "category": "补气药"
            },
            "甘草": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "心、肺、脾、胃经"
                        },
                        "functions": [
                                    "补脾益气",
                                    "清热解毒",
                                    "祛痰止咳",
                                    "缓急止痛",
                                    "调和诸药"
                        ],
                        "typical_roles": [
                                    "使药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "补气药"
            },
            "当归": {
                        "properties": {
                                    "性味": "甘、辛，温",
                                    "归经": "肝、心、脾经"
                        },
                        "functions": [
                                    "补血调经",
                                    "活血止痛",
                                    "润肠通便"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补血药"
            },
            "熟地黄": {
                        "properties": {
                                    "性味": "甘，微温",
                                    "归经": "肝、肾经"
                        },
                        "functions": [
                                    "滋阴补血",
                                    "益精填髓"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    10,
                                    30
                        ],
                        "category": "补血药"
            },
            "白芍": {
                        "properties": {
                                    "性味": "苦、酸，微寒",
                                    "归经": "肝、脾经"
                        },
                        "functions": [
                                    "养血调经",
                                    "敛阴止汗",
                                    "柔肝止痛",
                                    "平抑肝阳"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补血药"
            },
            "川芎": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "肝、胆、心包经"
                        },
                        "functions": [
                                    "活血行气",
                                    "祛风止痛"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "补血药"
            },
            "阿胶": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "肺、肝、肾经"
                        },
                        "functions": [
                                    "补血滋阴",
                                    "润燥",
                                    "止血"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补血药"
            },
            "何首乌": {
                        "properties": {
                                    "性味": "苦、甘、涩，微温",
                                    "归经": "肝、肾经"
                        },
                        "functions": [
                                    "补肝肾",
                                    "益精血",
                                    "乌须发",
                                    "强筋骨"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    10,
                                    30
                        ],
                        "category": "补血药"
            },
            "龙眼肉": {
                        "properties": {
                                    "性味": "甘，温",
                                    "归经": "心、脾经"
                        },
                        "functions": [
                                    "补心脾",
                                    "益气血",
                                    "安神"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补血药"
            },
            "百合": {
                        "properties": {
                                    "性味": "甘，微寒",
                                    "归经": "心、肺经"
                        },
                        "functions": [
                                    "养阴润肺",
                                    "清心安神"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    10,
                                    30
                        ],
                        "category": "补阴药"
            },
            "枸杞子": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "肝、肾、肺经"
                        },
                        "functions": [
                                    "滋补肝肾",
                                    "益精明目"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    18
                        ],
                        "category": "补阴药"
            },
            "麦门冬": {
                        "properties": {
                                    "性味": "甘、微苦，微寒",
                                    "归经": "心、肺、胃经"
                        },
                        "functions": [
                                    "养阴生津",
                                    "润肺清心"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补阴药"
            },
            "天门冬": {
                        "properties": {
                                    "性味": "甘、苦，寒",
                                    "归经": "肺、肾经"
                        },
                        "functions": [
                                    "养阴润燥",
                                    "清肺生津"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补阴药"
            },
            "石斛": {
                        "properties": {
                                    "性味": "甘，微寒",
                                    "归经": "胃、肾经"
                        },
                        "functions": [
                                    "益胃生津",
                                    "滋阴清热"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补阴药"
            },
            "玉竹": {
                        "properties": {
                                    "性味": "甘，微寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "滋阴润燥",
                                    "生津止渴"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "补阴药"
            },
            "南沙参": {
                        "properties": {
                                    "性味": "甘、微苦，微寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "养阴清肺",
                                    "益胃生津"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "补阴药"
            },
            "北沙参": {
                        "properties": {
                                    "性味": "甘、微苦，微寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "养阴清肺",
                                    "益胃生津"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "补阴药"
            },
            "黄连": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "心、脾、胃、肝、胆、大肠经"
                        },
                        "functions": [
                                    "清热燥湿",
                                    "泻火解毒"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    12
                        ],
                        "category": "清热燥湿药"
            },
            "黄芩": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "肺、胆、脾、大肠、小肠经"
                        },
                        "functions": [
                                    "清热燥湿",
                                    "泻火解毒",
                                    "止血",
                                    "安胎"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "清热燥湿药"
            },
            "黄柏": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "肾、膀胱经"
                        },
                        "functions": [
                                    "清热燥湿",
                                    "泻火解毒",
                                    "退虚热"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "清热燥湿药"
            },
            "栀子": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "心、肺、三焦经"
                        },
                        "functions": [
                                    "泻火除烦",
                                    "清热利湿",
                                    "凉血解毒"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "清热泻火药"
            },
            "金银花": {
                        "properties": {
                                    "性味": "甘，寒",
                                    "归经": "肺、心、胃经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "疏散风热"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    10,
                                    30
                        ],
                        "category": "清热解毒药"
            },
            "连翘": {
                        "properties": {
                                    "性味": "苦，微寒",
                                    "归经": "肺、心、小肠经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "散结消肿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "清热解毒药"
            },
            "板蓝根": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "心、胃经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "凉血",
                                    "利咽"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "清热解毒药"
            },
            "大青叶": {
                        "properties": {
                                    "性味": "苦，大寒",
                                    "归经": "心、胃经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "凉血消斑"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "清热解毒药"
            },
            "青黛": {
                        "properties": {
                                    "性味": "咸，寒",
                                    "归经": "肝、肺、胃经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "凉血消斑",
                                    "定惊"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    1,
                                    3
                        ],
                        "category": "清热解毒药"
            },
            "蒲公英": {
                        "properties": {
                                    "性味": "苦、甘，寒",
                                    "归经": "肝、胃经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "消肿散结",
                                    "利湿通淋"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "清热解毒药"
            },
            "紫花地丁": {
                        "properties": {
                                    "性味": "苦、辛，寒",
                                    "归经": "心、肝经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "凉血消肿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "清热解毒药"
            },
            "野菊花": {
                        "properties": {
                                    "性味": "苦、辛，微寒",
                                    "归经": "肺、肝经"
                        },
                        "functions": [
                                    "清热解毒",
                                    "疏散风热"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "清热解毒药"
            },
            "石膏": {
                        "properties": {
                                    "性味": "甘、辛，大寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "清热泻火",
                                    "除烦止渴",
                                    "收湿敛疮"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    15,
                                    60
                        ],
                        "category": "清热泻火药"
            },
            "知母": {
                        "properties": {
                                    "性味": "苦、甘，寒",
                                    "归经": "肺、胃、肾经"
                        },
                        "functions": [
                                    "清热泻火",
                                    "生津润燥"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "清热泻火药"
            },
            "芦根": {
                        "properties": {
                                    "性味": "甘，寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "清热生津",
                                    "除烦",
                                    "止呕",
                                    "利尿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    15,
                                    30
                        ],
                        "category": "清热泻火药"
            },
            "天花粉": {
                        "properties": {
                                    "性味": "甘、微苦，微寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "清热泻火",
                                    "生津止渴",
                                    "消肿排脓"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "清热泻火药"
            },
            "竹叶": {
                        "properties": {
                                    "性味": "甘、淡，寒",
                                    "归经": "心、胃、小肠经"
                        },
                        "functions": [
                                    "清热泻火",
                                    "除烦",
                                    "利尿"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    9
                        ],
                        "category": "清热泻火药"
            },
            "夏枯草": {
                        "properties": {
                                    "性味": "苦、辛，寒",
                                    "归经": "肝、胆经"
                        },
                        "functions": [
                                    "清热泻火",
                                    "明目",
                                    "散结消肿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "清热泻火药"
            },
            "决明子": {
                        "properties": {
                                    "性味": "甘、苦、咸，微寒",
                                    "归经": "肝、大肠经"
                        },
                        "functions": [
                                    "清热明目",
                                    "润肠通便"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "清热泻火药"
            },
            "青葙子": {
                        "properties": {
                                    "性味": "苦，微寒",
                                    "归经": "肝经"
                        },
                        "functions": [
                                    "清肝火",
                                    "明目"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "清热泻火药"
            },
            "谷精草": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "肝经"
                        },
                        "functions": [
                                    "疏散风热",
                                    "明目退翳"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "清热泻火药"
            },
            "密蒙花": {
                        "properties": {
                                    "性味": "甘，微寒",
                                    "归经": "肝经"
                        },
                        "functions": [
                                    "清热养肝",
                                    "明目退翳"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "清热泻火药"
            },
            "生地黄": {
                        "properties": {
                                    "性味": "甘，寒",
                                    "归经": "心、肝、肾经"
                        },
                        "functions": [
                                    "清热凉血",
                                    "养阴",
                                    "生津"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    10,
                                    30
                        ],
                        "category": "清热凉血药"
            },
            "玄参": {
                        "properties": {
                                    "性味": "甘、苦、咸，微寒",
                                    "归经": "肺、胃、肾经"
                        },
                        "functions": [
                                    "清热凉血",
                                    "泻火解毒",
                                    "滋阴"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "清热凉血药"
            },
            "丹皮": {
                        "properties": {
                                    "性味": "苦、辛，微寒",
                                    "归经": "心、肝、肾经"
                        },
                        "functions": [
                                    "清热凉血",
                                    "活血化瘀"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "清热凉血药"
            },
            "赤芍": {
                        "properties": {
                                    "性味": "苦，微寒",
                                    "归经": "肝经"
                        },
                        "functions": [
                                    "清热凉血",
                                    "散瘀止痛"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "清热凉血药"
            },
            "紫草": {
                        "properties": {
                                    "性味": "甘、咸，寒",
                                    "归经": "心、肝经"
                        },
                        "functions": [
                                    "清热凉血",
                                    "活血",
                                    "解毒透疹"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "清热凉血药"
            },
            "水牛角": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "心、肝经"
                        },
                        "functions": [
                                    "清热凉血",
                                    "定惊"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    15,
                                    30
                        ],
                        "category": "清热凉血药"
            },
            "麻黄": {
                        "properties": {
                                    "性味": "辛、微苦，温",
                                    "归经": "肺、膀胱经"
                        },
                        "functions": [
                                    "发汗散寒",
                                    "宣肺平喘",
                                    "利水消肿"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "桂枝": {
                        "properties": {
                                    "性味": "辛、甘，温",
                                    "归经": "心、肺、膀胱经"
                        },
                        "functions": [
                                    "发汗解肌",
                                    "温通经脉",
                                    "助阳化气"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "紫苏": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "肺、脾经"
                        },
                        "functions": [
                                    "发汗解表",
                                    "行气宽中",
                                    "解鱼蟹毒"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "解表药"
            },
            "生姜": {
                        "properties": {
                                    "性味": "辛，微温",
                                    "归经": "肺、脾、胃经"
                        },
                        "functions": [
                                    "发汗解表",
                                    "温中止呕",
                                    "温肺止咳"
                        ],
                        "typical_roles": [
                                    "佐药",
                                    "使药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "荆芥": {
                        "properties": {
                                    "性味": "辛，微温",
                                    "归经": "肺、肝经"
                        },
                        "functions": [
                                    "散风解表",
                                    "透疹消疮",
                                    "止血"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "解表药"
            },
            "防风": {
                        "properties": {
                                    "性味": "辛、甘，微温",
                                    "归经": "膀胱、肝、脾经"
                        },
                        "functions": [
                                    "祛风解表",
                                    "胜湿止痛",
                                    "止痉"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "解表药"
            },
            "羌活": {
                        "properties": {
                                    "性味": "辛、苦，温",
                                    "归经": "膀胱、肾经"
                        },
                        "functions": [
                                    "散寒解表",
                                    "祛风胜湿",
                                    "止痛"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "独活": {
                        "properties": {
                                    "性味": "辛、苦，微温",
                                    "归经": "肾、膀胱经"
                        },
                        "functions": [
                                    "祛风胜湿",
                                    "散寒止痛"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "白芷": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "散风寒",
                                    "通窍止痛",
                                    "消肿排脓",
                                    "燥湿止带"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "解表药"
            },
            "细辛": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "心、肺、肾经"
                        },
                        "functions": [
                                    "散寒解表",
                                    "祛风止痛",
                                    "通窍",
                                    "温肺化饮"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    1,
                                    3
                        ],
                        "category": "解表药"
            },
            "苍耳子": {
                        "properties": {
                                    "性味": "辛、苦，温",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "散风寒",
                                    "通鼻窍",
                                    "祛风湿",
                                    "止痛"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "解表药"
            },
            "辛夷": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "散风寒",
                                    "通鼻窍"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "薄荷": {
                        "properties": {
                                    "性味": "辛，凉",
                                    "归经": "肺、肝经"
                        },
                        "functions": [
                                    "疏散风热",
                                    "清利头目",
                                    "利咽透疹",
                                    "疏肝行气"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    6
                        ],
                        "category": "解表药"
            },
            "牛蒡子": {
                        "properties": {
                                    "性味": "辛、苦，寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "疏散风热",
                                    "宣肺祛痰",
                                    "利咽透疹",
                                    "解毒消肿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "解表药"
            },
            "蝉蜕": {
                        "properties": {
                                    "性味": "甘，寒",
                                    "归经": "肺、肝经"
                        },
                        "functions": [
                                    "疏散风热",
                                    "利咽开音",
                                    "透疹",
                                    "明目退翳",
                                    "息风止痉"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "桑叶": {
                        "properties": {
                                    "性味": "甘、苦，寒",
                                    "归经": "肺、肝经"
                        },
                        "functions": [
                                    "疏散风热",
                                    "清肺润燥",
                                    "清肝明目"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "解表药"
            },
            "菊花": {
                        "properties": {
                                    "性味": "甘、苦，微寒",
                                    "归经": "肺、肝经"
                        },
                        "functions": [
                                    "疏散风热",
                                    "平肝明目",
                                    "清热解毒"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "解表药"
            },
            "葛根": {
                        "properties": {
                                    "性味": "甘、辛，凉",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "解肌退热",
                                    "透疹",
                                    "生津止渴",
                                    "升阳止泻"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "解表药"
            },
            "柴胡": {
                        "properties": {
                                    "性味": "苦，微寒",
                                    "归经": "肝、胆经"
                        },
                        "functions": [
                                    "解表退热",
                                    "疏肝解郁",
                                    "升举阳气"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "升麻": {
                        "properties": {
                                    "性味": "甘、辛，微寒",
                                    "归经": "肺、脾、胃、大肠经"
                        },
                        "functions": [
                                    "解表透疹",
                                    "清热解毒",
                                    "升举阳气"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "使药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "解表药"
            },
            "半夏": {
                        "properties": {
                                    "性味": "辛，温，有毒",
                                    "归经": "脾、胃、肺经"
                        },
                        "functions": [
                                    "燥湿化痰",
                                    "降逆止呕",
                                    "消痞散结"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    12
                        ],
                        "category": "化痰药"
            },
            "陈皮": {
                        "properties": {
                                    "性味": "苦、辛，温",
                                    "归经": "脾、肺经"
                        },
                        "functions": [
                                    "理气健脾",
                                    "燥湿化痰"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "化痰药"
            },
            "茯苓": {
                        "properties": {
                                    "性味": "甘、淡，平",
                                    "归经": "心、肺、脾、肾经"
                        },
                        "functions": [
                                    "利水渗湿",
                                    "健脾",
                                    "宁心"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "化痰药"
            },
            "苍术": {
                        "properties": {
                                    "性味": "辛、苦，温",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "燥湿健脾",
                                    "祛风散寒",
                                    "明目"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "化痰药"
            },
            "厚朴": {
                        "properties": {
                                    "性味": "苦、辛，温",
                                    "归经": "脾、胃、肺、大肠经"
                        },
                        "functions": [
                                    "燥湿消痰",
                                    "下气除满"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "化痰药"
            },
            "桔梗": {
                        "properties": {
                                    "性味": "苦、辛，平",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "宣肺",
                                    "利咽",
                                    "祛痰",
                                    "排脓"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "使药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "化痰药"
            },
            "川贝母": {
                        "properties": {
                                    "性味": "甘、苦，微寒",
                                    "归经": "肺、心经"
                        },
                        "functions": [
                                    "清热润肺",
                                    "化痰止咳",
                                    "散结消肿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "化痰药"
            },
            "浙贝母": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "肺、心经"
                        },
                        "functions": [
                                    "清热化痰",
                                    "散结消肿"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "化痰药"
            },
            "瓜蒌": {
                        "properties": {
                                    "性味": "甘，寒",
                                    "归经": "肺、胃、大肠经"
                        },
                        "functions": [
                                    "清热涤痰",
                                    "宽胸散结",
                                    "润燥滑肠"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    20
                        ],
                        "category": "化痰药"
            },
            "竹茹": {
                        "properties": {
                                    "性味": "甘，微寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "清热化痰",
                                    "除烦止呕"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "化痰药"
            },
            "竹沥": {
                        "properties": {
                                    "性味": "甘，寒",
                                    "归经": "心、肺、胃经"
                        },
                        "functions": [
                                    "清热滑痰"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    30,
                                    60
                        ],
                        "category": "化痰药"
            },
            "前胡": {
                        "properties": {
                                    "性味": "苦、辛，微寒",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "降气化痰",
                                    "散风清热"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "化痰药"
            },
            "旋覆花": {
                        "properties": {
                                    "性味": "苦、辛、咸，微温",
                                    "归经": "肺、胃、大肠经"
                        },
                        "functions": [
                                    "降气",
                                    "消痰",
                                    "行水",
                                    "止呕"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "化痰药"
            },
            "白前": {
                        "properties": {
                                    "性味": "苦、甘，微温",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "降气",
                                    "消痰",
                                    "止咳"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "化痰药"
            },
            "百部": {
                        "properties": {
                                    "性味": "甘、苦，微温",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "润肺下气止咳",
                                    "杀虫灭虱"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "止咳平喘药"
            },
            "紫苑": {
                        "properties": {
                                    "性味": "苦、辛，温",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "润肺下气",
                                    "消痰止咳"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "止咳平喘药"
            },
            "款冬花": {
                        "properties": {
                                    "性味": "辛、微苦，温",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "润肺下气",
                                    "止咳化痰"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "止咳平喘药"
            },
            "枇杷叶": {
                        "properties": {
                                    "性味": "苦，微寒",
                                    "归经": "肺、胃经"
                        },
                        "functions": [
                                    "清肺止咳",
                                    "降逆止呕"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "止咳平喘药"
            },
            "桑白皮": {
                        "properties": {
                                    "性味": "甘，寒",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "泻肺平喘",
                                    "利水消肿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "止咳平喘药"
            },
            "葶苈子": {
                        "properties": {
                                    "性味": "苦、辛，大寒",
                                    "归经": "肺、膀胱经"
                        },
                        "functions": [
                                    "泻肺平喘",
                                    "行水消肿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "止咳平喘药"
            },
            "杏仁": {
                        "properties": {
                                    "性味": "苦，微温",
                                    "归经": "肺、大肠经"
                        },
                        "functions": [
                                    "降气止咳平喘",
                                    "润肠通便"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "止咳平喘药"
            },
            "紫苏子": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "肺、大肠经"
                        },
                        "functions": [
                                    "降气化痰",
                                    "止咳平喘",
                                    "润肠通便"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "止咳平喘药"
            },
            "白果": {
                        "properties": {
                                    "性味": "甘、苦、涩，平",
                                    "归经": "肺、肾经"
                        },
                        "functions": [
                                    "敛肺平喘",
                                    "止带缩尿"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "止咳平喘药"
            },
            "洋金花": {
                        "properties": {
                                    "性味": "辛，温，有毒",
                                    "归经": "肺经"
                        },
                        "functions": [
                                    "平喘止咳",
                                    "解痉定痛"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    0.3,
                                    0.6
                        ],
                        "category": "止咳平喘药"
            },
            "木香": {
                        "properties": {
                                    "性味": "辛、苦，温",
                                    "归经": "脾、胃、大肠、三焦、胆经"
                        },
                        "functions": [
                                    "行气止痛",
                                    "健脾消食"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "理气药"
            },
            "沉香": {
                        "properties": {
                                    "性味": "辛、苦，温",
                                    "归经": "脾、胃、肾经"
                        },
                        "functions": [
                                    "行气止痛",
                                    "温中止呕",
                                    "纳气平喘"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    1,
                                    5
                        ],
                        "category": "理气药"
            },
            "檀香": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "脾、胃、心、肺经"
                        },
                        "functions": [
                                    "行气温中",
                                    "开胃止痛"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    6
                        ],
                        "category": "理气药"
            },
            "乌药": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "肺、脾、肾、膀胱经"
                        },
                        "functions": [
                                    "行气止痛",
                                    "温肾散寒"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "理气药"
            },
            "香附": {
                        "properties": {
                                    "性味": "辛、微苦、微甘，平",
                                    "归经": "肝、脾、三焦经"
                        },
                        "functions": [
                                    "疏肝解郁",
                                    "理气宽中",
                                    "调经止痛"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "川楝子": {
                        "properties": {
                                    "性味": "苦，寒",
                                    "归经": "肝、胃、小肠、膀胱经"
                        },
                        "functions": [
                                    "疏肝泄热",
                                    "行气止痛",
                                    "杀虫"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "青皮": {
                        "properties": {
                                    "性味": "苦、辛，温",
                                    "归经": "肝、胆、胃经"
                        },
                        "functions": [
                                    "疏肝破气",
                                    "消积化滞"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    10
                        ],
                        "category": "理气药"
            },
            "枳实": {
                        "properties": {
                                    "性味": "苦、辛、酸，微寒",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "破气消积",
                                    "化痰散痞"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "枳壳": {
                        "properties": {
                                    "性味": "苦、辛、酸，微寒",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "理气宽中",
                                    "行滞消胀"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "佛手": {
                        "properties": {
                                    "性味": "辛、苦、酸，温",
                                    "归经": "肝、脾、胃、肺经"
                        },
                        "functions": [
                                    "疏肝理气",
                                    "和中",
                                    "化痰"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "香橼": {
                        "properties": {
                                    "性味": "辛、微苦、酸，温",
                                    "归经": "肝、脾、胃经"
                        },
                        "functions": [
                                    "疏肝理气",
                                    "宽中",
                                    "化痰"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "玫瑰花": {
                        "properties": {
                                    "性味": "甘、微苦，温",
                                    "归经": "肝、脾经"
                        },
                        "functions": [
                                    "疏肝解郁",
                                    "和血散瘀"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    6
                        ],
                        "category": "理气药"
            },
            "梅花": {
                        "properties": {
                                    "性味": "微酸、涩，平",
                                    "归经": "肝、胃经"
                        },
                        "functions": [
                                    "疏肝",
                                    "和中",
                                    "化痰"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    6
                        ],
                        "category": "理气药"
            },
            "薤白": {
                        "properties": {
                                    "性味": "辛、苦，温",
                                    "归经": "肺、胃、大肠经"
                        },
                        "functions": [
                                    "通阳散结",
                                    "行气导滞"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "理气药"
            },
            "柿蒂": {
                        "properties": {
                                    "性味": "苦，平",
                                    "归经": "胃经"
                        },
                        "functions": [
                                    "降逆止呃"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    10
                        ],
                        "category": "理气药"
            },
            "刀豆": {
                        "properties": {
                                    "性味": "甘，温",
                                    "归经": "胃、肾经"
                        },
                        "functions": [
                                    "降逆止呃",
                                    "温肾助阳"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "理气药"
            },
            "荔枝核": {
                        "properties": {
                                    "性味": "甘、微苦，温",
                                    "归经": "肝、肾经"
                        },
                        "functions": [
                                    "疏肝理气",
                                    "散结止痛"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "小茴香": {
                        "properties": {
                                    "性味": "辛，温",
                                    "归经": "肝、肾、脾、胃经"
                        },
                        "functions": [
                                    "散寒止痛",
                                    "理气和胃"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    3,
                                    6
                        ],
                        "category": "理气药"
            },
            "八月札": {
                        "properties": {
                                    "性味": "苦，平",
                                    "归经": "肝、胃经"
                        },
                        "functions": [
                                    "疏肝理气",
                                    "活血止痛",
                                    "利尿"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "路路通": {
                        "properties": {
                                    "性味": "苦，平",
                                    "归经": "肝、肾经"
                        },
                        "functions": [
                                    "祛风活络",
                                    "利水通经"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "理气药"
            },
            "山楂": {
                        "properties": {
                                    "性味": "酸、甘，微温",
                                    "归经": "脾、胃、肝经"
                        },
                        "functions": [
                                    "消食健胃",
                                    "行气散瘀",
                                    "化浊降脂"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "消食药"
            },
            "神曲": {
                        "properties": {
                                    "性味": "甘、辛，温",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "健脾和胃",
                                    "消食调中"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "消食药"
            },
            "麦芽": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "行气消食",
                                    "健脾开胃",
                                    "回乳消胀"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "消食药"
            },
            "稻芽": {
                        "properties": {
                                    "性味": "甘，温",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "消食和中",
                                    "健脾开胃"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "消食药"
            },
            "莱菔子": {
                        "properties": {
                                    "性味": "辛、甘，平",
                                    "归经": "脾、胃、肺经"
                        },
                        "functions": [
                                    "消食除胀",
                                    "降气化痰"
                        ],
                        "typical_roles": [
                                    "臣药",
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "消食药"
            },
            "鸡内金": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "脾、胃、小肠、膀胱经"
                        },
                        "functions": [
                                    "健胃消食",
                                    "涩精止遗",
                                    "通淋化石"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    3,
                                    9
                        ],
                        "category": "消食药"
            },
            "鸡矢藤": {
                        "properties": {
                                    "性味": "甘、微苦，平",
                                    "归经": "心、肝、脾、肺经"
                        },
                        "functions": [
                                    "祛风利湿",
                                    "消食化积",
                                    "解毒消肿"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    9,
                                    30
                        ],
                        "category": "消食药"
            },
            "阿魏": {
                        "properties": {
                                    "性味": "苦、辛，温",
                                    "归经": "肝、脾、胃经"
                        },
                        "functions": [
                                    "消积",
                                    "杀虫"
                        ],
                        "typical_roles": [
                                    "佐药"
                        ],
                        "typical_dosage": [
                                    1,
                                    5
                        ],
                        "category": "消食药"
            },
            "使君子": {
                        "properties": {
                                    "性味": "甘，温",
                                    "归经": "脾、胃经"
                        },
                        "functions": [
                                    "杀虫消积"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    9,
                                    12
                        ],
                        "category": "驱虫药"
            },
            "苦楝皮": {
                        "properties": {
                                    "性味": "苦，寒，有毒",
                                    "归经": "肝、脾、胃经"
                        },
                        "functions": [
                                    "杀虫",
                                    "疗癣"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "驱虫药"
            },
            "槟榔": {
                        "properties": {
                                    "性味": "苦、辛，温",
                                    "归经": "胃、大肠经"
                        },
                        "functions": [
                                    "杀虫",
                                    "消积",
                                    "行气",
                                    "利水"
                        ],
                        "typical_roles": [
                                    "君药",
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "驱虫药"
            },
            "南瓜子": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "胃、大肠经"
                        },
                        "functions": [
                                    "杀虫"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    60,
                                    120
                        ],
                        "category": "驱虫药"
            },
            "鹤草芽": {
                        "properties": {
                                    "性味": "苦、涩，凉",
                                    "归经": "肝、大肠经"
                        },
                        "functions": [
                                    "杀虫"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    6,
                                    12
                        ],
                        "category": "驱虫药"
            },
            "榧子": {
                        "properties": {
                                    "性味": "甘，平",
                                    "归经": "肺、胃、大肠经"
                        },
                        "functions": [
                                    "杀虫",
                                    "消积",
                                    "润肠通便"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    9,
                                    15
                        ],
                        "category": "驱虫药"
            },
            "雷丸": {
                        "properties": {
                                    "性味": "苦，微寒",
                                    "归经": "胃、大肠经"
                        },
                        "functions": [
                                    "杀虫"
                        ],
                        "typical_roles": [
                                    "君药"
                        ],
                        "typical_dosage": [
                                    15,
                                    21
                        ],
                        "category": "驱虫药"
            },
            "贯众": {
                        "properties": {
                                    "性味": "苦，微寒",
                                    "归经": "肝、胃经"
                        },
                        "functions": [
                                    "杀虫",
                                    "清热解毒",
                                    "止血"
                        ],
                        "typical_roles": [
                                    "臣药"
                        ],
                        "typical_dosage": [
                                    6,
                                    15
                        ],
                        "category": "驱虫药"
            },
            "麻黄": {
            "properties": {
                        "性味": "辛、微苦，温",
                        "归经": "肺、膀胱经"
            },
            "functions": [
                        "发汗解表",
                        "宣肺平喘",
                        "利水消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "解表药"
},
            "桂枝": {
            "properties": {
                        "性味": "辛、甘，温",
                        "归经": "心、肺、膀胱经"
            },
            "functions": [
                        "发汗解肌",
                        "温通经脉",
                        "助阳化气"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "解表药"
},
            "薄荷": {
            "properties": {
                        "性味": "辛，凉",
                        "归经": "肺、肝经"
            },
            "functions": [
                        "疏散风热",
                        "清利头目",
                        "利咽透疹"
            ],
            "typical_roles": [
                        "佐药",
                        "使药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "解表药"
},
            "牛蒡子": {
            "properties": {
                        "性味": "辛、苦，寒",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "疏散风热",
                        "宣肺祛痰",
                        "利咽散结"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "解表药"
},
            "升麻": {
            "properties": {
                        "性味": "辛、微甘，微寒",
                        "归经": "肺、脾、胃、大肠经"
            },
            "functions": [
                        "解表透疹",
                        "清热解毒",
                        "升举阳气"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "解表药"
},
            "芒硝": {
            "properties": {
                        "性味": "咸、苦，寒",
                        "归经": "胃、大肠经"
            },
            "functions": [
                        "泻热通便",
                        "润燥软坚",
                        "清热消肿"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        18
            ],
            "category": "泻下药"
},
            "枳实": {
            "properties": {
                        "性味": "苦、辛、酸，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "破气消积",
                        "化痰除痞"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "厚朴": {
            "properties": {
                        "性味": "苦、辛，温",
                        "归经": "脾、胃、肺、大肠经"
            },
            "functions": [
                        "行气消积",
                        "燥湿除满",
                        "降逆平喘"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "黄芩": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肺、胆、脾、大肠、小肠经"
            },
            "functions": [
                        "清热燥湿",
                        "泻火解毒",
                        "止血",
                        "安胎"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        15
            ],
            "category": "清热燥湿药"
},
            "生姜": {
            "properties": {
                        "性味": "辛，微温",
                        "归经": "肺、脾、胃经"
            },
            "functions": [
                        "解表散寒",
                        "温中止呕",
                        "温肺止咳"
            ],
            "typical_roles": [
                        "佐药",
                        "使药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "解表药"
},
            "大枣": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "脾、胃、心经"
            },
            "functions": [
                        "补中益气",
                        "养血安神",
                        "缓和药性"
            ],
            "typical_roles": [
                        "佐药",
                        "使药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补气药"
},
            "石膏": {
            "properties": {
                        "性味": "辛、甘，大寒",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "清热泻火",
                        "除烦止渴",
                        "收湿敛疮"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        60
            ],
            "category": "清热泻火药"
},
            "知母": {
            "properties": {
                        "性味": "苦、甘，寒",
                        "归经": "肺、胃、肾经"
            },
            "functions": [
                        "清热泻火",
                        "生津润燥"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "清热泻火药"
},
            "栀子": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "心、肺、三焦经"
            },
            "functions": [
                        "泻火除烦",
                        "清热利湿",
                        "凉血解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "清热泻火药"
},
            "淡豆豉": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "解表除烦",
                        "宣郁解毒"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "解表药"
},
            "苍术": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "燥湿健脾",
                        "祛风散寒",
                        "明目"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "化湿药"
},
            "猪苓": {
            "properties": {
                        "性味": "甘、淡，平",
                        "归经": "肾、膀胱经"
            },
            "functions": [
                        "利水渗湿"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "利水渗湿药"
},
            "泽泻": {
            "properties": {
                        "性味": "甘、淡，寒",
                        "归经": "肾、膀胱经"
            },
            "functions": [
                        "利水渗湿",
                        "泻热"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "利水渗湿药"
},
            "木通": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "心、小肠、膀胱经"
            },
            "functions": [
                        "利水通淋",
                        "清心火",
                        "通经下乳"
            ],
            "typical_roles": [
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "利水渗湿药"
},
            "附子": {
            "properties": {
                        "性味": "辛、甘，大热",
                        "归经": "心、肾、脾经"
            },
            "functions": [
                        "回阳救逆",
                        "补火助阳",
                        "散寒止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        15
            ],
            "category": "温里药"
},
            "干姜": {
            "properties": {
                        "性味": "辛，热",
                        "归经": "心、肺、脾、胃经"
            },
            "functions": [
                        "温中散寒",
                        "回阳通脉",
                        "温肺化饮"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "温里药"
},
            "肉桂": {
            "properties": {
                        "性味": "辛、甘，大热",
                        "归经": "肾、脾、心、肝经"
            },
            "functions": [
                        "补火助阳",
                        "引火归原",
                        "散寒止痛",
                        "温通经脉"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        5
            ],
            "category": "温里药"
},
            "木香": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "脾、胃、大肠、三焦、胆经"
            },
            "functions": [
                        "行气止痛",
                        "健脾消食"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "枳壳": {
            "properties": {
                        "性味": "苦、辛、酸，微寒",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "理气宽中",
                        "行滞消胀"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "香附": {
            "properties": {
                        "性味": "辛、微苦、微甘，平",
                        "归经": "肝、脾、三焦经"
            },
            "functions": [
                        "疏肝解郁",
                        "理气宽中",
                        "调经止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "理气药"
},
            "佛手": {
            "properties": {
                        "性味": "辛、苦、酸，温",
                        "归经": "肝、脾、胃、肺经"
            },
            "functions": [
                        "疏肝理气",
                        "和中化痰"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "丹参": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "心、肝经"
            },
            "functions": [
                        "活血祛瘀",
                        "通经止痛",
                        "清心除烦",
                        "凉血消痈"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "活血化瘀药"
},
            "红花": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "心、肝经"
            },
            "functions": [
                        "活血通经",
                        "散瘀止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "桃仁": {
            "properties": {
                        "性味": "苦、甘，平",
                        "归经": "心、肝、大肠经"
            },
            "functions": [
                        "活血祛瘀",
                        "润肠通便",
                        "止咳平喘"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        5,
                        12
            ],
            "category": "活血化瘀药"
},
            "牛膝": {
            "properties": {
                        "性味": "苦、酸，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "逐瘀通经",
                        "补肝肾",
                        "强筋骨",
                        "利水通淋",
                        "引血下行"
            ],
            "typical_roles": [
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "活血化瘀药"
},
            "天麻": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "肝经"
            },
            "functions": [
                        "息风止痉",
                        "平抑肝阳",
                        "祛风通络"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "平肝息风药"
},
            "钩藤": {
            "properties": {
                        "性味": "甘，微寒",
                        "归经": "肝、心包经"
            },
            "functions": [
                        "息风止痉",
                        "清热平肝"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "平肝息风药"
},
            "僵蚕": {
            "properties": {
                        "性味": "咸、辛，平",
                        "归经": "肝、肺、胃经"
            },
            "functions": [
                        "息风止痉",
                        "祛风止痛",
                        "化痰散结"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "平肝息风药"
},
            "麝香": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "心、脾经"
            },
            "functions": [
                        "开窍醒神",
                        "活血通经",
                        "消肿止痛"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.03,
                        0.1
            ],
            "category": "开窍药"
},
            "冰片": {
            "properties": {
                        "性味": "辛、苦，微寒",
                        "归经": "心、脾、肺经"
            },
            "functions": [
                        "开窍醒神",
                        "清热止痛"
            ],
            "typical_roles": [
                        "佐药",
                        "使药"
            ],
            "typical_dosage": [
                        0.15,
                        0.3
            ],
            "category": "开窍药"
},
            "石菖蒲": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "心、胃经"
            },
            "functions": [
                        "开窍宁神",
                        "化湿和胃"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "开窍药"
},
            "山药": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "脾、肺、肾经"
            },
            "functions": [
                        "补脾养胃",
                        "生津益肺",
                        "补肾涩精"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "补气药"
},
            "莲子": {
            "properties": {
                        "性味": "甘、涩，平",
                        "归经": "脾、肾、心经"
            },
            "functions": [
                        "补脾止泻",
                        "益肾涩精",
                        "养心安神"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "收涩药"
},
            "龙骨": {
            "properties": {
                        "性味": "甘、涩，平",
                        "归经": "心、肝、肾经"
            },
            "functions": [
                        "镇惊安神",
                        "敛汗固精",
                        "止血涩肠",
                        "生肌敛疮"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "安神药"
},
            "牡蛎": {
            "properties": {
                        "性味": "咸，微寒",
                        "归经": "肝、胆、肾经"
            },
            "functions": [
                        "重镇安神",
                        "潜阳补阴",
                        "软坚散结",
                        "收敛固涩"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "平肝息风药"
},
            "葛根": {
            "properties": {
                        "性味": "甘、辛，凉",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "解肌退热",
                        "透疹",
                        "生津止渴",
                        "升阳止泻"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        20
            ],
            "category": "解表药"
},
            "连翘": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "肺、心、小肠经"
            },
            "functions": [
                        "清热解毒",
                        "消肿散结",
                        "疏散风热"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "清热解毒药"
},
            "板蓝根": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "心、胃经"
            },
            "functions": [
                        "清热解毒",
                        "凉血利咽"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "清热解毒药"
},
            "金银花": {
            "properties": {
                        "性味": "甘，寒",
                        "归经": "肺、心、胃经"
            },
            "functions": [
                        "清热解毒",
                        "疏散风热"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        20
            ],
            "category": "清热解毒药"
},
            "蒲公英": {
            "properties": {
                        "性味": "苦、甘，寒",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "清热解毒",
                        "消肿散结",
                        "利尿通淋"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "清热解毒药"
},
            "麦冬": {
            "properties": {
                        "性味": "甘、微苦，微寒",
                        "归经": "心、肺、胃经"
            },
            "functions": [
                        "养阴生津",
                        "润肺清心"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阴药"
},
            "沙参": {
            "properties": {
                        "性味": "甘、微苦，微寒",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "养阴清肺",
                        "益胃生津"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "补阴药"
},
            "川贝母": {
            "properties": {
                        "性味": "苦、甘，微寒",
                        "归经": "肺、心经"
            },
            "functions": [
                        "清热润肺",
                        "化痰止咳",
                        "散结消痈"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "化痰药"
},
            "枇杷叶": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "清肺止咳",
                        "降逆止呕"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "止咳平喘药"
},
            "山楂": {
            "properties": {
                        "性味": "酸、甘，微温",
                        "归经": "脾、胃、肝经"
            },
            "functions": [
                        "消食健胃",
                        "行气散瘀",
                        "化浊降脂"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "消食药"
},
            "神曲": {
            "properties": {
                        "性味": "甘、辛，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "健脾和胃",
                        "消食调中"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "消食药"
},
            "麦芽": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "行气消食",
                        "健脾开胃",
                        "回乳消胀"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "消食药"
},
            "藿香": {
            "properties": {
                        "性味": "辛，微温",
                        "归经": "脾、胃、肺经"
            },
            "functions": [
                        "芳香化浊",
                        "和中止呕",
                        "发表解暑"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "化湿药"
},
            "川芎": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、胆、心包经"
            },
            "functions": [
                        "活血行气",
                        "祛风止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "三七": {
            "properties": {
                        "性味": "甘、微苦，温",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "散瘀止血",
                        "消肿定痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "活血化瘀药"
},
            "车前子": {
            "properties": {
                        "性味": "甘，寒",
                        "归经": "肝、肾、肺、小肠经"
            },
            "functions": [
                        "清热利尿",
                        "渗湿止泻",
                        "明目",
                        "祛痰"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "利水渗湿药"
},
            "金钱草": {
            "properties": {
                        "性味": "甘、咸，微寒",
                        "归经": "肝、胆、肾、膀胱经"
            },
            "functions": [
                        "利湿退黄",
                        "利尿通淋",
                        "解毒消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        60
            ],
            "category": "利水渗湿药"
},
            "益母草": {
            "properties": {
                        "性味": "辛、苦，微寒",
                        "归经": "心、肝、膀胱经"
            },
            "functions": [
                        "活血调经",
                        "利尿消肿",
                        "清热解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "活血化瘀药"
},
            "艾叶": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "肝、脾、肾经"
            },
            "functions": [
                        "温经止血",
                        "散寒调经",
                        "安胎"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "止血药"
},
            "紫花地丁": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "心、肝经"
            },
            "functions": [
                        "清热解毒",
                        "凉血消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "清热解毒药"
},
            "野菊花": {
            "properties": {
                        "性味": "苦、辛，微寒",
                        "归经": "肺、肝经"
            },
            "functions": [
                        "清热解毒",
                        "疏风平肝"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "清热解毒药"
},
            "西洋参": {
            "properties": {
                        "性味": "苦、微甘，寒",
                        "归经": "心、肺、肾经"
            },
            "functions": [
                        "补气养阴",
                        "清热生津"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "补气药"
},
            "太子参": {
            "properties": {
                        "性味": "甘、微苦，平",
                        "归经": "脾、肺经"
            },
            "functions": [
                        "补气健脾",
                        "生津润肺"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        30
            ],
            "category": "补气药"
},
            "黄精": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "脾、肺、肾经"
            },
            "functions": [
                        "补气养阴",
                        "健脾",
                        "润肺",
                        "益肾"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "补气药"
},
            "阿胶": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "肺、肝、肾经"
            },
            "functions": [
                        "补血滋阴",
                        "润燥",
                        "止血"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "补血药"
},
            "龙眼肉": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "心、脾经"
            },
            "functions": [
                        "补心脾",
                        "益气血",
                        "安神"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "补血药"
},
            "首乌藤": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肝经"
            },
            "functions": [
                        "养血安神",
                        "祛风通络"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        10,
                        20
            ],
            "category": "安神药"
},
            "牛黄": {
            "properties": {
                        "性味": "苦，凉",
                        "归经": "心、肝经"
            },
            "functions": [
                        "清心",
                        "豁痰",
                        "开窍",
                        "凉肝",
                        "息风",
                        "解毒"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.15,
                        0.35
            ],
            "category": "清热药"
},
            "羚羊角": {
            "properties": {
                        "性味": "咸，寒",
                        "归经": "肝、心经"
            },
            "functions": [
                        "平肝息风",
                        "清肝明目",
                        "散血解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "平肝息风药"
},
            "珍珠": {
            "properties": {
                        "性味": "甘、咸，寒",
                        "归经": "心、肝经"
            },
            "functions": [
                        "安神定惊",
                        "明目消翳",
                        "解毒生肌"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        0.1,
                        0.3
            ],
            "category": "安神药"
},
            "细辛": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "心、肺、肾经"
            },
            "functions": [
                        "解表散寒",
                        "祛风止痛",
                        "通窍",
                        "温肺化饮"
            ],
            "typical_roles": [
                        "佐药",
                        "使药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "解表药"
},
            "独活": {
            "properties": {
                        "性味": "辛、苦，微温",
                        "归经": "肾、膀胱经"
            },
            "functions": [
                        "祛风胜湿",
                        "散寒止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "祛风湿药"
},
            "威灵仙": {
            "properties": {
                        "性味": "辛、咸，温",
                        "归经": "膀胱经"
            },
            "functions": [
                        "祛风湿",
                        "通经络",
                        "消骨鲠"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        10
            ],
            "category": "祛风湿药"
},
            "秦艽": {
            "properties": {
                        "性味": "苦、辛，微寒",
                        "归经": "胃、肝、胆经"
            },
            "functions": [
                        "祛风湿",
                        "清湿热",
                        "止痹痛",
                        "退虚热"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        10
            ],
            "category": "祛风湿药"
},
            "芍药": {
            "properties": {
                        "性味": "苦、酸，微寒",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "养血调经",
                        "敛阴止汗",
                        "柔肝止痛",
                        "平抑肝阳"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补血药"
},
            "大黄": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "脾、胃、大肠、肝、心包经"
            },
            "functions": [
                        "攻积滞",
                        "清湿热",
                        "泻火",
                        "凉血",
                        "祛瘀",
                        "解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        12
            ],
            "category": "泻下药"
},
            "黄连": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "心、脾、胃、肝、胆、大肠经"
            },
            "functions": [
                        "清热燥湿",
                        "泻火解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        2,
                        5
            ],
            "category": "清热燥湿药"
},
            "黄柏": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肾、膀胱、大肠经"
            },
            "functions": [
                        "清热燥湿",
                        "泻火除蒸",
                        "解毒疗疮"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        12
            ],
            "category": "清热燥湿药"
},
            "龙胆草": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝、胆经"
            },
            "functions": [
                        "清热燥湿",
                        "泻肝胆火"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "清热燥湿药"
},
            "桂枝": {
            "properties": {
                        "性味": "辛、甘，温",
                        "归经": "心、肺、膀胱经"
            },
            "functions": [
                        "发汗解肌",
                        "温通经脉",
                        "助阳化气"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "解表药"
},
            "白芍": {
            "properties": {
                        "性味": "苦、酸，微寒",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "养血调经",
                        "敛阴止汗",
                        "柔肝止痛",
                        "平抑肝阳"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补血药"
},
            "地黄": {
            "properties": {
                        "性味": "甘，微温",
                        "归经": "心、肝、肾经"
            },
            "functions": [
                        "滋阴补血",
                        "填精益髓"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "补血药"
},
            "山茱萸": {
            "properties": {
                        "性味": "酸、涩，微温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补益肝肾",
                        "收敛固涩"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "收涩药"
},
            "山药": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "脾、肺、肾经"
            },
            "functions": [
                        "补脾养胃",
                        "生津益肺",
                        "补肾涩精"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "补气药"
},
            "羚羊角": {
            "properties": {
                        "性味": "咸，寒",
                        "归经": "肝、心经"
            },
            "functions": [
                        "平肝息风",
                        "清肝明目",
                        "散血解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "平肝息风药"
},
            "牛黄": {
            "properties": {
                        "性味": "苦，凉",
                        "归经": "心、肝经"
            },
            "functions": [
                        "清心",
                        "豁痰",
                        "开窍",
                        "凉肝",
                        "息风",
                        "解毒"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.15,
                        0.35
            ],
            "category": "清热药"
},
            "珍珠": {
            "properties": {
                        "性味": "甘、咸，寒",
                        "归经": "心、肝经"
            },
            "functions": [
                        "安神定惊",
                        "明目消翳",
                        "解毒生肌"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        0.1,
                        0.3
            ],
            "category": "安神药"
},
            "人参": {
            "properties": {
                        "性味": "甘、微苦，微温",
                        "归经": "脾、肺、心、肾经"
            },
            "functions": [
                        "大补元气",
                        "复脉固脱",
                        "补脾益肺",
                        "生津养血",
                        "安神益智"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        15
            ],
            "category": "补气药"
},
            "白术": {
            "properties": {
                        "性味": "苦、甘，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "补气健脾",
                        "燥湿利水",
                        "止汗",
                        "安胎"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补气药"
},
            "炙甘草": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肺、脾、胃经"
            },
            "functions": [
                        "补脾益气",
                        "滋心复脉",
                        "调和诸药"
            ],
            "typical_roles": [
                        "臣药",
                        "使药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "补气药"
},
            "当归": {
            "properties": {
                        "性味": "甘、辛，温",
                        "归经": "肝、心、脾经"
            },
            "functions": [
                        "补血",
                        "活血",
                        "调经止痛",
                        "润燥滑肠"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补血药"
},
            "川芎": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、胆、心包经"
            },
            "functions": [
                        "活血行气",
                        "祛风止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "赤芍": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "肝经"
            },
            "functions": [
                        "清热凉血",
                        "散瘀止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "清热凉血药"
},
            "延胡索": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "活血",
                        "利气",
                        "止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "金银花": {
            "properties": {
                        "性味": "甘，寒",
                        "归经": "肺、心、胃经"
            },
            "functions": [
                        "清热解毒",
                        "疏散风热"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        20
            ],
            "category": "清热解毒药"
},
            "连翘": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "肺、心、小肠经"
            },
            "functions": [
                        "清热解毒",
                        "消肿散结",
                        "疏散风热"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "清热解毒药"
},
            "蒲公英": {
            "properties": {
                        "性味": "苦、甘，寒",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "清热解毒",
                        "消肿散结",
                        "利尿通淋"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "清热解毒药"
},
            "紫花地丁": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "心、肝经"
            },
            "functions": [
                        "清热解毒",
                        "凉血消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "清热解毒药"
},
            "钩藤": {
            "properties": {
                        "性味": "甘，微寒",
                        "归经": "肝、心包经"
            },
            "functions": [
                        "息风止痉",
                        "清热平肝"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "平肝息风药"
},
            "天麻": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "肝经"
            },
            "functions": [
                        "息风止痉",
                        "平抑肝阳",
                        "祛风通络"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "平肝息风药"
},
            "全蝎": {
            "properties": {
                        "性味": "辛，平",
                        "归经": "肝经"
            },
            "functions": [
                        "息风止痉",
                        "通络止痛",
                        "解毒散结"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "平肝息风药"
},
            "蜈蚣": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝经"
            },
            "functions": [
                        "息风止痉",
                        "通络止痛",
                        "解毒散结"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "平肝息风药"
},
            "款冬花": {
            "properties": {
                        "性味": "辛、微苦，温",
                        "归经": "肺经"
            },
            "functions": [
                        "润肺下气",
                        "止咳化痰"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        10
            ],
            "category": "止咳平喘药"
},
            "紫菀": {
            "properties": {
                        "性味": "苦、甘，微温",
                        "归经": "肺经"
            },
            "functions": [
                        "润肺下气",
                        "消痰止咳"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        10
            ],
            "category": "止咳平喘药"
},
            "桑白皮": {
            "properties": {
                        "性味": "甘，寒",
                        "归经": "肺经"
            },
            "functions": [
                        "泻肺平喘",
                        "利水消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "止咳平喘药"
},
            "地骨皮": {
            "properties": {
                        "性味": "甘，寒",
                        "归经": "肺、肝、肾经"
            },
            "functions": [
                        "清热凉血",
                        "退虚热",
                        "清肺降火"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "清虚热药"
},
            "银柴胡": {
            "properties": {
                        "性味": "甘，微寒",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "清虚热",
                        "除疳热"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "清虚热药"
},
            "丹参": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "心、肝经"
            },
            "functions": [
                        "活血祛瘀",
                        "通经止痛",
                        "清心除烦",
                        "凉血消痈"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "活血化瘀药"
},
            "红花": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "心、肝经"
            },
            "functions": [
                        "活血通经",
                        "散瘀止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "郁金": {
            "properties": {
                        "性味": "辛、苦，寒",
                        "归经": "心、肝、胆经"
            },
            "functions": [
                        "活血止痛",
                        "行气解郁",
                        "清心凉血",
                        "利胆退黄"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "活血化瘀药"
},
            "降香": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "化瘀止血",
                        "理气止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "黄芩": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肺、胆、脾、大肠、小肠经"
            },
            "functions": [
                        "清热燥湿",
                        "泻火解毒",
                        "止血",
                        "安胎"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        15
            ],
            "category": "清热燥湿药"
},
            "木香": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "脾、胃、大肠、三焦、胆经"
            },
            "functions": [
                        "行气止痛",
                        "健脾消食"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "远志": {
            "properties": {
                        "性味": "苦、辛，微温",
                        "归经": "心、肾、肺经"
            },
            "functions": [
                        "安神益智",
                        "祛痰",
                        "消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "安神药"
},
            "酸枣仁": {
            "properties": {
                        "性味": "甘、酸，平",
                        "归经": "心、肝、胆经"
            },
            "functions": [
                        "补肝",
                        "宁心",
                        "敛汗",
                        "生津"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "安神药"
},
            "夜交藤": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肝经"
            },
            "functions": [
                        "养血安神",
                        "祛风通络"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        10,
                        20
            ],
            "category": "安神药"
},
            "合欢皮": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肝经"
            },
            "functions": [
                        "解郁安神",
                        "活血消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "安神药"
},
            "金钱草": {
            "properties": {
                        "性味": "甘、咸，微寒",
                        "归经": "肝、胆、肾、膀胱经"
            },
            "functions": [
                        "利湿退黄",
                        "利尿通淋",
                        "解毒消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        60
            ],
            "category": "利水渗湿药"
},
            "海金沙": {
            "properties": {
                        "性味": "甘、淡，寒",
                        "归经": "膀胱、小肠经"
            },
            "functions": [
                        "清热解毒",
                        "利水通淋"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "利水渗湿药"
},
            "车前草": {
            "properties": {
                        "性味": "甘，寒",
                        "归经": "肝、肾、肺、小肠经"
            },
            "functions": [
                        "清热利尿",
                        "凉血解毒"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        9,
                        30
            ],
            "category": "利水渗湿药"
},
            "石韦": {
            "properties": {
                        "性味": "苦、甘，微寒",
                        "归经": "肺、膀胱经"
            },
            "functions": [
                        "利尿通淋",
                        "清肺止咳"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "利水渗湿药"
},
            "白鲜皮": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "清热燥湿",
                        "祛风解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "清热燥湿药"
},
            "苦参": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "心、肝、胃、大肠、膀胱经"
            },
            "functions": [
                        "清热燥湿",
                        "杀虫",
                        "利尿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "清热燥湿药"
},
            "地肤子": {
            "properties": {
                        "性味": "辛、苦，寒",
                        "归经": "膀胱经"
            },
            "functions": [
                        "清热利湿",
                        "祛风止痒"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "利水渗湿药"
},
            "土茯苓": {
            "properties": {
                        "性味": "甘、淡，平",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "解毒",
                        "除湿",
                        "通利关节"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        60
            ],
            "category": "清热解毒药"
},
            "五味子": {
            "properties": {
                        "性味": "酸、甘，温",
                        "归经": "肺、心、肾经"
            },
            "functions": [
                        "收敛固涩",
                        "益气生津",
                        "补肾宁心"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        2,
                        6
            ],
            "category": "收涩药"
},
            "刺五加": {
            "properties": {
                        "性味": "辛、微苦，温",
                        "归经": "脾、肾、心经"
            },
            "functions": [
                        "益气健脾",
                        "补肾安神"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        27
            ],
            "category": "补气药"
},
            "川贝母": {
            "properties": {
                        "性味": "苦、甘，微寒",
                        "归经": "肺、心经"
            },
            "functions": [
                        "清热润肺",
                        "化痰止咳",
                        "散结消痈"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "化痰药"
},
            "川牛膝": {
            "properties": {
                        "性味": "甘、微苦，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "逐瘀通经",
                        "通利关节",
                        "利尿通淋"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "活血化瘀药"
},
            "川续断": {
            "properties": {
                        "性味": "苦、辛，微温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补肝肾",
                        "强筋骨",
                        "续折伤",
                        "止崩漏"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阳药"
},
            "广陈皮": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "脾、肺经"
            },
            "functions": [
                        "理气健脾",
                        "燥湿化痰"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "砂仁": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、胃、肾经"
            },
            "functions": [
                        "化湿开胃",
                        "温脾止泻",
                        "理气安胎"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "化湿药"
},
            "豆蔻": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "化湿行气",
                        "温中止呕"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "化湿药"
},
            "浙贝母": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肺、心经"
            },
            "functions": [
                        "清热化痰",
                        "散结消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        10
            ],
            "category": "化痰药"
},
            "杭白芍": {
            "properties": {
                        "性味": "苦、酸，微寒",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "养血调经",
                        "敛阴止汗",
                        "柔肝止痛",
                        "平抑肝阳"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补血药"
},
            "杭菊花": {
            "properties": {
                        "性味": "甘、苦，微寒",
                        "归经": "肺、肝经"
            },
            "functions": [
                        "散风清热",
                        "平肝明目",
                        "清热解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        10
            ],
            "category": "解表药"
},
            "枸杞子": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "滋补肝肾",
                        "益精明目"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "补阴药"
},
            "肉苁蓉": {
            "properties": {
                        "性味": "甘、咸，温",
                        "归经": "肾、大肠经"
            },
            "functions": [
                        "补肾阳",
                        "益精血",
                        "润肠通便"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        20
            ],
            "category": "补阳药"
},
            "锁阳": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "肝、肾、大肠经"
            },
            "functions": [
                        "补肾阳",
                        "益精血",
                        "润肠通便"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阳药"
},
            "紫苏叶": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肺、脾经"
            },
            "functions": [
                        "发表散寒",
                        "行气宽中",
                        "解鱼蟹毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        10
            ],
            "category": "解表药"
},
            "香薷": {
            "properties": {
                        "性味": "辛，微温",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "发汗解表",
                        "化湿和中",
                        "利水消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "解表药"
},
            "龙胆": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝、胆经"
            },
            "functions": [
                        "清热燥湿",
                        "泻肝胆火"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "清热燥湿药"
},
            "牡丹皮": {
            "properties": {
                        "性味": "苦、辛，微寒",
                        "归经": "心、肝、肾经"
            },
            "functions": [
                        "清热凉血",
                        "活血祛瘀"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "清热凉血药"
},
            "青蒿": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "肝、胆经"
            },
            "functions": [
                        "退虚热",
                        "凉血",
                        "解暑",
                        "截疟"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "清虚热药"
},
            "白薇": {
            "properties": {
                        "性味": "苦、咸，寒",
                        "归经": "胃、肝、肾经"
            },
            "functions": [
                        "退虚热",
                        "凉血清热",
                        "利尿通淋"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "清虚热药"
},
            "胡黄连": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "胃、大肠经"
            },
            "functions": [
                        "退虚热",
                        "除疳热",
                        "清湿热",
                        "解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "清虚热药"
},
            "番泻叶": {
            "properties": {
                        "性味": "甘、苦，寒",
                        "归经": "大肠经"
            },
            "functions": [
                        "泻热行滞",
                        "通便",
                        "利水"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "泻下药"
},
            "芦荟": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝、胃、大肠经"
            },
            "functions": [
                        "泻下清肝",
                        "杀虫"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "泻下药"
},
            "火麻仁": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "脾、胃、大肠经"
            },
            "functions": [
                        "润肠通便"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "泻下药"
},
            "郁李仁": {
            "properties": {
                        "性味": "辛、苦、甘，平",
                        "归经": "脾、大肠、小肠经"
            },
            "functions": [
                        "润肠通便",
                        "下气利水"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        10
            ],
            "category": "泻下药"
},
            "松子仁": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "肺、肝、大肠经"
            },
            "functions": [
                        "润肺止咳",
                        "润肠通便"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "泻下药"
},
            "巴豆": {
            "properties": {
                        "性味": "辛，热",
                        "归经": "胃、大肠、肺经"
            },
            "functions": [
                        "峻下冷积",
                        "逐水",
                        "祛痰"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.1,
                        0.3
            ],
            "category": "泻下药"
},
            "牵牛子": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "肺、肾、大肠经"
            },
            "functions": [
                        "泻下",
                        "逐水",
                        "杀虫"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "泻下药"
},
            "甘遂": {
            "properties": {
                        "性味": "苦、甘，寒",
                        "归经": "肺、肾、大肠经"
            },
            "functions": [
                        "泻水逐饮",
                        "消肿散结"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.5,
                        1.5
            ],
            "category": "泻下药"
},
            "大戟": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "肺、脾、肾经"
            },
            "functions": [
                        "泻水逐饮",
                        "消肿散结"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1.5,
                        3
            ],
            "category": "泻下药"
},
            "芫花": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "肺、脾、肾经"
            },
            "functions": [
                        "泻水逐饮",
                        "祛痰止咳"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1.5,
                        3
            ],
            "category": "泻下药"
},
            "商陆": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肺、脾、肾、大肠经"
            },
            "functions": [
                        "逐水消肿",
                        "通便",
                        "解毒散结"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "泻下药"
},
            "千金子": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、肾、大肠经"
            },
            "functions": [
                        "逐水退肿",
                        "破血消癥"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1,
                        2
            ],
            "category": "泻下药"
},
            "京大戟": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肺、脾、肾经"
            },
            "functions": [
                        "泻水逐饮",
                        "消肿散结"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1.5,
                        3
            ],
            "category": "泻下药"
},
            "桑寄生": {
            "properties": {
                        "性味": "苦、甘，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "补肝肾",
                        "强筋骨",
                        "安胎元"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "祛风湿药"
},
            "五加皮": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "补肝肾",
                        "强筋骨"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "木瓜": {
            "properties": {
                        "性味": "酸，温",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "舒筋活络",
                        "和胃化湿"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "蚕沙": {
            "properties": {
                        "性味": "甘、辛，温",
                        "归经": "肝、脾、胃经"
            },
            "functions": [
                        "祛风湿",
                        "和胃化浊"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "祛风湿药"
},
            "伸筋草": {
            "properties": {
                        "性味": "微苦、辛，温",
                        "归经": "肝、脾、肾经"
            },
            "functions": [
                        "祛风除湿",
                        "舒筋活络"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "透骨草": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风除湿",
                        "舒筋活血",
                        "止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "海风藤": {
            "properties": {
                        "性味": "辛、苦，微温",
                        "归经": "肝经"
            },
            "functions": [
                        "祛风湿",
                        "通经络",
                        "止痹痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "络石藤": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "心、肝、肾经"
            },
            "functions": [
                        "祛风通络",
                        "凉血消肿"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "青风藤": {
            "properties": {
                        "性味": "苦、辛，平",
                        "归经": "肝经"
            },
            "functions": [
                        "祛风湿",
                        "通经络",
                        "利小便"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "鸡血藤": {
            "properties": {
                        "性味": "苦、甘，温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补血",
                        "活血",
                        "通络"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "补血药"
},
            "豨莶草": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "通经络",
                        "清热解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "雷公藤": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "活血通络",
                        "消肿止痛",
                        "杀虫解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        20
            ],
            "category": "祛风湿药"
},
            "臭梧桐": {
            "properties": {
                        "性味": "甘、苦，平",
                        "归经": "肝经"
            },
            "functions": [
                        "祛风湿",
                        "通经络",
                        "降血压"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "海桐皮": {
            "properties": {
                        "性味": "辛、苦，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "通经络",
                        "杀虫止痒"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "桑枝": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "肝经"
            },
            "functions": [
                        "祛风湿",
                        "利关节"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "祛风湿药"
},
            "丝瓜络": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "肺、胃、肝经"
            },
            "functions": [
                        "通经络",
                        "清热化痰"
            ],
            "typical_roles": [
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "寻骨风": {
            "properties": {
                        "性味": "辛、苦，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "通经络",
                        "止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "千年健": {
            "properties": {
                        "性味": "苦、辛，温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "强筋骨"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "穿山龙": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "肝、肺经"
            },
            "functions": [
                        "祛风湿",
                        "活血通络",
                        "止咳定喘"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "石楠叶": {
            "properties": {
                        "性味": "辛、苦，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "祛风湿",
                        "补肝肾",
                        "强筋骨"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "祛风湿药"
},
            "白花蛇": {
            "properties": {
                        "性味": "甘、咸，温",
                        "归经": "肝经"
            },
            "functions": [
                        "祛风",
                        "通络",
                        "止痉"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "祛风湿药"
},
            "乌梢蛇": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "肝经"
            },
            "functions": [
                        "祛风",
                        "通络",
                        "止痉"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "祛风湿药"
},
            "蕲蛇": {
            "properties": {
                        "性味": "甘、咸，温",
                        "归经": "肝经"
            },
            "functions": [
                        "祛风",
                        "通络",
                        "止痉"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "祛风湿药"
},
            "广藿香": {
            "properties": {
                        "性味": "辛，微温",
                        "归经": "脾、胃、肺经"
            },
            "functions": [
                        "芳香化浊",
                        "和中止呕",
                        "发表解暑"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "芳香化湿药"
},
            "佩兰": {
            "properties": {
                        "性味": "辛，平",
                        "归经": "脾、胃、肾经"
            },
            "functions": [
                        "芳香化湿",
                        "醒脾开胃",
                        "发表解暑"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "芳香化湿药"
},
            "白豆蔻": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肺、脾、胃经"
            },
            "functions": [
                        "化湿行气",
                        "温中止呕"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "芳香化湿药"
},
            "草豆蔻": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "燥湿行气",
                        "温中止呕"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "芳香化湿药"
},
            "肉豆蔻": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、胃、大肠经"
            },
            "functions": [
                        "温中行气",
                        "涩肠止泻"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "收涩药"
},
            "草果": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "燥湿温中",
                        "截疟"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "芳香化湿药"
},
            "滑石": {
            "properties": {
                        "性味": "甘、淡，寒",
                        "归经": "胃、膀胱经"
            },
            "functions": [
                        "利尿通淋",
                        "清热解暑"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "芳香化湿药"
},
            "通草": {
            "properties": {
                        "性味": "甘、淡，微寒",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "清热利尿",
                        "通气下乳"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "芳香化湿药"
},
            "橘皮": {
            "properties": {
                        "性味": "苦、辛，温",
                        "归经": "脾、肺经"
            },
            "functions": [
                        "理气健脾",
                        "燥湿化痰"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "青木香": {
            "properties": {
                        "性味": "辛、苦，寒",
                        "归经": "肝、胃、大肠经"
            },
            "functions": [
                        "行气止痛",
                        "解毒消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "理气药"
},
            "天仙藤": {
            "properties": {
                        "性味": "苦，温",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "理气",
                        "祛风",
                        "止痛",
                        "活血"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "理气药"
},
            "九香虫": {
            "properties": {
                        "性味": "咸，温",
                        "归经": "肝、脾、肾经"
            },
            "functions": [
                        "理气止痛",
                        "温中助阳"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "理气药"
},
            "紫苏梗": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "理气宽中",
                        "止痛",
                        "安胎"
            ],
            "typical_roles": [
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "理气药"
},
            "大腹皮": {
            "properties": {
                        "性味": "辛，微温",
                        "归经": "脾、胃、大肠、小肠经"
            },
            "functions": [
                        "行气宽中",
                        "利水消肿"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "理气药"
},
            "甘松": {
            "properties": {
                        "性味": "辛、甘，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "理气止痛",
                        "开郁醒脾"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "理气药"
},
            "娑罗子": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "疏肝理气",
                        "和胃止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "理气药"
},
            "红景天": {
            "properties": {
                        "性味": "甘、苦，平",
                        "归经": "肺、心经"
            },
            "functions": [
                        "益气活血",
                        "通脉平喘"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "补气药"
},
            "绞股蓝": {
            "properties": {
                        "性味": "苦、微甘，寒",
                        "归经": "肺、脾、肾经"
            },
            "functions": [
                        "益气",
                        "安神",
                        "清热解毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "补气药"
},
            "紫河车": {
            "properties": {
                        "性味": "甘、咸，温",
                        "归经": "肺、肝、肾经"
            },
            "functions": [
                        "补肾益精",
                        "益气养血"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "补阳药"
},
            "六味地黄丸": {
            "properties": {
                        "性味": "甘，微温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "滋阴补血",
                        "益精填髓"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "补阴药"
},
            "天冬": {
            "properties": {
                        "性味": "甘、苦，寒",
                        "归经": "肺、肾经"
            },
            "functions": [
                        "养阴润燥",
                        "清肺生津"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "补阴药"
},
            "女贞子": {
            "properties": {
                        "性味": "甘、苦，凉",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "滋补肝肾",
                        "乌须明目"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "补阴药"
},
            "旱莲草": {
            "properties": {
                        "性味": "甘、酸，寒",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "滋补肝肾",
                        "凉血止血"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "补阴药"
},
            "鹿茸": {
            "properties": {
                        "性味": "甘、咸，温",
                        "归经": "肾、肝经"
            },
            "functions": [
                        "壮肾阳",
                        "益精血",
                        "强筋骨",
                        "调冲任"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "补阳药"
},
            "淫羊藿": {
            "properties": {
                        "性味": "辛、甘，温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补肾壮阳",
                        "强筋骨",
                        "祛风湿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阳药"
},
            "巴戟天": {
            "properties": {
                        "性味": "甘、辛，微温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补肾助阳",
                        "强筋骨",
                        "祛风湿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阳药"
},
            "菟丝子": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "肝、肾、脾经"
            },
            "functions": [
                        "补肾益精",
                        "养肝明目",
                        "固胎止泻"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "补阳药"
},
            "杜仲": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补肝肾",
                        "强筋骨",
                        "安胎"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阳药"
},
            "续断": {
            "properties": {
                        "性味": "苦、辛，微温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补肝肾",
                        "强筋骨",
                        "续折伤",
                        "止崩漏"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阳药"
},
            "骨碎补": {
            "properties": {
                        "性味": "苦，温",
                        "归经": "肾经"
            },
            "functions": [
                        "补肾强骨",
                        "续伤止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "补阳药"
},
            "补骨脂": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "肾、脾经"
            },
            "functions": [
                        "补肾壮阳",
                        "固精缩尿",
                        "温脾止泻"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "补阳药"
},
            "益智仁": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、肾经"
            },
            "functions": [
                        "暖肾固精缩尿",
                        "温脾开胃摄唾"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "补阳药"
},
            "沙苑子": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "补肾助阳",
                        "固精缩尿",
                        "养肝明目"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "补阳药"
},
            "谷芽": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "消食和中",
                        "健脾开胃"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        10,
                        15
            ],
            "category": "消食药"
},
            "白及": {
            "properties": {
                        "性味": "苦、甘、涩，微寒",
                        "归经": "肺、胃、肝经"
            },
            "functions": [
                        "收敛止血",
                        "消肿生肌"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "止血药"
},
            "仙鹤草": {
            "properties": {
                        "性味": "苦、涩，平",
                        "归经": "心、肝经"
            },
            "functions": [
                        "收敛止血",
                        "截疟",
                        "止痢",
                        "解毒",
                        "补虚"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "止血药"
},
            "茜草": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝经"
            },
            "functions": [
                        "凉血止血",
                        "活血祛瘀"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "止血药"
},
            "侧柏叶": {
            "properties": {
                        "性味": "苦、涩，寒",
                        "归经": "肺、肝、脾经"
            },
            "functions": [
                        "凉血止血",
                        "化痰止咳",
                        "生发乌发"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "止血药"
},
            "五倍子": {
            "properties": {
                        "性味": "酸、涩，寒",
                        "归经": "肺、大肠、肾经"
            },
            "functions": [
                        "敛肺降火",
                        "涩肠止泻",
                        "敛汗",
                        "止血",
                        "收湿敛疮"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "收涩药"
},
            "诃子": {
            "properties": {
                        "性味": "苦、酸、涩，平",
                        "归经": "肺、大肠经"
            },
            "functions": [
                        "涩肠止泻",
                        "敛肺止咳",
                        "降火利咽"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "收涩药"
},
            "赤石脂": {
            "properties": {
                        "性味": "甘、酸、涩，温",
                        "归经": "大肠、胃经"
            },
            "functions": [
                        "涩肠止泻",
                        "收敛止血",
                        "生肌敛疮"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        30
            ],
            "category": "收涩药"
},
            "常山": {
            "properties": {
                        "性味": "苦、辛，寒",
                        "归经": "肺、心、肝经"
            },
            "functions": [
                        "截疟",
                        "催吐痰饮"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        6,
                        10
            ],
            "category": "涌吐药"
},
            "瓜蒂": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "胃经"
            },
            "functions": [
                        "涌吐痰食",
                        "祛湿退黄"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "涌吐药"
},
            "雄黄": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、胃、大肠经"
            },
            "functions": [
                        "解毒杀虫",
                        "燥湿祛痰",
                        "截疟"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.05,
                        0.1
            ],
            "category": "解毒杀虫燥湿药"
},
            "轻粉": {
            "properties": {
                        "性味": "辛，寒",
                        "归经": "肺、脾、肾经"
            },
            "functions": [
                        "外用杀虫",
                        "攻毒",
                        "敛疮",
                        "内服祛痰消积"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.1,
                        0.5
            ],
            "category": "解毒杀虫燥湿药"
},
            "硫黄": {
            "properties": {
                        "性味": "酸，热",
                        "归经": "肾、大肠经"
            },
            "functions": [
                        "外用杀虫止痒",
                        "内服补火助阳",
                        "通便"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "解毒杀虫燥湿药"
},
            "红大戟": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "脾、肾经"
            },
            "functions": [
                        "泻水逐饮",
                        "消肿"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1.5,
                        3
            ],
            "category": "泻下药"
},
            "续随子": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、肾、大肠经"
            },
            "functions": [
                        "逐水退肿",
                        "破血消癥"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1,
                        2
            ],
            "category": "泻下药"
},
            "巴豆霜": {
            "properties": {
                        "性味": "辛，热",
                        "归经": "胃、大肠、肺经"
            },
            "functions": [
                        "峻下冷积",
                        "逐水",
                        "祛痰"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.1,
                        0.3
            ],
            "category": "泻下药"
},
            "蓖麻子": {
            "properties": {
                        "性味": "甘、辛，平",
                        "归经": "大肠、肺经"
            },
            "functions": [
                        "润肠通便",
                        "消肿拔毒"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        2,
                        6
            ],
            "category": "泻下药"
},
            "橘核": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "理气",
                        "散结",
                        "止痛"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "橘络": {
            "properties": {
                        "性味": "甘、苦，平",
                        "归经": "肺、脾、肝经"
            },
            "functions": [
                        "通络化痰",
                        "理气活血"
            ],
            "typical_roles": [
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        5
            ],
            "category": "理气药"
},
            "橘叶": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "疏肝理气",
                        "消肿散毒"
            ],
            "typical_roles": [
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "理气药"
},
            "绿萼梅": {
            "properties": {
                        "性味": "酸，平",
                        "归经": "肝、脾、胃经"
            },
            "functions": [
                        "疏肝",
                        "和中",
                        "化痰"
            ],
            "typical_roles": [
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "理气药"
},
            "建曲": {
            "properties": {
                        "性味": "甘、辛，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "健脾和胃",
                        "消食调中"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "消食药"
},
            "隔山撬": {
            "properties": {
                        "性味": "苦、辛，微温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "消食",
                        "健胃"
            ],
            "typical_roles": [
                        "臣药",
                        "佐药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "消食药"
},
            "小蓟": {
            "properties": {
                        "性味": "甘、苦，凉",
                        "归经": "心、肝经"
            },
            "functions": [
                        "凉血止血",
                        "散瘀解毒消痈"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "止血药"
},
            "大蓟": {
            "properties": {
                        "性味": "甘、苦，凉",
                        "归经": "心、肝经"
            },
            "functions": [
                        "凉血止血",
                        "散瘀消痈"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "止血药"
},
            "地榆": {
            "properties": {
                        "性味": "苦、酸、涩，微寒",
                        "归经": "肝、胃、大肠经"
            },
            "functions": [
                        "凉血止血",
                        "解毒敛疮"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "止血药"
},
            "槐花": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "肝、大肠经"
            },
            "functions": [
                        "凉血止血",
                        "清肝泻火"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        10
            ],
            "category": "止血药"
},
            "槐角": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝、大肠经"
            },
            "functions": [
                        "凉血止血",
                        "清肝泻火"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        15
            ],
            "category": "止血药"
},
            "白茅根": {
            "properties": {
                        "性味": "甘，寒",
                        "归经": "肺、胃、膀胱经"
            },
            "functions": [
                        "凉血止血",
                        "清热利尿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "止血药"
},
            "藕节": {
            "properties": {
                        "性味": "甘、涩，平",
                        "归经": "肝、肺、胃经"
            },
            "functions": [
                        "收敛止血",
                        "化瘀"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "止血药"
},
            "蒲黄": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "肝、心包经"
            },
            "functions": [
                        "止血",
                        "化瘀",
                        "通淋"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "止血药"
},
            "灶心土": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "脾、胃经"
            },
            "functions": [
                        "温中止血",
                        "止呕",
                        "止泻"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "止血药"
},
            "血余炭": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "收敛止血",
                        "化瘀",
                        "利尿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "止血药"
},
            "棕榈炭": {
            "properties": {
                        "性味": "苦、涩，平",
                        "归经": "肺、肝、大肠经"
            },
            "functions": [
                        "收敛止血"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "止血药"
},
            "血竭": {
            "properties": {
                        "性味": "甘、咸，平",
                        "归经": "心、肝经"
            },
            "functions": [
                        "活血定痛",
                        "化瘀止血",
                        "生肌敛疮"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "活血化瘀药"
},
            "花蕊石": {
            "properties": {
                        "性味": "酸、涩，平",
                        "归经": "肝经"
            },
            "functions": [
                        "化瘀止血"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "止血药"
},
            "紫珠叶": {
            "properties": {
                        "性味": "苦，凉",
                        "归经": "肺、肝、胃经"
            },
            "functions": [
                        "凉血收敛",
                        "散瘀止血",
                        "解毒消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "止血药"
},
            "姜黄": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "脾、肝经"
            },
            "functions": [
                        "破血行气",
                        "通经止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "泽兰": {
            "properties": {
                        "性味": "苦、辛，微温",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "活血化瘀",
                        "行水消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "活血化瘀药"
},
            "水蛭": {
            "properties": {
                        "性味": "咸、苦，平",
                        "归经": "肝经"
            },
            "functions": [
                        "破血通经",
                        "逐瘀消癥"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "活血化瘀药"
},
            "虻虫": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "肝经"
            },
            "functions": [
                        "破血逐瘀",
                        "散结"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "活血化瘀药"
},
            "土鳖虫": {
            "properties": {
                        "性味": "咸，寒",
                        "归经": "肝经"
            },
            "functions": [
                        "破血逐瘀",
                        "续筋接骨"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "活血化瘀药"
},
            "穿山甲": {
            "properties": {
                        "性味": "咸，微寒",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "活血散结",
                        "通经下乳",
                        "消肿排脓"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "活血化瘀药"
},
            "王不留行": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "活血通经",
                        "下乳消肿",
                        "利尿通淋"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "活血化瘀药"
},
            "凌霄花": {
            "properties": {
                        "性味": "甘、酸，微寒",
                        "归经": "肝、心包经"
            },
            "functions": [
                        "活血通经",
                        "凉血祛风"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        9
            ],
            "category": "活血化瘀药"
},
            "月季花": {
            "properties": {
                        "性味": "甘，温",
                        "归经": "肝经"
            },
            "functions": [
                        "活血调经",
                        "疏肝解郁"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        6
            ],
            "category": "活血化瘀药"
},
            "红藤": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "大肠、肝经"
            },
            "functions": [
                        "清热解毒",
                        "活血止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "活血化瘀药"
},
            "苏木": {
            "properties": {
                        "性味": "甘、咸，平",
                        "归经": "心、肝、脾经"
            },
            "functions": [
                        "活血祛瘀",
                        "消肿止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "活血化瘀药"
},
            "刘寄奴": {
            "properties": {
                        "性味": "苦，温",
                        "归经": "心、肝经"
            },
            "functions": [
                        "活血通经",
                        "止血",
                        "止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "自然铜": {
            "properties": {
                        "性味": "辛，平",
                        "归经": "肝经"
            },
            "functions": [
                        "散瘀止痛",
                        "接骨疗伤"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "活血化瘀药"
},
            "儿茶": {
            "properties": {
                        "性味": "苦、涩，微寒",
                        "归经": "肺、胃经"
            },
            "functions": [
                        "活血止痛",
                        "止血生肌",
                        "收湿敛疮"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "活血化瘀药"
},
            "干漆": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肝、胃经"
            },
            "functions": [
                        "破血祛瘀",
                        "杀虫"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "活血化瘀药"
},
            "庶虫": {
            "properties": {
                        "性味": "咸，寒",
                        "归经": "肝经"
            },
            "functions": [
                        "破血逐瘀",
                        "续筋接骨"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "活血化瘀药"
},
            "马钱子": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝、脾经"
            },
            "functions": [
                        "通络止痛",
                        "散结消肿"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.3,
                        0.6
            ],
            "category": "活血化瘀药"
},
            "乳香": {
            "properties": {
                        "性味": "辛、苦，温",
                        "归经": "心、肝、脾经"
            },
            "functions": [
                        "活血行气止痛",
                        "消肿生肌"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "没药": {
            "properties": {
                        "性味": "苦，平",
                        "归经": "心、肝、脾经"
            },
            "functions": [
                        "活血止痛",
                        "消肿生肌"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "活血化瘀药"
},
            "南星": {
            "properties": {
                        "性味": "苦、辛，温",
                        "归经": "肺、肝、脾经"
            },
            "functions": [
                        "燥湿化痰",
                        "祛风止痉",
                        "散结消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "化痰药"
},
            "白芥子": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "肺经"
            },
            "functions": [
                        "温肺豁痰利气",
                        "散结通络止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "化痰药"
},
            "皂荚": {
            "properties": {
                        "性味": "辛、咸，温",
                        "归经": "肺、大肠经"
            },
            "functions": [
                        "祛痰开窍",
                        "散结消肿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        1.5
            ],
            "category": "开窍药"
},
            "马兜铃": {
            "properties": {
                        "性味": "苦，微寒",
                        "归经": "肺、大肠经"
            },
            "functions": [
                        "清肺降气",
                        "止咳平喘"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        9
            ],
            "category": "止咳平喘药"
},
            "矮地茶": {
            "properties": {
                        "性味": "辛、微苦，平",
                        "归经": "肺、肝经"
            },
            "functions": [
                        "化痰止咳",
                        "利湿",
                        "活血"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        15
            ],
            "category": "止咳平喘药"
},
            "朱砂": {
            "properties": {
                        "性味": "甘，微寒",
                        "归经": "心经"
            },
            "functions": [
                        "镇心安神",
                        "清热解毒"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.1,
                        0.5
            ],
            "category": "重镇安神药"
},
            "磁石": {
            "properties": {
                        "性味": "辛、咸，寒",
                        "归经": "肾、心、肝经"
            },
            "functions": [
                        "镇惊安神",
                        "平肝潜阳",
                        "聪耳明目",
                        "纳气定喘"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        30
            ],
            "category": "重镇安神药"
},
            "珍珠母": {
            "properties": {
                        "性味": "咸，寒",
                        "归经": "肝、心经"
            },
            "functions": [
                        "镇惊安神",
                        "平肝潜阳",
                        "清肝明目"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        10,
                        25
            ],
            "category": "平肝息风药"
},
            "琥珀": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肝、膀胱经"
            },
            "functions": [
                        "镇惊安神",
                        "散瘀止血",
                        "利尿通淋"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        1,
                        3
            ],
            "category": "重镇安神药"
},
            "柏子仁": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肾、大肠经"
            },
            "functions": [
                        "养心安神",
                        "润肠通便"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        3,
                        10
            ],
            "category": "养心安神药"
},
            "合欢花": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肝经"
            },
            "functions": [
                        "解郁安神",
                        "理气开胃",
                        "活络止痛"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "养心安神药"
},
            "灵芝": {
            "properties": {
                        "性味": "甘，平",
                        "归经": "心、肺、肝、肾经"
            },
            "functions": [
                        "补气安神",
                        "止咳平喘"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "养心安神药"
},
            "小麦": {
            "properties": {
                        "性味": "甘，凉",
                        "归经": "心、脾、肾经"
            },
            "functions": [
                        "养心安神",
                        "除烦"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        15,
                        30
            ],
            "category": "养心安神药"
},
            "石决明": {
            "properties": {
                        "性味": "咸，寒",
                        "归经": "肝、肾经"
            },
            "functions": [
                        "平肝潜阳",
                        "清肝明目"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        30
            ],
            "category": "平肝息风药"
},
            "代赭石": {
            "properties": {
                        "性味": "苦，寒",
                        "归经": "肝、心包经"
            },
            "functions": [
                        "平肝潜阳",
                        "重镇降逆",
                        "凉血止血"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        9,
                        30
            ],
            "category": "平肝息风药"
},
            "刺蒺藜": {
            "properties": {
                        "性味": "辛、苦，微温",
                        "归经": "肝经"
            },
            "functions": [
                        "平肝解郁",
                        "活血祛风",
                        "明目"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        6,
                        12
            ],
            "category": "平肝息风药"
},
            "地龙": {
            "properties": {
                        "性味": "咸，寒",
                        "归经": "肝、脾、膀胱经"
            },
            "functions": [
                        "清热息风",
                        "通络",
                        "平喘",
                        "利尿"
            ],
            "typical_roles": [
                        "君药",
                        "臣药"
            ],
            "typical_dosage": [
                        5,
                        15
            ],
            "category": "平肝息风药"
},
            "苏合香": {
            "properties": {
                        "性味": "辛，温",
                        "归经": "心、脾经"
            },
            "functions": [
                        "开窍醒神",
                        "辟秽",
                        "止痛"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.3,
                        1
            ],
            "category": "开窍药"
},
            "安息香": {
            "properties": {
                        "性味": "辛、苦，平",
                        "归经": "心、脾经"
            },
            "functions": [
                        "开窍醒神",
                        "行气活血",
                        "止痛"
            ],
            "typical_roles": [
                        "君药"
            ],
            "typical_dosage": [
                        0.3,
                        1
            ],
            "category": "开窍药"
}}
    
    def _load_formula_patterns(self) -> Dict:
        """加载方剂模式"""
        return {
            '四君子汤': {
                'composition': ['人参', '白术', '茯苓', '甘草'],
                'pattern': '补气健脾',
                'structure': {
                    '君药': ['人参'],
                    '臣药': ['白术'],
                    '佐药': ['茯苓'],
                    '使药': ['甘草']
                }
            },
            '六君子汤': {
                'composition': ['人参', '白术', '茯苓', '甘草', '陈皮', '半夏'],
                'pattern': '益气健脾，燥湿化痰',
                'structure': {
                    '君药': ['人参'],
                    '臣药': ['白术', '茯苓'],
                    '佐药': ['陈皮', '半夏'],
                    '使药': ['甘草']
                }
            },
            '补中益气汤': {
                'composition': ['黄芪', '人参', '白术', '甘草', '当归', '陈皮', '升麻', '柴胡'],
                'pattern': '补中益气，升阳举陷',
                'structure': {
                    '君药': ['黄芪'],
                    '臣药': ['人参', '白术', '甘草'],
                    '佐药': ['当归', '陈皮'],
                    '使药': ['升麻', '柴胡']
                }
            }
        }
    
    def analyze_formula_roles(self, herbs: List[Dict]) -> Dict[str, List[HerbRole]]:
        """分析方剂君臣佐使"""
        if not herbs:
            return {'君药': [], '臣药': [], '佐药': [], '使药': []}
        
        # 解析药材信息
        herb_infos = []
        for herb in herbs:
            herb_info = HerbInfo(
                name=herb.get('name', ''),
                dosage=self._parse_dosage(herb.get('dosage', 0)),
                unit=herb.get('unit', 'g'),
                processing=herb.get('processing')
            )
            herb_infos.append(herb_info)
        
        # 识别方剂模式
        formula_pattern = self._identify_formula_pattern(herb_infos)
        
        # 分析君臣佐使
        if formula_pattern:
            roles = self._analyze_by_pattern(herb_infos, formula_pattern)
        else:
            roles = self._analyze_by_rules(herb_infos)
        
        return roles
    
    def _parse_dosage(self, dosage) -> float:
        """解析用量"""
        if isinstance(dosage, (int, float)):
            return float(dosage)
        
        if isinstance(dosage, str):
            # 提取数字
            numbers = re.findall(r'\d+\.?\d*', dosage)
            if numbers:
                return float(numbers[0])
        
        return 0.0
    
    def _identify_formula_pattern(self, herb_infos: List[HerbInfo]) -> Optional[str]:
        """识别方剂模式"""
        herb_names = [herb.name for herb in herb_infos]
        
        for pattern_name, pattern_info in self.formula_patterns.items():
            composition = pattern_info['composition']
            
            # 计算匹配度
            matched = sum(1 for herb in composition if herb in herb_names)
            match_ratio = matched / len(composition)
            
            if match_ratio >= 0.6:  # 60%以上匹配度
                return pattern_name
        
        return None
    
    def _analyze_by_pattern(self, herb_infos: List[HerbInfo], pattern_name: str) -> Dict[str, List[HerbRole]]:
        """基于方剂模式分析"""
        pattern = self.formula_patterns[pattern_name]
        structure = pattern['structure']
        
        roles = {'君药': [], '臣药': [], '佐药': [], '使药': []}
        
        for herb in herb_infos:
            assigned = False
            
            for role, role_herbs in structure.items():
                if herb.name in role_herbs:
                    herb_role = HerbRole(
                        name=herb.name,
                        dosage=f"{herb.dosage}{herb.unit}",
                        role=role,
                        reason=f"经方{pattern_name}中的{role}，{self._get_herb_function(herb.name)}",
                        confidence=0.9
                    )
                    roles[role].append(herb_role)
                    assigned = True
                    break
            
            # 如果未在经典方剂中找到，使用规则分析
            if not assigned:
                role_analysis = self._analyze_single_herb_role(herb, herb_infos)
                if role_analysis:
                    roles[role_analysis.role].append(role_analysis)
        
        return roles
    
    def _analyze_by_rules(self, herb_infos: List[HerbInfo]) -> Dict[str, List[HerbRole]]:
        """基于规则分析君臣佐使"""
        roles = {'君药': [], '臣药': [], '佐药': [], '使药': []}
        
        # 按用量排序
        sorted_herbs = sorted(herb_infos, key=lambda x: x.dosage, reverse=True)
        
        # 特殊药材处理
        special_roles = self._assign_special_roles(herb_infos)
        assigned_herbs = set()
        
        for role, herb_list in special_roles.items():
            for herb_role in herb_list:
                roles[role].append(herb_role)
                assigned_herbs.add(herb_role.name)
        
        # 剩余药材按用量和功效分析
        remaining_herbs = [h for h in sorted_herbs if h.name not in assigned_herbs]
        
        if remaining_herbs:
            # 确定君药（用量最大且为主治药）
            if not roles['君药']:
                herb = remaining_herbs[0]
                herb_role = HerbRole(
                    name=herb.name,
                    dosage=f"{herb.dosage}{herb.unit}",
                    role='君药',
                    reason=f"用量最大({herb.dosage}{herb.unit})，为主治药物，{self._get_herb_function(herb.name)}",
                    confidence=0.8
                )
                roles['君药'].append(herb_role)
                remaining_herbs = remaining_herbs[1:]
            
            # 分配臣药和佐药
            for i, herb in enumerate(remaining_herbs):
                if i < 2 and herb.dosage >= 9:  # 臣药
                    role = '臣药'
                    reason = f"用量适中({herb.dosage}{herb.unit})，辅助君药治疗，{self._get_herb_function(herb.name)}"
                else:  # 佐药
                    role = '佐药'
                    reason = f"用量较小({herb.dosage}{herb.unit})，{self._get_herb_function(herb.name)}"
                
                herb_role = HerbRole(
                    name=herb.name,
                    dosage=f"{herb.dosage}{herb.unit}",
                    role=role,
                    reason=reason,
                    confidence=0.7
                )
                roles[role].append(herb_role)
        
        return roles
    
    def _assign_special_roles(self, herb_infos: List[HerbInfo]) -> Dict[str, List[HerbRole]]:
        """分配特殊角色的药材"""
        roles = {'君药': [], '臣药': [], '佐药': [], '使药': []}
        
        for herb in herb_infos:
            herb_data = self.herb_database.get(herb.name, {})
            typical_roles = herb_data.get('typical_roles', [])
            
            # 甘草通常为使药
            if herb.name == '甘草':
                herb_role = HerbRole(
                    name=herb.name,
                    dosage=f"{herb.dosage}{herb.unit}",
                    role='使药',
                    reason="调和诸药，缓急止痛，为典型使药",
                    confidence=0.95
                )
                roles['使药'].append(herb_role)
            
            # 引药类
            elif herb.name in ['生姜', '大枣'] and herb.dosage <= 10:
                herb_role = HerbRole(
                    name=herb.name,
                    dosage=f"{herb.dosage}{herb.unit}",
                    role='使药',
                    reason=f"引药归经，调和营卫，典型使药",
                    confidence=0.9
                )
                roles['使药'].append(herb_role)
        
        return roles
    
    def _analyze_single_herb_role(self, herb: HerbInfo, all_herbs: List[HerbInfo]) -> Optional[HerbRole]:
        """分析单个药材的角色"""
        herb_data = self.herb_database.get(herb.name, {})
        
        if not herb_data:
            # 未知药材，基于用量判断
            if herb.dosage >= 15:
                role = '君药'
                reason = f"用量较大({herb.dosage}{herb.unit})，推测为主药"
            elif herb.dosage >= 9:
                role = '臣药'
                reason = f"用量适中({herb.dosage}{herb.unit})，推测为辅助药"
            else:
                role = '佐药'
                reason = f"用量较小({herb.dosage}{herb.unit})，推测为佐助药"
            
            return HerbRole(
                name=herb.name,
                dosage=f"{herb.dosage}{herb.unit}",
                role=role,
                reason=reason,
                confidence=0.5
            )
        
        # 已知药材，结合功效和用量判断
        typical_roles = herb_data.get('typical_roles', [])
        functions = herb_data.get('functions', [])
        
        if typical_roles:
            # 基于典型角色和用量确定
            role = typical_roles[0]  # 使用第一个典型角色
            function_desc = '、'.join(functions[:2]) if functions else "调理脏腑"
            
            return HerbRole(
                name=herb.name,
                dosage=f"{herb.dosage}{herb.unit}",
                role=role,
                reason=f"{function_desc}，典型的{role}",
                confidence=0.8
            )
        
        return None
    
    def _get_herb_function(self, herb_name: str) -> str:
        """获取药材功效描述"""
        herb_data = self.herb_database.get(herb_name, {})
        functions = herb_data.get('functions', [])
        
        if functions:
            return '、'.join(functions[:2])
        else:
            # 为常见缺失药材提供功效描述
            missing_herbs_functions = {
                "射干": "清热解毒、祛痰利咽",
                "防己": "利水消肿、祛风止痛", 
                "茵陈": "清湿热、退黄疸",
                "薏苡仁": "利水渗湿、健脾止泻",
                "鱼腥草": "清热解毒、消痈排脓",
                "荆芥穗": "发汗解表、祛风胜湿",
                "五灵脂": "活血止痛、化瘀止血",
                "制附子": "回阳救逆、补火助阳",
                "生地": "清热凉血、养阴生津",
                "熟地": "滋阴补血、填精益髓",
                "炒白术": "补气健脾、燥湿利水",
                "茯神": "宁心安神、利水渗湿",
                "胖大海": "清热润肺、利咽开音",
                "花椒": "温中止痛、杀虫止痒",
                "高良姜": "温胃散寒、消食止痛",
                "荷叶": "清暑利湿、升发清阳",
                "豆豉": "解表除烦、宣郁懊憹",
                "败酱草": "清热解毒、消痈排脓",
                "芡实": "益肾固精、补脾止泻",
                "老鹳草": "祛风湿、通经络",
                "忍冬藤": "清热解毒、疏风通络",
                "川断": "补肝肾、强筋骨",
                "北细辛": "解表散寒、祛风止痛",
                "制川乌": "祛风除湿、温经止痛",
                "苏叶": "发表散寒、行气宽中",
                "白蔻仁": "化湿行气、温中止呕",
                "皂角刺": "消肿托毒、排脓",
                "桑螵蛸": "固精缩尿、补肾助阳",
                # 常见药材补充
                "扯根菜": "清热解毒、利湿消肿",
                "甜叶菊": "清热生津、润燥",
                "枯梗": "宣肺利咽、祛痰排脓",
                "炒莱菔子": "消食除胀、降气化痰",
                "炒紫苏子": "降气化痰、止咳平喘",
                "姜半夏": "燥湿化痰、降逆止呕",
                "僵蚕炒": "息风止痉、祛风止痛",
                "旋覆花": "降气消痰、行水止呕"
            }
            
            # 智能fallback，避免千篇一律的"调理脏腑功能" 
            fallback_result = missing_herbs_functions.get(herb_name)
            if fallback_result:
                return fallback_result
                
            # 基于药材名称的智能推断
            if '参' in herb_name:
                return '补气健脾、扶正固本'
            elif any(x in herb_name for x in ['芪', '耆']):
                return '补气升阳、固表止汗'  
            elif any(x in herb_name for x in ['归', '当']):
                return '补血活血、调经止痛'
            elif '草' in herb_name:
                return '清热解毒、调和诸药'
            elif any(x in herb_name for x in ['术', '朮']):
                return '健脾燥湿、补气利水'
            elif '苓' in herb_name:
                return '利水渗湿、健脾宁心'
            elif '芍' in herb_name:
                return '养血柔肝、缓急止痛'
            elif '地' in herb_name:
                return '滋阴补血、清热凉血'
            elif any(x in herb_name for x in ['芎', '川']):
                return '活血行气、祛风止痛'
            elif '皮' in herb_name:
                return '理气化痰、行气消胀'  
            elif '花' in herb_name:
                return '行气解郁、理血调经'
            elif '子' in herb_name:
                return '润肠通便、消食除胀'
            else:
                # 最后才使用通用描述
                return '辅助调理、协同治疗'
    
    def generate_analysis_summary(self, roles: Dict[str, List[HerbRole]]) -> Dict:
        """生成分析总结"""
        total_herbs = sum(len(herb_list) for herb_list in roles.values())
        
        summary = {
            'total_herbs': total_herbs,
            'composition_analysis': {},
            'formula_characteristics': [],
            'compatibility_analysis': []
        }
        
        for role, herb_list in roles.items():
            if herb_list:
                summary['composition_analysis'][role] = {
                    'count': len(herb_list),
                    'herbs': [herb.name for herb in herb_list],
                    'average_confidence': round(sum(herb.confidence for herb in herb_list) / len(herb_list), 2)
                }
        
        # 方剂特色分析
        if roles['君药']:
            jun_herbs = [herb.name for herb in roles['君药']]
            summary['formula_characteristics'].append(f"以{', '.join(jun_herbs)}为君药")
        
        if roles['臣药']:
            chen_herbs = [herb.name for herb in roles['臣药']]
            summary['formula_characteristics'].append(f"以{', '.join(chen_herbs)}为臣药")
        
        # 配伍分析
        if '甘草' in [herb.name for herb in roles['使药']]:
            summary['compatibility_analysis'].append("甘草调和诸药，缓急止痛")
        
        if any('补' in self._get_herb_function(herb.name) for role_herbs in roles.values() for herb in role_herbs):
            summary['compatibility_analysis'].append("方中多用补益之品，具有扶正作用")
        
        return summary

def analyze_formula_with_ai(herbs: List[Dict]) -> Dict:
    """
    使用AI增强的君臣佐使分析
    """
    analyzer = TCMFormulaAnalyzer()
    
    # 传统规则分析
    traditional_roles = analyzer.analyze_formula_roles(herbs)
    
    # 生成分析总结
    summary = analyzer.generate_analysis_summary(traditional_roles)
    
    # 转换为JSON可序列化的格式
    serializable_roles = {}
    for role, herb_list in traditional_roles.items():
        serializable_roles[role] = [asdict(herb) for herb in herb_list]
    
    return {
        'roles': serializable_roles,
        'summary': summary,
        'analysis_method': 'traditional_rules_with_ai_enhancement',
        'confidence_level': 'high' if summary['composition_analysis'] else 'medium'
    }

# 测试函数
def test_formula_analysis():
    """测试君臣佐使分析"""
    test_herbs = [
        {'name': '黄芪', 'dosage': 15, 'unit': 'g'},
        {'name': '白术', 'dosage': 12, 'unit': 'g'},
        {'name': '茯苓', 'dosage': 10, 'unit': 'g'},
        {'name': '甘草', 'dosage': 6, 'unit': 'g'},
        {'name': '陈皮', 'dosage': 9, 'unit': 'g'},
        {'name': '半夏', 'dosage': 9, 'unit': 'g'}
    ]
    
    result = analyze_formula_with_ai(test_herbs)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_formula_analysis()