#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除不需要的JavaScript函数
"""

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("📖 读取文件...")
content = read_file('/opt/tcm-ai/static/decision_tree_visual_builder.html')

# 逐行处理，删除特定函数
lines = content.split('\n')
new_lines = []
skip = False
skip_reason = ""
brace_count = 0

for i, line in enumerate(lines, 1):
    # 检测需要删除的函数开始
    if '// ======================== 💊 智能处方提取功能' in line:
        skip = True
        skip_reason = "智能处方提取"
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    if 'async function extractPrescriptionInfo' in line:
        skip = True
        skip_reason = "extractPrescriptionInfo函数"
        brace_count = 0
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    if '// 方剂AI分析' in line and 'async function analyzeFormula' in lines[i] if i < len(lines) else False:
        skip = True
        skip_reason = "方剂AI分析"
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    if 'async function analyzeFormula()' in line:
        skip = True
        skip_reason = "analyzeFormula函数"
        brace_count = 0
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    if 'function showLocalFormulaAnalysis' in line:
        skip = True
        skip_reason = "showLocalFormulaAnalysis函数"
        brace_count = 0
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    if 'function analyzeFormulaLocally' in line:
        skip = True
        skip_reason = "analyzeFormulaLocally函数"
        brace_count = 0
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    if 'function showFormulaAnalysisResult' in line:
        skip = True
        skip_reason = "showFormulaAnalysisResult函数"
        brace_count = 0
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    if 'function showPrescriptionExtractionResult' in line:
        skip = True
        skip_reason = "showPrescriptionExtractionResult函数"
        brace_count = 0
        print(f"❌ 第{i}行开始删除: {skip_reason}")
        continue

    # 如果在跳过模式，计算花括号
    if skip:
        brace_count += line.count('{')
        brace_count -= line.count('}')

        # 如果花括号平衡，说明函数结束
        if brace_count <= 0 and ('{' in line or '}' in line):
            print(f"  ✓ 第{i}行结束删除: {skip_reason}")
            skip = False
            skip_reason = ""
            brace_count = 0
        continue

    new_lines.append(line)

content = '\n'.join(new_lines)

# 删除事件绑定
print("\n❌ 删除事件监听器...")
content = content.replace("const extractPrescriptionBtn = document.getElementById('extractPrescriptionBtn');", '')
content = content.replace("if (extractPrescriptionBtn) extractPrescriptionBtn.addEventListener('click', extractPrescriptionInfo);", '')
content = content.replace("const formulaAnalyzeBtn = document.getElementById('formulaAnalyzeBtn');", '')
content = content.replace("if (formulaAnalyzeBtn) formulaAnalyzeBtn.addEventListener('click', analyzeFormula);", '')

print("\n💾 保存文件...")
write_file('/opt/tcm-ai/static/decision_tree_visual_builder.html', content)

print("\n✅ JavaScript函数清理完成！")
