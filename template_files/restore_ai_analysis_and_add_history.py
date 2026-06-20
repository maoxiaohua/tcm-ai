#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策树构建器功能调整脚本
1. 恢复AI分析决策树功能（方剂AI分析）
2. 移除成人/儿童剂量相关内容
3. 添加历史决策树查看和管理功能
"""

import re
import sys

def read_file(file_path):
    """读取文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path, content):
    """写入文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def restore_ai_formula_analysis(content):
    """恢复方剂AI分析功能"""

    # 1. 在按钮区域添加"方剂AI分析"按钮（在"保存到思维库"按钮后面）
    button_pattern = r'(<button class="btn btn-primary" id="saveToLibraryBtn".*?</button>)'

    ai_analysis_button = '''<button class="btn btn-primary" id="saveToLibraryBtn" style="background: #7c3aed;">💾 保存到思维库</button>
                <button class="btn btn-primary" id="formulaAnalyzeBtn" style="background: #a855f7; margin-top: 10px;">💊 方剂AI分析</button>'''

    content = re.sub(
        r'<button class="btn btn-primary" id="saveToLibraryBtn"[^>]*>💾 保存到思维库</button>',
        ai_analysis_button,
        content
    )

    # 2. 添加方剂AI分析的JavaScript函数（在文件末尾，</script>之前）
    ai_analysis_functions = '''
        // ======================== 方剂AI分析功能 ========================

        async function analyzeFormula() {
            console.log('方剂AI分析被调用');

            const formulaNodes = nodes.filter(node => node.type === 'formula');
            if (formulaNodes.length === 0) {
                alert('请先添加方剂节点');
                return;
            }

            const diseaseName = document.getElementById('diseaseName')?.value;
            if (!diseaseName) {
                alert('请先输入疾病名称');
                return;
            }

            showLoading('正在进行AI方剂分析...');

            try {
                const response = await fetch('/api/extract_prescription_info', {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        thinking_process: document.getElementById('doctorThought')?.value || '',
                        formulas: formulaNodes.map(node => ({
                            name: node.name,
                            description: node.description
                        })),
                        patient_symptoms: nodes.filter(n => n.type === 'symptom').map(n => n.name)
                    })
                });

                const data = await response.json();
                hideLoading();

                if (data.success) {
                    showFormulaAnalysisResult(data.data || {});
                } else {
                    showResult('提示', '暂无AI分析结果，请检查网络连接或稍后再试', 'warning');
                }
            } catch (error) {
                console.error('方剂分析失败:', error);
                hideLoading();
                showResult('错误', `方剂分析失败: ${error.message}`, 'error');
            }
        }

        function showFormulaAnalysisResult(data) {
            const resultsDiv = document.getElementById('analysisResults') || createResultsPanel();
            resultsDiv.innerHTML = '';

            const resultElement = document.createElement('div');
            resultElement.className = 'result-panel';

            let html = '<div class="result-title">💊 方剂AI分析结果</div>';

            if (data.disease_name) {
                html += `<div style="margin: 10px 0;"><strong>病种:</strong> ${data.disease_name}</div>`;
            }

            if (data.syndrome_differentiation) {
                html += `<div style="margin: 10px 0;"><strong>证型:</strong> ${data.syndrome_differentiation}</div>`;
            }

            if (data.treatment_principle) {
                html += `<div style="margin: 10px 0;"><strong>治法:</strong> ${data.treatment_principle}</div>`;
            }

            if (data.base_prescription && data.base_prescription.composition) {
                html += `<div style="margin-top: 15px;"><strong>方剂组成:</strong></div>`;
                html += '<div style="background: #f9fafb; padding: 10px; border-radius: 5px; margin-top: 5px;">';

                data.base_prescription.composition.forEach(herb => {
                    html += `<div style="margin: 5px 0;">
                        <span style="color: #059669; font-weight: bold;">${herb.herb_name}</span>:
                        ${herb.current_dose || herb.standard_dose}
                        <span style="color: #6b7280; font-size: 12px;">${herb.function || ''}</span>
                    </div>`;
                });

                html += '</div>';
            }

            if (data.administration) {
                html += `<div style="margin-top: 15px; padding: 10px; background: #fef3c7; border-radius: 5px;">`;
                html += `<strong>用法:</strong> ${data.administration.dosage || ''}<br>`;
                html += `<strong>煎服:</strong> ${data.administration.preparation || ''}`;
                html += `</div>`;
            }

            resultElement.innerHTML = html;
            resultsDiv.appendChild(resultElement);
        }

        function createResultsPanel() {
            let panel = document.getElementById('analysisResults');
            if (!panel) {
                panel = document.createElement('div');
                panel.id = 'analysisResults';
                panel.style.cssText = 'margin-top: 20px; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px;';
                document.querySelector('.left-panel').appendChild(panel);
            }
            return panel;
        }

        // 添加事件监听器
        document.addEventListener('DOMContentLoaded', function() {
            const formulaBtn = document.getElementById('formulaAnalyzeBtn');
            if (formulaBtn) {
                formulaBtn.addEventListener('click', analyzeFormula);
                console.log('✅ 方剂AI分析按钮事件已绑定');
            }
        });

'''

    # 在</script>标签前插入函数
    content = content.replace('</script>', ai_analysis_functions + '\n</script>')

    return content

def remove_dosage_related_content(content):
    """移除成人剂量、儿童剂量相关内容"""

    # 1. 移除HTML中的年龄分支UI
    patterns_to_remove = [
        # 智能年龄分支生成面板
        r'<!-- 🆕 智能分支生成 -->.*?</div>\s*</div>',

        # 成人剂量、儿童剂量输入框
        r'<div class="age-branch-inputs">.*?</div>\s*</div>',

        # 年龄分支开关
        r'<label for="enableSmartBranching".*?</label>',
        r'<input type="checkbox" id="enableSmartBranching".*?>',

        # 年龄分支相关CSS
        r'/\* 🎯 智能年龄分支样式 \*/.*?}',
    ]

    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    # 2. 移除JavaScript中的剂量调整逻辑
    js_removals = [
        r'enable_smart_branching:\s*.*?,',
        r'enableSmartBranching.*?\n',
        r'// 智能年龄分支.*?\n',
        r'剂量.*?成人.*?\n',
        r'儿童剂量.*?\n',
    ]

    for pattern in js_removals:
        content = re.sub(pattern, '', content)

    return content

def add_history_management_panel(content):
    """添加历史决策树查看和管理面板"""

    # 在侧边栏添加"历史决策树"按钮（在"保存到思维库"后面）
    history_button = '''
                <button class="btn btn-secondary" id="viewHistoryBtn" style="background: #6b7280; margin-top: 10px;">📋 查看历史决策树</button>
'''

    content = re.sub(
        r'(<button class="btn btn-primary" id="formulaAnalyzeBtn".*?</button>)',
        r'\1' + history_button,
        content
    )

    # 添加历史记录模态框HTML（在body结束前）
    history_modal_html = '''
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

    content = content.replace('</body>', history_modal_html + '\n</body>')

    # 添加历史记录管理的JavaScript函数
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
                // 获取当前医生ID
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

                            // 重新绘制
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

            try {
                // TODO: 实现删除API
                showResult('提示', '删除功能开发中...', 'info');
            } catch (error) {
                console.error('删除失败:', error);
                showResult('错误', `删除失败: ${error.message}`, 'error');
            }
        }

        function closeHistoryModal() {
            document.getElementById('historyModal').style.display = 'none';
        }

        function getCurrentDoctorId() {
            // 从localStorage获取医生ID，如果没有则使用默认值
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

        // 绑定事件
        document.addEventListener('DOMContentLoaded', function() {
            const viewHistoryBtn = document.getElementById('viewHistoryBtn');
            if (viewHistoryBtn) {
                viewHistoryBtn.addEventListener('click', viewHistoryTrees);
                console.log('✅ 历史决策树按钮事件已绑定');
            }
        });

'''

    content = content.replace('</script>', history_js + '\n</script>')

    return content

def main():
    # 读取当前文件
    file_path = '/opt/tcm-ai/static/decision_tree_visual_builder.html'

    print("📖 读取决策树构建器文件...")
    content = read_file(file_path)

    print("✅ 恢复AI分析决策树功能...")
    content = restore_ai_formula_analysis(content)

    print("❌ 移除成人/儿童剂量相关内容...")
    content = remove_dosage_related_content(content)

    print("➕ 添加历史决策树管理功能...")
    content = add_history_management_panel(content)

    print("💾 保存修改后的文件...")
    write_file(file_path, content)

    print("✅ 所有修改完成！")
    print("\n修改内容：")
    print("  1. ✅ 恢复了 方剂AI分析 功能")
    print("  2. ❌ 移除了 成人/儿童剂量 相关内容")
    print("  3. ➕ 新增了 历史决策树查看和管理 功能")

    return 0

if __name__ == '__main__':
    sys.exit(main())
