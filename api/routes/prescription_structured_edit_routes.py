#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化处方编辑API路由
支持君臣佐使分类的智能处方调整
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prescription-structured", tags=["结构化处方编辑"])

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("/opt/tcm-ai/data/user_history.sqlite")
    conn.row_factory = sqlite3.Row
    return conn

class HerbItem(BaseModel):
    """单个药材项目"""
    name: str  # 药材名称
    dosage: str  # 用量 (如 "10g", "3片")
    effect: str  # 功效说明
    action: str = "keep"  # 操作类型: add, modify, delete, keep

class PrescriptionCategory(BaseModel):
    """处方分类（君臣佐使）"""
    category: str  # jun, chen, zuo, shi
    herbs: List[HerbItem]

class StructuredPrescriptionEdit(BaseModel):
    """结构化处方编辑请求"""
    prescription_id: int
    doctor_id: str
    categories: List[PrescriptionCategory]  # 君臣佐使各分类的药材
    doctor_notes: Optional[str] = None
    preserve_analysis: bool = True  # 是否保留原始辨证分析
    preserve_instructions: bool = True  # 是否保留原始煎服法

def parse_prescription_structure(prescription_text: str) -> Dict[str, Any]:
    """解析处方结构，提取君臣佐使药材"""
    structure = {
        "analysis": "",
        "categories": {
            "jun": [],  # 君药
            "chen": [],  # 臣药
            "zuo": [],  # 佐药
            "shi": []   # 使药
        },
        "instructions": "",
        "followup": ""
    }
    
    try:
        # 提取辨证分析部分
        analysis_match = re.search(r'【辨证分析】(.*?)(?=【|$)', prescription_text, re.DOTALL)
        if analysis_match:
            structure["analysis"] = analysis_match.group(1).strip()
        
        # 提取各药材分类
        category_patterns = {
            "jun": r'【君药】\s*(.*?)(?=【|$)',
            "chen": r'【臣药】\s*(.*?)(?=【|$)', 
            "zuo": r'【佐药】\s*(.*?)(?=【|$)',
            "shi": r'【使药】\s*(.*?)(?=【|$)'
        }
        
        for category, pattern in category_patterns.items():
            match = re.search(pattern, prescription_text, re.DOTALL)
            if match:
                herbs_text = match.group(1).strip()
                # 解析每个药材
                herb_lines = re.findall(r'-\s*([^(]+?)\s+([0-9]+[^\s(]*)\s*\(([^)]+)\)', herbs_text)
                for herb_line in herb_lines:
                    name = herb_line[0].strip()
                    dosage = herb_line[1].strip()
                    effect = herb_line[2].strip()
                    structure["categories"][category].append({
                        "name": name,
                        "dosage": dosage,
                        "effect": effect,
                        "action": "keep"
                    })
        
        # 提取煎服法
        instructions_match = re.search(r'【煎服法与注意事项】(.*?)(?=【|$)', prescription_text, re.DOTALL)
        if instructions_match:
            structure["instructions"] = instructions_match.group(1).strip()
        
        # 提取复诊建议
        followup_match = re.search(r'【复诊建议】(.*?)$', prescription_text, re.DOTALL)
        if followup_match:
            structure["followup"] = followup_match.group(1).strip()
            
    except Exception as e:
        logger.error(f"解析处方结构失败: {e}")
    
    return structure

def generate_structured_prescription(structure: Dict[str, Any], categories: List[PrescriptionCategory]) -> str:
    """根据调整后的结构生成新的处方文本"""
    
    category_names = {
        "jun": "【君药】",
        "chen": "【臣药】", 
        "zuo": "【佐药】",
        "shi": "【使药】"
    }
    
    # 构建新处方
    prescription_parts = []
    
    # 添加辨证分析
    if structure.get("analysis"):
        prescription_parts.append("【辨证分析】")
        prescription_parts.append(structure["analysis"])
        prescription_parts.append("\n---\n")
    
    # 添加处方方案标题
    prescription_parts.append("【处方方案】")
    prescription_parts.append("根据病情调整，拟定以下处方：\n")
    
    # 添加各分类药材
    for category_data in categories:
        category = category_data.category
        if category in category_names and category_data.herbs:
            prescription_parts.append(f"\n{category_names[category]}")
            for herb in category_data.herbs:
                if herb.action != "delete":  # 不包含删除的药材
                    prescription_parts.append(f"- {herb.name} {herb.dosage} ({herb.effect})")
    
    # 添加煎服法
    if structure.get("instructions"):
        prescription_parts.append("\n---\n")
        prescription_parts.append("【煎服法与注意事项】")
        prescription_parts.append(structure["instructions"])
    
    # 添加复诊建议
    if structure.get("followup"):
        prescription_parts.append("\n---\n")
        prescription_parts.append("【复诊建议】")
        prescription_parts.append(structure["followup"])
    
    return "\n".join(prescription_parts)

@router.get("/parse/{prescription_id}")
async def parse_prescription_for_editing(prescription_id: int):
    """解析处方结构，为编辑准备数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ai_prescription, doctor_prescription, status 
            FROM prescriptions WHERE id = ?
        """, (prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        # 🔑 修复：优先使用AI原始处方进行结构化编辑，忽略简单文本调整
        # 因为doctor_prescription可能只是简单文本，无法解析结构
        current_prescription = prescription['ai_prescription']
        
        # 如果doctor_prescription包含结构化内容，才使用它
        if prescription['doctor_prescription'] and '【君药】' in prescription['doctor_prescription']:
            current_prescription = prescription['doctor_prescription']
        
        # 解析处方结构
        structure = parse_prescription_structure(current_prescription)
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "prescription_id": prescription_id,
                "status": prescription['status'],
                "structure": structure,
                "editable": prescription['status'] == 'pending_review'
            }
        }
        
    except Exception as e:
        logger.error(f"解析处方失败: {e}")
        return {
            "success": False,
            "message": f"解析处方失败: {str(e)}"
        }

@router.post("/edit")
async def edit_structured_prescription(request: StructuredPrescriptionEdit):
    """结构化编辑处方"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取原始处方
        cursor.execute("""
            SELECT ai_prescription, doctor_prescription, status 
            FROM prescriptions WHERE id = ?
        """, (request.prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        if prescription['status'] != 'pending_review':
            raise HTTPException(status_code=400, detail="处方不在待审核状态，无法编辑")
        
        # 解析原始结构
        original_prescription = prescription['doctor_prescription'] or prescription['ai_prescription']
        structure = parse_prescription_structure(original_prescription)
        
        # 生成新的处方文本
        new_prescription = generate_structured_prescription(structure, request.categories)
        
        # 更新数据库
        cursor.execute("""
            UPDATE prescriptions 
            SET doctor_prescription = ?,
                doctor_notes = ?,
                reviewed_at = datetime('now')
            WHERE id = ?
        """, (new_prescription, request.doctor_notes, request.prescription_id))
        
        # 记录编辑历史
        cursor.execute("""
            INSERT INTO prescription_review_history (
                prescription_id, doctor_id, action, modified_prescription, 
                doctor_notes, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (request.prescription_id, request.doctor_id, 'structured_edit', 
               new_prescription, request.doctor_notes))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 结构化处方编辑完成: prescription_id={request.prescription_id}")
        
        return {
            "success": True,
            "message": "处方结构化调整完成",
            "data": {
                "prescription_id": request.prescription_id,
                "new_prescription": new_prescription,
                "categories_modified": len(request.categories)
            }
        }
        
    except Exception as e:
        logger.error(f"结构化处方编辑失败: {e}")
        return {
            "success": False,
            "message": f"编辑失败: {str(e)}"
        }

@router.get("/preview/{prescription_id}")
async def preview_final_prescription(prescription_id: int):
    """预览最终处方（用于患者端显示）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ai_prescription, doctor_prescription, status, doctor_notes
            FROM prescriptions WHERE id = ?
        """, (prescription_id,))
        
        prescription = cursor.fetchone()
        if not prescription:
            raise HTTPException(status_code=404, detail="处方不存在")
        
        # 选择要显示的处方版本
        if prescription['doctor_prescription']:
            final_prescription = prescription['doctor_prescription']
            prescription_type = "doctor_modified"
        else:
            final_prescription = prescription['ai_prescription']
            prescription_type = "ai_original"
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "prescription_id": prescription_id,
                "status": prescription['status'],
                "prescription_type": prescription_type,
                "final_prescription": final_prescription,
                "doctor_notes": prescription['doctor_notes'],
                "is_modified": bool(prescription['doctor_prescription'])
            }
        }
        
    except Exception as e:
        logger.error(f"预览处方失败: {e}")
        return {
            "success": False,
            "message": f"预览失败: {str(e)}"
        }