/**
 * 用户会话管理模块
 * 管理对话会话、历史记录、会话状态等
 */

import { StorageUtils } from '../utils/storage_utils.js';
import { FormatUtils } from '../utils/format_utils.js';

export class UserSession {
    constructor() {
        this.currentConversationId = null;
        this.conversationHistory = [];
        this.sessionStartTime = null;
    }

    /**
     * 初始化新会话
     * @param {string} doctorCode - 医生代码
     * @returns {string} 会话ID
     */
    startNewSession(doctorCode) {
        this.currentConversationId = StorageUtils.generateConversationId();
        this.conversationHistory = [];
        this.sessionStartTime = new Date();

        console.log('🆕 开始新会话:', {
            conversation_id: this.currentConversationId,
            doctor: doctorCode,
            startTime: this.sessionStartTime
        });

        // 保存会话元数据
        this.saveSessionMetadata(doctorCode);

        return this.currentConversationId;
    }

    /**
     * 保存会话元数据
     * @param {string} doctorCode - 医生代码
     */
    saveSessionMetadata(doctorCode) {
        const metadata = {
            conversation_id: this.currentConversationId,
            doctor: doctorCode,
            startTime: this.sessionStartTime.toISOString(),
            userId: StorageUtils.getCurrentUserId(),
            messageCount: 0,
            status: 'active'
        };

        StorageUtils.saveUserData(
            `session_meta_${this.currentConversationId}`,
            metadata,
            false
        );
    }

    /**
     * 获取当前会话ID
     * @returns {string|null} 会话ID
     */
    getCurrentSessionId() {
        return this.currentConversationId;
    }

    /**
     * 添加消息到会话历史
     * @param {string} type - 消息类型 (user/ai)
     * @param {string} content - 消息内容
     * @param {Object} metadata - 附加元数据
     */
    addMessage(type, content, metadata = {}) {
        const message = {
            type,
            content,
            timestamp: new Date().toISOString(),
            ...metadata
        };

        this.conversationHistory.push(message);

        // 保存到本地存储
        this.saveConversationHistory();

        console.log(`💬 添加${type}消息:`, content.substring(0, 50) + '...');
    }

    /**
     * 保存会话历史到localStorage
     */
    saveConversationHistory() {
        if (!this.currentConversationId) {
            console.warn('⚠️ 无当前会话ID，无法保存');
            return;
        }

        const storageKey = `conversationId_${this.currentConversationId}`;
        const sessionData = {
            conversation_id: this.currentConversationId,
            history: this.conversationHistory,
            lastUpdate: new Date().toISOString(),
            messageCount: this.conversationHistory.length
        };

        StorageUtils.saveUserData(storageKey, sessionData, false);
    }

    /**
     * 加载会话历史
     * @param {string} conversationId - 会话ID
     * @returns {Array} 会话历史
     */
    loadConversationHistory(conversationId) {
        const storageKey = `conversationId_${conversationId}`;
        const sessionData = StorageUtils.getUserData(storageKey, false, null);

        if (sessionData && sessionData.history) {
            this.currentConversationId = conversationId;
            this.conversationHistory = sessionData.history;
            console.log(`✅ 加载了${sessionData.history.length}条消息`);
            return sessionData.history;
        }

        console.warn('⚠️ 未找到会话历史:', conversationId);
        return [];
    }

    /**
     * 获取所有会话列表
     * @param {string} doctorCode - 医生代码（可选，用于筛选）
     * @returns {Array} 会话列表
     */
    getAllSessions(doctorCode = null) {
        const userId = StorageUtils.getCurrentUserId();
        const keys = Object.keys(localStorage);

        // 查找所有会话记录
        const sessionKeys = keys.filter(key =>
            key.startsWith('conversationId_') ||
            key.startsWith(`${userId}_conversationId_`)
        );

        const sessions = sessionKeys.map(key => {
            try {
                const data = StorageUtils.getUserData(key, false);
                if (data && data.conversation_id) {
                    // 获取会话元数据
                    const metaKey = `session_meta_${data.conversation_id}`;
                    const metadata = StorageUtils.getUserData(metaKey, false, {});

                    return {
                        ...data,
                        ...metadata,
                        storageKey: key
                    };
                }
                return null;
            } catch (error) {
                console.error('解析会话数据失败:', error);
                return null;
            }
        }).filter(session => session !== null);

        // 按医生代码筛选
        if (doctorCode) {
            return sessions.filter(s => s.doctor === doctorCode);
        }

        // 按时间排序（最新的在前）
        return sessions.sort((a, b) => {
            const timeA = new Date(a.lastUpdate || a.startTime);
            const timeB = new Date(b.lastUpdate || b.startTime);
            return timeB - timeA;
        });
    }

    /**
     * 删除会话
     * @param {string} conversationId - 会话ID
     */
    deleteSession(conversationId) {
        const storageKey = `conversationId_${conversationId}`;
        const metaKey = `session_meta_${conversationId}`;

        localStorage.removeItem(storageKey);
        localStorage.removeItem(metaKey);

        console.log('🗑️ 已删除会话:', conversationId);

        // 如果是当前会话，清除状态
        if (this.currentConversationId === conversationId) {
            this.currentConversationId = null;
            this.conversationHistory = [];
        }
    }

    /**
     * 清空所有会话
     */
    clearAllSessions() {
        const sessions = this.getAllSessions();

        sessions.forEach(session => {
            this.deleteSession(session.conversation_id);
        });

        console.log(`🧹 清空了${sessions.length}个会话`);
    }

    /**
     * 获取会话摘要
     * @param {string} conversationId - 会话ID
     * @returns {Object|null} 会话摘要
     */
    getSessionSummary(conversationId) {
        const history = this.loadConversationHistory(conversationId);

        if (history.length === 0) {
            return null;
        }

        // 提取第一条用户消息作为主诉
        const firstUserMessage = history.find(m => m.type === 'user');
        const chiefComplaint = firstUserMessage ?
            FormatUtils.truncate(firstUserMessage.content, 50) :
            '未记录';

        // 统计信息
        const userMessages = history.filter(m => m.type === 'user').length;
        const aiMessages = history.filter(m => m.type === 'ai').length;

        return {
            conversation_id: conversationId,
            chiefComplaint,
            messageCount: history.length,
            userMessageCount: userMessages,
            aiMessageCount: aiMessages,
            lastUpdate: history[history.length - 1]?.timestamp,
            firstMessage: history[0]?.timestamp
        };
    }

    /**
     * 恢复会话状态
     * @param {string} conversationId - 会话ID
     * @returns {boolean} 是否成功恢复
     */
    restoreSession(conversationId) {
        const history = this.loadConversationHistory(conversationId);

        if (history.length > 0) {
            this.currentConversationId = conversationId;
            this.conversationHistory = history;
            console.log(`✅ 恢复会话: ${conversationId}, ${history.length}条消息`);
            return true;
        }

        console.warn('⚠️ 无法恢复会话:', conversationId);
        return false;
    }

    /**
     * 结束当前会话
     * @param {Object} summary - 会话总结（可选）
     */
    endSession(summary = {}) {
        if (!this.currentConversationId) {
            return;
        }

        // 更新会话元数据
        const metaKey = `session_meta_${this.currentConversationId}`;
        const metadata = StorageUtils.getUserData(metaKey, false, {});

        metadata.status = 'completed';
        metadata.endTime = new Date().toISOString();
        metadata.messageCount = this.conversationHistory.length;
        metadata.summary = summary;

        StorageUtils.saveUserData(metaKey, metadata, false);

        console.log('✅ 会话已结束:', this.currentConversationId);

        // 清除当前状态
        this.currentConversationId = null;
        this.conversationHistory = [];
        this.sessionStartTime = null;
    }

    /**
     * 获取会话持续时间
     * @returns {number} 持续时间（秒）
     */
    getSessionDuration() {
        if (!this.sessionStartTime) {
            return 0;
        }

        const now = new Date();
        const duration = Math.floor((now - this.sessionStartTime) / 1000);
        return duration;
    }

    /**
     * 导出会话数据
     * @param {string} conversationId - 会话ID
     * @returns {Object} 导出的数据
     */
    exportSession(conversationId) {
        const history = this.loadConversationHistory(conversationId);
        const metaKey = `session_meta_${conversationId}`;
        const metadata = StorageUtils.getUserData(metaKey, false, {});

        return {
            metadata,
            messages: history,
            exportTime: new Date().toISOString(),
            version: '1.0'
        };
    }

    /**
     * 导出所有会话数据
     * @returns {Object} 所有会话数据
     */
    exportAllSessions() {
        const sessions = this.getAllSessions();

        const exportData = {
            userId: StorageUtils.getCurrentUserId(),
            exportTime: new Date().toISOString(),
            sessionCount: sessions.length,
            sessions: sessions.map(s => this.exportSession(s.conversation_id))
        };

        return exportData;
    }

    /**
     * 搜索会话
     * @param {string} keyword - 搜索关键词
     * @returns {Array} 匹配的会话列表
     */
    searchSessions(keyword) {
        if (!keyword) {
            return this.getAllSessions();
        }

        const sessions = this.getAllSessions();
        const lowerKeyword = keyword.toLowerCase();

        return sessions.filter(session => {
            const summary = this.getSessionSummary(session.conversation_id);

            if (!summary) return false;

            // 搜索主诉
            if (summary.chiefComplaint.toLowerCase().includes(lowerKeyword)) {
                return true;
            }

            // 搜索消息内容
            const history = this.loadConversationHistory(session.conversation_id);
            return history.some(msg =>
                msg.content.toLowerCase().includes(lowerKeyword)
            );
        });
    }

    /**
     * 获取会话统计信息
     * @returns {Object} 统计数据
     */
    getStatistics() {
        const sessions = this.getAllSessions();

        const stats = {
            totalSessions: sessions.length,
            activeSessions: sessions.filter(s => s.status === 'active').length,
            completedSessions: sessions.filter(s => s.status === 'completed').length,
            totalMessages: 0,
            doctorBreakdown: {}
        };

        sessions.forEach(session => {
            stats.totalMessages += session.messageCount || 0;

            // 按医生统计
            const doctor = session.doctor || 'unknown';
            if (!stats.doctorBreakdown[doctor]) {
                stats.doctorBreakdown[doctor] = 0;
            }
            stats.doctorBreakdown[doctor]++;
        });

        return stats;
    }
}
