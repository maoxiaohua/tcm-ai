#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正确的决策树构建器修改脚本
"""

import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# 从备份恢复
print("📖 从备份文件读取...")
content = read_file('/opt/tcm-ai/static/decision_tree_visual_builder.html.backup')

print("\n=== 开始修改 ===\n")

# 1. 移除"智能分支生成"整个模块（705-741行）
print("❌ 移除智能分支生成模块...")
content = re.sub(
    r'<!-- 🆕 智能分支生成 -->.*?</div>\s*</div>\s*</div>',
    '',
    content,
    flags=re.DOTALL
)

# 2. 移除"智能处方提取"按钮
print("❌ 移除智能处方提取按钮...")
content = re.sub(
    r'<button class="btn btn-success" id="extractPrescriptionBtn"[^>]*>.*?</button>',
    '',
    content,
    flags=re.DOTALL
)

# 3. 移除"方剂AI分析"按钮（保留智能生成决策树）
print("❌ 移除方剂AI分析按钮...")
content = re.sub(
    r'<!-- ✨ 高级分析功能 -->.*?<button class="btn btn-primary" id="formulaAnalyzeBtn"[^>]*>.*?</button>\s*</div>',
    '',
    content,
    flags=re.DOTALL
)

# 4. 在"保存到思维库"按钮后添加"查看历史决策树"按钮
print("➕ 添加查看历史决策树按钮...")
history_button = '''
            <div class="btn-group">
                <button class="btn btn-secondary" id="viewHistoryBtn" style="background: #6b7280;">📋 查看历史决策树</button>
            </div>'''

content = re.sub(
    r'(<button class="btn btn-primary" id="saveToLibraryBtn"[^>]*>💾 保存到思维库</button>\s*</div>)',
    r'\1' + history_button,
    content
)

# 5. 移除右侧分析结果面板
print("❌ 移除右侧分析结果面板...")
content = re.sub(
    r'<!-- 右侧分析结果面板 -->.*?<!-- 中医辨证思维指导 -->.*?</div>\s*</div>\s*</div>\s*</div>',
    '</div>\n    </div>',
    content,
    flags=re.DOTALL
)

# 6. 调整main-content样式，使其占满宽度
print("🎨 调整布局样式...")
content = re.sub(
    r'\.main-content\s*\{[^}]*\}',
    '''.main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            width: 100%;
        }''',
    content
)

# 7. 移除右侧面板相关CSS
print("❌ 移除右侧面板CSS...")
content = re.sub(r'/\* 右侧面板样式 \*/.*?\.right-panel\s*\{[^}]*\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.tcm-guide-panel\s*\{[^}]*\}', '', content)
content = re.sub(r'\.guide-section\s*\{[^}]*\}', '', content)

# 8. 添加历史记录模态框HTML（在</body>前）
print("➕ 添加历史记录模态框...")
history_modal = '''
<!-- 历史决策树模态框 -->
<div id="historyModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; overflow-y: auto;">
    <div style="background: white; max-width: 900px; margin: 50px auto; padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1e40af;">📋 我的决策树历史</h2>
            <button onclick="closeHistoryModal()" style="background: none; border: none; font-size: 28px; cursor: pointer; color: #6b7280;">&times;</button>
        </div>

        <div id="historyListContainer" style="max-height: 600px; overflow-y: auto;">
            <div style="text-align: center; padding: 40px; color: #6b7280;">
                <div style="font-size: 48px;">🔍</div>
                <div style="margin-top: 10px;">加载中...</div>
            </div>
        </div>
    </div>
</div>
'''

content = content.replace('</body>', history_modal + '\n</body>')

# 9. 添加历史记录JavaScript（在最后一个</script>前）
print("➕ 添加历史记录JavaScript...")
history_js = '''
        // ======================== 历史决策树管理功能 ========================

        async function viewHistoryTrees() {
            console.log('查看历史决策树');
            document.getElementById('historyModal').style.display = 'block';
            await loadHistoryList();
        }

        async function loadHistoryList() {
            const container = document.getElementById('historyListContainer');

            try {
                const doctorId = getCurrentDoctorId();
                const response = await fetch(`/api/get_doctor_patterns/${doctorId}`, {
                    headers: getAuthHeaders()
                });

                const data = await response.json();

                if (data.success && data.data.patterns && data.data.patterns.length > 0) {
                    displayHistoryList(data.data.patterns);
                } else {
                    container.innerHTML = `
                        <div style="text-align: center; padding: 40px; color: #6b7280;">
                            <div style="font-size: 48px;">📭</div>
                            <div style="margin-top: 10px;">暂无保存的决策树</div>
                            <div style="margin-top: 5px; font-size: 14px;">点击"保存到思维库"保存您的决策树</div>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('加载历史记录失败:', error);
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #ef4444;">
                        <div style="font-size: 48px;">⚠️</div>
                        <div style="margin-top: 10px;">加载失败: ${error.message}</div>
                    </div>
                `;
            }
        }

        function displayHistoryList(patterns) {
            const container = document.getElementById('historyListContainer');

            let html = '';
            patterns.forEach((pattern, index) => {
                const createdDate = new Date(pattern.created_at).toLocaleString('zh-CN');
                const usageCount = pattern.usage_count || 0;

                html += `
                    <div class="history-item" style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #f9fafb;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h3 style="margin: 0 0 10px 0; color: #1e40af; font-size: 18px;">
                                    ${index + 1}. ${pattern.disease_name}
                                </h3>
                                <div style="font-size: 13px; color: #6b7280; margin-bottom: 8px;">
                                    📅 创建时间: ${createdDate} | 📊 使用次数: ${usageCount}
                                </div>
                                <div style="font-size: 13px; color: #374151; max-height: 60px; overflow: hidden;">
                                    ${pattern.thinking_process ? pattern.thinking_process.substring(0, 150) + '...' : '无诊疗思路'}
                                </div>
                            </div>
                            <div style="display: flex; gap: 10px; margin-left: 15px;">
                                <button onclick="loadHistoryTree('${pattern.pattern_id}')"
                                        style="background: #3b82f6; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; white-space: nowrap;">
                                    📂 加载
                                </button>
                                <button onclick="deleteHistoryTree('${pattern.pattern_id}')"
                                        style="background: #ef4444; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; white-space: nowrap;">
                                    🗑️ 删除
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        async function loadHistoryTree(patternId) {
            try {
                showLoading('正在加载决策树...');

                const doctorId = getCurrentDoctorId();
                const response = await fetch(`/api/get_doctor_patterns/${doctorId}`, {
                    headers: getAuthHeaders()
                });

                const data = await response.json();

                if (data.success) {
                    const pattern = data.data.patterns.find(p => p.pattern_id === patternId);

                    if (pattern) {
                        // 恢复疾病名称
                        document.getElementById('diseaseName').value = pattern.disease_name;

                        // 恢复诊疗思路
                        if (pattern.thinking_process) {
                            document.getElementById('doctorThought').value = pattern.thinking_process;
                        }

                        // 恢复决策树结构
                        if (pattern.tree_structure && pattern.tree_structure.nodes) {
                            nodes.splice(0, nodes.length);
                            nodes.push(...pattern.tree_structure.nodes);
                            edges.splice(0, edges.length);
                            if (pattern.tree_structure.edges) {
                                edges.push(...pattern.tree_structure.edges);
                            }

                            draw();
                        }

                        closeHistoryModal();
                        hideLoading();
                        showResult('成功', `决策树"${pattern.disease_name}"已加载`, 'success');
                    }
                }
            } catch (error) {
                console.error('加载决策树失败:', error);
                hideLoading();
                showResult('错误', `加载失败: ${error.message}`, 'error');
            }
        }

        async function deleteHistoryTree(patternId) {
            if (!confirm('确定要删除这个决策树吗？此操作不可恢复。')) {
                return;
            }

            showResult('提示', '删除功能开发中...', 'info');
        }

        function closeHistoryModal() {
            document.getElementById('historyModal').style.display = 'none';
        }

        function getCurrentDoctorId() {
            const userData = localStorage.getItem('userData');
            if (userData) {
                try {
                    const user = JSON.parse(userData);
                    return user.user_id || 'temp_doctor_default';
                } catch (e) {
                    console.error('解析用户数据失败:', e);
                }
            }
            return 'temp_doctor_default';
        }

        // 绑定历史记录按钮事件
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                const viewHistoryBtn = document.getElementById('viewHistoryBtn');
                if (viewHistoryBtn) {
                    viewHistoryBtn.addEventListener('click', viewHistoryTrees);
                    console.log('✅ 历史决策树按钮事件已绑定');
                }
            }, 500);
        });

'''

# 找到最后一个</script>标签位置
last_script_pos = content.rfind('</script>')
if last_script_pos != -1:
    content = content[:last_script_pos] + history_js + content[last_script_pos:]

# 10. 保存文件
print("\n💾 保存修改后的文件...")
write_file('/opt/tcm-ai/static/decision_tree_visual_builder.html', content)

print("\n✅ 修改完成！\n")
print("修改内容：")
print("  ❌ 移除了: 智能分支生成")
print("  ❌ 移除了: 智能处方提取")
print("  ❌ 移除了: 方剂AI分析")
print("  ❌ 移除了: 右侧分析面板")
print("  ✅ 保留了: AI智能生成决策树")
print("  ✅ 保留了: 保存到思维库")
print("  ➕ 新增了: 查看历史决策树")

