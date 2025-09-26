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
        
        // 自动同步状态到服务器（有重要状态变更时）
        if (this.shouldAutoSync(newState, oldState)) {
            this.syncStateToServer();
        }
    }
    
    /**
     * 判断是否需要自动同步
     */
    shouldAutoSync(newState, oldState) {
        // 重要状态变更需要立即同步
        const importantStates = [
            this.STATES.PRESCRIPTION,
            this.STATES.PRESCRIPTION_CONFIRM,
            this.STATES.COMPLETED
        ];
        
        return importantStates.includes(newState) || 
               (this.stateHistory.length % 3 === 0); // 每3次状态变更同步一次
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
     * 加载状态 - 支持服务器优先的数据恢复
     */
    async loadState() {
        const userId = this.getCurrentUserId();
        const selectedDoctor = window.selectedDoctor;
        
        if (!userId || !selectedDoctor) return;

        // 先尝试从服务器恢复状态
        const serverState = await this.loadStateFromServer(userId, selectedDoctor);
        
        if (serverState) {
            // 使用服务器数据
            this.applyServerState(serverState);
            return;
        }
        
        // 服务器恢复失败，降级到本地存储
        this.loadStateFromLocal(userId, selectedDoctor);
    }
    
    /**
     * 从服务器加载状态
     */
    async loadStateFromServer(userId, selectedDoctor) {
        if (userId.startsWith('temp_user_') || userId.startsWith('device_')) {
            console.log('📋 临时用户，跳过服务器数据恢复');
            return null;
        }
        
        try {
            console.log('🌐 尝试完整用户数据同步...');
            
            // 首先尝试完整的用户数据同步
            const syncData = await this.performFullUserSync(userId);
            if (syncData && syncData.success) {
                console.log('✅ 用户数据完整同步成功');
                
                // 从同步的数据中提取当前对话状态
                const conversations = syncData.data?.conversations || [];
                const currentConversation = conversations.find(conv => 
                    conv.doctor_id === selectedDoctor && conv.user_id === userId
                );
                
                if (currentConversation) {
                    console.log('📋 找到匹配的对话状态');
                    return {
                        current_stage: currentConversation.current_stage,
                        symptoms_collected: JSON.parse(currentConversation.symptoms_collected || '{}'),
                        stage_history: JSON.parse(currentConversation.stage_history || '[]'),
                        start_time: currentConversation.start_time,
                        conversation_id: currentConversation.conversation_id
                    };
                }
                
                console.log('📋 未找到匹配的对话，但同步了其他数据');
            }
            
            // 如果完整同步失败，回退到原有的API  
            console.log('🔄 回退到单独的对话状态API...');
            const response = await fetch(`/api/conversation/status/${userId}/${selectedDoctor}`);
            if (!response.ok) {
                throw new Error(`服务器响应失败: ${response.status}`);
            }
            
            const result = await response.json();
            if (result.success && result.data) {
                console.log('✅ 从服务器成功恢复对话状态');
                return result.data;
            } else {
                console.log('📋 服务器未找到对话状态');
                return null;
            }
        } catch (error) {
            console.warn('服务器数据恢复失败:', error);
            return null;
        }
    }
    
    /**
     * 应用服务器状态
     */
    applyServerState(serverData) {
        try {
            this.currentState = serverData.current_stage || this.STATES.INITIAL_INQUIRY;
            this.conversationData = serverData.symptoms_collected || {};
            this.stateHistory = serverData.stage_history || [];
            this.startTime = new Date(serverData.start_time).getTime() || Date.now();
            
            console.log(`🌐 已应用服务器状态: ${this.currentState}`);
            this.onStateChange(this.currentState, null);
            
            // 保存到本地作为备份
            this.saveState();
            
            // 显示同步成功提示
            this.showSyncStatus('server_restored', '已从云端恢复对话状态');
            
        } catch (error) {
            console.error('应用服务器状态失败:', error);
            this.loadStateFromLocal();
        }
    }
    
    /**
     * 从本地存储加载状态
     */
    loadStateFromLocal(userId, selectedDoctor) {
        userId = userId || this.getCurrentUserId();
        selectedDoctor = selectedDoctor || window.selectedDoctor;
        
        if (!userId || !selectedDoctor) return;

        const key = `conversation_state_${userId}_${selectedDoctor}`;
        let saved = localStorage.getItem(key);
        
        // 如果找不到当前用户的数据，尝试从备份恢复
        if (!saved) {
            saved = this.tryRestoreFromBackup(userId, selectedDoctor);
        }
        
        if (saved) {
            try {
                const stateData = JSON.parse(saved);
                this.currentState = stateData.currentState;
                this.stateHistory = stateData.stateHistory || [];
                this.conversationData = stateData.conversationData || {};
                this.startTime = stateData.startTime || Date.now();
                
                console.log(`📱 已加载本地对话状态: ${this.currentState}`);
                this.onStateChange(this.currentState, null);
                
                // 保存到正确的key（如果是从备份恢复的）
                localStorage.setItem(key, saved);
                
                // 显示本地恢复提示
                this.showSyncStatus('local_restored', '已从本地恢复对话状态');
                
            } catch (error) {
                console.error('本地状态加载失败:', error);
                this.showSyncStatus('load_failed', '对话状态加载失败');
            }
        } else {
            console.log('🎆 开始新的对话');
            this.showSyncStatus('new_conversation', '开始新的对话');
        }
    }

    /**
     * 尝试从备份恢复数据
     */
    tryRestoreFromBackup(userId, selectedDoctor) {
        console.log('🔍 尝试从备份恢复数据...');
        
        // 1. 尝试从全局备份恢复
        const globalBackup = localStorage.getItem('conversation_backup_global');
        if (globalBackup) {
            try {
                const backupData = JSON.parse(globalBackup);
                const targetKey = `conversation_state_${userId}_${selectedDoctor}`;
                if (backupData[targetKey]) {
                    console.log('📦 从全局备份恢复数据');
                    return backupData[targetKey];
                }
            } catch (error) {
                console.warn('全局备份数据损坏:', error);
            }
        }
        
        // 2. 尝试从其他可能的key恢复
        const possibleKeys = this.findSimilarStateKeys(userId, selectedDoctor);
        for (const possibleKey of possibleKeys) {
            const data = localStorage.getItem(possibleKey);
            if (data) {
                console.log(`📦 从相似key恢复数据: ${possibleKey}`);
                return data;
            }
        }
        
        console.log('❌ 未找到可恢复的备份数据');
        return null;
    }
    
    /**
     * 查找相似的状态存储key
     */
    findSimilarStateKeys(userId, selectedDoctor) {
        const allKeys = Object.keys(localStorage);
        const similarKeys = [];
        
        // 查找同一医生的其他用户ID组合
        const doctorPattern = new RegExp(`conversation_state_.*_${selectedDoctor}`);
        const userPattern = new RegExp(`conversation_state_${userId}_.*`);
        
        allKeys.forEach(key => {
            if (key.startsWith('conversation_state_')) {
                if (doctorPattern.test(key) || userPattern.test(key)) {
                    similarKeys.push(key);
                }
            }
        });
        
        // 按时间排序，返回最近的
        return similarKeys.sort((a, b) => {
            const aTime = this.getKeyTimestamp(a);
            const bTime = this.getKeyTimestamp(b);
            return bTime - aTime;
        }).slice(0, 3); // 只检查最近的3个
    }
    
    /**
     * 从存储key中提取时间戳
     */
    getKeyTimestamp(key) {
        try {
            const data = localStorage.getItem(key);
            if (data) {
                const parsed = JSON.parse(data);
                return parsed.lastUpdated || parsed.startTime || 0;
            }
        } catch (error) {
            // 忽略错误
        }
        return 0;
    }
    
    /**
     * 创建全局备份
     */
    createGlobalBackup() {
        try {
            const backup = {};
            const allKeys = Object.keys(localStorage);
            
            // 备份所有对话状态数据
            allKeys.forEach(key => {
                if (key.startsWith('conversation_state_')) {
                    backup[key] = localStorage.getItem(key);
                }
            });
            
            // 保存备份
            localStorage.setItem('conversation_backup_global', JSON.stringify(backup));
            console.log('📦 已创建全局备份，包含', Object.keys(backup).length, '个对话状态');
            
        } catch (error) {
            console.error('创建全局备份失败:', error);
        }
    }
    
    /**
     * 清理过期数据
     */
    cleanupExpiredData() {
        const now = Date.now();
        const maxAge = 7 * 24 * 60 * 60 * 1000; // 7天
        const allKeys = Object.keys(localStorage);
        
        allKeys.forEach(key => {
            if (key.startsWith('conversation_state_')) {
                try {
                    const data = localStorage.getItem(key);
                    if (data) {
                        const parsed = JSON.parse(data);
                        const lastUpdated = parsed.lastUpdated || parsed.startTime || 0;
                        
                        if (now - lastUpdated > maxAge) {
                            localStorage.removeItem(key);
                            console.log('🗑️ 已清理过期数据:', key);
                        }
                    }
                } catch (error) {
                    // 数据损坏，直接删除
                    localStorage.removeItem(key);
                }
            }
        });
    }

    /**
     * 同步状态到服务器
     */
    async syncStateToServer() {
        const userId = this.getCurrentUserId();
        const selectedDoctor = window.selectedDoctor;
        
        // 不同步临时用户数据
        if (!userId || !selectedDoctor || userId.startsWith('temp_user_') || userId.startsWith('device_')) {
            console.log('📋 跳过临时用户数据同步');
            return;
        }
        
        try {
            const stateData = {
                currentState: this.currentState,
                stateHistory: this.stateHistory,
                conversationData: this.conversationData,
                startTime: this.startTime,
                lastUpdated: Date.now()
            };
            
            const deviceInfo = {
                fingerprint: this.getDeviceFingerprint(),
                timestamp: Date.now()
            };
            
            const response = await fetch('/api/conversation/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    doctor_id: selectedDoctor,
                    state_data: stateData,
                    device_info: deviceInfo
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    console.log('✅ 状态同步成功');
                    this.showSyncStatus('synced', '已同步到云端');
                    this.lastSyncTime = Date.now();
                } else {
                    throw new Error(result.message);
                }
            } else {
                throw new Error(`同步失败: ${response.status}`);
            }
            
        } catch (error) {
            console.warn('同步状态失败:', error);
            this.showSyncStatus('sync_failed', '同步失败，仅本地保存');
        }
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
     * 获取当前用户ID - 统一用户标识机制，解决跨设备数据丢失问题
     */
    getCurrentUserId() {
        // 1. 优先使用登录用户的固定ID（解决跨设备一致性问题）
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        if (currentUser.id && !currentUser.id.startsWith('temp_user_')) {
            console.log('🔑 使用登录用户固定ID:', currentUser.id);
            return currentUser.id;
        }
        
        // 2. 检查认证token中的用户信息
        const patientToken = localStorage.getItem('patientToken');
        if (patientToken) {
            try {
                const tokenUserInfo = this.parseTokenUserInfo(patientToken);
                if (tokenUserInfo?.id && !tokenUserInfo.id.startsWith('temp_user_')) {
                    console.log('🔑 使用token中的用户ID:', tokenUserInfo.id);
                    return tokenUserInfo.id;
                }
            } catch (error) {
                console.warn('解析token失败:', error);
            }
        }

        // 3. 尝试使用全局函数（兼容性）
        if (typeof window.getCurrentUserId === 'function') {
            const globalUserId = window.getCurrentUserId();
            if (globalUserId && !globalUserId.startsWith('temp_user_')) {
                console.log('🔑 使用全局函数返回的用户ID:', globalUserId);
                return globalUserId;
            }
        }

        // 4. 检查是否有持久化的用户身份
        const persistentUserId = localStorage.getItem('persistentUserId');
        if (persistentUserId && !persistentUserId.startsWith('temp_user_')) {
            console.log('🔑 使用持久化用户ID:', persistentUserId);
            return persistentUserId;
        }

        // 5. 生成一致性的临时ID（基于设备指纹）
        const consistentTempId = this.generateConsistentTempId();
        console.log('🔑 生成一致性临时ID:', consistentTempId);
        return consistentTempId;
    }

    /**
     * 解析token中的用户信息
     */
    parseTokenUserInfo(token) {
        try {
            // 简单的token解析（实际项目中应该用JWT库）
            const tokenData = JSON.parse(atob(token.split('.')[1] || ''));
            return tokenData;
        } catch (error) {
            // token格式不正确，尝试从localStorage获取用户信息
            const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
            if (currentUser.id) {
                return currentUser;
            }
            return null;
        }
    }

    /**
     * 生成一致性的临时ID（基于设备特征）
     */
    generateConsistentTempId() {
        // 尝试生成基于设备特征的一致性ID
        const deviceFingerprint = this.getDeviceFingerprint();
        const consistentId = 'device_' + deviceFingerprint;
        
        // 保存为持久化ID
        localStorage.setItem('persistentUserId', consistentId);
        return consistentId;
    }

    /**
     * 获取设备指纹（简化版）
     */
    getDeviceFingerprint() {
        const factors = [
            navigator.userAgent,
            navigator.language,
            screen.width + 'x' + screen.height,
            Intl.DateTimeFormat().resolvedOptions().timeZone,
            navigator.hardwareConcurrency || 'unknown'
        ];
        
        // 生成简单的哈希
        let hash = 0;
        const combined = factors.join('|');
        for (let i = 0; i < combined.length; i++) {
            const char = combined.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 转换为32位整数
        }
        
        return Math.abs(hash).toString(36).substr(0, 8);
    }

    /**
     * 设置用户ID（登录时调用）
     */
    setCurrentUserId(userId, userInfo = {}) {
        if (userId && !userId.startsWith('temp_user_')) {
            // 保存固定用户ID
            localStorage.setItem('persistentUserId', userId);
            
            // 更新当前用户信息
            const currentUser = {
                id: userId,
                ...userInfo,
                lastLogin: Date.now()
            };
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            console.log('✅ 已设置固定用户ID:', userId);
            
            // 如果有旧的临时ID，尝试迁移数据
            this.migrateDataFromTempId(userId);
        }
    }

    /**
     * 从临时ID迁移数据到固定ID
     */
    migrateDataFromTempId(newUserId) {
        const selectedDoctor = window.selectedDoctor;
        if (!selectedDoctor) return;
        
        // 查找可能的临时ID数据
        const storageKeys = Object.keys(localStorage);
        const tempKeys = storageKeys.filter(key => 
            key.startsWith('conversation_state_') && 
            (key.includes('temp_user_') || key.includes('device_'))
        );
        
        tempKeys.forEach(tempKey => {
            const tempData = localStorage.getItem(tempKey);
            if (tempData) {
                try {
                    const data = JSON.parse(tempData);
                    // 迁移到新的key
                    const newKey = `conversation_state_${newUserId}_${selectedDoctor}`;
                    const existingData = localStorage.getItem(newKey);
                    
                    if (!existingData) {
                        // 只有当新key不存在时才迁移
                        localStorage.setItem(newKey, tempData);
                        console.log('📦 已迁移对话数据:', tempKey, '→', newKey);
                    }
                    
                    // 清理旧数据
                    localStorage.removeItem(tempKey);
                } catch (error) {
                    console.warn('迁移数据失败:', tempKey, error);
                }
            }
        });
    }

    /**
     * 获取当前状态信息
     */
    getStateInfo() {
        return {
            current: this.currentState,
            duration: Date.now() - this.startTime,
            transitions: this.stateHistory.length,
            isCompleted: this.currentState === this.STATES.COMPLETED,
            userId: this.getCurrentUserId()
        };
    }

    /**
     * 执行完整用户数据同步
     */
    async performFullUserSync(userId) {
        try {
            console.log('🔄 执行完整用户数据同步...', userId);
            
            // 收集本地数据准备同步
            const localData = this.collectLocalData(userId);
            
            const response = await fetch('/api/user-sync/full-sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': this.getAuthToken()
                },
                body: JSON.stringify({
                    user_id: userId,
                    device_info: {
                        fingerprint: this.getDeviceFingerprint(),
                        user_agent: navigator.userAgent,
                        timestamp: Date.now()
                    },
                    sync_data: localData,
                    sync_type: 'full',
                    client_timestamp: Date.now()
                })
            });

            if (!response.ok) {
                throw new Error(`同步请求失败: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                console.log('✅ 用户数据同步成功');
                // 保存同步后的数据到本地
                if (result.data) {
                    this.applySyncedData(result.data);
                }
                return result;
            } else if (result.conflicts && result.conflicts.length > 0) {
                console.warn('⚠️ 检测到数据冲突，需要处理');
                // 可以在这里添加冲突处理逻辑
                return result;
            } else {
                console.error('❌ 数据同步失败:', result.message);
                return null;
            }
        } catch (error) {
            console.error('❌ 用户数据同步异常:', error);
            return null;
        }
    }

    /**
     * 收集本地数据
     */
    collectLocalData(userId) {
        const conversations = [];
        
        // 收集所有相关的localStorage数据
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(`conversation_state_${userId}_`)) {
                try {
                    const data = JSON.parse(localStorage.getItem(key));
                    const doctorId = key.split('_').pop();
                    
                    conversations.push({
                        conversation_id: `conv_${userId}_${doctorId}`,
                        user_id: userId,
                        doctor_id: doctorId,
                        current_stage: data.currentState,
                        symptoms_collected: JSON.stringify(data.conversationData || {}),
                        stage_history: JSON.stringify(data.stateHistory || []),
                        start_time: new Date(data.startTime || Date.now()).toISOString(),
                        last_activity: new Date().toISOString()
                    });
                } catch (error) {
                    console.warn('解析本地对话数据失败:', key, error);
                }
            }
        }

        return {
            conversations: conversations,
            device_id: this.getDeviceFingerprint(),
            last_updated: new Date().toISOString()
        };
    }

    /**
     * 应用同步后的数据
     */
    applySyncedData(syncedData) {
        const conversations = syncedData.conversations || [];
        
        conversations.forEach(conv => {
            const key = `conversation_state_${conv.user_id}_${conv.doctor_id}`;
            const stateData = {
                currentState: conv.current_stage,
                stateHistory: JSON.parse(conv.stage_history || '[]'),
                conversationData: JSON.parse(conv.symptoms_collected || '{}'),
                startTime: new Date(conv.start_time).getTime()
            };
            
            localStorage.setItem(key, JSON.stringify(stateData));
            console.log('💾 更新本地对话状态:', key);
        });
    }

    /**
     * 获取设备指纹
     */
    getDeviceFingerprint() {
        let fingerprint = localStorage.getItem('deviceFingerprint');
        if (!fingerprint) {
            fingerprint = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            localStorage.setItem('deviceFingerprint', fingerprint);
        }
        return fingerprint;
    }

    /**
     * 获取认证token
     */
    getAuthToken() {
        return localStorage.getItem('patientToken') || localStorage.getItem('authToken') || '';
    }
}

// 创建全局实例
window.conversationStateManager = new ConversationStateManager();

// 添加同步状态显示方法
ConversationStateManager.prototype.showSyncStatus = function(type, message) {
    // 查找或创建状态显示元素
    let statusElement = document.getElementById('conversationSyncStatus');
    if (!statusElement) {
        statusElement = document.createElement('div');
        statusElement.id = 'conversationSyncStatus';
        statusElement.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 500;
            max-width: 200px;
            transition: all 0.3s ease;
            opacity: 0;
        `;
        document.body.appendChild(statusElement);
    }
    
    // 根据类型设置样式
    const styles = {
        'server_restored': {
            background: '#e7f5e7',
            color: '#2e7d32',
            border: '1px solid #a5d6a7',
            icon: '🌐'
        },
        'local_restored': {
            background: '#fff3e0',
            color: '#ef6c00',
            border: '1px solid #ffb74d',
            icon: '📱'
        },
        'synced': {
            background: '#e3f2fd',
            color: '#1565c0',
            border: '1px solid #64b5f6',
            icon: '✅'
        },
        'sync_failed': {
            background: '#ffebee',
            color: '#c62828',
            border: '1px solid #ef5350',
            icon: '⚠️'
        },
        'new_conversation': {
            background: '#f3e5f5',
            color: '#7b1fa2',
            border: '1px solid #ce93d8',
            icon: '🎆'
        },
        'load_failed': {
            background: '#ffebee',
            color: '#c62828',
            border: '1px solid #ef5350',
            icon: '❌'
        }
    };
    
    const style = styles[type] || styles['synced'];
    
    statusElement.style.background = style.background;
    statusElement.style.color = style.color;
    statusElement.style.border = style.border;
    statusElement.innerHTML = `${style.icon} ${message}`;
    statusElement.style.opacity = '1';
    
    // 3秒后自动隐藏
    setTimeout(() => {
        if (statusElement) {
            statusElement.style.opacity = '0';
            setTimeout(() => {
                if (statusElement && statusElement.parentNode) {
                    statusElement.parentNode.removeChild(statusElement);
                }
            }, 300);
        }
    }, 3000);
};

// 添加最后同步时间追踪
ConversationStateManager.prototype.lastSyncTime = null;

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

// 全局函数，供外部调用
window.createConversationBackup = function() {
    if (window.conversationStateManager) {
        window.conversationStateManager.createGlobalBackup();
    }
};

window.cleanupConversationData = function() {
    if (window.conversationStateManager) {
        window.conversationStateManager.cleanupExpiredData();
    }
};

// 页面卸载时创建备份
window.addEventListener('beforeunload', function() {
    if (window.conversationStateManager) {
        window.conversationStateManager.createGlobalBackup();
    }
});

// 定时清理过期数据（每天1小时）
setInterval(function() {
    if (window.conversationStateManager) {
        window.conversationStateManager.cleanupExpiredData();
    }
}, 60 * 60 * 1000);

// 定时同步状态（每5分钟）
setInterval(function() {
    if (window.conversationStateManager && window.conversationStateManager.isActive()) {
        window.conversationStateManager.periodicSync();
    }
}, 5 * 60 * 1000);

// 添加定期同步和活跃检测方法
ConversationStateManager.prototype.isActive = function() {
    // 检查最近10分钟是否有活动
    const lastActivity = this.getLastActivityTime();
    return (Date.now() - lastActivity) < 10 * 60 * 1000;
};

ConversationStateManager.prototype.getLastActivityTime = function() {
    return this.lastSyncTime || this.startTime || Date.now();
};

ConversationStateManager.prototype.periodicSync = function() {
    // 只有当有状态变更时才进行定期同步
    if (this.hasUnsyncedChanges()) {
        console.log('🔄 执行定期状态同步...');
        this.syncStateToServer();
    }
};

ConversationStateManager.prototype.hasUnsyncedChanges = function() {
    // 检查是否有未同步的变更
    const lastStateChange = this.stateHistory.length > 0 ? 
        this.stateHistory[this.stateHistory.length - 1].timestamp : this.startTime;
    
    return this.lastSyncTime ? (lastStateChange > this.lastSyncTime) : true;
};

// 增强的同步状态显示，包含同步历史
ConversationStateManager.prototype.showDetailedSyncStatus = function() {
    const userId = this.getCurrentUserId();
    const isTemporary = userId.startsWith('temp_user_') || userId.startsWith('device_');
    
    let statusHtml = `
        <div style="
            position: fixed; 
            bottom: 20px; 
            left: 20px; 
            background: white; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            padding: 16px; 
            max-width: 300px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1001;
            font-size: 14px;
        ">
            <div style="font-weight: 600; margin-bottom: 8px;">📊 对话状态信息</div>
            <div>👤 用户ID: ${userId}</div>
            <div>👨‍⚕️ 医生: ${window.selectedDoctor || '未选择'}</div>
            <div>🔄 当前状态: ${this.getCurrentStateLabel()}</div>
            <div>📈 状态变更: ${this.stateHistory.length}次</div>
            <div>⏰ 对话时长: ${this.getConversationDuration()}</div>
            <div>
                ${isTemporary ? 
                    '💾 数据存储: 仅本地 (临时用户)' : 
                    `☁️ 云端同步: ${this.lastSyncTime ? '已同步' : '未同步'}`
                }
            </div>
            ${this.lastSyncTime ? 
                `<div>🕐 最后同步: ${new Date(this.lastSyncTime).toLocaleTimeString()}</div>` : 
                ''
            }
            <button onclick="this.parentElement.remove()" style="
                position: absolute; 
                top: 8px; 
                right: 8px; 
                border: none; 
                background: none; 
                cursor: pointer;
                font-size: 16px;
            ">×</button>
        </div>
    `;
    
    // 移除现有的详细状态显示
    const existing = document.querySelector('[data-sync-detail]');
    if (existing) existing.remove();
    
    const statusElement = document.createElement('div');
    statusElement.setAttribute('data-sync-detail', 'true');
    statusElement.innerHTML = statusHtml;
    document.body.appendChild(statusElement);
    
    // 10秒后自动消失
    setTimeout(() => {
        if (statusElement.parentNode) {
            statusElement.parentNode.removeChild(statusElement);
        }
    }, 10000);
};

ConversationStateManager.prototype.getCurrentStateLabel = function() {
    const stateLabels = {
        [this.STATES.INITIAL_INQUIRY]: '初始问诊',
        [this.STATES.DETAILED_INQUIRY]: '详细了解', 
        [this.STATES.INTERIM_ADVICE]: '初步建议',
        [this.STATES.DIAGNOSIS]: '诊断分析',
        [this.STATES.PRESCRIPTION]: '处方建议',
        [this.STATES.PRESCRIPTION_CONFIRM]: '确认处方',
        [this.STATES.COMPLETED]: '问诊完成'
    };
    return stateLabels[this.currentState] || this.currentState;
};

ConversationStateManager.prototype.getConversationDuration = function() {
    const duration = Date.now() - this.startTime;
    const minutes = Math.floor(duration / 60000);
    const seconds = Math.floor((duration % 60000) / 1000);
    return `${minutes}分${seconds}秒`;
};

// 全局函数，供开发调试使用
window.showConversationStatus = function() {
    if (window.conversationStateManager) {
        window.conversationStateManager.showDetailedSyncStatus();
    }
};