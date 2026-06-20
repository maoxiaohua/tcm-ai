/**
 * 决策树数据驱动模块 v3.0
 *
 * 功能：
 * 1. 左侧文本编辑器自动保存和同步
 * 2. 右侧画布节点监听和同步
 * 3. AI生成功能集成
 * 4. 数据加载和初始化
 * 5. UI状态指示器和错误处理
 *
 * 日期：2025-10-31
 */

class DecisionTreeDataDriven {
    constructor() {
        // API基础URL
        this.API_BASE = '/api/decision-tree-data';

        // 当前决策数据
        this.currentDecisionId = null;
        this.currentDoctorId = null;
        this.isSyncing = false;

        // 防抖定时器
        this.textSaveTimeout = null;
        this.canvasSaveTimeout = null;

        // 状态标志
        this.isTextEditorInitialized = false;
        this.isCanvasInitialized = false;

        // UI元素
        this.textEditor = null;
        this.saveStatusIndicator = null;

        console.log('✅ DecisionTreeDataDriven初始化完成');
    }

    /**
     * 初始化数据驱动功能
     */
    async init() {
        try {
            // 获取当前医生ID
            this.currentDoctorId = this.getCurrentDoctorId();

            if (!this.currentDoctorId) {
                console.warn('⚠️ 未获取到医生ID，部分功能可能受限');
                this.currentDoctorId = 'zhang_zhongjing'; // 默认值
            }

            // 初始化UI元素
            this.initUIElements();

            // 初始化左侧文本编辑器
            this.initTextEditor();

            // 初始化右侧画布监听
            this.initCanvasMonitoring();

            // 初始化AI生成功能
            this.initAIGeneration();

            // 添加保存状态指示器
            this.addSaveStatusIndicator();

            console.log('✅ 数据驱动功能初始化完成');

        } catch (error) {
            console.error('❌ 数据驱动功能初始化失败:', error);
            this.showError('初始化失败：' + error.message);
        }
    }

    /**
     * 初始化UI元素
     */
    initUIElements() {
        // 左侧文本编辑区域
        this.textEditor = document.getElementById('doctorThought');

        if (!this.textEditor) {
            console.warn('⚠️ 未找到文本编辑器元素 #doctorThought');
            // 尝试创建一个
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                const textareaDiv = document.createElement('div');
                textareaDiv.className = 'form-group';
                textareaDiv.innerHTML = `
                    <label class="form-label">📝 诊疗思路（自动同步）</label>
                    <textarea class="form-input form-textarea" id="doctorThought"
                              placeholder="请按以下格式输入：&#10;【疾病】疾病名称&#10;【主症】主要症状&#10;【兼症】次要症状&#10;【舌象】舌象描述&#10;【脉象】脉象描述&#10;【证候】证候名称&#10;【处方】处方名称&#10;【方剂】方剂组成"
                              rows="15"></textarea>
                `;
                sidebar.insertBefore(textareaDiv, sidebar.querySelector('.btn-group'));
                this.textEditor = document.getElementById('doctorThought');
            }
        }
    }

    /**
     * 获取当前医生ID
     */
    getCurrentDoctorId() {
        // 从localStorage获取
        const userData = localStorage.getItem('userData');
        if (userData) {
            try {
                const user = JSON.parse(userData);
                return user.username || user.id || user.doctor_id;
            } catch (e) {
                console.error('解析用户数据失败:', e);
            }
        }

        // 从URL参数获取
        const urlParams = new URLSearchParams(window.location.search);
        const doctorId = urlParams.get('doctor_id');
        if (doctorId) return doctorId;

        return null;
    }

    /**
     * 初始化左侧文本编辑器
     */
    initTextEditor() {
        if (!this.textEditor) {
            console.warn('⚠️ 文本编辑器未找到，跳过初始化');
            return;
        }

        // 监听输入事件
        this.textEditor.addEventListener('input', () => {
            this.onTextChanged();
        });

        // 监听粘贴事件
        this.textEditor.addEventListener('paste', () => {
            setTimeout(() => this.onTextChanged(), 100);
        });

        this.isTextEditorInitialized = true;
        console.log('✅ 文本编辑器监听已启动');
    }

    /**
     * 文本变化处理
     */
    onTextChanged() {
        // 显示保存中状态
        this.updateSaveStatus('editing');

        // 清除之前的定时器
        clearTimeout(this.textSaveTimeout);

        // 500ms防抖
        this.textSaveTimeout = setTimeout(() => {
            this.saveFromText();
        }, 500);
    }

    /**
     * 从文本保存并同步到画布
     */
    async saveFromText() {
        if (this.isSyncing) {
            console.log('⏳ 正在同步中，跳过本次保存');
            return;
        }

        const textContent = this.textEditor.value.trim();

        if (!textContent) {
            console.log('📝 文本为空，跳过保存');
            this.updateSaveStatus('empty');
            return;
        }

        try {
            this.isSyncing = true;
            this.updateSaveStatus('saving');

            console.log('💾 开始保存文本数据...');

            const response = await fetch(`${this.API_BASE}/save-from-text`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text_content: textContent,
                    doctor_id: this.currentDoctorId,
                    decision_id: this.currentDecisionId
                })
            });

            const result = await response.json();

            if (result.success) {
                console.log('✅ 文本保存成功:', result.message);

                // 更新当前决策ID
                if (result.data && result.data.id) {
                    this.currentDecisionId = result.data.id;
                }

                // 刷新右侧画布
                if (result.data && result.data.tree_structure) {
                    this.updateCanvas(result.data.tree_structure);
                }

                this.updateSaveStatus('saved');

            } else {
                throw new Error(result.message || '保存失败');
            }

        } catch (error) {
            console.error('❌ 保存文本失败:', error);
            this.updateSaveStatus('error');
            this.showError('保存失败：' + error.message);
        } finally {
            this.isSyncing = false;
        }
    }

    /**
     * 更新画布显示
     */
    updateCanvas(treeStructure) {
        try {
            console.log('🎨 更新画布...', treeStructure);

            // 清空现有节点
            if (typeof window.nodes !== 'undefined') {
                window.nodes = [];
            }
            if (typeof window.connections !== 'undefined') {
                window.connections = [];
            }

            // 添加新节点
            if (treeStructure && treeStructure.nodes) {
                treeStructure.nodes.forEach(node => {
                    if (typeof window.addNode === 'function') {
                        // 使用页面已有的addNode函数
                        const newNode = {
                            id: node.id || `node_${Date.now()}_${Math.random()}`,
                            type: node.type || 'info',
                            content: node.label || node.content || '',
                            description: node.data ? JSON.stringify(node.data) : '',
                            x: node.x || 100,
                            y: node.y || 100
                        };
                        window.nodes.push(newNode);
                    }
                });
            }

            // 添加连接
            if (treeStructure && treeStructure.connections) {
                treeStructure.connections.forEach(conn => {
                    if (window.connections) {
                        window.connections.push({
                            from: conn.from,
                            to: conn.to,
                            type: conn.type || 'default'
                        });
                    }
                });
            }

            // 重绘画布
            if (typeof window.render === 'function') {
                window.render();
            } else if (typeof window.renderCanvas === 'function') {
                window.renderCanvas();
            }

            // 隐藏空状态提示
            const emptyHint = document.getElementById('emptyHint');
            if (emptyHint) {
                emptyHint.style.display = 'none';
            }

            // 显示工具栏
            const toolbar = document.getElementById('canvasToolbar');
            if (toolbar && window.nodes && window.nodes.length > 0) {
                toolbar.style.display = 'flex';
            }

            console.log('✅ 画布更新完成');

        } catch (error) {
            console.error('❌ 更新画布失败:', error);
        }
    }

    /**
     * 初始化画布监听
     */
    initCanvasMonitoring() {
        // 监听节点变化
        const originalAddNode = window.addNode;
        if (typeof originalAddNode === 'function') {
            window.addNode = (...args) => {
                const result = originalAddNode.apply(window, args);
                this.onCanvasChanged();
                return result;
            };
        }

        // 监听节点移动
        const canvas = document.getElementById('canvas');
        if (canvas) {
            canvas.addEventListener('mouseup', () => {
                if (window.isDragging) {
                    this.onCanvasChanged();
                }
            });
        }

        // 监听节点编辑
        const originalUpdateNode = window.updateNodeFromEditPanel;
        if (typeof originalUpdateNode === 'function') {
            window.updateNodeFromEditPanel = (...args) => {
                const result = originalUpdateNode.apply(window, args);
                this.onCanvasChanged();
                return result;
            };
        }

        this.isCanvasInitialized = true;
        console.log('✅ 画布监听已启动');
    }

    /**
     * 画布变化处理
     */
    onCanvasChanged() {
        // 显示保存中状态
        this.updateSaveStatus('editing');

        // 清除之前的定时器
        clearTimeout(this.canvasSaveTimeout);

        // 500ms防抖
        this.canvasSaveTimeout = setTimeout(() => {
            this.saveFromCanvas();
        }, 500);
    }

    /**
     * 从画布保存并同步到文本
     */
    async saveFromCanvas() {
        if (this.isSyncing) {
            console.log('⏳ 正在同步中，跳过本次保存');
            return;
        }

        if (!window.nodes || window.nodes.length === 0) {
            console.log('🎨 画布为空，跳过保存');
            return;
        }

        try {
            this.isSyncing = true;
            this.updateSaveStatus('saving');

            console.log('💾 开始保存画布数据...');

            // 提取树形结构
            const treeStructure = {
                nodes: window.nodes.map(node => ({
                    id: node.id,
                    type: node.type,
                    label: node.content,
                    data: node.data || {},
                    x: node.x,
                    y: node.y
                })),
                connections: (window.connections || []).map(conn => ({
                    from: conn.from,
                    to: conn.to,
                    type: conn.type || 'default'
                }))
            };

            const response = await fetch(`${this.API_BASE}/save-from-canvas`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tree_structure: treeStructure,
                    doctor_id: this.currentDoctorId,
                    decision_id: this.currentDecisionId
                })
            });

            const result = await response.json();

            if (result.success) {
                console.log('✅ 画布保存成功:', result.message);

                // 更新当前决策ID
                if (result.data && result.data.id) {
                    this.currentDecisionId = result.data.id;
                }

                // 刷新左侧文本（暂时禁用，避免光标跳动）
                // if (result.data && result.data.text_format && this.textEditor) {
                //     this.textEditor.value = result.data.text_format;
                // }

                this.updateSaveStatus('saved');

            } else {
                throw new Error(result.message || '保存失败');
            }

        } catch (error) {
            console.error('❌ 保存画布失败:', error);
            this.updateSaveStatus('error');
            this.showError('保存失败：' + error.message);
        } finally {
            this.isSyncing = false;
        }
    }

    /**
     * 初始化AI生成功能
     */
    initAIGeneration() {
        const generateBtn = document.getElementById('generateBtn');
        if (!generateBtn) {
            console.warn('⚠️ 未找到生成按钮');
            return;
        }

        // 保存原有的点击事件
        const originalOnClick = generateBtn.onclick;

        // 替换为新的AI生成功能
        generateBtn.onclick = async () => {
            await this.generateFromAI();
        };

        console.log('✅ AI生成功能已替换');
    }

    /**
     * AI生成决策树
     */
    async generateFromAI() {
        const diseaseNameInput = document.getElementById('diseaseName');
        const doctorThoughtInput = document.getElementById('doctorThought');

        let naturalLanguage = '';

        // 构建自然语言输入
        if (diseaseNameInput && diseaseNameInput.value.trim()) {
            naturalLanguage += `疾病：${diseaseNameInput.value.trim()}\n`;
        }

        if (doctorThoughtInput && doctorThoughtInput.value.trim()) {
            naturalLanguage += doctorThoughtInput.value.trim();
        }

        if (!naturalLanguage.trim()) {
            this.showError('请输入疾病名称或诊疗思路');
            return;
        }

        try {
            this.updateSaveStatus('generating');
            console.log('🤖 开始AI生成...', naturalLanguage);

            const response = await fetch(`${this.API_BASE}/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    natural_language: naturalLanguage,
                    doctor_id: this.currentDoctorId
                })
            });

            const result = await response.json();

            if (result.success && result.data) {
                console.log('✅ AI生成成功');

                // 更新文本编辑器
                if (result.data.text_format && this.textEditor) {
                    this.textEditor.value = result.data.text_format;
                }

                // 更新画布
                if (result.data.tree_structure) {
                    this.updateCanvas(result.data.tree_structure);
                }

                // 如果有structured_content，保存到数据库
                if (result.data.structured_content) {
                    this.currentDecisionId = null; // 强制创建新记录
                    await this.saveFromText();
                }

                this.updateSaveStatus('saved');
                this.showSuccess('AI生成成功！');

            } else {
                throw new Error(result.message || 'AI生成失败');
            }

        } catch (error) {
            console.error('❌ AI生成失败:', error);
            this.updateSaveStatus('error');
            this.showError('AI生成失败：' + error.message);
        }
    }

    /**
     * 加载决策数据
     */
    async loadDecision(decisionId) {
        try {
            console.log('📥 加载决策数据:', decisionId);

            const response = await fetch(
                `${this.API_BASE}/${decisionId}?doctor_id=${this.currentDoctorId}`
            );

            const result = await response.json();

            if (result.success && result.data) {
                console.log('✅ 决策数据加载成功');

                this.currentDecisionId = result.data.id;

                // 更新文本编辑器
                if (result.data.text_format && this.textEditor) {
                    this.textEditor.value = result.data.text_format;
                }

                // 更新画布
                if (result.data.tree_structure) {
                    this.updateCanvas(result.data.tree_structure);
                }

                // 更新疾病名称
                if (result.data.disease_name) {
                    const diseaseNameInput = document.getElementById('diseaseName');
                    if (diseaseNameInput) {
                        diseaseNameInput.value = result.data.disease_name;
                    }
                }

                this.showSuccess('数据加载成功');

            } else {
                throw new Error(result.message || '加载失败');
            }

        } catch (error) {
            console.error('❌ 加载决策数据失败:', error);
            this.showError('加载失败：' + error.message);
        }
    }

    /**
     * 添加保存状态指示器
     */
    addSaveStatusIndicator() {
        // 检查是否已存在
        if (document.getElementById('dataSyncStatus')) {
            this.saveStatusIndicator = document.getElementById('dataSyncStatus');
            return;
        }

        // 创建状态指示器
        const statusDiv = document.createElement('div');
        statusDiv.id = 'dataSyncStatus';
        statusDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            display: none;
            transition: all 0.3s ease;
        `;

        document.body.appendChild(statusDiv);
        this.saveStatusIndicator = statusDiv;

        console.log('✅ 保存状态指示器已添加');
    }

    /**
     * 更新保存状态
     */
    updateSaveStatus(status) {
        if (!this.saveStatusIndicator) return;

        const statusConfig = {
            'editing': {
                text: '✏️ 编辑中...',
                bg: '#f3f4f6',
                color: '#6b7280',
                display: true
            },
            'saving': {
                text: '💾 保存中...',
                bg: '#dbeafe',
                color: '#1e40af',
                display: true
            },
            'saved': {
                text: '✅ 已保存',
                bg: '#d1fae5',
                color: '#065f46',
                display: true,
                autoHide: 2000
            },
            'generating': {
                text: '🤖 AI生成中...',
                bg: '#fef3c7',
                color: '#92400e',
                display: true
            },
            'error': {
                text: '❌ 保存失败',
                bg: '#fee2e2',
                color: '#991b1b',
                display: true,
                autoHide: 3000
            },
            'empty': {
                text: '',
                display: false
            }
        };

        const config = statusConfig[status] || statusConfig['empty'];

        if (config.display) {
            this.saveStatusIndicator.textContent = config.text;
            this.saveStatusIndicator.style.background = config.bg;
            this.saveStatusIndicator.style.color = config.color;
            this.saveStatusIndicator.style.display = 'block';

            if (config.autoHide) {
                setTimeout(() => {
                    this.saveStatusIndicator.style.display = 'none';
                }, config.autoHide);
            }
        } else {
            this.saveStatusIndicator.style.display = 'none';
        }
    }

    /**
     * 显示成功消息
     */
    showSuccess(message) {
        console.log('✅', message);
        // 可以集成现有的消息提示系统
        if (typeof window.showToast === 'function') {
            window.showToast(message, 'success');
        } else {
            alert(message);
        }
    }

    /**
     * 显示错误消息
     */
    showError(message) {
        console.error('❌', message);
        // 可以集成现有的消息提示系统
        if (typeof window.showToast === 'function') {
            window.showToast(message, 'error');
        } else {
            alert(message);
        }
    }
}

// 创建全局实例
window.decisionTreeDataDriven = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 延迟初始化，确保页面其他脚本加载完成
    setTimeout(function() {
        window.decisionTreeDataDriven = new DecisionTreeDataDriven();
        window.decisionTreeDataDriven.init();
    }, 1000);
});

console.log('📦 决策树数据驱动模块加载完成');
