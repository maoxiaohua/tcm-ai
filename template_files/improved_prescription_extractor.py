#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的中医处方提取器
基于真实文档结构优化的提取算法
"""

import sys
import re
import json
from docx import Document
from typing import Dict, List, Any, Optional, Tuple
import logging

sys.path.append('/opt/tcm-ai')

logger = logging.getLogger(__name__)

class ImprovedPrescriptionExtractor:
    """改进的处方提取器"""
    
    def __init__(self):
        # 基于真实分析的中医术语模式
        self.syndrome_patterns = [
            # 风寒证型
            r'风寒[感冒外感束表袭肺]', r'外感风寒', r'寒[邪气]入侵',
            
            # 风热证型  
            r'风热[感冒外感犯肺上炎]', r'外感风热', r'热[邪气]入侵',
            
            # 痰湿证型
            r'痰湿[咳嗽阻肺中阻]', r'湿痰[咳嗽内生]', r'痰[热湿]互结',
            
            # 阴虚证型
            r'阴虚[火旺肺燥]', r'肺阴虚[损耗]', r'阴[液津]不足',
            
            # 脏腑辨证
            r'肺[热气虚]', r'脾[虚湿]', r'肝[郁火]', r'肾[虚阳虚阴虚]',
            
            # 具体病症
            r'咳嗽[痰多声重]', r'哮喘[气促]', r'胸[闷痛]', r'气[短促急]'
        ]
        
        # 处方关键标识词
        self.prescription_indicators = [
            r'方药[：:]', r'处方[：:]', r'组成[：:]', 
            r'治法[：:]', r'用法[：:]', r'主治[：:]',
            r'方中', r'药物[：:]', r'方剂[：:]'
        ]
        
        # 药物名称+剂量的精确模式
        self.herb_dose_pattern = r'([\\u4e00-\\u9fff]{2,6})\\s*(\\d+(?:\\.\\d+)?)\\s*([克钱g两])'
        
        # 方剂名称模式  
        self.formula_name_pattern = r'([\\u4e00-\\u9fff]{2,8}[汤散丸膏饮方])'
        
        # 用法模式
        self.usage_patterns = [
            r'每日[一二三]剂', r'水煎[服分]', r'分[二三]次[温]?服',
            r'煎服', r'温服', r'每次.*[克粒丸]'
        ]

    def extract_text_from_docx(self, docx_path: str) -> str:
        """提取文档文本"""
        try:
            doc = Document(docx_path)
            paragraphs = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            return '\\n'.join(paragraphs)
        except Exception as e:
            logger.error(f"提取文档失败: {e}")
            return ""

    def identify_syndrome_contexts(self, text: str) -> List[Dict[str, Any]]:
        """识别证型及其上下文"""
        syndrome_contexts = []
        
        for pattern in self.syndrome_patterns:
            for match in re.finditer(pattern, text):
                start_pos = match.start()
                end_pos = match.end()
                
                # 扩展上下文范围(前后各800字符)
                context_start = max(0, start_pos - 800)
                context_end = min(len(text), end_pos + 1200)
                context = text[context_start:context_end]
                
                syndrome_contexts.append({
                    'syndrome': match.group(),
                    'position': start_pos,
                    'context': context,
                    'context_start': context_start,
                    'context_end': context_end
                })
        
        # 去重相近的上下文
        filtered_contexts = []
        for context in syndrome_contexts:
            is_duplicate = False
            for existing in filtered_contexts:
                if abs(context['position'] - existing['position']) < 200:
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_contexts.append(context)
        
        return filtered_contexts[:15]  # 最多返回15个上下文

    def extract_prescriptions_from_context(self, context: str) -> List[Dict[str, Any]]:
        """从上下文中提取处方信息"""
        prescriptions = []
        
        # 1. 查找方剂名称
        formula_names = re.findall(self.formula_name_pattern, context)
        
        # 2. 查找药物组成
        herb_compositions = self._extract_herb_compositions_improved(context)
        
        # 3. 查找用法信息
        usage_info = self._extract_usage_info(context)
        
        # 4. 查找治法
        treatment_methods = self._extract_treatment_methods(context)
        
        # 组合处方信息
        if formula_names or herb_compositions:
            for i, herbs in enumerate(herb_compositions):
                if len(herbs) >= 3:  # 至少3味药
                    prescription = {
                        'formula_name': formula_names[i] if i < len(formula_names) else f"处方{i+1}",
                        'herbs': herbs,
                        'herb_count': len(herbs),
                        'usage': usage_info[i] if i < len(usage_info) else '',
                        'treatment_method': treatment_methods[i] if i < len(treatment_methods) else '',
                        'source_context': context[:200] + '...'
                    }
                    prescriptions.append(prescription)
        
        return prescriptions

    def _extract_herb_compositions_improved(self, text: str) -> List[List[Dict[str, str]]]:
        """改进的药物组成提取"""
        compositions = []
        
        # 查找药物组成段落的方法1：基于关键词后的内容
        for indicator in self.prescription_indicators:
            pattern = f'{indicator}([^。]*)'
            matches = re.findall(pattern, text, re.DOTALL)
            
            for match in matches:
                herbs = self._parse_herbs_from_text(match)
                if len(herbs) >= 3:
                    compositions.append(herbs)
        
        # 方法2：查找包含大量药物的段落  
        paragraphs = text.split('\\n')
        for para in paragraphs:
            if len(para) > 50:  # 足够长的段落
                herbs = self._parse_herbs_from_text(para)
                if len(herbs) >= 4:  # 至少4味药
                    compositions.append(herbs)
        
        # 方法3：查找连续的药物列表
        # 寻找如"麻黄10克、杏仁15克、甘草5克"的模式
        continuous_herbs_pattern = r'([\\u4e00-\\u9fff]{2,6}\\s*\\d+[克钱g][、，\\s]*){3,}'
        matches = re.findall(continuous_herbs_pattern, text)
        
        for match in matches:
            herbs = self._parse_herbs_from_text(match)
            if len(herbs) >= 3:
                compositions.append(herbs)
        
        return compositions[:5]  # 最多返回5个处方

    def _parse_herbs_from_text(self, text: str) -> List[Dict[str, str]]:
        """从文本中解析药物信息"""
        herbs = []
        
        # 使用改进的正则表达式匹配药物
        matches = re.findall(self.herb_dose_pattern, text)
        
        for herb_name, dose, unit in matches:
            # 过滤无效的药名
            if self._is_valid_herb_name(herb_name):
                herbs.append({
                    'name': herb_name,
                    'dose': dose,
                    'unit': unit,
                    'full_text': f'{herb_name}{dose}{unit}'
                })
        
        # 去重
        seen_herbs = set()
        unique_herbs = []
        for herb in herbs:
            if herb['name'] not in seen_herbs:
                unique_herbs.append(herb)
                seen_herbs.add(herb['name'])
        
        return unique_herbs

    def _is_valid_herb_name(self, name: str) -> bool:
        """验证是否为有效的药名"""
        # 排除明显不是药名的词汇
        invalid_words = [
            '患者', '医生', '治疗', '方法', '效果', '症状', '疾病', 
            '每日', '服用', '时间', '剂量', '次数', '水煎', '煎服',
            '加减', '随证', '临证', '主治', '功效', '用法', '服法'
        ]
        
        if name in invalid_words:
            return False
        
        # 药名长度合理(2-6个字符)
        if len(name) < 2 or len(name) > 6:
            return False
        
        # 不包含数字
        if any(char.isdigit() for char in name):
            return False
        
        return True

    def _extract_usage_info(self, text: str) -> List[str]:
        """提取用法信息"""
        usage_list = []
        
        for pattern in self.usage_patterns:
            matches = re.findall(pattern, text)
            usage_list.extend(matches)
        
        # 查找"用法："后的内容
        usage_pattern = r'用法[：:]([^。\\n]{5,50})'
        matches = re.findall(usage_pattern, text)
        usage_list.extend(matches)
        
        return list(set(usage_list))  # 去重

    def _extract_treatment_methods(self, text: str) -> List[str]:
        """提取治法"""
        treatments = []
        
        # 查找"治法："后的内容
        treatment_pattern = r'治法[：:]([^。\\n]{5,30})'
        matches = re.findall(treatment_pattern, text)
        treatments.extend(matches)
        
        # 常见治法词汇
        common_treatments = [
            '疏风散寒', '辛温解表', '清热解毒', '辛凉解表',
            '润肺止咳', '化痰止咳', '宣肺止咳', '降气化痰',
            '滋阴润燥', '养阴清肺', '温肺散寒', '清肺化痰'
        ]
        
        for treatment in common_treatments:
            if treatment in text:
                treatments.append(treatment)
        
        return list(set(treatments))  # 去重

    def process_document(self, docx_path: str) -> Dict[str, Any]:
        """处理文档，提取病症-处方信息"""
        result = {
            'success': False,
            'filename': docx_path.split('/')[-1],
            'total_syndromes': 0,
            'total_prescriptions': 0,
            'extracted_data': [],
            'summary': {},
            'error_message': ''
        }
        
        try:
            # 提取文本
            text = self.extract_text_from_docx(docx_path)
            if not text:
                result['error_message'] = "无法提取文档内容"
                return result
            
            # 识别证型及上下文
            syndrome_contexts = self.identify_syndrome_contexts(text)
            result['total_syndromes'] = len(syndrome_contexts)
            
            total_prescriptions = 0
            
            # 为每个证型上下文提取处方
            for i, syndrome_ctx in enumerate(syndrome_contexts):
                prescriptions = self.extract_prescriptions_from_context(syndrome_ctx['context'])
                
                if prescriptions:
                    syndrome_data = {
                        'syndrome_index': i + 1,
                        'syndrome_name': syndrome_ctx['syndrome'],
                        'prescriptions': prescriptions,
                        'prescription_count': len(prescriptions)
                    }
                    result['extracted_data'].append(syndrome_data)
                    total_prescriptions += len(prescriptions)
            
            result['total_prescriptions'] = total_prescriptions
            
            # 生成摘要
            result['summary'] = {
                'syndromes_with_prescriptions': len(result['extracted_data']),
                'avg_prescriptions_per_syndrome': total_prescriptions / len(syndrome_contexts) if syndrome_contexts else 0,
                'total_herbs_found': sum(len(p['herbs']) for data in result['extracted_data'] for p in data['prescriptions'])
            }
            
            result['success'] = True
            
            logger.info(f"处理完成 {result['filename']}: {result['total_syndromes']}个证型, {total_prescriptions}个处方")
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"处理文档失败: {e}")
        
        return result

def test_improved_extractor():
    """测试改进的提取器"""
    extractor = ImprovedPrescriptionExtractor()
    
    test_files = [
        '/opt/tcm-ai/all_tcm_docs/感冒.docx',
        '/opt/tcm-ai/all_tcm_docs/咳嗽.docx'
    ]
    
    print("🧪 测试改进的处方提取器")
    print("=" * 60)
    
    for test_file in test_files:
        print(f"\\n📄 处理: {test_file.split('/')[-1]}")
        result = extractor.process_document(test_file)
        
        if result['success']:
            print(f"✅ 成功提取:")
            print(f"   证型数量: {result['total_syndromes']}")
            print(f"   处方数量: {result['total_prescriptions']}")
            print(f"   药物总数: {result['summary']['total_herbs_found']}")
            
            # 显示前2个处方详情
            for data in result['extracted_data'][:2]:
                print(f"\\n🏥 证型: {data['syndrome_name']}")
                for j, prescription in enumerate(data['prescriptions'][:1]):
                    print(f"  📋 处方{j+1}: {prescription['formula_name']}")
                    print(f"     治法: {prescription['treatment_method']}")
                    print(f"     药物({len(prescription['herbs'])}味): ", end="")
                    herb_names = [h['full_text'] for h in prescription['herbs'][:5]]
                    print(", ".join(herb_names))
                    if prescription['usage']:
                        print(f"     用法: {prescription['usage']}")
        else:
            print(f"❌ 失败: {result['error_message']}")
    
    return result

if __name__ == "__main__":
    test_improved_extractor()