#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终版本的处方提取器
适应文档中的实际格式（包含空格的药物名称）
"""

import sys
import re
import json
from docx import Document
from typing import Dict, List, Any
import logging

sys.path.append('/opt/tcm-ai')

logger = logging.getLogger(__name__)

class FinalPrescriptionExtractor:
    """最终版本的处方提取器"""
    
    def __init__(self):
        # 适应空格分隔的药物+剂量模式
        # 匹配如："荆 芥 6 克" 或 "杏仁9克" 
        self.herb_pattern = r'([\\u4e00-\\u9fff](?:[\\s]*[\\u4e00-\\u9fff]){1,4})\\s*(\\d+(?:\\.\\d+)?)\\s*([克钱g])'
        
        # 更精确的药物名称模式（考虑空格）
        self.herb_name_pattern = r'[\\u4e00-\\u9fff](?:[\\s]*[\\u4e00-\\u9fff]){1,4}'
        
        # 常见中药名（包括带空格的版本）
        self.common_herbs = {
            '甘草', '甘 草', '生姜', '生 姜', '大枣', '大 枣', 
            '麻黄', '麻 黄', '桂枝', '桂 枝', '白芍', '白 芍', 
            '杏仁', '杏 仁', '石膏', '石 膏', '黄芩', '黄 芩',
            '柴胡', '柴 胡', '半夏', '半 夏', '陈皮', '陈 皮',
            '茯苓', '茯 苓', '白术', '白 术', '人参', '人 参',
            '当归', '当 归', '川芎', '川 芎', '熟地', '熟 地',
            '知母', '知 母', '连翘', '连 翘', '金银花', '金 银 花',
            '板蓝根', '板 蓝 根', '桔梗', '桔 梗', '薄荷', '薄 荷',
            '荆芥', '荆 芥', '防风', '防 风', '羌活', '羌 活',
            '独活', '独 活', '葛根', '葛 根', '升麻', '升 麻',
            '前胡', '前 胡', '紫苏', '紫 苏', '藿香', '藿 香',
            '枳壳', '枳 壳', '木香', '木 香', '牛蒡子', '牛 蒡 子',
            '竹叶', '竹 叶', '豆豉', '豆 豉', '沙参', '沙 参',
            '浙贝母', '浙 贝 母', '麦冬', '麦 冬', '栀子', '栀 子',
            '桑叶', '桑 叶', '桑白皮', '桑 白 皮', '苍耳子', '苍 耳 子',
            '白前', '白 前', '莱菔子', '莱 菔 子', '山豆根', '山 豆 根',
            '射干', '射 干', '菊花', '菊 花', '蔓荆子', '蔓 荆 子'
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
                # 清理药物名称（去除多余空格）
                clean_herb_name = re.sub(r'\\s+', '', herb_name)
                spaced_herb_name = herb_name  # 保留原始格式
                
                if self._is_valid_herb(clean_herb_name, spaced_herb_name):
                    valid_herbs.append({
                        'name': clean_herb_name,
                        'original_name': spaced_herb_name,
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

    def _is_valid_herb(self, clean_name: str, spaced_name: str) -> bool:
        """验证是否为有效药名"""
        # 检查清理后的名称或原始名称是否在常见中药列表中
        if clean_name in self.common_herbs or spaced_name in self.common_herbs:
            return True
        
        # 长度合理且不包含明显的非药名词汇
        if 2 <= len(clean_name) <= 6:
            invalid_words = ['患者', '医生', '治疗', '方法', '每日', '服用', '剂量', '时间']
            if not any(word in clean_name for word in invalid_words):
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
        
        # 搜索前后5个段落
        start_idx = max(0, prescription_para_index - 5)
        end_idx = min(len(paragraphs), prescription_para_index + 6)
        
        context_text = ' '.join(paragraphs[start_idx:end_idx])
        
        # 提取证型/病症
        syndrome_patterns = [
            r'(风寒[感冒外感束表])', r'(风热[感冒外感犯肺])', 
            r'(痰湿[咳嗽阻肺])', r'(阴虚[火旺肺燥])', 
            r'(肺热[咳嗽])', r'(脾虚[湿盛])',
            r'(外感风寒)', r'(外感风热)', r'(风寒感冒)', r'(风热感冒)'
        ]
        
        for pattern in syndrome_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['syndrome'] = match.group(1)
                break
        
        # 提取治法
        treatment_patterns = [
            r'治法[：:]([^。\\n]{5,30})',
            r'(疏风散寒)', r'(辛温解表)', r'(清热解毒)', r'(辛凉解表)',
            r'(宣肺止咳)', r'(化痰止咳)', r'(润肺止咳)'
        ]
        
        for pattern in treatment_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['treatment_method'] = match.group(1)
                break
        
        # 提取方剂名
        formula_patterns = [
            r'([\\u4e00-\\u9fff]{2,8}[汤散丸膏饮方])',
            r'方药[：:]([^。\\n]{0,20}([\\u4e00-\\u9fff]{2,8}[汤散丸膏饮方]))'
        ]
        
        for pattern in formula_patterns:
            match = re.search(pattern, context_text)
            if match:
                if len(match.groups()) > 1:
                    context_info['formula_name'] = match.group(2)  # 第二个捕获组
                else:
                    context_info['formula_name'] = match.group(1)
                break
        
        # 提取用法
        usage_patterns = [
            r'(水煎[服分])', r'(每日[一二三]剂)', r'(分[二三]次[温]?服)',
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
            'summary': {},
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
            total_herbs = 0
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
                    'source_text': presc_para['text'][:300] + '...' if len(presc_para['text']) > 300 else presc_para['text']
                }
                
                result['prescriptions'].append(prescription)
                total_herbs += presc_para['herb_count']
            
            result['total_prescriptions'] = len(prescription_paragraphs)
            result['summary'] = {
                'total_herbs': total_herbs,
                'avg_herbs_per_prescription': total_herbs / len(prescription_paragraphs) if prescription_paragraphs else 0,
                'prescriptions_with_syndrome': len([p for p in result['prescriptions'] if p['syndrome']]),
                'prescriptions_with_treatment': len([p for p in result['prescriptions'] if p['treatment_method']])
            }
            result['success'] = True
            
            logger.info(f"处理完成 {result['filename']}: 找到{len(prescription_paragraphs)}个处方，共{total_herbs}味药")
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"处理文档失败: {e}")
        
        return result

def create_prescription_database(docx_files: List[str]) -> Dict[str, Any]:
    """创建病症-处方数据库"""
    extractor = FinalPrescriptionExtractor()
    
    database = {
        'creation_time': '2025-08-20',
        'total_documents': len(docx_files),
        'total_prescriptions': 0,
        'documents': [],
        'syndromes_index': {},
        'herbs_index': {},
        'formulas_index': {}
    }
    
    print("🏥 创建中医病症-处方数据库")
    print("=" * 60)
    
    for docx_file in docx_files:
        print(f"\\n📄 处理: {docx_file.split('/')[-1]}")
        result = extractor.process_document(docx_file)
        
        if result['success']:
            print(f"✅ 成功: {result['total_prescriptions']}个处方, {result['summary']['total_herbs']}味药")
            database['documents'].append(result)
            database['total_prescriptions'] += result['total_prescriptions']
            
            # 建立索引
            for prescription in result['prescriptions']:
                # 证型索引
                if prescription['syndrome']:
                    syndrome = prescription['syndrome']
                    if syndrome not in database['syndromes_index']:
                        database['syndromes_index'][syndrome] = []
                    database['syndromes_index'][syndrome].append({
                        'document': result['filename'],
                        'prescription_id': prescription['prescription_id'],
                        'formula_name': prescription['formula_name']
                    })
                
                # 药物索引
                for herb in prescription['herbs']:
                    herb_name = herb['name']
                    if herb_name not in database['herbs_index']:
                        database['herbs_index'][herb_name] = []
                    database['herbs_index'][herb_name].append({
                        'document': result['filename'],
                        'prescription_id': prescription['prescription_id'],
                        'dose': f"{herb['dose']}{herb['unit']}"
                    })
                
                # 方剂索引
                formula = prescription['formula_name']
                if formula not in database['formulas_index']:
                    database['formulas_index'][formula] = []
                database['formulas_index'][formula].append({
                    'document': result['filename'],
                    'prescription_id': prescription['prescription_id'],
                    'syndrome': prescription['syndrome']
                })
        else:
            print(f"❌ 失败: {result['error_message']}")
    
    print(f"\\n📊 数据库创建完成:")
    print(f"   总处方数: {database['total_prescriptions']}")
    print(f"   证型数: {len(database['syndromes_index'])}")
    print(f"   药物数: {len(database['herbs_index'])}")
    print(f"   方剂数: {len(database['formulas_index'])}")
    
    return database

def test_final_extractor():
    """测试最终版本提取器"""
    test_files = [
        '/opt/tcm-ai/all_tcm_docs/感冒.docx',
        '/opt/tcm-ai/all_tcm_docs/咳嗽.docx'
    ]
    
    # 创建数据库
    database = create_prescription_database(test_files)
    
    # 保存数据库
    with open('/opt/tcm-ai/template_files/prescription_database.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    
    print(f"\\n💾 数据库已保存到: prescription_database.json")
    
    # 显示一些处方示例
    print(f"\\n📋 处方示例:")
    for doc in database['documents']:
        if doc['prescriptions']:
            print(f"\\n📄 来源: {doc['filename']}")
            for prescription in doc['prescriptions'][:2]:  # 显示前2个处方
                print(f"   🏥 {prescription['formula_name']}")
                if prescription['syndrome']:
                    print(f"      证型: {prescription['syndrome']}")
                if prescription['treatment_method']:
                    print(f"      治法: {prescription['treatment_method']}")
                print(f"      药物组成({prescription['herb_count']}味):")
                for herb in prescription['herbs'][:6]:  # 显示前6味药
                    print(f"        • {herb['name']} {herb['dose']}{herb['unit']}")
                if prescription['usage']:
                    print(f"      用法: {prescription['usage']}")
                print()
    
    return database

if __name__ == "__main__":
    test_final_extractor()