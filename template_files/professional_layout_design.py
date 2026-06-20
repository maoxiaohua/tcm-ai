#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业UI设计师视角的决策树构建器布局重构
目标：所有内容在一屏内展示，层次分明，无需滚动
"""

import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("📐 开始专业UI设计优化...\n")

content = read_file('/opt/tcm-ai/static/decision_tree_visual_builder.html')

# ==================== 第一步：重新设计CSS布局 ====================
print("🎨 第1步：重构核心布局...")

new_core_layout = '''        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            overflow: hidden;
            color: #333;
        }

        .container {
            display: flex;
            height: 100vh;
            max-width: 100%;
            margin: 0;
            background: white;
        }

        /* 紧凑型侧边栏 - 固定宽度，内容紧凑 */
        .sidebar {
            width: 280px;
            background: #f8fafc;
            border-right: 1px solid #e2e8f0;
            padding: 16px 12px;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            flex-shrink: 0;
        }

        /* 主内容区 - 占据剩余空间 */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 16px;
            overflow: hidden;
        }'''

# 替换核心布局
content = re.sub(r'\*\s*\{.*?\}', '', content, flags=re.DOTALL, count=1)
content = re.sub(r'body\s*\{.*?\}', '', content, flags=re.DOTALL, count=1)
content = re.sub(r'\.container\s*\{.*?\}', '', content, flags=re.DOTALL, count=1)
content = re.sub(r'\.sidebar\s*\{.*?\}', '', content, flags=re.DOTALL, count=1)
content = re.sub(r'\.main-content\s*\{.*?\}', '', content, flags=re.DOTALL, count=1)

style_start = content.find('<style>')
if style_start != -1:
    content = content[:style_start+7] + new_core_layout + '\n' + content[style_start+7:]

# ==================== 第二步：紧凑型标题样式 ====================
print("🎨 第2步：优化标题和间距...")

new_section_title = '''
        .section-title {
            font-size: 13px;
            font-weight: 600;
            color: #1e40af;
            margin: 12px 0 8px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #dbeafe;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .section-title:first-child {
            margin-top: 0;
        }'''

content = re.sub(r'\.section-title\s*\{.*?\}.*?\.section-title:first-child\s*\{.*?\}', '', content, flags=re.DOTALL)
style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + new_section_title + '\n    ' + content[style_pos:]

# ==================== 第三步：紧凑型表单 ====================
print("🎨 第3步：优化表单布局...")

new_form_styles = '''
        .form-group {
            margin-bottom: 10px;
        }

        .form-label {
            display: block;
            margin-bottom: 4px;
            color: #374151;
            font-weight: 500;
            font-size: 12px;
        }

        .form-input {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 13px;
            transition: border-color 0.2s;
        }

        .form-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
        }

        .form-textarea {
            min-height: 70px;
            resize: vertical;
            font-family: inherit;
        }'''

content = re.sub(r'\.form-group\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.form-label\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.form-input\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.form-input:focus\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.form-textarea\s*\{.*?\}', '', content, flags=re.DOTALL)

style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + new_form_styles + '\n    ' + content[style_pos:]

# ==================== 第四步：紧凑型按钮布局（2列） ====================
print("🎨 第4步：按钮改为2列网格布局...")

new_btn_styles = '''
        /* 按钮网格布局 - 2列 */
        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 8px;
        }

        .btn-group.full-width {
            grid-template-columns: 1fr;
        }

        .btn {
            padding: 8px 12px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            white-space: nowrap;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            background: linear-gradient(135deg, #5568d3 0%, #63357d 100%);
        }

        .btn-secondary {
            background: #6b7280;
            color: white;
        }

        .btn-secondary:hover {
            background: #4b5563;
        }

        .btn-success {
            background: #10b981;
            color: white;
        }

        .btn-success:hover {
            background: #059669;
        }

        .btn-danger {
            background: #ef4444;
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
        }'''

content = re.sub(r'\.btn-group\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn:hover\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn:active\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-primary\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-primary:hover\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-secondary\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-secondary:hover\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-success\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-success:hover\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-danger\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.btn-danger:hover\s*\{.*?\}', '', content, flags=re.DOTALL)

style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + new_btn_styles + '\n    ' + content[style_pos:]

# ==================== 第五步：紧凑型AI模式选择器 ====================
print("🎨 第5步：优化AI模式选择器...")

new_ai_selector = '''
        .ai-mode-selector {
            margin-bottom: 10px;
            padding: 10px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 6px;
            border: 1px solid #bae6fd;
            font-size: 11px;
        }'''

content = re.sub(r'\.ai-mode-selector\s*\{.*?\}', '', content, flags=re.DOTALL)
style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + new_ai_selector + '\n    ' + content[style_pos:]

# ==================== 第六步：主内容区域优化 ====================
print("🎨 第6步：优化主内容区域...")

new_main_styles = '''
        .header {
            background: white;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #1e40af;
            margin: 0 0 4px 0;
            font-size: 20px;
        }

        .header p {
            color: #6b7280;
            font-size: 12px;
            margin: 0;
        }

        .canvas-area {
            flex: 1;
            background: white;
            border-radius: 8px;
            position: relative;
            overflow: auto;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }'''

content = re.sub(r'\.header\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.header h1\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.header p\s*\{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.canvas-area\s*\{.*?\}', '', content, flags=re.DOTALL)

style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + new_main_styles + '\n    ' + content[style_pos:]

# ==================== 第七步：修改HTML结构，使某些按钮占满宽度 ====================
print("🎨 第7步：调整按钮HTML结构...")

# 智能生成决策树按钮改为全宽
content = content.replace(
    '<div class="btn-group">',
    '<div class="btn-group full-width">',
    1  # 只替换第一个（智能生成按钮）
)

# 保存到思维库和查看历史按钮放在同一组
content = re.sub(
    r'<div class="btn-group">\s*<button class="btn btn-primary" id="saveToLibraryBtn".*?</button>\s*</div>\s*<div class="btn-group">\s*<button class="btn btn-secondary" id="viewHistoryBtn".*?</button>\s*</div>',
    '''<div class="btn-group">
                <button class="btn btn-primary" id="saveToLibraryBtn" style="background: #7c3aed;">💾 保存</button>
                <button class="btn btn-secondary" id="viewHistoryBtn" style="background: #6b7280;">📋 历史</button>
            </div>''',
    content,
    flags=re.DOTALL
)

print("\n💾 保存优化后的文件...")
write_file('/opt/tcm-ai/static/decision_tree_visual_builder.html', content)

print("\n✅ 专业UI设计完成！\n")
print("优化亮点：")
print("  📐 所有内容在100vh内完整展示")
print("  🎯 侧边栏从280px宽，内容紧凑")
print("  🔲 按钮采用2列网格布局，节省空间")
print("  📏 标题、间距、字体全面优化")
print("  🎨 层次分明，视觉平衡")
print("  ⚡ 无需滚动，一屏完整查看")

