#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作版本的处方提取器
基于调试结果优化的正则表达式
"""

import sys
import re
import json
from docx import Document
from typing import Dict, List, Any
import logging

sys.path.append('/opt/tcm-ai')

logger = logging.getLogger(__name__)

class WorkingPrescriptionExtractor:
    """基于实际格式的处方提取器"""
    
    def __init__(self):
        # 常见中药名（包括带空格的版本）
        self.common_herbs = {
            '甘草', '生姜', '大枣', '麻黄', '桂枝', '白芍', '杏仁', '石膏',
            '黄芩', '柴胡', '半夏', '陈皮', '茯苓', '白术', '人参', '当归',
            '川芎', '熟地', '生地', '知母', '连翘', '金银花', '板蓝根',
            '桔梗', '薄荷', '荆芥', '防风', '羌活', '独活', '葛根', '升麻',
            '前胡', '紫苏', '藿香', '佩兰', '苍术', '厚朴', '枳壳', '木香',
            '牛蒡子', '竹叶', '豆豉', '沙参', '浙贝母', '麦冬', '栀子',
            '桑叶', '桑白皮', '苍耳子', '白前', '莱菔子', '山豆根',
            '射干', '菊花', '蔓荆子', '茅根', '葛根', '黄芩', '连翘',
            '侧柏叶', '三七', '瓜蒌', '丹皮', '辛夷', '党参', '黄芪'
        }

    def extract_herbs_from_paragraph(self, para_text: str) -> List[Dict[str, str]]:
        """从段落中提取药物信息"""
        herbs = []
        
        # 先处理明显的处方格式
        # 模式1: "荆 芥 6 克" (空格分隔的药名和剂量)
        pattern1 = r'([\u4e00-\u9fff]\s*[\u4e00-\u9fff](?:\s*[\u4e00-\u9fff])?(?:\s*[\u4e00-\u9fff])?)\s*(\d+(?:\.\d+)?)\s*克'
        matches1 = re.findall(pattern1, para_text)
        
        for herb_name, dose in matches1:
            clean_name = re.sub(r'\s+', '', herb_name)  # 去除空格
            if self._is_valid_herb(clean_name):
                herbs.append({
                    'name': clean_name,
                    'dose': dose,
                    'unit': '克'
                })
        
        # 模式2: "柴胡6克" (无空格的药名和剂量)
        pattern2 = r'([\u4e00-\u9fff]{2,4})(\d+(?:\.\d+)?)克'
        matches2 = re.findall(pattern2, para_text)
        
        for herb_name, dose in matches2:
            if self._is_valid_herb(herb_name):
                # 避免重复添加
                if not any(h['name'] == herb_name for h in herbs):
                    herbs.append({
                        'name': herb_name,
                        'dose': dose,
                        'unit': '克'
                    })
        
        # 模式3: 处理特殊格式如 "板 蓝 根 1 5 克" (剂量也被分隔)
        pattern3 = r'([\u4e00-\u9fff](?:\s*[\u4e00-\u9fff]){1,3})\s*(\d+(?:\s+\d+)?)\s*克'
        matches3 = re.findall(pattern3, para_text)
        
        for herb_name, dose in matches3:
            clean_name = re.sub(r'\s+', '', herb_name)
            clean_dose = re.sub(r'\s+', '', dose)  # 去除剂量中的空格
            if self._is_valid_herb(clean_name):
                # 避免重复添加
                if not any(h['name'] == clean_name for h in herbs):
                    herbs.append({
                        'name': clean_name,
                        'dose': clean_dose,
                        'unit': '克'
                    })
        
        return herbs

    def _is_valid_herb(self, herb_name: str) -> bool:
        """验证是否为有效药名"""
        # 在常见中药列表中
        if herb_name in self.common_herbs:
            return True
        
        # 长度合理且不包含明显的非药名词汇
        if 2 <= len(herb_name) <= 6:
            invalid_words = ['患者', '医生', '治疗', '方法', '每日', '服用', '剂量', '时间', '加减']
            if not any(word in herb_name for word in invalid_words):
                return True
        
        return False

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
            # 提取药物信息
            herbs = self.extract_herbs_from_paragraph(para)
            
            # 如果包含3个以上有效药物，认为是处方段落
            if len(herbs) >= 3:
                prescription_paragraphs.append({
                    'paragraph_index': i + 1,
                    'text': para,
                    'herbs': herbs,
                    'herb_count': len(herbs)
                })
        
        return prescription_paragraphs

    def extract_context_info(self, paragraphs: List[str], prescription_para_index: int) -> Dict[str, Any]:
        """提取处方前后的上下文信息"""
        context_info = {
            'syndrome': '',
            'treatment_method': '',
            'formula_name': '',
            'usage': ''
        }
        
        # 搜索前后5个段落
        start_idx = max(0, prescription_para_index - 5)
        end_idx = min(len(paragraphs), prescription_para_index + 5)
        
        context_text = ' '.join(paragraphs[start_idx:end_idx])
        
        # 提取证型/病症
        syndrome_patterns = [
            r'(风寒感冒)', r'(风热感冒)', r'(外感风寒)', r'(外感风热)',
            r'(风寒束表)', r'(风热犯肺)', r'(痰湿咳嗽)', r'(阴虚火旺)',
            r'(肺热咳嗽)', r'(脾虚湿盛)'
        ]
        
        for pattern in syndrome_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['syndrome'] = match.group(1)
                break
        
        # 提取治法
        treatment_patterns = [
            r'治法[：:]([^。\n]{5,30})',
            r'(疏风散寒)', r'(辛温解表)', r'(清热解毒)', r'(辛凉解表)',
            r'(宣肺止咳)', r'(化痰止咳)', r'(润肺止咳)'
        ]
        
        for pattern in treatment_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['treatment_method'] = match.group(1)
                break
        
        # 提取方剂名
        formula_match = re.search(r'([\u4e00-\u9fff]{2,8}[汤散丸膏饮方])', context_text)
        if formula_match:
            context_info['formula_name'] = formula_match.group(1)
        
        # 提取用法
        usage_patterns = [
            r'(水煎[分服])', r'(每日[一二三]剂)', r'(分[二三]次[温]?服)',
            r'(煎服)', r'(温服)'
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
                    'source_paragraph': presc_para['paragraph_index'],
                    'source_text': presc_para['text'][:200] + '...' if len(presc_para['text']) > 200 else presc_para['text']
                }
                
                result['prescriptions'].append(prescription)
            
            result['total_prescriptions'] = len(prescription_paragraphs)
            result['success'] = True
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"处理文档失败: {e}")
        
        return result

def test_working_extractor():
    """测试工作版本提取器"""
    extractor = WorkingPrescriptionExtractor()
    
    test_files = [
        '/opt/tcm-ai/all_tcm_docs/感冒.docx',
        '/opt/tcm-ai/all_tcm_docs/咳嗽.docx'
    ]
    
    print("🔬 测试工作版本的处方提取器")
    print("=" * 60)
    
    all_results = []
    
    for test_file in test_files:
        print(f"\n📄 处理: {test_file.split('/')[-1]}")
        result = extractor.process_document(test_file)
        all_results.append(result)
        
        if result['success']:
            print(f"✅ 成功提取 {result['total_prescriptions']} 个处方")
            
            # 显示每个处方的详细信息
            for i, prescription in enumerate(result['prescriptions']):
                print(f"\n📋 处方{i+1} (来源段落{prescription['source_paragraph']}):")
                print(f"   方剂名称: {prescription['formula_name']}")
                if prescription['syndrome']:
                    print(f"   证型: {prescription['syndrome']}")
                if prescription['treatment_method']:
                    print(f"   治法: {prescription['treatment_method']}")
                print(f"   药物组成({prescription['herb_count']}味):")
                for herb in prescription['herbs']:
                    print(f"     • {herb['name']} {herb['dose']}{herb['unit']}")
                if prescription['usage']:
                    print(f"   用法: {prescription['usage']}")
                print(f"   原文: {prescription['source_text']}")
        else:
            print(f"❌ 失败: {result['error_message']}")
    
    # 保存结果
    if any(r['success'] for r in all_results):
        with open('/opt/tcm-ai/template_files/working_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存到: working_extraction_results.json")
    
    # 生成总结
    total_prescriptions = sum(r['total_prescriptions'] for r in all_results if r['success'])
    print(f"\n📊 总结:")
    print(f"   成功处理文档: {sum(1 for r in all_results if r['success'])}/{len(all_results)}")
    print(f"   总提取处方数: {total_prescriptions}")
    
    return all_results

if __name__ == "__main__":
    test_working_extractor()