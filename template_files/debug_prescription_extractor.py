#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本的处方提取器
详细分析文档内容，找出问题所在
"""

import sys
import re
from docx import Document

sys.path.append('/opt/tcm-ai')

def debug_document_content(docx_path):
    """调试文档内容"""
    
    print(f"🔍 调试分析: {docx_path.split('/')[-1]}")
    print("=" * 60)
    
    try:
        doc = Document(docx_path)
        paragraphs = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        print(f"📊 文档统计:")
        print(f"   总段落数: {len(paragraphs)}")
        
        # 1. 查找包含"克"的段落
        herb_pattern = r'([\\u4e00-\\u9fff]{2,5})\\s*(\\d+(?:\\.\\d+)?)\\s*([克钱g])'
        
        print(f"\\n🔍 搜索药物模式...")
        paragraphs_with_herbs = []
        
        for i, para in enumerate(paragraphs):
            matches = re.findall(herb_pattern, para)
            if matches:
                paragraphs_with_herbs.append((i, para, matches))
        
        print(f"   找到包含药物的段落: {len(paragraphs_with_herbs)}个")
        
        # 显示前10个包含药物的段落
        print(f"\\n📋 包含药物的段落详情:")
        for i, (para_idx, para_text, matches) in enumerate(paragraphs_with_herbs[:10]):
            print(f"\\n段落{para_idx+1} [找到{len(matches)}个药物]:") 
            print(f"   内容: {para_text[:150]}...")
            print(f"   药物: {matches}")
        
        # 2. 简单搜索包含"克"字的段落
        print(f"\\n🔍 搜索包含'克'字的段落...")
        ke_paragraphs = []
        
        for i, para in enumerate(paragraphs):
            if '克' in para:
                ke_paragraphs.append((i, para))
        
        print(f"   找到包含'克'的段落: {len(ke_paragraphs)}个")
        
        # 显示前5个
        for i, (para_idx, para_text) in enumerate(ke_paragraphs[:5]):
            print(f"\\n段落{para_idx+1}:")
            print(f"   {para_text[:200]}...")
        
        # 3. 搜索特定的药物名称
        print(f"\\n🌿 搜索特定药物...")
        test_herbs = ['甘草', '麻黄', '杏仁', '桔梗', '荆芥', '防风']
        
        for herb in test_herbs:
            count = sum(1 for para in paragraphs if herb in para)
            print(f"   {herb}: 出现在{count}个段落中")
            
            if count > 0:
                # 找到第一个包含该药物的段落
                for i, para in enumerate(paragraphs):
                    if herb in para:
                        print(f"     示例段落{i+1}: {para[:100]}...")
                        break
        
        # 4. 查找数字+克的模式
        print(f"\\n🔢 搜索数字+克模式...")
        number_ke_pattern = r'\\d+[\\s]*克'
        
        ke_count = 0
        for para in paragraphs:
            matches = re.findall(number_ke_pattern, para)
            if matches:
                ke_count += len(matches)
                print(f"   找到: {matches}")
                if ke_count >= 10:  # 只显示前10个
                    break
        
        print(f"   总共找到{ke_count}个数字+克模式")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        return False

def main():
    """主函数"""
    test_files = [
        '/opt/tcm-ai/all_tcm_docs/感冒.docx'
    ]
    
    for test_file in test_files:
        debug_document_content(test_file)
        print("\\n" + "="*80 + "\\n")

if __name__ == "__main__":
    main()