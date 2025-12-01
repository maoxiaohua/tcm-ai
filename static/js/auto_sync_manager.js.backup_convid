/**
 * 自动同步管理器 v2.0
 * 基于用户操作自动触发实时同步，无需手动操作
 * 支持离线缓存、冲突解决、智能重试
 */

class AutoSyncManager {
    constructor() {
        this.deviceId = this.generateDeviceId();
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 1秒
        this.heartbeatInterval = null;
        this.pendingOperations = [];
        this.syncQueue = [];
        this.isProcessingQueue = false;
        this.lastSyncTime = 0;
        this.offlineOperations = [];
        
        // 事件监听器
        this.eventListeners = {
            connected: [],
            disconnected: [],
            synced: [],
            conflict: [],
            error: []
        };
        
        this.init();
    }
    
    /**
     * 初始化自动同步系统
     */
    init() {
        // 检查是否为临时用户
        if (this.isTemporaryUser()) {
            console.log('🔄 临时用户，跳过自动同步初始化');
            return;
        }
        
        // 建立WebSocket连接
        this.connect();
        
        // 监听DOM变化和用户操作
        this.setupOperationListeners();
        
        // 监听页面和网络状态
        this.setupStatusListeners();
        
        // 启动定期状态检查
        this.startPeriodicCheck();
        
        console.log('✅ 自动同步管理器已启动');
    }
    
    /**
     * 建立WebSocket连接
     */
    async connect() {
        try {
            const userId = this.getCurrentUserId();
            if (!userId || this.isTemporaryUser()) {
                return;
            }
            
            // 构建WebSocket URL
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/sync/${userId}?device_id=${this.deviceId}`;
            
            console.log('🔌 建立自动同步连接...');
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = this.handleOpen.bind(this);
            this.websocket.onmessage = this.handleMessage.bind(this);
            this.websocket.onclose = this.handleClose.bind(this);
            this.websocket.onerror = this.handleError.bind(this);
            
        } catch (error) {
            console.error('❌ 连接自动同步服务失败:', error);
            this.scheduleReconnect();
        }
    }
    
    /**
     * 设置操作监听器 - 核心自动同步逻辑
     */
    setupOperationListeners() {
        // 1. 监听对话消息发送
        this.observeMessageSending();
        
        // 2. 监听医生切换
        this.observeDoctorSwitch();
        
        // 3. 监听处方生成/更新
        this.observePrescriptionChanges();
        
        // 4. 监听对话状态变化
        this.observeConversationStageChanges();
        
        // 5. 监听页面路由变化
        this.observeRouteChanges();
    }
    
    /**
     * 监听消息发送操作
     */
    observeMessageSending() {
        // 重写全局的addMessage函数，在消息添加时自动同步
        const originalAddMessage = window.addMessage;
        const originalAddMobileMessage = window.addMobileMessage;
        
        window.addMessage = (sender, message, isTyping = false, fromRemote = false) => {
            // 调用原始函数
            if (originalAddMessage) {
                originalAddMessage(sender, message, isTyping, fromRemote);
            }
            
            // 如果不是来自远程且不是打字状态，触发同步
            if (!fromRemote && !isTyping && sender === 'user') {
                this.autoSyncOperation('new_message', {
                    message: message,
                    sender: sender,
                    conversation_id: window.currentConversationId,
                    timestamp: Date.now()
                });
            }
        };
        
        window.addMobileMessage = (sender, message, isTyping = false, fromRemote = false) => {
            // 调用原始函数
            if (originalAddMobileMessage) {
                originalAddMobileMessage(sender, message, isTyping, fromRemote);
            }
            
            // 触发同步
            if (!fromRemote && !isTyping && sender === 'user') {
                this.autoSyncOperation('new_message', {
                    message: message,
                    sender: sender,
                    conversation_id: window.currentConversationId,
                    timestamp: Date.now()
                });
            }
        };
    }
    
    /**
     * 监听医生切换操作
     */
    observeDoctorSwitch() {
        // 监听医生选择变化
        const doctorObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && 
                    mutation.attributeName === 'class' && 
                    mutation.target.classList.contains('selected')) {
                    
                    const doctorId = mutation.target.dataset.doctorId;
                    const doctorName = mutation.target.querySelector('.doctor-name')?.textContent;
                    
                    if (doctorId) {
                        this.autoSyncOperation('doctor_switch', {
                            doctor_id: doctorId,
                            doctor_name: doctorName,
                            timestamp: Date.now()
                        });
                    }
                }
            });
        });
        
        // 观察医生卡片容器
        const doctorContainer = document.querySelector('.doctors-grid');
        if (doctorContainer) {
            doctorObserver.observe(doctorContainer, {
                attributes: true,
                subtree: true,
                attributeFilter: ['class']
            });
        }
    }
    
    /**
     * 监听处方变化
     */
    observePrescriptionChanges() {
        // 重写处方相关函数
        const originalCreatePrescription = window.createPrescriptionRecord;
        
        window.createPrescriptionRecord = async function(...args) {
            const result = originalCreatePrescription ? await originalCreatePrescription.apply(this, args) : null;
            
            // 同步处方创建
            if (window.autoSyncManager) {
                window.autoSyncManager.autoSyncOperation('prescription_update', {
                    action: 'created',
                    prescription_data: result,
                    timestamp: Date.now()
                });
            }
            
            return result;
        };
    }
    
    /**
     * 监听对话状态变化
     */
    observeConversationStageChanges() {
        // 监听会话状态管理器的状态变化
        if (window.conversationStateManager) {
            const originalSetState = window.conversationStateManager.setState;
            
            window.conversationStateManager.setState = function(newStage, reason) {
                const result = originalSetState.call(this, newStage, reason);
                
                // 自动同步状态变化
                if (window.autoSyncManager) {
                    window.autoSyncManager.autoSyncOperation('conversation_update', {
                        conversation_id: this.conversationId,
                        current_stage: newStage,
                        reason: reason,
                        timestamp: Date.now()
                    });
                }
                
                return result;
            };
        }
    }
    
    /**
     * 监听路由变化
     */
    observeRouteChanges() {
        // 监听URL变化
        let currentUrl = window.location.href;
        
        const checkUrlChange = () => {
            if (window.location.href !== currentUrl) {
                currentUrl = window.location.href;
                
                this.autoSyncOperation('route_change', {
                    url: currentUrl,
                    timestamp: Date.now()
                });
            }
        };
        
        // 监听历史记录变化
        window.addEventListener('popstate', checkUrlChange);
        
        // 定期检查URL变化（针对单页应用）
        setInterval(checkUrlChange, 1000);
    }
    
    /**
     * 自动同步操作 - 核心方法
     */
    autoSyncOperation(operationType, operationData) {
        // 检查连接状态
        if (!this.isConnected) {
            // 离线时缓存操作
            this.cacheOfflineOperation(operationType, operationData);
            return;
        }
        
        // 防抖处理 - 避免频繁同步
        const now = Date.now();
        if (now - this.lastSyncTime < 500) { // 500ms内不重复同步相同操作
            return;
        }
        
        // 添加到同步队列
        this.syncQueue.push({
            type: operationType,
            data: operationData,
            timestamp: now,
            retryCount: 0
        });
        
        // 处理同步队列
        this.processSyncQueue();
        
        this.lastSyncTime = now;
        
        console.log(`🔄 自动同步: ${operationType}`, operationData);
    }
    
    /**
     * 处理同步队列
     */
    async processSyncQueue() {
        if (this.isProcessingQueue || this.syncQueue.length === 0) {
            return;
        }
        
        this.isProcessingQueue = true;
        
        try {
            while (this.syncQueue.length > 0) {
                const operation = this.syncQueue.shift();
                await this.sendSyncEvent(operation.type, operation.data);
                
                // 短暂延迟避免过于频繁的请求
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        } catch (error) {
            console.error('❌ 处理同步队列失败:', error);
        } finally {
            this.isProcessingQueue = false;
        }
    }
    
    /**
     * 发送同步事件
     */
    async sendSyncEvent(eventType, data) {
        const event = {
            type: eventType,
            data: data,
            timestamp: Date.now(),
            device_id: this.deviceId
        };
        
        if (this.isConnected && this.websocket.readyState === WebSocket.OPEN) {
            try {
                this.websocket.send(JSON.stringify(event));
                console.log('📤 自动同步事件已发送:', eventType);
                
                // 触发同步成功事件
                this.notifyEventListeners('synced', { type: eventType, data });
                
            } catch (error) {
                console.error('❌ 发送同步事件失败:', error);
                throw error;
            }
        } else {
            throw new Error('WebSocket连接不可用');
        }
    }
    
    /**
     * 缓存离线操作
     */
    cacheOfflineOperation(operationType, operationData) {
        this.offlineOperations.push({
            type: operationType,
            data: operationData,
            timestamp: Date.now()
        });
        
        // 限制离线缓存大小
        if (this.offlineOperations.length > 100) {
            this.offlineOperations = this.offlineOperations.slice(-100);
        }
        
        // 保存到本地存储
        localStorage.setItem('autoSyncOfflineOps', JSON.stringify(this.offlineOperations));
        
        console.log('📦 操作已缓存，等待网络恢复:', operationType);
    }
    
    /**
     * 恢复离线操作
     */
    async recoverOfflineOperations() {
        // 从本地存储恢复
        try {
            const cached = localStorage.getItem('autoSyncOfflineOps');
            if (cached) {
                this.offlineOperations = JSON.parse(cached);
            }
        } catch (error) {
            console.error('恢复离线操作失败:', error);
            this.offlineOperations = [];
        }
        
        // 处理离线操作
        if (this.offlineOperations.length > 0) {
            console.log(`🔄 恢复${this.offlineOperations.length}个离线操作`);
            
            for (const operation of this.offlineOperations) {
                this.syncQueue.push({
                    type: operation.type,
                    data: operation.data,
                    timestamp: operation.timestamp,
                    retryCount: 0,
                    fromOffline: true
                });
            }
            
            // 清空离线缓存
            this.offlineOperations = [];
            localStorage.removeItem('autoSyncOfflineOps');
            
            // 处理队列
            this.processSyncQueue();
        }
    }
    
    /**
     * 连接打开处理
     */
    handleOpen(event) {
        console.log('✅ 自动同步连接已建立');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // 开始心跳
        this.startHeartbeat();
        
        // 恢复离线操作
        this.recoverOfflineOperations();
        
        // 显示连接状态
        this.updateSyncIndicator('connected');
        
        // 通知监听器
        this.notifyEventListeners('connected', event);
    }
    
    /**
     * 消息处理
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('📨 收到自动同步消息:', message.type);
            
            switch (message.type) {
                case 'heartbeat_ack':
                    // 心跳响应，无需处理
                    break;
                    
                case 'state_sync':
                    this.handleRemoteStateUpdate(message.data);
                    break;
                    
                case 'message_sync':
                    this.handleRemoteMessage(message.data);
                    break;
                    
                case 'prescription_sync':
                    this.handleRemotePrescription(message.data);
                    break;
                    
                case 'doctor_sync':
                    this.handleRemoteDoctorSwitch(message.data);
                    break;
                    
                case 'conflict_detected':
                    this.handleConflict(message.data);
                    break;
                    
                default:
                    console.log('未处理的同步消息类型:', message.type);
            }
            
        } catch (error) {
            console.error('❌ 处理同步消息失败:', error);
        }
    }
    
    /**
     * 处理远程状态更新
     */
    handleRemoteStateUpdate(data) {
        if (window.conversationStateManager && data.conversation_id) {
            const currentState = window.conversationStateManager.currentState;
            const remoteState = data.current_stage;
            
            if (currentState !== remoteState) {
                console.log('🔄 应用远程状态更新:', remoteState);
                window.conversationStateManager.setState(remoteState, '远程设备同步');
                
                this.showSyncNotification('对话状态已同步', 'state');
            }
        }
    }
    
    /**
     * 处理远程消息
     */
    handleRemoteMessage(data) {
        if (data.message && data.sender) {
            console.log('💬 收到远程消息同步:', data);
            
            // 添加消息（标记为远程来源）
            if (typeof window.addMessage === 'function') {
                window.addMessage(data.sender, data.message, false, true);
            }
            
            this.showSyncNotification('收到新消息', 'message');
        }
    }
    
    /**
     * 处理远程处方更新
     */
    handleRemotePrescription(data) {
        console.log('💊 收到处方同步:', data);
        this.showSyncNotification('处方已更新', 'prescription');
        
        // 可以在这里触发处方列表刷新
        if (window.refreshPrescriptionList) {
            window.refreshPrescriptionList();
        }
    }
    
    /**
     * 处理远程医生切换
     */
    handleRemoteDoctorSwitch(data) {
        if (data.doctor_id && window.selectedDoctor !== data.doctor_id) {
            console.log('👨‍⚕️ 应用远程医生切换:', data.doctor_name);
            
            // 更新选中的医生
            window.selectedDoctor = data.doctor_id;
            
            // 更新UI
            if (window.updateSelectedDoctor) {
                window.updateSelectedDoctor(data.doctor_id);
            }
            
            this.showSyncNotification(`已切换到${data.doctor_name}`, 'doctor');
        }
    }
    
    /**
     * 处理冲突
     */
    handleConflict(data) {
        console.warn('⚠️ 检测到数据冲突:', data);
        
        this.showConflictDialog(data);
        this.notifyEventListeners('conflict', data);
    }
    
    /**
     * 显示同步通知
     */
    showSyncNotification(message, type) {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = 'auto-sync-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 25px;
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
            z-index: 1002;
            font-size: 14px;
            max-width: 280px;
            animation: slideInBounce 0.5s ease-out;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        
        const icons = {
            'state': '🔄',
            'message': '💬',
            'prescription': '💊',
            'doctor': '👨‍⚕️',
            'connected': '🟢',
            'disconnected': '🔴'
        };
        
        notification.innerHTML = `
            <span>${icons[type] || '🔄'}</span>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        // 自动消失
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOutBounce 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, 3000);
        
        // 添加动画样式
        this.addAnimationStyles();
    }
    
    /**
     * 添加动画样式
     */
    addAnimationStyles() {
        if (!document.getElementById('autoSyncAnimations')) {
            const style = document.createElement('style');
            style.id = 'autoSyncAnimations';
            style.textContent = `
                @keyframes slideInBounce {
                    0% {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    60% {
                        transform: translateX(-10px);
                    }
                    100% {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                
                @keyframes slideOutBounce {
                    0% {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    100% {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    /**
     * 显示冲突对话框
     */
    showConflictDialog(conflictData) {
        // 这里可以显示一个优雅的冲突解决对话框
        const shouldUseServer = confirm(`检测到数据冲突，是否使用服务器版本？\n\n冲突详情: ${JSON.stringify(conflictData, null, 2)}`);
        
        this.resolveConflict(conflictData.conflict_id, shouldUseServer ? 'server_wins' : 'client_wins');
    }
    
    /**
     * 解决冲突
     */
    resolveConflict(conflictId, strategy) {
        this.sendSyncEvent('conflict_resolution', {
            conflict_id: conflictId,
            strategy: strategy
        });
    }
    
    /**
     * 更新同步指示器
     */
    updateSyncIndicator(status) {
        let indicator = document.getElementById('autoSyncIndicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'autoSyncIndicator';
            indicator.style.cssText = `
                position: fixed;
                bottom: 80px;
                right: 20px;
                background: rgba(255, 255, 255, 0.95);
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                border: 1px solid #ddd;
                cursor: pointer;
                z-index: 1001;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            `;
            document.body.appendChild(indicator);
        }
        
        const statusConfig = {
            'connected': { color: '#4caf50', text: '实时同步', icon: '🟢' },
            'disconnected': { color: '#ff9800', text: '连接断开', icon: '🟡' },
            'syncing': { color: '#2196f3', text: '同步中', icon: '🔄' },
            'error': { color: '#f44336', text: '同步错误', icon: '🔴' }
        };
        
        const config = statusConfig[status] || statusConfig['disconnected'];
        
        indicator.style.color = config.color;
        indicator.innerHTML = `${config.icon} ${config.text}`;
        indicator.title = `自动同步状态: ${config.text}`;
    }
    
    /**
     * 设置状态监听器
     */
    setupStatusListeners() {
        // 页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.handlePageHidden();
            } else {
                this.handlePageVisible();
            }
        });
        
        // 网络状态变化
        window.addEventListener('online', () => this.handleNetworkOnline());
        window.addEventListener('offline', () => this.handleNetworkOffline());
    }
    
    /**
     * 定期状态检查
     */
    startPeriodicCheck() {
        setInterval(() => {
            // 检查连接状态
            if (!this.isConnected && !this.isTemporaryUser()) {
                this.connect();
            }
            
            // 清理过期的操作
            this.cleanupExpiredOperations();
            
        }, 30000); // 30秒检查一次
    }
    
    /**
     * 清理过期操作
     */
    cleanupExpiredOperations() {
        const now = Date.now();
        const maxAge = 5 * 60 * 1000; // 5分钟
        
        this.offlineOperations = this.offlineOperations.filter(
            op => now - op.timestamp < maxAge
        );
        
        this.syncQueue = this.syncQueue.filter(
            op => now - op.timestamp < maxAge
        );
    }
    
    // WebSocket事件处理方法（继承自原有实现）
    handleClose(event) {
        console.log('❌ 自动同步连接已关闭:', event.code);
        this.isConnected = false;
        this.stopHeartbeat();
        
        this.updateSyncIndicator('disconnected');
        this.notifyEventListeners('disconnected', event);
        
        // 非正常关闭时重连
        if (event.code !== 1000 && !this.isTemporaryUser()) {
            this.scheduleReconnect();
        }
    }
    
    handleError(error) {
        console.error('❌ 自动同步连接错误:', error);
        this.updateSyncIndicator('error');
        this.notifyEventListeners('error', error);
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`🔄 ${delay/1000}秒后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, delay);
        }
    }
    
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({ type: 'heartbeat' }));
            }
        }, 30000);
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    handlePageHidden() {
        // 页面隐藏时减少活动
        this.stopHeartbeat();
    }
    
    handlePageVisible() {
        // 页面重新显示时恢复活动
        if (this.isConnected) {
            this.startHeartbeat();
        } else {
            this.connect();
        }
    }
    
    handleNetworkOnline() {
        console.log('🌐 网络已连接，重新建立自动同步');
        if (!this.isConnected) {
            this.reconnectAttempts = 0;
            this.connect();
        }
    }
    
    handleNetworkOffline() {
        console.log('📵 网络已断开，切换到离线模式');
        this.updateSyncIndicator('disconnected');
    }
    
    // 工具方法
    generateDeviceId() {
        let deviceId = localStorage.getItem('autoSyncDeviceId');
        if (!deviceId) {
            deviceId = 'auto_device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('autoSyncDeviceId', deviceId);
        }
        return deviceId;
    }
    
    getCurrentUserId() {
        if (window.conversationStateManager) {
            return window.conversationStateManager.getCurrentUserId();
        }
        
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        return currentUser.id || localStorage.getItem('currentUserId');
    }
    
    isTemporaryUser() {
        const userId = this.getCurrentUserId();
        return !userId || userId.startsWith('temp_user_') || userId.startsWith('device_');
    }
    
    // 事件监听器管理
    addEventListener(eventType, callback) {
        if (this.eventListeners[eventType]) {
            this.eventListeners[eventType].push(callback);
        }
    }
    
    removeEventListener(eventType, callback) {
        if (this.eventListeners[eventType]) {
            const index = this.eventListeners[eventType].indexOf(callback);
            if (index > -1) {
                this.eventListeners[eventType].splice(index, 1);
            }
        }
    }
    
    notifyEventListeners(eventType, data) {
        if (this.eventListeners[eventType]) {
            this.eventListeners[eventType].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('事件监听器执行失败:', error);
                }
            });
        }
    }
    
    // 公共API
    getStatus() {
        return {
            connected: this.isConnected,
            deviceId: this.deviceId,
            reconnectAttempts: this.reconnectAttempts,
            pendingOperations: this.offlineOperations.length,
            syncQueueLength: this.syncQueue.length
        };
    }
    
    disconnect() {
        if (this.websocket) {
            this.websocket.close(1000, 'Manual disconnect');
        }
        this.stopHeartbeat();
    }
}

// 创建全局实例并自动初始化
window.autoSyncManager = new AutoSyncManager();

// 页面卸载时断开连接
window.addEventListener('beforeunload', () => {
    if (window.autoSyncManager) {
        window.autoSyncManager.disconnect();
    }
});

// 导出全局函数
window.getAutoSyncStatus = function() {
    return window.autoSyncManager ? window.autoSyncManager.getStatus() : null;
};

console.log('✅ 自动同步管理器 v2.0 已加载');