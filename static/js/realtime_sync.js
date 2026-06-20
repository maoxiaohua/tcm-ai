/**
 * 实时同步管理器
 * 支持多设备会话状态实时同步
 */

class RealtimeSyncManager {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.heartbeatInterval = null;
        this.pendingEvents = [];
        this.deviceId = this.generateDeviceId();
        
        // 事件监听器
        this.eventListeners = {
            'state_change': [],
            'message_received': [],
            'prescription_created': [],
            'connection_status': []
        };
        
        this.init();
    }
    
    /**
     * 初始化实时同步
     */
    init() {
        // 检查用户是否为临时用户
        if (this.isTemporaryUser()) {
            console.log('🔄 临时用户，跳过实时同步初始化');
            return;
        }
        
        // 连接WebSocket
        this.connect();
        
        // 监听页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.handlePageHidden();
            } else {
                this.handlePageVisible();
            }
        });
        
        // 监听网络状态变化
        window.addEventListener('online', () => this.handleNetworkOnline());
        window.addEventListener('offline', () => this.handleNetworkOffline());
    }
    
    /**
     * 连接WebSocket服务器
     */
    connect() {
        try {
            const userId = this.getCurrentUserId();
            if (!userId || this.isTemporaryUser()) {
                return;
            }
            
            // 构建WebSocket URL
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/sync/${userId}?device_id=${this.deviceId}`;
            
            console.log('🔌 连接实时同步服务器...');
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = this.handleOpen.bind(this);
            this.websocket.onmessage = this.handleMessage.bind(this);
            this.websocket.onclose = this.handleClose.bind(this);
            this.websocket.onerror = this.handleError.bind(this);
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.scheduleReconnect();
        }
    }
    
    /**
     * 处理连接建立
     */
    handleOpen() {
        console.log('✅ 实时同步连接已建立');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // 开始心跳
        this.startHeartbeat();
        
        // 发送待处理的事件
        this.processPendingEvents();
        
        // 通知连接状态变化
        this.notifyConnectionStatus('connected');
        
        // 请求最新状态
        this.requestLatestState();
    }
    
    /**
     * 处理接收到的消息
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('📨 收到实时同步消息:', message);
            
            switch (message.type) {
                case 'state_sync':
                    this.handleStateSync(message.data);
                    break;
                case 'message_sync':
                    this.handleMessageSync(message.data);
                    break;
                case 'prescription_sync':
                    this.handlePrescriptionSync(message.data);
                    break;
                case 'device_notification':
                    this.handleDeviceNotification(message.data);
                    break;
                case 'conflict_detected':
                    this.handleConflictDetected(message.data);
                    break;
                case 'heartbeat_ack':
                    // 心跳确认，无需处理
                    break;
                case 'latest_state':
                    this.handleLatestState(message.data);
                    break;
                default:
                    console.warn('未知消息类型:', message.type);
            }\n        } catch (error) {\n            console.error('处理WebSocket消息失败:', error);\n        }\n    }\n    \n    /**\n     * 处理连接关闭\n     */\n    handleClose(event) {\n        console.log('❌ 实时同步连接已关闭:', event.code, event.reason);\n        this.isConnected = false;\n        this.stopHeartbeat();\n        \n        this.notifyConnectionStatus('disconnected');\n        \n        // 如果不是正常关闭，尝试重连\n        if (event.code !== 1000) {\n            this.scheduleReconnect();\n        }\n    }\n    \n    /**\n     * 处理连接错误\n     */\n    handleError(error) {\n        console.error('WebSocket错误:', error);\n        this.notifyConnectionStatus('error');\n    }\n    \n    /**\n     * 发送实时事件\n     */\n    sendEvent(eventType, data) {\n        const event = {\n            type: eventType,\n            data: data,\n            timestamp: Date.now(),\n            device_id: this.deviceId\n        };\n        \n        if (this.isConnected && this.websocket.readyState === WebSocket.OPEN) {\n            this.websocket.send(JSON.stringify(event));\n            console.log('📤 发送实时事件:', eventType, data);\n        } else {\n            // 连接未建立，加入待处理队列\n            this.pendingEvents.push(event);\n            console.log('📋 事件加入待处理队列:', eventType);\n        }\n    }\n    \n    /**\n     * 处理状态同步\n     */\n    handleStateSync(data) {\n        if (window.conversationStateManager && data.conversation_id) {\n            // 检查是否需要更新本地状态\n            const currentState = window.conversationStateManager.currentState;\n            const remoteState = data.current_stage;\n            \n            if (currentState !== remoteState) {\n                console.log('🔄 检测到状态变更，同步远程状态:', remoteState);\n                \n                // 显示同步提示\n                this.showSyncNotification('状态已在其他设备更新', 'state_updated');\n                \n                // 更新本地状态\n                window.conversationStateManager.setState(remoteState, '远程设备同步');\n            }\n        }\n        \n        this.notifyEventListeners('state_change', data);\n    }\n    \n    /**\n     * 处理消息同步\n     */\n    handleMessageSync(data) {\n        if (data.message && data.sender) {\n            console.log('💬 收到新消息同步:', data);\n            \n            // 显示同步的消息\n            if (typeof window.addMessage === 'function') {\n                window.addMessage(data.sender, data.message, false, true); // 最后参数表示来自远程\n            }\n            \n            this.showSyncNotification('收到新消息', 'message_received');\n        }\n        \n        this.notifyEventListeners('message_received', data);\n    }\n    \n    /**\n     * 处理处方同步\n     */\n    handlePrescriptionSync(data) {\n        console.log('💊 收到处方同步:', data);\n        \n        this.showSyncNotification('处方已更新', 'prescription_updated');\n        this.notifyEventListeners('prescription_created', data);\n    }\n    \n    /**\n     * 处理设备通知\n     */\n    handleDeviceNotification(data) {\n        console.log('📱 收到设备通知:', data);\n        \n        if (data.type === 'new_device_login') {\n            this.showSyncNotification(`新设备登录: ${data.device_info}`, 'device_login');\n        } else if (data.type === 'device_logout') {\n            this.showSyncNotification(`设备已退出: ${data.device_info}`, 'device_logout');\n        }\n    }\n    \n    /**\n     * 处理冲突检测\n     */\n    handleConflictDetected(data) {\n        console.warn('⚠️ 检测到数据冲突:', data);\n        \n        this.showConflictResolutionDialog(data);\n    }\n    \n    /**\n     * 处理最新状态响应\n     */\n    handleLatestState(data) {\n        console.log('📥 收到最新状态:', data);\n        \n        if (window.conversationStateManager && data.conversation_state) {\n            const remoteState = data.conversation_state;\n            const localTimestamp = window.conversationStateManager.lastSyncTime || 0;\n            const remoteTimestamp = new Date(remoteState.last_activity).getTime();\n            \n            if (remoteTimestamp > localTimestamp) {\n                console.log('🔄 远程状态更新，应用到本地');\n                window.conversationStateManager.applyServerState(remoteState);\n            }\n        }\n    }\n    \n    /**\n     * 显示同步通知\n     */\n    showSyncNotification(message, type) {\n        // 创建通知元素\n        const notification = document.createElement('div');\n        notification.className = 'realtime-sync-notification';\n        notification.style.cssText = `\n            position: fixed;\n            top: 80px;\n            right: 20px;\n            background: #e3f2fd;\n            color: #1565c0;\n            padding: 12px 16px;\n            border-radius: 8px;\n            border-left: 4px solid #2196f3;\n            box-shadow: 0 4px 12px rgba(0,0,0,0.15);\n            z-index: 1002;\n            font-size: 14px;\n            max-width: 250px;\n            animation: slideInRight 0.3s ease;\n        `;\n        \n        const icons = {\n            'state_updated': '🔄',\n            'message_received': '💬',\n            'prescription_updated': '💊',\n            'device_login': '📱',\n            'device_logout': '📴'\n        };\n        \n        notification.innerHTML = `${icons[type] || '🔄'} ${message}`;\n        document.body.appendChild(notification);\n        \n        // 3秒后自动消失\n        setTimeout(() => {\n            if (notification.parentNode) {\n                notification.style.animation = 'slideOutRight 0.3s ease';\n                setTimeout(() => {\n                    if (notification.parentNode) {\n                        notification.parentNode.removeChild(notification);\n                    }\n                }, 300);\n            }\n        }, 3000);\n    }\n    \n    /**\n     * 显示冲突解决对话框\n     */\n    showConflictResolutionDialog(conflictData) {\n        const dialog = document.createElement('div');\n        dialog.style.cssText = `\n            position: fixed;\n            top: 50%;\n            left: 50%;\n            transform: translate(-50%, -50%);\n            background: white;\n            border-radius: 12px;\n            padding: 24px;\n            box-shadow: 0 8px 32px rgba(0,0,0,0.3);\n            z-index: 1003;\n            max-width: 400px;\n            width: 90%;\n        `;\n        \n        dialog.innerHTML = `\n            <h3 style=\"margin-bottom: 16px; color: #f57c00;\">⚠️ 数据冲突</h3>\n            <p style=\"margin-bottom: 16px;\">检测到与其他设备的数据冲突，请选择解决方案：</p>\n            <div style=\"margin-bottom: 16px;\">\n                <button onclick=\"this.parentElement.parentElement.remove(); realtimeSyncManager.resolveConflict('server_wins', '${conflictData.conflict_id}')\" \n                        style=\"margin: 4px; padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; cursor: pointer;\">\n                    使用服务器版本\n                </button>\n                <button onclick=\"this.parentElement.parentElement.remove(); realtimeSyncManager.resolveConflict('client_wins', '${conflictData.conflict_id}')\" \n                        style=\"margin: 4px; padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; cursor: pointer;\">\n                    使用本地版本\n                </button>\n            </div>\n            <button onclick=\"this.parentElement.remove()\" \n                    style=\"position: absolute; top: 8px; right: 8px; border: none; background: none; font-size: 18px; cursor: pointer;\">×</button>\n        `;\n        \n        document.body.appendChild(dialog);\n    }\n    \n    /**\n     * 解决冲突\n     */\n    resolveConflict(strategy, conflictId) {\n        this.sendEvent('conflict_resolution', {\n            conflict_id: conflictId,\n            strategy: strategy\n        });\n    }\n    \n    /**\n     * 开始心跳\n     */\n    startHeartbeat() {\n        this.heartbeatInterval = setInterval(() => {\n            if (this.isConnected && this.websocket.readyState === WebSocket.OPEN) {\n                this.websocket.send(JSON.stringify({ type: 'heartbeat' }));\n            }\n        }, 30000); // 30秒心跳\n    }\n    \n    /**\n     * 停止心跳\n     */\n    stopHeartbeat() {\n        if (this.heartbeatInterval) {\n            clearInterval(this.heartbeatInterval);\n            this.heartbeatInterval = null;\n        }\n    }\n    \n    /**\n     * 计划重连\n     */\n    scheduleReconnect() {\n        if (this.reconnectAttempts < this.maxReconnectAttempts) {\n            this.reconnectAttempts++;\n            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);\n            \n            console.log(`🔄 ${delay/1000}秒后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);\n            \n            setTimeout(() => {\n                this.connect();\n            }, delay);\n        } else {\n            console.error('❌ 达到最大重连次数，停止重连');\n            this.notifyConnectionStatus('max_retries_reached');\n        }\n    }\n    \n    /**\n     * 处理待处理事件\n     */\n    processPendingEvents() {\n        while (this.pendingEvents.length > 0) {\n            const event = this.pendingEvents.shift();\n            this.websocket.send(JSON.stringify(event));\n        }\n    }\n    \n    /**\n     * 请求最新状态\n     */\n    requestLatestState() {\n        this.sendEvent('request_latest_state', {\n            user_id: this.getCurrentUserId(),\n            doctor_id: window.selectedDoctor\n        });\n    }\n    \n    /**\n     * 处理页面隐藏\n     */\n    handlePageHidden() {\n        // 页面隐藏时停止心跳，减少资源消耗\n        this.stopHeartbeat();\n    }\n    \n    /**\n     * 处理页面显示\n     */\n    handlePageVisible() {\n        // 页面重新显示时恢复心跳和检查连接\n        if (this.isConnected) {\n            this.startHeartbeat();\n            this.requestLatestState();\n        } else {\n            this.connect();\n        }\n    }\n    \n    /**\n     * 处理网络上线\n     */\n    handleNetworkOnline() {\n        console.log('🌐 网络已连接，尝试重新建立实时同步');\n        if (!this.isConnected) {\n            this.reconnectAttempts = 0;\n            this.connect();\n        }\n    }\n    \n    /**\n     * 处理网络离线\n     */\n    handleNetworkOffline() {\n        console.log('📵 网络已断开，实时同步将在网络恢复后重连');\n        this.notifyConnectionStatus('offline');\n    }\n    \n    /**\n     * 添加事件监听器\n     */\n    addEventListener(eventType, callback) {\n        if (this.eventListeners[eventType]) {\n            this.eventListeners[eventType].push(callback);\n        }\n    }\n    \n    /**\n     * 移除事件监听器\n     */\n    removeEventListener(eventType, callback) {\n        if (this.eventListeners[eventType]) {\n            const index = this.eventListeners[eventType].indexOf(callback);\n            if (index > -1) {\n                this.eventListeners[eventType].splice(index, 1);\n            }\n        }\n    }\n    \n    /**\n     * 通知事件监听器\n     */\n    notifyEventListeners(eventType, data) {\n        if (this.eventListeners[eventType]) {\n            this.eventListeners[eventType].forEach(callback => {\n                try {\n                    callback(data);\n                } catch (error) {\n                    console.error('事件监听器执行失败:', error);\n                }\n            });\n        }\n    }\n    \n    /**\n     * 通知连接状态变化\n     */\n    notifyConnectionStatus(status) {\n        this.notifyEventListeners('connection_status', { status });\n        \n        // 更新UI指示器\n        this.updateConnectionIndicator(status);\n    }\n    \n    /**\n     * 更新连接指示器\n     */\n    updateConnectionIndicator(status) {\n        const indicator = document.getElementById('realtimeSyncIndicator') || this.createConnectionIndicator();\n        \n        const statusConfig = {\n            'connected': { color: '#4caf50', text: '实时同步', icon: '🟢' },\n            'disconnected': { color: '#ff9800', text: '连接断开', icon: '🟡' },\n            'error': { color: '#f44336', text: '连接错误', icon: '🔴' },\n            'offline': { color: '#9e9e9e', text: '离线模式', icon: '⚫' },\n            'max_retries_reached': { color: '#f44336', text: '连接失败', icon: '❌' }\n        };\n        \n        const config = statusConfig[status] || statusConfig['disconnected'];\n        \n        indicator.style.color = config.color;\n        indicator.innerHTML = `${config.icon} ${config.text}`;\n        indicator.title = `实时同步状态: ${config.text}`;\n    }\n    \n    /**\n     * 创建连接指示器\n     */\n    createConnectionIndicator() {\n        const indicator = document.createElement('div');\n        indicator.id = 'realtimeSyncIndicator';\n        indicator.style.cssText = `\n            position: fixed;\n            bottom: 20px;\n            right: 20px;\n            background: rgba(255, 255, 255, 0.9);\n            padding: 6px 12px;\n            border-radius: 16px;\n            font-size: 12px;\n            border: 1px solid #ddd;\n            cursor: pointer;\n            z-index: 1000;\n            transition: all 0.3s ease;\n        `;\n        \n        indicator.onclick = () => {\n            if (window.showConversationStatus) {\n                window.showConversationStatus();\n            }\n        };\n        \n        document.body.appendChild(indicator);\n        return indicator;\n    }\n    \n    /**\n     * 生成设备ID\n     */\n    generateDeviceId() {\n        let deviceId = localStorage.getItem('deviceId');\n        if (!deviceId) {\n            deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);\n            localStorage.setItem('deviceId', deviceId);\n        }\n        return deviceId;\n    }\n    \n    /**\n     * 获取当前用户ID\n     */\n    getCurrentUserId() {\n        if (window.conversationStateManager) {\n            return window.conversationStateManager.getCurrentUserId();\n        }\n        \n        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');\n        return currentUser.id || localStorage.getItem('currentUserId');\n    }\n    \n    /**\n     * 检查是否为临时用户\n     */\n    isTemporaryUser() {\n        const userId = this.getCurrentUserId();\n        return !userId || userId.startsWith('temp_user_') || userId.startsWith('device_');\n    }\n    \n    /**\n     * 断开连接\n     */\n    disconnect() {\n        if (this.websocket) {\n            this.websocket.close(1000, 'Manual disconnect');\n        }\n        this.stopHeartbeat();\n    }\n    \n    /**\n     * 获取连接状态\n     */\n    getConnectionStatus() {\n        return {\n            connected: this.isConnected,\n            deviceId: this.deviceId,\n            reconnectAttempts: this.reconnectAttempts,\n            pendingEvents: this.pendingEvents.length\n        };\n    }\n}\n\n// 创建全局实例\nwindow.realtimeSyncManager = new RealtimeSyncManager();\n\n// 页面卸载时断开连接\nwindow.addEventListener('beforeunload', () => {\n    if (window.realtimeSyncManager) {\n        window.realtimeSyncManager.disconnect();\n    }\n});\n\n// 导出为全局函数\nwindow.sendRealtimeEvent = function(eventType, data) {\n    if (window.realtimeSyncManager) {\n        window.realtimeSyncManager.sendEvent(eventType, data);\n    }\n};\n\nwindow.getRealtimeSyncStatus = function() {\n    if (window.realtimeSyncManager) {\n        return window.realtimeSyncManager.getConnectionStatus();\n    }\n    return null;\n};\n\nconsole.log('✅ 实时同步管理器已初始化');