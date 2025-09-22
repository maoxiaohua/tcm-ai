#!/usr/bin/env python3
"""
医学知识库API路由
Medical Knowledge Base API Routes
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional, Any
import json
import sqlite3
from pathlib import Path

router = APIRouter(prefix="/api/medical-knowledge", tags=["医学知识库"])

# 知识库数据缓存
knowledge_cache = {}

def load_tcm_database():
    """加载TCM数据库"""
    global knowledge_cache
    if knowledge_cache:
        return knowledge_cache
    
    try:
        db_path = Path("/opt/tcm-ai/template_files/complete_tcm_database.json")
        if db_path.exists():
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                knowledge_cache = data
                return data
    except Exception as e:
        print(f"加载TCM数据库失败: {e}")
    
    return {"documents": [], "total_prescriptions": 0}

@router.get("/classics/{classic_type}")
async def get_classic_content(classic_type: str):
    """获取经典文献内容"""
    
    classics_data = {
        "huangdi": {
            "title": "黄帝内经",
            "subtitle": "中医基础理论的经典著作",
            "content": {
                "core_concepts": [
                    {"name": "阴阳理论", "description": "阴阳是宇宙万物的基本规律，人体生理病理的根本", "details": "阴阳互根、阴阳制约、阴阳转化"},
                    {"name": "五行学说", "description": "木、火、土、金、水五行相生相克", "details": "五行配五脏：肝木、心火、脾土、肺金、肾水"},
                    {"name": "气血津液", "description": "人体生命活动的基本物质", "details": "气为阳，血为阴，津液润养全身"},
                    {"name": "藏象学说", "description": "五脏六腑的生理功能及相互关系", "details": "心主血脉，肺主气，脾主运化，肝主疏泄，肾主藏精"}
                ],
                "diagnostic_methods": [
                    {"name": "望诊", "description": "观察患者的神、色、形、态", "key_points": ["神志、面色、形体、舌象"]},
                    {"name": "闻诊", "description": "听声音、嗅气味", "key_points": ["语音、呼吸、咳嗽、各种气味"]},
                    {"name": "问诊", "description": "询问症状、病史", "key_points": ["主诉、现病史、既往史、家族史"]},
                    {"name": "切诊", "description": "触摸脉象、按压穴位", "key_points": ["脉象、腹诊、皮肤弹性"]}
                ],
                "key_quotes": [
                    "阴平阳秘，精神乃治",
                    "正气存内，邪不可干",
                    "治病必求于本",
                    "上工治未病，不治已病"
                ]
            }
        },
        "shanghan": {
            "title": "伤寒杂病论",
            "subtitle": "张仲景经方理论，六经辨证的经典",
            "content": {
                "six_meridians": [
                    {"name": "太阳病", "symptoms": "项背强几几，恶寒发热，脉浮", "representative_formula": "麻黄汤、桂枝汤"},
                    {"name": "阳明病", "symptoms": "胃家实，身热汗出，不恶寒", "representative_formula": "白虎汤、承气汤"},
                    {"name": "少阳病", "symptoms": "口苦，咽干，目眩，往来寒热", "representative_formula": "小柴胡汤"},
                    {"name": "太阴病", "symptoms": "腹满而吐，食不下，自利益甚", "representative_formula": "理中汤"},
                    {"name": "少阴病", "symptoms": "脉微细，但欲寐", "representative_formula": "四逆汤、麻黄附子细辛汤"},
                    {"name": "厥阴病", "symptoms": "消渴，气上撞心，饥而不欲食", "representative_formula": "乌梅丸"}
                ],
                "classic_formulas": [
                    {"name": "麻黄汤", "composition": "麻黄、桂枝、杏仁、甘草", "function": "发汗解表，宣肺平喘"},
                    {"name": "桂枝汤", "composition": "桂枝、芍药、甘草、生姜、大枣", "function": "解肌发表，调和营卫"},
                    {"name": "小柴胡汤", "composition": "柴胡、黄芩、人参、甘草、生姜、大枣、半夏", "function": "和解少阳"},
                    {"name": "四逆汤", "composition": "附子、干姜、甘草", "function": "回阳救逆"}
                ],
                "key_principles": [
                    "观其脉证，知犯何逆，随证治之",
                    "见肝之病，知肝传脾，当先实脾",
                    "但见一证便是，不必悉具"
                ]
            }
        },
        "bencao": {
            "title": "神农本草经",
            "subtitle": "中药学的奠基之作",
            "content": {
                "drug_classification": [
                    {"grade": "上品", "description": "无毒，久服不伤人", "examples": ["人参", "甘草", "茯苓", "大枣"], "count": "120种"},
                    {"grade": "中品", "description": "有毒无毒并存，当适当使用", "examples": ["当归", "芍药", "黄连", "麻黄"], "count": "120种"},
                    {"grade": "下品", "description": "多有毒，不可久服", "examples": ["附子", "乌头", "巴豆", "斑蝥"], "count": "125种"}
                ],
                "key_herbs": [
                    {"name": "人参", "nature": "温", "flavor": "甘微苦", "meridian": ["脾", "肺"], "effects": "大补元气，复脉固脱，补脾益肺，生津止渴，安神益智"},
                    {"name": "甘草", "nature": "平", "flavor": "甘", "meridian": ["脾", "胃", "心", "肺"], "effects": "补脾益气，清热解毒，祛痰止咳，缓急止痛，调和诸药"},
                    {"name": "当归", "nature": "温", "flavor": "甘辛", "meridian": ["心", "肝", "脾"], "effects": "补血调经，活血止痛，润肠通便"},
                    {"name": "黄连", "nature": "寒", "flavor": "苦", "meridian": ["心", "脾", "胃", "肝", "胆", "大肠"], "effects": "清热燥湿，泻火解毒"}
                ],
                "four_natures": ["寒", "热", "温", "凉"],
                "five_flavors": ["酸", "苦", "甘", "辛", "咸"],
                "key_principles": [
                    "药有酸咸甘苦辛五味，又有寒热温凉四气",
                    "疗寒以热药，疗热以寒药",
                    "欲利小便者，必秋冬乃可，春夏慎之"
                ]
            }
        }
    }
    
    if classic_type not in classics_data:
        raise HTTPException(status_code=404, detail="经典文献类型不存在")
    
    return {
        "success": True,
        "data": classics_data[classic_type]
    }

@router.get("/prescriptions/search")
async def search_prescriptions(
    keyword: str = None,
    disease: str = None,
    herb: str = None,
    limit: int = 20
):
    """搜索处方信息"""
    
    db_data = load_tcm_database()
    if not db_data or "documents" not in db_data:
        raise HTTPException(status_code=500, detail="知识库数据加载失败")
    
    results = []
    
    for doc in db_data["documents"]:
        if not doc.get("prescriptions"):
            continue
            
        for prescription in doc["prescriptions"]:
            match = False
            
            # 按关键词搜索
            if keyword:
                if (keyword.lower() in prescription.get("formula_name", "").lower() or
                    keyword.lower() in prescription.get("disease_name", "").lower() or
                    keyword.lower() in prescription.get("syndrome", "").lower()):
                    match = True
            
            # 按疾病搜索
            if disease and disease.lower() in prescription.get("disease_name", "").lower():
                match = True
                
            # 按药材搜索
            if herb:
                for h in prescription.get("herbs", []):
                    if herb.lower() in h.get("name", "").lower():
                        match = True
                        break
            
            # 如果没有搜索条件，返回所有
            if not keyword and not disease and not herb:
                match = True
            
            if match:
                results.append({
                    "prescription_id": prescription.get("prescription_id"),
                    "disease_name": prescription.get("disease_name"),
                    "syndrome": prescription.get("syndrome"),
                    "formula_name": prescription.get("formula_name"),
                    "herbs": prescription.get("herbs", []),
                    "treatment_method": prescription.get("treatment_method", "")
                })
                
                if len(results) >= limit:
                    break
        
        if len(results) >= limit:
            break
    
    return {
        "success": True,
        "total": len(results),
        "data": results[:limit]
    }

@router.get("/herbs/info/{herb_name}")
async def get_herb_info(herb_name: str):
    """获取药材详细信息"""
    
    # 基础药材信息数据库
    herbs_info = {
        "人参": {
            "name": "人参",
            "category": "补虚药",
            "nature": "温",
            "flavor": "甘微苦",
            "meridian": ["脾", "肺"],
            "effects": ["大补元气", "复脉固脱", "补脾益肺", "生津止渴", "安神益智"],
            "indications": ["气虚欲脱", "脾气虚弱", "肺气虚喘", "津伤口渴", "心神不安"],
            "dosage": "3-9g",
            "contraindications": ["实证、热证忌用"],
            "processing": ["生用", "红参", "白参"]
        },
        "甘草": {
            "name": "甘草",
            "category": "补虚药",
            "nature": "平",
            "flavor": "甘",
            "meridian": ["脾", "胃", "心", "肺"],
            "effects": ["补脾益气", "清热解毒", "祛痰止咳", "缓急止痛", "调和诸药"],
            "indications": ["脾胃虚弱", "咽喉肿痛", "痰多咳嗽", "脘腹疼痛", "药物中毒"],
            "dosage": "2-10g",
            "contraindications": ["湿阻中焦", "浮肿胀满者忌用"],
            "processing": ["生甘草", "炙甘草"]
        }
        # 可以继续添加更多药材...
    }
    
    # 如果没有预定义信息，从处方数据中提取
    if herb_name not in herbs_info:
        db_data = load_tcm_database()
        herb_prescriptions = []
        
        for doc in db_data.get("documents", []):
            for prescription in doc.get("prescriptions", []):
                for herb in prescription.get("herbs", []):
                    if herb_name.lower() in herb.get("name", "").lower():
                        herb_prescriptions.append({
                            "formula": prescription.get("formula_name"),
                            "disease": prescription.get("disease_name"),
                            "dose": herb.get("dose"),
                            "unit": herb.get("unit")
                        })
        
        if herb_prescriptions:
            return {
                "success": True,
                "data": {
                    "name": herb_name,
                    "found_in_prescriptions": len(herb_prescriptions),
                    "usage_examples": herb_prescriptions[:10],
                    "note": "详细药材信息正在完善中"
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"未找到药材 '{herb_name}' 的相关信息")
    
    return {
        "success": True,
        "data": herbs_info[herb_name]
    }

@router.get("/diagnostics/methods")
async def get_diagnostic_methods():
    """获取诊断方法说明"""
    
    methods = {
        "four_examinations": {
            "name": "四诊合参",
            "description": "中医诊断的基本方法",
            "methods": [
                {
                    "name": "望诊",
                    "description": "观察患者的外在表现",
                    "content": [
                        "望神：观察患者精神状态",
                        "望色：面色变化反映脏腑盛衰",
                        "望形：体形胖瘦、姿态动静",
                        "望态：行为举止、表情变化",
                        "望舌：舌质舌苔反映内在病变"
                    ]
                },
                {
                    "name": "闻诊", 
                    "description": "听声音、嗅气味",
                    "content": [
                        "听语音：声音高低、清浊、强弱",
                        "听呼吸：呼吸的深浅、快慢、强弱",
                        "听咳嗽：咳声特点、痰音变化",
                        "嗅体味：口臭、汗味、分泌物气味"
                    ]
                }
            ]
        },
        "pattern_identification": {
            "name": "辨证论治",
            "description": "中医诊疗的核心思维",
            "types": [
                {"name": "八纲辨证", "content": "阴阳、表里、寒热、虚实"},
                {"name": "脏腑辨证", "content": "心、肝、脾、肺、肾及六腑辨证"},
                {"name": "六经辨证", "content": "太阳、阳明、少阳、太阴、少阴、厥阴"},
                {"name": "卫气营血辨证", "content": "温病学说的辨证体系"},
                {"name": "三焦辨证", "content": "温病的另一辨证体系"}
            ]
        }
    }
    
    return {
        "success": True,
        "data": methods
    }

@router.get("/formulas/categories")  
async def get_formula_categories():
    """获取方剂分类信息"""
    
    categories = {
        "categories": [
            {
                "name": "解表剂",
                "description": "治疗外感表证的方剂",
                "subcategories": [
                    {"name": "辛温解表", "examples": ["麻黄汤", "桂枝汤", "九味羌活汤"]},
                    {"name": "辛凉解表", "examples": ["银翘散", "桑菊饮", "麻杏石甘汤"]}
                ]
            },
            {
                "name": "泻下剂",
                "description": "通过泻下作用治疗里实证的方剂",
                "subcategories": [
                    {"name": "寒下", "examples": ["大承气汤", "小承气汤", "调胃承气汤"]},
                    {"name": "温下", "examples": ["大黄附子汤", "温脾汤"]},
                    {"name": "润下", "examples": ["麻子仁丸", "润肠丸"]}
                ]
            },
            {
                "name": "和解剂", 
                "description": "和解少阳或调和肝脾的方剂",
                "subcategories": [
                    {"name": "和解少阳", "examples": ["小柴胡汤", "大柴胡汤"]},
                    {"name": "调和肝脾", "examples": ["逍遥散", "痛泻要方"]}
                ]
            },
            {
                "name": "清热剂",
                "description": "清热泻火、凉血解毒的方剂", 
                "subcategories": [
                    {"name": "清气分热", "examples": ["白虎汤", "竹叶石膏汤"]},
                    {"name": "清营凉血", "examples": ["清营汤", "犀角地黄汤"]},
                    {"name": "清热解毒", "examples": ["黄连解毒汤", "普济消毒饮"]}
                ]
            }
        ],
        "principles": [
            "君臣佐使：方剂配伍的基本结构",
            "七情配伍：单行、相须、相使、相畏、相杀、相恶、相反",
            "升降浮沉：药物的趋向性",
            "引经报使：引导药物到达病所"
        ]
    }
    
    return {
        "success": True,
        "data": categories
    }