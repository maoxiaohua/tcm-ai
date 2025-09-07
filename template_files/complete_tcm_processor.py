#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的TCM文档处理系统
处理所有58个文档，提取病症-处方映射，创建结构化数据库
"""

import sys
import os
import re
import json
from docx import Document
from typing import Dict, List, Any
import logging
from datetime import datetime
import glob

sys.path.append('/opt/tcm-ai')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteTCMProcessor:
    """完整的TCM文档处理器"""
    
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
            '射干', '菊花', '蔓荆子', '茅根', '黄芪', '党参', '白扁豆',
            '侧柏叶', '三七', '瓜蒌', '丹皮', '辛夷', '紫菀', '款冬花',
            '百部', '桃仁', '红花', '丹参', '赤芍', '牛膝', '续断', '杜仲',
            '桑寄生', '威灵仙', '秦艽', '防己', '木瓜', '五加皮', '狗脊',
            '补骨脂', '菟丝子', '枸杞子', '女贞子', '墨旱莲', '何首乌',
            '黄精', '玉竹', '百合', '天冬', '石斛', '西洋参', '太子参',
            '山药', '莲子', '芡实', '五味子', '酸枣仁', '远志', '茯神',
            '龙骨', '牡蛎', '磁石', '代赭石', '朱砂', '琥珀', '珍珠',
            '冰片', '麝香', '牛黄', '羚羊角', '犀角', '鹿茸', '紫河车',
            '阿胶', '龟板', '鳖甲', '穿山甲', '地龙', '全蝎', '蜈蚣',
            '水蛭', '虻虫', '土鳖虫', '僵蚕', '蝉蜕', '浮萍', '木贼',
            '谷精草', '密蒙花', '青葙子', '决明子', '车前子', '山茱萸',
            '泽泻', '天花粉', '知母', '黄连', '黄柏', '苦参', '龙胆草',
            '山栀子', '大黄', '芒硝', '番泻叶', '郁李仁', '火麻仁',
            '瓜蒌仁', '杏仁', '桃仁', '苏子', '白芥子', '莱菔子',
            '葶苈子', '车前子', '牵牛子', '商陆', '泽漆', '猪苓',
            '茯苓', '泽泻', '木通', '通草', '灯心草', '瞿麦', '篇蓄',
            '石韦', '海金沙', '金钱草', '茵陈', '虎杖', '蒲公英',
            '白花蛇舌草', '半枝莲', '白英', '龙葵', '山慈菇', '夏枯草'
        }
        
        # 病症/证型关键词
        self.syndrome_patterns = [
            r'(风寒感冒)', r'(风热感冒)', r'(外感风寒)', r'(外感风热)',
            r'(风寒束表)', r'(风热犯肺)', r'(痰湿咳嗽)', r'(阴虚火旺)',
            r'(肺热咳嗽)', r'(脾虚湿盛)', r'(肝郁气滞)', r'(心血不足)',
            r'(肾阳虚)', r'(肾阴虚)', r'(气血两虚)', r'(痰热内扰)',
            r'(湿热下注)', r'(血瘀内阻)', r'(寒湿内盛)', r'(燥热伤肺)',
            r'(肝胆湿热)', r'(脾胃虚弱)', r'(心肾不交)', r'(肝肾阴虚)',
            r'(脾肾阳虚)', r'(心脾两虚)', r'(肺脾两虚)', r'(肝脾不调)',
            r'(胃热炽盛)', r'(胃阴不足)', r'(中焦虚寒)', r'(下焦虚寒)',
            r'(上焦燥热)', r'(痰火扰心)', r'(瘀血阻络)', r'(寒凝血瘀)',
            r'(风痰内动)', r'(痰瘀互结)', r'(气滞血瘀)', r'(湿浊中阻)'
        ]
        
        # 治法关键词
        self.treatment_patterns = [
            r'治法[：:]([^。\n]{5,30})',
            r'(疏风散寒)', r'(辛温解表)', r'(清热解毒)', r'(辛凉解表)',
            r'(宣肺止咳)', r'(化痰止咳)', r'(润肺止咳)', r'(理气化痰)',
            r'(健脾益气)', r'(补肾壮阳)', r'(滋阴润燥)', r'(养血安神)',
            r'(疏肝理气)', r'(清肝泻火)', r'(温中散寒)', r'(消食导滞)',
            r'(活血化瘀)', r'(利水渗湿)', r'(祛风除湿)', r'(清热燥湿)',
            r'(益气养阴)', r'(温阳利水)', r'(清心安神)', r'(镇肝熄风)',
            r'(补血养心)', r'(温肾助阳)', r'(滋肾养肝)', r'(健脾化湿)',
            r'(和胃降逆)', r'(清胃泻火)', r'(温胃散寒)', r'(养胃生津)'
        ]

    def get_all_docx_files(self, folder_path: str) -> List[str]:
        """获取所有docx文件"""
        docx_files = []
        for file in os.listdir(folder_path):
            if file.endswith('.docx') and not file.startswith('~'):
                docx_files.append(os.path.join(folder_path, file))
        return sorted(docx_files)

    def extract_herbs_from_paragraph(self, para_text: str) -> List[Dict[str, str]]:
        """从段落中提取药物信息"""
        herbs = []
        
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
            invalid_words = ['患者', '医生', '治疗', '方法', '每日', '服用', '剂量', '时间', '加减', '重者', '轻者']
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
            logger.error(f"提取文档失败 {docx_path}: {e}")
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
            'usage': '',
            'indication': ''
        }
        
        # 搜索前后5个段落
        start_idx = max(0, prescription_para_index - 5)
        end_idx = min(len(paragraphs), prescription_para_index + 5)
        
        context_text = ' '.join(paragraphs[start_idx:end_idx])
        
        # 提取证型/病症
        for pattern in self.syndrome_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['syndrome'] = match.group(1)
                break
        
        # 提取治法
        for pattern in self.treatment_patterns:
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
            r'(煎服)', r'(温服)', r'(冲服)', r'(研末)', r'(丸剂)'
        ]
        
        for pattern in usage_patterns:
            match = re.search(pattern, context_text)
            if match:
                context_info['usage'] = match.group(1)
                break
        
        return context_info

    def process_document(self, docx_path: str) -> Dict[str, Any]:
        """处理单个文档提取处方信息"""
        filename = os.path.basename(docx_path)
        disease_name = filename.replace('.docx', '')
        
        result = {
            'success': False,
            'filename': filename,
            'disease_name': disease_name,
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
                    'disease_name': disease_name,
                    'syndrome': context_info['syndrome'],
                    'treatment_method': context_info['treatment_method'],
                    'formula_name': context_info['formula_name'] or f"{disease_name}处方{i+1}",
                    'herbs': presc_para['herbs'],
                    'herb_count': presc_para['herb_count'],
                    'usage': context_info['usage'],
                    'source_paragraph': presc_para['paragraph_index'],
                    'source_text': presc_para['text'][:300] + '...' if len(presc_para['text']) > 300 else presc_para['text']
                }
                
                result['prescriptions'].append(prescription)
            
            result['total_prescriptions'] = len(prescription_paragraphs)
            result['success'] = True
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"处理文档失败 {filename}: {e}")
        
        return result

    def create_comprehensive_database(self, folder_path: str) -> Dict[str, Any]:
        """创建全面的TCM病症-处方数据库"""
        docx_files = self.get_all_docx_files(folder_path)
        
        database = {
            'creation_time': datetime.now().isoformat(),
            'total_documents': len(docx_files),
            'total_prescriptions': 0,
            'documents': [],
            'syndromes_index': {},
            'herbs_index': {},
            'formulas_index': {},
            'diseases_index': {},
            'treatment_methods_index': {},
            'statistics': {}
        }
        
        print("🏥 创建完整的TCM病症-处方数据库")
        print("=" * 80)
        print(f"待处理文档数量: {len(docx_files)}")
        
        successful_count = 0
        failed_count = 0
        total_herbs = 0
        
        for i, docx_file in enumerate(docx_files, 1):
            filename = os.path.basename(docx_file)
            print(f"\n[{i}/{len(docx_files)}] 📄 处理: {filename}")
            
            result = self.process_document(docx_file)
            
            if result['success']:
                print(f"✅ 成功: {result['total_prescriptions']}个处方")
                database['documents'].append(result)
                database['total_prescriptions'] += result['total_prescriptions']
                successful_count += 1
                
                # 建立各种索引
                self._build_indexes(database, result)
                
                # 统计药物总数
                for prescription in result['prescriptions']:
                    total_herbs += prescription['herb_count']
                    
            else:
                print(f"❌ 失败: {result['error_message']}")
                failed_count += 1
        
        # 添加统计信息
        database['statistics'] = {
            'successful_documents': successful_count,
            'failed_documents': failed_count,
            'success_rate': f"{successful_count/len(docx_files)*100:.1f}%",
            'total_herbs_extracted': total_herbs,
            'avg_prescriptions_per_document': database['total_prescriptions'] / successful_count if successful_count > 0 else 0,
            'unique_syndromes': len(database['syndromes_index']),
            'unique_herbs': len(database['herbs_index']),
            'unique_formulas': len(database['formulas_index']),
            'unique_diseases': len(database['diseases_index']),
            'unique_treatment_methods': len(database['treatment_methods_index'])
        }
        
        print(f"\n📊 数据库创建完成:")
        print(f"   成功处理: {successful_count}/{len(docx_files)} 文档")
        print(f"   总处方数: {database['total_prescriptions']}")
        print(f"   证型数: {len(database['syndromes_index'])}")
        print(f"   药物数: {len(database['herbs_index'])}")
        print(f"   方剂数: {len(database['formulas_index'])}")
        print(f"   病症数: {len(database['diseases_index'])}")
        print(f"   治法数: {len(database['treatment_methods_index'])}")
        
        return database

    def _build_indexes(self, database: Dict[str, Any], document_result: Dict[str, Any]):
        """建立各种索引"""
        for prescription in document_result['prescriptions']:
            # 证型索引
            if prescription['syndrome']:
                syndrome = prescription['syndrome']
                if syndrome not in database['syndromes_index']:
                    database['syndromes_index'][syndrome] = []
                database['syndromes_index'][syndrome].append({
                    'document': document_result['filename'],
                    'disease': document_result['disease_name'],
                    'prescription_id': prescription['prescription_id'],
                    'formula_name': prescription['formula_name']
                })
            
            # 药物索引
            for herb in prescription['herbs']:
                herb_name = herb['name']
                if herb_name not in database['herbs_index']:
                    database['herbs_index'][herb_name] = []
                database['herbs_index'][herb_name].append({
                    'document': document_result['filename'],
                    'disease': document_result['disease_name'],
                    'prescription_id': prescription['prescription_id'],
                    'dose': f"{herb['dose']}{herb['unit']}",
                    'formula_name': prescription['formula_name']
                })
            
            # 方剂索引
            formula = prescription['formula_name']
            if formula not in database['formulas_index']:
                database['formulas_index'][formula] = []
            database['formulas_index'][formula].append({
                'document': document_result['filename'],
                'disease': document_result['disease_name'],
                'prescription_id': prescription['prescription_id'],
                'syndrome': prescription['syndrome']
            })
            
            # 病症索引
            disease = document_result['disease_name']
            if disease not in database['diseases_index']:
                database['diseases_index'][disease] = []
            database['diseases_index'][disease].append({
                'prescription_id': prescription['prescription_id'],
                'syndrome': prescription['syndrome'],
                'formula_name': prescription['formula_name'],
                'treatment_method': prescription['treatment_method']
            })
            
            # 治法索引
            if prescription['treatment_method']:
                treatment = prescription['treatment_method']
                if treatment not in database['treatment_methods_index']:
                    database['treatment_methods_index'][treatment] = []
                database['treatment_methods_index'][treatment].append({
                    'document': document_result['filename'],
                    'disease': document_result['disease_name'],
                    'prescription_id': prescription['prescription_id'],
                    'syndrome': prescription['syndrome']
                })

def main():
    """主函数"""
    processor = CompleteTCMProcessor()
    
    # 处理所有文档
    database = processor.create_comprehensive_database('/opt/tcm-ai/all_tcm_docs')
    
    # 保存完整数据库
    output_file = '/opt/tcm-ai/template_files/complete_tcm_database.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 完整数据库已保存到: {output_file}")
    
    # 生成数据库摘要报告
    summary_file = '/opt/tcm-ai/template_files/database_summary.txt'
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("TCM病症-处方数据库摘要报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"创建时间: {database['creation_time']}\n")
        f.write(f"处理文档数: {database['statistics']['successful_documents']}/{database['total_documents']}\n")
        f.write(f"成功率: {database['statistics']['success_rate']}\n")
        f.write(f"总处方数: {database['total_prescriptions']}\n")
        f.write(f"提取药物总数: {database['statistics']['total_herbs_extracted']}\n\n")
        
        f.write("索引统计:\n")
        f.write(f"- 病症数: {database['statistics']['unique_diseases']}\n")
        f.write(f"- 证型数: {database['statistics']['unique_syndromes']}\n")
        f.write(f"- 方剂数: {database['statistics']['unique_formulas']}\n")
        f.write(f"- 药物数: {database['statistics']['unique_herbs']}\n")
        f.write(f"- 治法数: {database['statistics']['unique_treatment_methods']}\n\n")
        
        f.write("主要病症:\n")
        for disease in sorted(database['diseases_index'].keys())[:20]:
            count = len(database['diseases_index'][disease])
            f.write(f"- {disease}: {count}个处方\n")
        
        f.write("\n常用药物 (出现频次):\n")
        herb_counts = {}
        for herb, occurrences in database['herbs_index'].items():
            herb_counts[herb] = len(occurrences)
        
        for herb, count in sorted(herb_counts.items(), key=lambda x: x[1], reverse=True)[:30]:
            f.write(f"- {herb}: {count}次\n")
    
    print(f"📋 数据库摘要报告已保存到: {summary_file}")
    
    return database

if __name__ == "__main__":
    main()