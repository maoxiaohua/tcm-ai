/**
 * SessionManager - v4.0 重构版
 *
 * 核心理念：简单、清晰、可靠
 * - 纯内存状态管理
 * - 单一数据源（后端API）
 * - 清晰的API接口
 */

class SessionManager {
    constructor() {
        // 当前会话状态（纯内存）
        this.conversationId = null;
        this.messages = [];
        this.currentDoctor = null;
        this.userId = null;

        console.log('SessionManager v4.0 initialized');
    }

    /**
     * 初始化（页面加载时调用）
     */
    init(userId) {
        this.userId = userId;
        console.log(`SessionManager initialized for user: ${userId}`);
    }

    /**
     * 切换医生 - 核心功能
     *
     * 调用后端API，后端负责：
     * 1. 检查该医生的最新consultation是否有prescription
     * 2. 如果有处方 → 创建新consultation
     * 3. 如果无处方 → 返回现有consultation
     *
     * @param {string} doctorId - 医生ID
     * @returns {Promise<Object>} {conversationId, messages, isNew, reason}
     */
    async switchDoctor(doctorId) {
        console.log(`[SessionManager] 切换到医生: ${doctorId}`);

        try {
            // 1. 获取认证token（与其他模块保持一致）
            const token = window.userToken || localStorage.getItem('tcm_auth_token');
            if (!token) {
                throw new Error('未登录或会话已过期');
            }

            // 2. 调用后端API（使用与其他模块一致的header格式）
            const response = await fetch('/api/conversation/switch-doctor', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ doctor_id: doctorId })
            });

            if (!response.ok) {
                const errorData = await response.json();

                // 特殊处理401错误：会话过期
                if (response.status === 401) {
                    console.error('❌ 登录已过期，需要重新登录');
                    alert('您的登录已过期，请重新登录');

                    // 清除过期token
                    localStorage.removeItem('tcm_auth_token');
                    window.userToken = null;

                    // 跳转到登录页
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 1000);

                    throw new Error('登录已过期');
                }

                throw new Error(errorData.detail || '切换医生失败');
            }

            const data = await response.json();

            // 3. 更新内存状态
            this.conversationId = data.consultation_id;
            this.messages = data.messages || [];
            this.currentDoctor = doctorId;

            // 4. 日志输出
            if (data.is_new) {
                console.log(`✨ [SessionManager] 新对话: ${data.reason}`);
                console.log(`   Consultation ID: ${this.conversationId}`);
            } else {
                console.log(`📋 [SessionManager] 继续对话: ${data.reason}`);
                console.log(`   Consultation ID: ${this.conversationId}`);
                console.log(`   历史消息: ${this.messages.length}条`);
            }

            // 5. 返回数据供UI层使用
            return {
                conversationId: this.conversationId,
                messages: this.messages,
                isNew: data.is_new,
                reason: data.reason,
                message: data.message
            };

        } catch (error) {
            console.error('[SessionManager] 切换医生失败:', error);
            throw error;
        }
    }

    /**
     * 添加消息到当前会话
     */
    addMessage(type, content, time = null) {
        const message = {
            type: type,
            content: content,
            time: time || new Date().toLocaleTimeString(),
            timestamp: Date.now()
        };

        this.messages.push(message);
        return message;
    }

    /**
     * 获取当前会话ID
     */
    getConversationId() {
        return this.conversationId;
    }

    /**
     * 获取当前医生ID
     */
    getCurrentDoctor() {
        return this.currentDoctor;
    }

    /**
     * 获取当前消息列表
     */
    getMessages() {
        return this.messages;
    }

    /**
     * 清除会话（开始新对话按钮）
     */
    clearSession() {
        console.log('[SessionManager] 清除当前会话');
        this.conversationId = null;
        this.messages = [];
        // 注意：不清除currentDoctor，保持医生选择
    }

    /**
     * 完全重置（退出登录等场景）
     */
    reset() {
        console.log('[SessionManager] 完全重置');
        this.conversationId = null;
        this.messages = [];
        this.currentDoctor = null;
        this.userId = null;
    }
}

// 创建全局实例
if (typeof window !== 'undefined') {
    window.sessionManager = new SessionManager();
    console.log('✅ SessionManager全局实例已创建: window.sessionManager');
}
