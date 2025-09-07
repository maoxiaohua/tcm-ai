#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接版本的处方提取器
直接基于观察到的具体格式进行提取
"""

import sys
import re
from docx import Document
import json

sys.path.append('/opt/tcm-ai')

def extract_prescriptions_directly(docx_path):
    """直接提取处方信息"""
    
    print(f"🔍 直接提取: {docx_path.split('/')[-1]}")
    print("=" * 60)
    
    try:
        doc = Document(docx_path)
        paragraphs = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        prescriptions = []
        
        # 直接查找我们知道包含处方的段落模式
        for i, para in enumerate(paragraphs):
            # 方法1: 查找包含多个"克"的段落
            ke_count = para.count('克')
            if ke_count >= 5:  # 至少5个"克"
                print(f"\\n📋 找到可能的处方段落{i+1} (包含{ke_count}个'克'):")
                print(f"   {para[:200]}...")
                
                # 尝试提取药物信息
                herbs = extract_herbs_from_paragraph(para)
                if len(herbs) >= 3:
                    prescriptions.append({
                        'paragraph_index': i+1,
                        'herbs': herbs,
                        'herb_count': len(herbs),
                        'source_text': para
                    })
                    print(f"   ✅ 提取到{len(herbs)}味药物")
                else:
                    print(f"   ❌ 仅提取到{len(herbs)}味药物")
        
        print(f"\\n📊 提取结果:")
        print(f"   找到处方数量: {len(prescriptions)}")
        
        for i, prescription in enumerate(prescriptions):
            print(f"\\n处方{i+1}:")
            print(f"   药物数量: {prescription['herb_count']}")
            print(f"   药物组成:")
            for herb in prescription['herbs'][:10]:  # 显示前10味药
                print(f"     • {herb}")
            if len(prescription['herbs']) > 10:
                print(f"     ... 还有{len(prescription['herbs'])-10}味药")
        
        return prescriptions
        
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        return []

def extract_herbs_from_paragraph(para_text):
    """从段落中提取药物信息"""
    herbs = []
    
    # 多种药物模式
    patterns = [
        # 模式1: "荆 芥 6 克" (空格分隔)
        r'([\\u4e00-\\u9fff](?:\\s+[\\u4e00-\\u9fff]){0,3})\\s+(\\d+(?:\\.\\d+)?)\\s*克',
        
        # 模式2: "杏仁9克" (无空格)
        r'([\\u4e00-\\u9fff]{2,6})(\\d+(?:\\.\\d+)?)克',
        
        # 模式3: "甘草：3克" (冒号分隔)
        r'([\\u4e00-\\u9fff]{2,6})[：:](\\d+(?:\\.\\d+)?)克'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, para_text)
        for match in matches:
            herb_name = match[0].strip().replace(' ', '')  # 去除空格
            dose = match[1]
            
            # 验证药名
            if is_valid_herb_name(herb_name):
                herb_info = f"{herb_name} {dose}克"
                if herb_info not in herbs:  # 避免重复
                    herbs.append(herb_info)
    
    return herbs

def is_valid_herb_name(name):
    """验证药名"""
    # 常见中药名
    common_herbs = [
        '甘草', '生姜', '大枣', '麻黄', '桂枝', '白芍', '杏仁', '石膏',
        '黄芩', '柴胡', '半夏', '陈皮', '茯苓', '白术', '人参', '当归',
        '川芎', '熟地', '生地', '知母', '连翘', '金银花', '板蓝根',
        '桔梗', '薄荷', '荆芥', '防风', '羌活', '独活', '葛根', '升麻',
        '前胡', '紫苏', '藿香', '佩兰', '苍术', '厚朴', '枳壳', '木香',
        '牛蒡子', '竹叶', '豆豉', '沙参', '浙贝母', '麦冬', '栀子',
        '桑叶', '桑白皮', '苍耳子', '白前', '莱菔子', '山豆根',
        '射干', '菊花', '蔓荆子', '茅根', '葛根', '黄芩', '连翘',
        '侧柏叶', '三七', '金银花', '板蓝根', '瓜蒌', '丹皮'
    ]
    
    if name in common_herbs:
        return True
    
    # 长度合理
    if 2 <= len(name) <= 5:
        # 不包含明显的非药名词
        invalid_words = ['患者', '医生', '治疗', '每日', '服用', '剂量']
        if not any(word in name for word in invalid_words):
            return True
    
    return False

def test_specific_paragraphs():
    """测试特定段落"""
    
    # 从调试结果中我们知道的包含处方的段落
    test_paragraphs = [
        "荆 芥 6 克  防 风 6 克  羌 活 6 克  独 活 6 克  前 胡 9 克 柴胡6克  枳 壳 9 克  川 芎 9 克  桔 梗 9 克  甘 草 3 克  每 日一剂，水煎分二次温服。",
        
        "金银花15克  连翘15克  竹 叶 9 克  荆 芥 9 克  牛 蒡 子 9 克  豆 豉 9 克  薄荷6克  板 蓝 根 1 5 克  甘 草 3 克 每 日一剂，水煎分二次温服。",
        
        "加减：鼻塞流涕重者，加苍耳子9克、辛黄9克；咳嗽 重者，加杏仁9克、白前9克；痰多者，加陈皮9克、半夏 9克、莱菔子9克；挟消化不良者，加炒神曲9克、莱菔子 9克。"
    ]
    
    print("🧪 测试特定段落提取效果")
    print("=" * 60)
    
    for i, para in enumerate(test_paragraphs):
        print(f"\\n测试段落{i+1}:")
        print(f"原文: {para[:100]}...")
        
        herbs = extract_herbs_from_paragraph(para)
        print(f"提取结果: 找到{len(herbs)}味药物")
        for herb in herbs:
            print(f"  • {herb}")

def main():
    """主函数"""
    # 先测试特定段落
    test_specific_paragraphs()
    
    print("\\n" + "="*80 + "\\n")
    
    # 再测试完整文档
    test_files = [
        '/opt/tcm-ai/all_tcm_docs/感冒.docx'
    ]
    
    all_prescriptions = []
    for test_file in test_files:
        prescriptions = extract_prescriptions_directly(test_file)
        all_prescriptions.extend(prescriptions)
    
    # 保存结果
    if all_prescriptions:
        result = {
            'total_prescriptions': len(all_prescriptions),
            'prescriptions': all_prescriptions
        }
        
        with open('/opt/tcm-ai/template_files/extracted_prescriptions.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\\n💾 结果已保存到: extracted_prescriptions.json")

if __name__ == "__main__":
    main()