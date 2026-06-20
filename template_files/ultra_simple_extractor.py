#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超级简单的处方提取器
用最基础的方法调试问题
"""

import re

def test_regex_patterns():
    """测试正则表达式模式"""
    
    # 测试文本（从实际文档复制）
    test_text = "荆芝6克  防风6克  羌活6克  独活6克  前胡9克 柴胡6克  枳壳9克  川芎9克  桔梗9克  甘草3克"
    
    print("🧪 测试正则表达式模式")
    print("=" * 50)
    print(f"测试文本: {test_text}")
    
    # 测试不同的正则模式
    patterns = [
        # 模式1: 最简单的中文+数字+克
        r'([\\u4e00-\\u9fff]+)(\\d+)克',
        
        # 模式2: 考虑空格
        r'([\\u4e00-\\u9fff\\s]+?)\\s*(\\d+)\\s*克',
        
        # 模式3: 更宽松的匹配
        r'([^\\d]+?)(\\d+)克',
        
        # 模式4: 分步匹配
        r'(\\d+)克'
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\\n模式{i}: {pattern}")
        try:
            matches = re.findall(pattern, test_text)
            print(f"匹配结果: {matches}")
        except Exception as e:
            print(f"错误: {e}")

def test_simple_extraction():
    """测试简单提取"""
    
    # 最直接的方法：先找所有数字+克，再往前找药名
    test_text = "荆芥6克  防风6克  羌活6克  独活6克  前胡9克 柴胡6克"
    
    print(f"\\n🔍 简单提取测试")
    print(f"测试文本: {test_text}")
    
    # 方法1: 找所有"数字克"
    dose_pattern = r'\\d+克'
    doses = re.findall(dose_pattern, test_text)
    print(f"找到剂量: {doses}")
    
    # 方法2: 分割文本然后分析
    parts = test_text.split()
    print(f"分割结果: {parts}")
    
    # 方法3: 最简单的方法
    herbs = []
    words = test_text.replace('  ', ' ').split(' ')  # 处理多个空格
    
    i = 0
    while i < len(words) - 1:
        word = words[i].strip()
        next_word = words[i + 1].strip()
        
        # 如果下一个词包含"克"
        if '克' in next_word:
            # 提取数字
            dose_match = re.search(r'(\\d+)', next_word)
            if dose_match:
                dose = dose_match.group(1)
                herbs.append(f"{word} {dose}克")
                i += 2  # 跳过下一个词
                continue
        i += 1
    
    print(f"提取的药物: {herbs}")

def main():
    """主函数"""
    test_regex_patterns()
    test_simple_extraction()

if __name__ == "__main__":
    main()