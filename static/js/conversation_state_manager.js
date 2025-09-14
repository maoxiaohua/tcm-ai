/**
 * TCM-AI 对话状态管理系统
 * 实现智能问诊的状态控制和流程管理
 */

class ConversationStateManager {
    constructor() {
        // 对话状态枚举
        this.STATES = {
            INITIAL_INQUIRY: 'initial_inquiry',        // 初始问诊
            DETAILED_INQUIRY: 'detailed_inquiry',      // 详细问诊
            INTERIM_ADVICE: 'interim_advice',          // 临时建议
            DIAGNOSIS: 'diagnosis',                    // 诊断阶段
            PRESCRIPTION: 'prescription',              // 处方阶段
            PRESCRIPTION_CONFIRM: 'prescription_confirm', // 处方确认
            COMPLETED: 'completed'                     // 已完成
        };

        // 当前状态
        this.currentState = this.STATES.INITIAL_INQUIRY;
        this.stateHistory = [];
        this.conversationData = {
            symptoms: [],
            diagnosis: null,
            prescription: null,
            patientConfirmations: []
        };

        // 超时配置
        this.timeouts = {
            responseWarning: 5 * 60 * 1000,    // 5分钟响应提醒
            sessionTimeout: 30 * 60 * 1000,    // 30分钟会话超时
            prescriptionExpiry: 24 * 60 * 60 * 1000 // 24小时处方过期
        };

        this.timers = {};
        this.startTime = Date.now();
        
        // 绑定方法
        this.setState = this.setState.bind(this);
        this.analyzeMessage = this.analyzeMessage.bind(this);
        this.handleTimeout = this.handleTimeout.bind(this);
    }

    /**
     * 设置对话状态
     */
    setState(newState, reason = '') {
        const oldState = this.currentState;
        
        if (this.isValidTransition(oldState, newState)) {
            this.currentState = newState;
            this.stateHistory.push({
                from: oldState,
                to: newState,
                timestamp: Date.now(),
                reason: reason
            });

            console.log(`🔄 对话状态变更: ${oldState} → ${newState} (${reason})`);
            
            // 触发状态变更事件
            this.onStateChange(newState, oldState);
            
            // 保存状态到本地存储
            this.saveState();
            
            // 重置超时计时器
            this.resetTimeouts();
            
            return true;
        } else {
            console.warn(`❌ 无效状态转换: ${oldState} → ${newState}`);
            return false;
        }
    }

    /**
     * 验证状态转换是否有效
     */
    isValidTransition(fromState, toState) {
        const validTransitions = {
            [this.STATES.INITIAL_INQUIRY]: [
                this.STATES.DETAILED_INQUIRY,
                this.STATES.INTERIM_ADVICE,
                this.STATES.COMPLETED
            ],
            [this.STATES.DETAILED_INQUIRY]: [
                this.STATES.INTERIM_ADVICE,
                this.STATES.DIAGNOSIS,
                this.STATES.PRESCRIPTION,
                this.STATES.COMPLETED
            ],
            [this.STATES.INTERIM_ADVICE]: [
                this.STATES.DETAILED_INQUIRY,
                this.STATES.DIAGNOSIS,
                this.STATES.PRESCRIPTION,
                this.STATES.COMPLETED
            ],
            [this.STATES.DIAGNOSIS]: [
                this.STATES.INTERIM_ADVICE,
                this.STATES.PRESCRIPTION,
                this.STATES.COMPLETED
            ],
            [this.STATES.PRESCRIPTION]: [
                this.STATES.PRESCRIPTION_CONFIRM,
                this.STATES.INTERIM_ADVICE, // 患者要求修改
                this.STATES.COMPLETED
            ],
            [this.STATES.PRESCRIPTION_CONFIRM]: [
                this.STATES.COMPLETED,
                this.STATES.PRESCRIPTION // 重新修改处方
            ],
            [this.STATES.COMPLETED]: [] // 终态
        };

        return validTransitions[fromState]?.includes(toState) || false;
    }

    /**
     * 分析消息并确定下一步状态
     */
    analyzeMessage(message, isAI = false) {
        const analysis = {
            currentState: this.currentState,
            suggestedNextState: null,
            containsPrescription: false,
            isEndingMessage: false,
            needsMoreInfo: false
        };

        if (isAI) {
            // AI消息分析
            analysis.containsPrescription = this.detectPrescription(message);
            analysis.isInterimAdvice = this.detectInterimAdvice(message);
            
            if (analysis.containsPrescription) {
                analysis.suggestedNextState = this.STATES.PRESCRIPTION;
            } else if (analysis.isInterimAdvice) {
                analysis.suggestedNextState = this.STATES.INTERIM_ADVICE;
            } else {
                analysis.suggestedNextState = this.STATES.DETAILED_INQUIRY;
            }
        } else {
            // 用户消息分析
            analysis.isEndingMessage = this.detectEndingIntent(message);
            analysis.isConfirmation = this.detectConfirmation(message);
            
            if (analysis.isEndingMessage) {
                analysis.suggestedNextState = this.STATES.COMPLETED;
            } else if (analysis.isConfirmation && this.currentState === this.STATES.PRESCRIPTION) {
                analysis.suggestedNextState = this.STATES.PRESCRIPTION_CONFIRM;
            } else if (this.currentState === this.STATES.INITIAL_INQUIRY) {
                analysis.suggestedNextState = this.STATES.DETAILED_INQUIRY;
            }
        }

        return analysis;
    }

    /**
     * 检测是否包含处方
     */
    detectPrescription(message) {
        const prescriptionKeywords = [
            '处方如下', '方剂组成', '药物组成', '具体方药',
            '方解', '君药', '臣药', '佐药', '使药',
            '【君药】', '【臣药】', '【佐药】', '【使药】',
            '三、处方建议', '处方方案', '治疗方案', '用药方案'
        ];

        const hasDosage = /\d+[克g]\s*[，,，]/.test(message);
        const hasKeywords = prescriptionKeywords.some(keyword => message.includes(keyword));
        
        return hasKeywords && hasDosage;
    }

    /**
     * 检测是否为临时建议
     */
    detectInterimAdvice(message) {
        const temporaryKeywords = [
            '初步处方建议', '待确认', '若您能提供', '请补充', 
            '需要了解', '建议进一步', '完善信息后', '详细描述',
            '暂拟方药', '初步考虑', '待详诊后', '待补充',
            '补充舌象', '舌象信息后', '脉象信息后', '上传舌象',
            '提供舌象', '确认处方', '后确认', '暂拟处方'
        ];
        
        return temporaryKeywords.some(keyword => message.includes(keyword));
    }

    /**
     * 检测用户的结束意图
     */
    detectEndingIntent(message) {
        const endingKeywords = [
            '谢谢', '没有其他问题', '就这样吧', '我了解了',
            '结束问诊', '暂时这样', '先这样', '已经够了'
        ];
        
        return endingKeywords.some(keyword => message.includes(keyword));
    }

    /**
     * 检测用户确认
     */
    detectConfirmation(message) {
        const confirmKeywords = [
            '确认', '同意', '接受', '好的', '可以', '没问题'
        ];
        
        return confirmKeywords.some(keyword => message.includes(keyword));
    }

    /**
     * 状态变更回调
     */
    onStateChange(newState, oldState) {
        // 更新UI状态指示器
        this.updateStateIndicator(newState);
        
        // 根据新状态执行特定操作
        switch (newState) {
            case this.STATES.PRESCRIPTION:
                this.showPrescriptionActions();
                break;
            case this.STATES.PRESCRIPTION_CONFIRM:
                this.showConfirmationPrompt();
                break;
            case this.STATES.COMPLETED:
                this.handleConversationEnd();
                break;
        }
        
        // 发送状态更新到服务器
        this.syncStateToServer();
    }

    /**
     * 更新状态指示器UI
     */
    updateStateIndicator(state) {
        const indicator = document.getElementById('conversationStateIndicator');
        if (!indicator) return;

        const stateLabels = {
            [this.STATES.INITIAL_INQUIRY]: '初始问诊',
            [this.STATES.DETAILED_INQUIRY]: '详细了解',
            [this.STATES.INTERIM_ADVICE]: '初步建议',
            [this.STATES.DIAGNOSIS]: '诊断分析',
            [this.STATES.PRESCRIPTION]: '处方建议',
            [this.STATES.PRESCRIPTION_CONFIRM]: '确认处方',
            [this.STATES.COMPLETED]: '问诊完成'
        };

        indicator.innerHTML = `
            <div class="state-indicator">
                <span class="state-icon">🔄</span>
                <span class="state-label">${stateLabels[state] || state}</span>
            </div>
        `;
    }

    /**
     * 显示处方操作选项
     */
    showPrescriptionActions() {
        // 这里会被addMessage函数调用时处理
        console.log('🔄 进入处方阶段，显示确认选项');
    }

    /**
     * 显示确认提示
     */
    showConfirmationPrompt() {
        const confirmModal = document.createElement('div');
        confirmModal.className = 'confirmation-modal';
        confirmModal.innerHTML = `
            <div class="modal-content">
                <h3>处方确认</h3>
                <p>请确认是否接受此处方建议：</p>
                <div class="confirmation-buttons">
                    <button onclick="conversationStateManager.confirmPrescription()" class="confirm-btn">
                        确认并支付
                    </button>
                    <button onclick="conversationStateManager.continueConsultation()" class="continue-btn">
                        继续问诊
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(confirmModal);
    }

    /**
     * 处理对话结束
     */
    handleConversationEnd() {
        console.log('🏁 对话结束');
        this.clearTimeouts();
        this.saveConversationSummary();
    }

    /**
     * 重置超时计时器
     */
    resetTimeouts() {
        this.clearTimeouts();
        
        // 设置响应提醒
        this.timers.responseWarning = setTimeout(() => {
            this.showResponseWarning();
        }, this.timeouts.responseWarning);

        // 设置会话超时
        this.timers.sessionTimeout = setTimeout(() => {
            this.handleTimeout('session');
        }, this.timeouts.sessionTimeout);
    }

    /**
     * 清除所有计时器
     */
    clearTimeouts() {
        Object.values(this.timers).forEach(timer => {
            if (timer) clearTimeout(timer);
        });
        this.timers = {};
    }

    /**
     * 显示响应提醒
     */
    showResponseWarning() {
        console.log('⏰ 5分钟无响应提醒');
        // 可以在这里添加UI提醒
    }

    /**
     * 处理超时
     */
    handleTimeout(type) {
        console.log(`⏰ 对话超时: ${type}`);
        
        if (type === 'session') {
            this.setState(this.STATES.COMPLETED, '会话超时');
        }
    }

    /**
     * 保存状态到本地存储
     */
    saveState() {
        const userId = this.getCurrentUserId();
        const selectedDoctor = window.selectedDoctor;
        
        if (!userId || !selectedDoctor) return;

        const stateData = {
            currentState: this.currentState,
            stateHistory: this.stateHistory,
            conversationData: this.conversationData,
            startTime: this.startTime,
            lastUpdated: Date.now()
        };

        const key = `conversation_state_${userId}_${selectedDoctor}`;
        localStorage.setItem(key, JSON.stringify(stateData));
    }

    /**
     * 从本地存储加载状态
     */
    loadState() {
        const userId = this.getCurrentUserId();
        const selectedDoctor = window.selectedDoctor;
        
        if (!userId || !selectedDoctor) return;

        const key = `conversation_state_${userId}_${selectedDoctor}`;
        const saved = localStorage.getItem(key);
        
        if (saved) {
            try {
                const stateData = JSON.parse(saved);
                this.currentState = stateData.currentState;
                this.stateHistory = stateData.stateHistory || [];
                this.conversationData = stateData.conversationData || {};
                this.startTime = stateData.startTime || Date.now();
                
                console.log(`📂 已加载对话状态: ${this.currentState}`);
                this.onStateChange(this.currentState, null);
            } catch (error) {
                console.error('状态加载失败:', error);
            }
        }
    }

    /**
     * 同步状态到服务器
     */
    async syncStateToServer() {
        // 这里可以实现状态同步到后端
        console.log('🔄 同步状态到服务器:', this.currentState);
    }

    /**
     * 确认处方
     */
    confirmPrescription() {
        this.setState(this.STATES.PRESCRIPTION_CONFIRM, '用户确认处方');
        document.querySelector('.confirmation-modal')?.remove();
        
        // 触发支付流程
        if (typeof confirmPrescription === 'function') {
            // 获取最新的处方内容
            const lastPrescription = this.getLastPrescriptionMessage();
            if (lastPrescription) {
                confirmPrescription(btoa(encodeURIComponent(lastPrescription)));
            }
        }
    }

    /**
     * 继续问诊
     */
    continueConsultation() {
        this.setState(this.STATES.DETAILED_INQUIRY, '用户选择继续问诊');
        document.querySelector('.confirmation-modal')?.remove();
    }

    /**
     * 获取最后一条处方消息
     */
    getLastPrescriptionMessage() {
        const messages = document.querySelectorAll('.message.ai .message-text');
        for (let i = messages.length - 1; i >= 0; i--) {
            const content = messages[i].textContent;
            if (this.detectPrescription(content)) {
                return content;
            }
        }
        return null;
    }

    /**
     * 保存对话摘要
     */
    saveConversationSummary() {
        const summary = {
            duration: Date.now() - this.startTime,
            finalState: this.currentState,
            stateTransitions: this.stateHistory.length,
            completedAt: Date.now()
        };

        console.log('📊 对话摘要:', summary);
    }

    /**
     * 获取当前用户ID - 兼容主页面的getCurrentUserId函数
     */
    getCurrentUserId() {
        // 尝试使用全局函数
        if (typeof window.getCurrentUserId === 'function') {
            return window.getCurrentUserId();
        }

        // 备用方案：直接从localStorage获取
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        if (currentUser.id || currentUser.user_id) {
            return currentUser.id || currentUser.user_id;
        }

        const smartUser = localStorage.getItem('currentUserId');
        if (smartUser) {
            return smartUser;
        }

        // 生成临时ID
        const tempId = 'temp_user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('currentUserId', tempId);
        return tempId;
    }

    /**
     * 获取当前状态信息
     */
    getStateInfo() {
        return {
            current: this.currentState,
            duration: Date.now() - this.startTime,
            transitions: this.stateHistory.length,
            isCompleted: this.currentState === this.STATES.COMPLETED
        };
    }
}

// 创建全局实例
window.conversationStateManager = new ConversationStateManager();

// 延迟初始化，确保主页面JavaScript已加载
function initializeConversationStateManager() {
    if (window.conversationStateManager) {
        window.conversationStateManager.loadState();
        console.log('✅ 对话状态管理器已初始化');
    }
}

// 页面加载完成后延迟初始化
document.addEventListener('DOMContentLoaded', function() {
    // 延迟1秒确保其他JavaScript已加载
    setTimeout(initializeConversationStateManager, 1000);
});

// 如果页面已经加载完成，立即初始化
if (document.readyState === 'complete') {
    setTimeout(initializeConversationStateManager, 100);
}