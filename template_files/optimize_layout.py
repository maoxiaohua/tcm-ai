#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策树构建器页面排版优化脚本
"""

import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("📖 读取当前文件...")
content = read_file('/opt/tcm-ai/static/decision_tree_visual_builder.html')

print("\n=== 开始排版优化 ===\n")

# 1. 完全删除右侧面板HTML
print("❌ 删除右侧面板HTML...")
content = re.sub(
    r'<!-- 右侧分析结果面板 -->.*?</div>\s*</div>',
    '</div>',
    content,
    flags=re.DOTALL
)

# 如果还有残留的right-panel
content = re.sub(
    r'<div class="right-panel">.*?</div>\s*</div>',
    '</div>',
    content,
    flags=re.DOTALL
)

# 2. 删除空的div标签
print("🧹 清理空标签...")
content = re.sub(r'<div>\s*</div>\s*<div>\s*</div>', '', content)
content = re.sub(r'</div>\s*</div>\s*</div>\s*</div>\s*<!-- AI功能 -->', '<!-- AI功能 -->', content)

# 3. 删除right-panel相关CSS
print("❌ 删除右侧面板CSS...")
content = re.sub(r'\.right-panel\s*\{[^}]*\}', '', content)
content = re.sub(r'\.tcm-guide-panel\s*\{[^}]*\}', '', content)

# 4. 优化main-content样式
print("🎨 优化主内容区域样式...")
new_main_content_css = '''        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            padding: 20px;
        }'''

content = re.sub(
    r'\.main-content\s*\{[^}]*\}',
    new_main_content_css,
    content
)

# 5. 优化侧边栏样式
print("🎨 优化侧边栏样式...")
new_sidebar_css = '''        .sidebar {
            width: 320px;
            background: #f8fafc;
            border-right: 1px solid #e2e8f0;
            padding: 20px;
            overflow-y: auto;
        }'''

content = re.sub(
    r'\.sidebar\s*\{[^}]*\}',
    new_sidebar_css,
    content
)

# 6. 优化section-title样式
print("🎨 优化标题样式...")
new_section_title_css = '''        .section-title {
            font-size: 15px;
            font-weight: 600;
            color: #1e40af;
            margin: 20px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #dbeafe;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-title:first-child {
            margin-top: 0;
        }'''

content = re.sub(
    r'\.section-title\s*\{[^}]*\}',
    new_section_title_css,
    content
)

# 7. 优化按钮组样式
print("🎨 优化按钮样式...")
new_btn_group_css = '''        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 10px;
        }

        .btn {
            width: 100%;
            padding: 12px 16px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .btn:active {
            transform: translateY(0);
        }'''

content = re.sub(r'\.btn-group\s*\{[^}]*\}', '', content)
content = re.sub(r'\.btn\s*\{[^}]*\}', '', content)

# 在第一个</style>前插入新样式
style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + new_btn_group_css + '\n    ' + content[style_pos:]

# 8. 优化按钮颜色
print("🎨 优化按钮配色...")
btn_colors_css = '''
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

style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + btn_colors_css + '\n    ' + content[style_pos:]

# 9. 优化表单样式
print("🎨 优化表单样式...")
form_css = '''
        .form-group {
            margin-bottom: 16px;
        }

        .form-label {
            display: block;
            margin-bottom: 6px;
            color: #374151;
            font-weight: 500;
            font-size: 13px;
        }

        .form-input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.2s;
        }

        .form-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .form-textarea {
            min-height: 100px;
            resize: vertical;
            font-family: inherit;
        }'''

# 移除旧的form样式
content = re.sub(r'\.form-group\s*\{[^}]*\}', '', content)
content = re.sub(r'\.form-label\s*\{[^}]*\}', '', content)
content = re.sub(r'\.form-input\s*\{[^}]*\}', '', content)

style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + form_css + '\n    ' + content[style_pos:]

# 10. 优化canvas区域样式
print("🎨 优化画布区域...")
canvas_css = '''
        .header {
            background: white;
            padding: 20px 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #1e40af;
            margin: 0 0 8px 0;
            font-size: 24px;
        }

        .header p {
            color: #6b7280;
            font-size: 14px;
            margin: 0;
        }

        .canvas-area {
            flex: 1;
            background: white;
            border-radius: 12px;
            position: relative;
            overflow: auto;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            min-height: 500px;
        }'''

content = re.sub(r'\.header\s*\{[^}]*\}', '', content)
content = re.sub(r'\.canvas-area\s*\{[^}]*\}', '', content)

style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + canvas_css + '\n    ' + content[style_pos:]

# 11. 优化AI模式选择器样式
print("🎨 优化AI模式选择器...")
ai_mode_css = '''
        .ai-mode-selector {
            margin-bottom: 15px;
            padding: 14px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 8px;
            border: 1px solid #bae6fd;
        }'''

content = re.sub(r'\.ai-mode-selector\s*\{[^}]*\}', '', content)

style_pos = content.find('</style>')
if style_pos != -1:
    content = content[:style_pos] + ai_mode_css + '\n    ' + content[style_pos:]

print("\n💾 保存优化后的文件...")
write_file('/opt/tcm-ai/static/decision_tree_visual_builder.html', content)

print("\n✅ 排版优化完成！\n")
print("优化内容：")
print("  🎨 清理了右侧面板HTML")
print("  🎨 优化了侧边栏宽度和间距")
print("  🎨 美化了按钮样式和配色")
print("  🎨 改进了表单输入框样式")
print("  🎨 优化了标题和分组样式")
print("  🎨 调整了画布区域布局")

