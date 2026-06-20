#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单直接的处方提取器
直接基于观察到的模式提取处方信息
"""

import sys
import re
import json
from docx import Document
from typing import Dict, List, Any
import logging

sys.path.append('/opt/tcm-ai')

logger = logging.getLogger(__name__)

class SimplePrescriptionExtractor:
    """简单直接的处方提取器"""
    
    def __init__(self):
        # 直接的药物+剂量模式
        self.herb_pattern = r'([\\u4e00-\\u9fff]{2,5})\\s*(\\d+(?:\\.\\d+)?)\\s*([克钱g])'
        
        # 常见中药名（用于验证）
        self.common_herbs = {
            '甘草', '生姜', '大枣', '麻黄', '桂枝', '白芍', '杏仁', '石膏',
            '黄芩', '柴胡', '半夏', '陈皮', '茯苓', '白术', '人参', '当归',
            '川芎', '熟地', '生地', '知母', '石膏', '连翘', '金银花', '板蓝根',
            '桔梗', '薄荷', '荆芥', '防风', '羌活', '独活', '葛根', '升麻',
            '前胡', '紫苏', '藿香', '佩兰', '苍术', '厚朴', '枳壳', '木香',
            '香附', '郁金', '延胡索', '三七', '红花', '桃仁', '丹参', '赤芍',
            '牛膝', '续断', '杜仲', '桑寄生', '威灵仙', '秦艽', '防己', '木瓜',
            '五加皮', '狗脊', '补骨脂', '菟丝子', '枸杞子', '女贞子', '墨旱莲',
            '何首乌', '黄精', '玉竹', '百合', '沙参', '麦冬', '天冬', '石斛',
            '西洋参', '太子参', '党参', '黄芪', '白扁豆', '山药', '莲子', '芡实',
            '五味子', '酸枣仁', '远志', '茯神', '龙骨', '牡蛎', '磁石', '代赭石',
            '朱砂', '琥珀', '珍珠', '冰片', '麝香', '牛黄', '羚羊角', '犀角',
            '鹿茸', '紫河车', '阿胶', '龟板', '鳖甲', '穿山甲', '地龙', '全蝎',
            '蜈蚣', '水蛭', '虻虫', '土鳖虫', '僵蚕', '蝉蜕', '浮萍', '木贼',
            '谷精草', '密蒙花', '青葙子', '决明子', '车前子', '菟丝子', '女贞子'
        }

    def extract_text_from_docx(self, docx_path: str) -> List[str]:
        """提取文档文本，保持段落结构"""
        try:
            doc = Document(docx_path)
            paragraphs = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            return paragraphs
        except Exception as e:
            logger.error(f"提取文档失败: {e}")
            return []

    def find_prescription_paragraphs(self, paragraphs: List[str]) -> List[Dict[str, Any]]:
        """找到包含处方的段落"""
        prescription_paragraphs = []
        
        for i, para in enumerate(paragraphs):
            # 统计段落中的药物数量
            herbs_found = re.findall(self.herb_pattern, para)
            valid_herbs = []
            
            for herb_name, dose, unit in herbs_found:
                if self._is_valid_herb(herb_name):
                    valid_herbs.append({
                        'name': herb_name,
                        'dose': dose, 
                        'unit': unit
                    })
            
            # 如果包含3个以上有效药物，认为是处方段落
            if len(valid_herbs) >= 3:
                prescription_paragraphs.append({
                    'paragraph_index': i,
                    'text': para,
                    'herbs': valid_herbs,
                    'herb_count': len(valid_herbs)
                })
        
        return prescription_paragraphs

    def _is_valid_herb(self, herb_name: str) -> bool:
        """验证是否为有效药名"""
        # 在常见中药列表中
        if herb_name in self.common_herbs:
            return True
        
        # 长度合理且不包含明显的非药名词汇
        if 2 <= len(herb_name) <= 6:
            invalid_words = ['患者', '医生', '治疗', '方法', '每日', '服用', '剂量']
            if not any(word in herb_name for word in invalid_words):
                return True
        
        return False

    def extract_context_info(self, paragraphs: List[str], prescription_para_index: int) -> Dict[str, Any]:
        """提取处方前后的上下文信息"""
        context_info = {
            'syndrome': '',
            'treatment_method': '',
            'formula_name': '',
            'usage': '',
            'indication': ''
        }
        
        # 搜索前后3个段落
        start_idx = max(0, prescription_para_index - 3)
        end_idx = min(len(paragraphs), prescription_para_index + 4)
        
        context_text = ' '.join(paragraphs[start_idx:end_idx])
        
        # 提取证型/病症
        syndrome_patterns = [
            r'(风寒[感冒外感])', r'(风热[感冒外感])', r'(痰湿[咳嗽])', 
            r'(阴虚[火旺])', r'(肺热[咳嗽])', r'(脾虚[湿盛])'
        ]
        
        for pattern in syndrome_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['syndrome'] = match.group(1)
                break
        
        # 提取治法
        treatment_match = re.search(r'治法[：:]([^。\\n]{5,30})', context_text)
        if treatment_match:
            context_info['treatment_method'] = treatment_match.group(1)
        
        # 提取方剂名
        formula_match = re.search(r'([\\u4e00-\\u9fff]{2,8}[汤散丸膏饮方])', context_text)
        if formula_match:
            context_info['formula_name'] = formula_match.group(1)
        
        # 提取用法
        usage_patterns = [
            r'(水煎服)', r'(每日[一二三]剂)', r'(分[二三]次服)'
        ]
        
        for pattern in usage_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['usage'] = match.group(1)
                break
        
        return context_info

    def process_document(self, docx_path: str) -> Dict[str, Any]:
        """处理文档提取处方信息"""
        result = {
            'success': False,
            'filename': docx_path.split('/')[-1],
            'total_prescriptions': 0,
            'prescriptions': [],
            'error_message': ''
        }
        
        try:
            # 提取段落
            paragraphs = self.extract_text_from_docx(docx_path)
            if not paragraphs:
                result['error_message'] = "无法提取文档内容"
                return result
            
            # 找到处方段落
            prescription_paragraphs = self.find_prescription_paragraphs(paragraphs)
            
            if not prescription_paragraphs:
                result['error_message'] = "未找到处方信息"
                return result
            
            # 为每个处方段落提取完整信息
            for i, presc_para in enumerate(prescription_paragraphs):
                context_info = self.extract_context_info(paragraphs, presc_para['paragraph_index'])
                
                prescription = {
                    'prescription_id': i + 1,
                    'syndrome': context_info['syndrome'],
                    'treatment_method': context_info['treatment_method'],
                    'formula_name': context_info['formula_name'] or f"处方{i+1}",
                    'herbs': presc_para['herbs'],
                    'herb_count': presc_para['herb_count'],
                    'usage': context_info['usage'],
                    'source_text': presc_para['text'][:200] + '...' if len(presc_para['text']) > 200 else presc_para['text']
                }
                
                result['prescriptions'].append(prescription)
            
            result['total_prescriptions'] = len(prescription_paragraphs)
            result['success'] = True
            
            logger.info(f"处理完成 {result['filename']}: 找到{len(prescription_paragraphs)}个处方")
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"处理文档失败: {e}")
        
        return result

def test_simple_extractor():
    """测试简单提取器"""
    extractor = SimplePrescriptionExtractor()
    
    test_files = [
        '/opt/tcm-ai/all_tcm_docs/感冒.docx',
        '/opt/tcm-ai/all_tcm_docs/咳嗽.docx'
    ]
    
    print("🔬 测试简单直接的处方提取器")
    print("=" * 60)
    
    all_results = []
    
    for test_file in test_files:
        print(f"\\n📄 处理: {test_file.split('/')[-1]}")
        result = extractor.process_document(test_file)
        all_results.append(result)
        
        if result['success']:
            print(f"✅ 成功提取 {result['total_prescriptions']} 个处方")
            
            # 显示前3个处方的详细信息
            for i, prescription in enumerate(result['prescriptions'][:3]):
                print(f"\\n📋 处方{i+1}:")
                print(f"   方剂名称: {prescription['formula_name']}")
                if prescription['syndrome']:
                    print(f"   证型: {prescription['syndrome']}")
                if prescription['treatment_method']:
                    print(f"   治法: {prescription['treatment_method']}")
                print(f"   药物组成({prescription['herb_count']}味):")
                for herb in prescription['herbs'][:8]:  # 显示前8味药
                    print(f"     • {herb['name']} {herb['dose']}{herb['unit']}")
                if len(prescription['herbs']) > 8:
                    print(f"     ... 还有{len(prescription['herbs'])-8}味药")
                if prescription['usage']:
                    print(f"   用法: {prescription['usage']}")
        else:
            print(f"❌ 失败: {result['error_message']}")
    
    # 生成总结
    total_prescriptions = sum(r['total_prescriptions'] for r in all_results if r['success'])
    print(f"\\n📊 总结:")
    print(f"   成功处理文档: {sum(1 for r in all_results if r['success'])}/{len(all_results)}")
    print(f"   总提取处方数: {total_prescriptions}")
    
    return all_results

if __name__ == "__main__":
    test_simple_extractor()