#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理工具模块
提取main.py中与文本处理相关的函数
"""

import re
from typing import List, Dict, Any, Optional, Tuple

def normalize_prescription_dosage(prescription_text: str) -> str:
    """
    规范化处方用量格式
    从main.py中提取的函数
    """
    if not prescription_text:
        return ""
    
    # 处方用量规范化模式
    normalization_patterns = [
        # 范围用量转换为中值
        (r'(\d+)[-~～]\s*(\d+)\s*[gG克]', lambda m: f"{(int(m.group(1)) + int(m.group(2))) // 2}g"),
        (r'(\d+)[-~～]\s*(\d+)\s*钱', lambda m: f"{(int(m.group(1)) + int(m.group(2))) // 2}钱"),
        
        # 统一单位格式
        (r'(\d+)\s*[gG](?![a-zA-Z])', r'\1g'),
        (r'(\d+)\s*克', r'\1g'),
        (r'(\d+)\s*钱', r'\1钱'),
        
        # 清理多余空格
        (r'\s+', ' '),
        (r'^\s+|\s+$', ''),
    ]
    
    result = prescription_text
    for pattern, replacement in normalization_patterns:
        if callable(replacement):
            result = re.sub(pattern, replacement, result)
        else:
            result = re.sub(pattern, replacement, result)
    
    return result

def standardize_prescription_format(prescription_text: str) -> str:
    """
    标准化处方格式
    从main.py中提取并增强
    """
    if not prescription_text:
        return ""
    
    lines = prescription_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 标准化药材行格式
        if re.search(r'\d+[gG克钱]', line):
            # 确保药材名和用量之间有适当间距
            line = re.sub(r'([^\d\s]+)\s*(\d+[gG克钱])', r'\1 \2', line)
            
        formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def extract_keywords_from_query(query: str) -> List[str]:
    """
    从查询中提取关键词
    从main.py中提取
    """
    if not query:
        return []
    
    # 中医相关关键词模式
    keyword_patterns = [
        r'[^\s，。！？,\.!\?]{2,}',  # 基础词汇
        r'[头面]痛',  # 疼痛相关
        r'[咳喘]嗽',  # 呼吸相关
        r'[胃脾肝肾心肺]',  # 脏腑相关
    ]
    
    keywords = []
    for pattern in keyword_patterns:
        matches = re.findall(pattern, query)
        keywords.extend(matches)
    
    # 去重并过滤
    keywords = list(set(keywords))
    keywords = [kw for kw in keywords if len(kw) >= 2 and len(kw) <= 10]
    
    return keywords[:10]  # 最多返回10个关键词

def clean_medical_text(text: str) -> str:
    """
    清理医疗文本内容
    """
    if not text:
        return ""
    
    # 清理模式
    cleaning_patterns = [
        # 移除多余的标点符号
        (r'[，。]{2,}', '。'),
        (r'[,\.]{2,}', '.'),
        
        # 统一标点符号
        (r'，+', '，'),
        (r'。+', '。'),
        
        # 清理多余空格
        (r'\s+', ' '),
        (r'^\s+|\s+$', ''),
    ]
    
    result = text
    for pattern, replacement in cleaning_patterns:
        result = re.sub(pattern, replacement, result)
    
    return result

def extract_herb_names(text: str) -> List[str]:
    """
    从文本中提取中药名称
    """
    if not text:
        return []
    
    # 常见中药名称模式
    herb_patterns = [
        r'[党黄当川白熟生炒蜜酒][^，。\s]{1,4}',  # 常见前缀
        r'[甘茯陈半桔薄菊金银连翘板蓝根][\w]*',  # 常见药名
        r'[\u4e00-\u9fff]{2,6}(?=[gG克钱\d\s])',  # 后面跟用量的词
    ]
    
    herbs = []
    for pattern in herb_patterns:
        matches = re.findall(pattern, text)
        herbs.extend(matches)
    
    # 清理和去重
    herbs = [herb.strip() for herb in herbs if len(herb) >= 2]
    return list(set(herbs))

def format_diagnosis_text(diagnosis: str) -> str:
    """
    格式化诊断文本
    """
    if not diagnosis:
        return "待完善"
    
    # 清理诊断文本
    diagnosis = re.sub(r'[\n\r\t]+', ' ', diagnosis)
    diagnosis = re.sub(r'[。，；：]+$', '', diagnosis)
    diagnosis = diagnosis.strip()
    
    # 验证诊断长度和内容
    if len(diagnosis) < 3 or len(diagnosis) > 200:
        return "待完善"
    
    return diagnosis

def extract_symptom_keywords(symptoms_text: str) -> List[str]:
    """
    从症状描述中提取关键词
    """
    if not symptoms_text:
        return []
    
    # 症状关键词模式
    symptom_patterns = [
        r'[头颈肩背腰腿膝踝]痛',
        r'[咳喘]嗽',
        r'[恶心呕吐]',
        r'[发热寒战]',
        r'[失眠多梦]',
        r'[食欲不振]',
        r'[便秘腹泻]',
        r'[头晕眩晕]',
        r'[心悸胸闷]',
    ]
    
    keywords = []
    for pattern in symptom_patterns:
        matches = re.findall(pattern, symptoms_text)
        keywords.extend(matches)
    
    return list(set(keywords))

def validate_prescription_format(prescription: str) -> Tuple[bool, str]:
    """
    验证处方格式
    返回: (是否有效, 错误信息)
    """
    if not prescription:
        return False, "处方内容为空"
    
    lines = prescription.split('\n')
    valid_lines = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 检查是否包含药材和用量
        if re.search(r'[\u4e00-\u9fff]+.*\d+[gG克钱]', line):
            valid_lines += 1
    
    if valid_lines == 0:
        return False, "未找到有效的药材用量信息"
    elif valid_lines < 3:
        return False, "处方药味数量过少"
    
    return True, "处方格式正确"

def extract_dosage_info(text: str) -> Dict[str, Any]:
    """
    提取用量信息
    """
    dosage_info = {
        'herbs': [],
        'total_herbs': 0,
        'dosage_units': [],
        'dosage_range': {'min': 0, 'max': 0}
    }
    
    # 提取药材和用量
    herb_dosage_pattern = r'([^\d\s]+)\s*(\d+(?:\.\d+)?)\s*([gG克钱])'
    matches = re.findall(herb_dosage_pattern, text)
    
    dosages = []
    for herb, dosage, unit in matches:
        herb = herb.strip()
        if len(herb) >= 2:
            dosage_info['herbs'].append({
                'name': herb,
                'dosage': float(dosage),
                'unit': unit
            })
            dosages.append(float(dosage))
            if unit not in dosage_info['dosage_units']:
                dosage_info['dosage_units'].append(unit)
    
    dosage_info['total_herbs'] = len(dosage_info['herbs'])
    
    if dosages:
        dosage_info['dosage_range']['min'] = min(dosages)
        dosage_info['dosage_range']['max'] = max(dosages)
    
    return dosage_info

def clean_ai_response_text(response: str) -> str:
    """
    清理AI响应文本
    """
    if not response:
        return ""
    
    # 清理模式
    cleaning_patterns = [
        # 移除多余的换行
        (r'\n{3,}', '\n\n'),
        
        # 清理多余的空格
        (r' {2,}', ' '),
        
        # 统一标点符号
        (r'[，,]{2,}', '，'),
        (r'[。\.]{2,}', '。'),
        
        # 移除首尾空白
        (r'^\s+|\s+$', ''),
    ]
    
    result = response
    for pattern, replacement in cleaning_patterns:
        result = re.sub(pattern, replacement, result)
    
    return result

def split_long_text(text: str, max_length: int = 1000, split_on: str = '\n') -> List[str]:
    """
    分割长文本
    """
    if len(text) <= max_length:
        return [text]
    
    parts = text.split(split_on)
    result = []
    current_part = ""
    
    for part in parts:
        if len(current_part + split_on + part) <= max_length:
            if current_part:
                current_part += split_on + part
            else:
                current_part = part
        else:
            if current_part:
                result.append(current_part)
            current_part = part
    
    if current_part:
        result.append(current_part)
    
    return result

def count_chinese_characters(text: str) -> int:
    """
    统计中文字符数量
    """
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def has_medical_keywords(text: str) -> bool:
    """
    检查文本是否包含医疗关键词
    """
    medical_keywords = [
        '症状', '诊断', '治疗', '处方', '药方', '用药', '服用',
        '病史', '体征', '检查', '舌象', '脉象', '辨证', '证型',
        '头痛', '咳嗽', '发热', '腹痛', '便秘', '失眠'
    ]
    
    return any(keyword in text for keyword in medical_keywords)