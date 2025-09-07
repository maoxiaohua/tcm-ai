#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度分析中医文档中的处方结构
找到真实的病症-处方对应关系
"""

import sys
import re
from docx import Document

sys.path.append('/opt/tcm-ai')

def analyze_document_structure(docx_path):
    """深度分析文档结构"""
    
    print(f"🔍 深度分析: {docx_path.split('/')[-1]}")
    print("=" * 60)
    
    try:
        doc = Document(docx_path)
        
        # 提取所有段落
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        full_text = '\n'.join(paragraphs)
        
        print(f"📊 文档统计:")
        print(f"   总段落数: {len(paragraphs)}")
        print(f"   总字符数: {len(full_text)}")
        
        # 1. 查找所有可能的处方相关关键词
        prescription_keywords = [
            '方药', '处方', '方剂', '组成', '药物', '治法', '治疗',
            '主治', '功效', '用法', '服法', '水煎', '煎服',
            '加减', '随证', '临证'
        ]
        
        print(f"\\n📋 处方关键词分布:")
        for keyword in prescription_keywords:
            count = full_text.count(keyword)
            if count > 0:
                print(f"   {keyword}: {count}次")
                
                # 显示第一个出现的上下文
                index = full_text.find(keyword)
                if index >= 0:
                    start = max(0, index - 50)
                    end = min(len(full_text), index + 100)
                    context = full_text[start:end].replace('\\n', ' ')
                    print(f"     上下文: ...{context}...")
        
        # 2. 查找具体的药物名称模式
        print(f"\\n🌿 药物名称分析:")
        
        # 常见中药名
        common_herbs = [
            '甘草', '生姜', '大枣', '人参', '黄芪', '当归', '川芎', '白芍', '熟地',
            '柴胡', '黄芩', '半夏', '陈皮', '茯苓', '白术', '桂枝', '麻黄', '杏仁',
            '石膏', '知母', '连翘', '金银花', '板蓝根', '桔梗', '薄荷', '荆芥',
            '防风', '羌活', '独活', '葛根', '升麻', '前胡', '紫苏', '藿香'
        ]
        
        found_herbs = []
        for herb in common_herbs:
            if herb in full_text:
                # 查找药物及其可能的剂量
                pattern = f'{herb}[\\s]*\\d*[\\s]*[克钱g两]?'
                matches = re.findall(pattern, full_text)
                if matches:
                    found_herbs.extend(matches)
        
        if found_herbs:
            print(f"   找到药物: {len(found_herbs)}个")
            for herb in found_herbs[:10]:  # 显示前10个
                print(f"     • {herb}")
        
        # 3. 查找数字+单位的模式（剂量）
        print(f"\\n📏 剂量模式分析:")
        dose_patterns = [
            r'\\d+[\\s]*克',
            r'\\d+[\\s]*g', 
            r'\\d+[\\s]*钱',
            r'\\d+[\\s]*两'
        ]
        
        all_doses = []
        for pattern in dose_patterns:
            matches = re.findall(pattern, full_text)
            all_doses.extend(matches)
        
        if all_doses:
            print(f"   找到剂量: {len(all_doses)}个")
            for dose in all_doses[:10]:
                print(f"     • {dose}")
        
        # 4. 查找连续的中文+数字的模式
        print(f"\\n🔤 中文+数字模式:")
        chinese_number_pattern = r'[\\u4e00-\\u9fff]{2,4}[\\s]*\\d+[\\s]*[克钱g两]'
        matches = re.findall(chinese_number_pattern, full_text)
        
        if matches:
            print(f"   找到模式: {len(matches)}个")
            for match in matches[:15]:  # 显示前15个
                print(f"     • {match}")
        
        # 5. 查找特定段落（可能包含完整处方）
        print(f"\\n📝 可能的处方段落:")
        
        for i, para in enumerate(paragraphs):
            # 查找包含多个药物名的段落
            herb_count = sum(1 for herb in common_herbs if herb in para)
            dose_count = len(re.findall(r'\\d+[克钱g]', para))
            
            if herb_count >= 3 or dose_count >= 3:  # 包含3个以上药物或剂量
                print(f"\\n   段落{i+1} [药物:{herb_count}, 剂量:{dose_count}]:")
                print(f"     {para[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return False

def main():
    """主函数"""
    test_files = [
        '/opt/tcm-ai/all_tcm_docs/感冒.docx',
        '/opt/tcm-ai/all_tcm_docs/咳嗽.docx'
    ]
    
    for test_file in test_files:
        analyze_document_structure(test_file)
        print("\\n" + "="*80 + "\\n")

if __name__ == "__main__":
    main()