/**
 * TCM-AI 对话管理器
 * 负责对话历史的隔离存储和加载，确保不同对话互不干扰
 *
 * 核心功能：
 * 1. 按conversation_id隔离存储对话
 * 2. 切换医生时加载该医生的最新对话
 * 3. 新对话按钮创建全新对话
 *
 * @version 3.0
 * @date 2025-11-25
 */

class ConversationManager {
    constructor() {
        this.currentConversationId = null;
        this.currentDoctor = null;
        this.currentUserId = null;

        console.log('✅ ConversationManager 初始化完成');
    }

    /**
     * 获取对话索引表
     * @param {string} userId - 用户ID
     * @returns {Object} 对话索引对象
     */
    getConversationIndex(userId) {
        const key = `conversation_list_${userId}`;
        const stored = localStorage.getItem(key);

        if (stored) {
            try {
                return JSON.parse(stored);
            } catch (error) {
                console.error('解析对话索引失败:', error);
                return {};
            }
        }

        return {};
    }

    /**
     * 保存对话索引
     * @param {string} userId - 用户ID
     * @param {Object} index - 对话索引对象
     */
    saveConversationIndex(userId, index) {
        const key = `conversation_list_${userId}`;
        try {
            localStorage.setItem(key, JSON.stringify(index));
        } catch (error) {
            console.error('保存对话索引失败:', error);
        }
    }

    /**
     * 获取或创建对话
     * @param {string} userId - 用户ID
     * @param {string} doctorId - 医生ID
     * @param {boolean} forceNew - 是否强制创建新对话
     * @returns {string} conversation_id
     */
    getOrCreateConversation(userId, doctorId, forceNew = false) {
        const index = this.getConversationIndex(userId);

        if (!forceNew) {
            // 🔑 查找该医生的最新活跃对话
            const conversations = Object.values(index).filter(conv =>
                conv.doctor_id === doctorId && conv.is_active
            );

            if (conversations.length > 0) {
                // 按最后消息时间排序，返回最新的
                conversations.sort((a, b) =>
                    new Date(b.last_message_at) - new Date(a.last_message_at)
                );

                const latest = conversations[0];
                console.log(`✅ 加载${doctorId}的最新对话: ${latest.conversation_id}`);

                this.currentConversationId = latest.conversation_id;
                this.currentDoctor = doctorId;
                this.currentUserId = userId;

                return latest.conversation_id;
            }
        }

        // 创建新对话
        const conversationId = this.generateConversationId();

        index[conversation_id] = {
            conversation_id: conversation_id,
            doctor_id: doctorId,
            user_id: userId,
            created_at: new Date().toISOString(),
            last_message_at: new Date().toISOString(),
            is_active: true,
            message_count: 0
        };

        this.saveConversationIndex(userId, index);

        console.log(`✨ 创建新对话: ${conversation_id} (医生: ${doctorId})`);

        this.currentConversationId = conversation_id;
        this.currentDoctor = doctorId;
        this.currentUserId = userId;

        return conversationId;
    }

    /**
     * 生成对话ID
     * @returns {string} 对话ID
     */
    generateConversationId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 6);
        return `${timestamp}-${random}`;
    }

    /**
     * 保存对话消息
     * @param {string} conversationId - 对话ID
     * @param {Array} messages - 消息数组
     */
    saveConversationMessages(conversation_id, messages) {
        if (!conversation_id) {
            console.warn('⚠️ conversationId为空，无法保存消息');
            return;
        }

        const key = `conversation_messages_${conversation_id}`;
        const data = {
            conversation_id: conversation_id,
            doctor_id: this.currentDoctor,
            user_id: this.currentUserId,
            messages: messages,
            last_updated: new Date().toISOString(),
            version: '3.0'
        };

        try {
            localStorage.setItem(key, JSON.stringify(data));

            // 更新索引中的最后消息时间
            const userId = this.currentUserId;
            if (userId) {
                const index = this.getConversationIndex(userId);

                if (index[conversation_id]) {
                    index[conversation_id].last_message_at = new Date().toISOString();
                    index[conversation_id].message_count = messages.length;
                    this.saveConversationIndex(userId, index);
                }
            }

            console.log(`💾 保存对话 ${conversation_id}: ${messages.length}条消息`);
        } catch (error) {
            console.error('保存对话消息失败:', error);
        }
    }

    /**
     * 加载对话消息
     * @param {string} conversationId - 对话ID
     * @returns {Array} 消息数组
     */
    loadConversationMessages(conversation_id) {
        if (!conversation_id) {
            console.warn('⚠️ conversationId为空，返回空数组');
            return [];
        }

        const key = `conversation_messages_${conversation_id}`;
        const stored = localStorage.getItem(key);

        if (stored) {
            try {
                const data = JSON.parse(stored);
                console.log(`📱 加载对话 ${conversation_id}: ${data.messages?.length || 0}条消息`);
                return data.messages || [];
            } catch (error) {
                console.error(`解析对话 ${conversation_id} 失败:`, error);
                return [];
            }
        }

        console.log(`📝 对话 ${conversation_id} 无历史记录`);
        return [];
    }

    /**
     * 切换医生 - 加载该医生的最新对话
     * @param {string} userId - 用户ID
     * @param {string} newDoctorId - 新医生ID
     * @returns {Object} {conversation_id, messages}
     */
    switchDoctor(userId, newDoctorId) {
        console.log(`🔄 切换医生: ${newDoctorId}`);

        // 获取该医生的最新对话（不创建新对话）
        let conversationId = this.getOrCreateConversation(userId, newDoctorId, false);
        let messages = this.loadConversationMessages(conversation_id);

        // 🔑 v3.0 关键修复：如果最新对话已有处方（已完成），自动创建新对话
        console.log(`🔍 [DEBUG] 检查处方 - 消息数量: ${messages ? messages.length : 0}`);
        if (messages && messages.length > 0) {
            console.log(`🔍 [DEBUG] 第一条消息:`, messages[0]);
            console.log(`🔍 [DEBUG] 最后一条消息:`, messages[messages.length - 1]);
        }

        const hasPrescription = messages && messages.some(msg => {
            const hasKeyword = msg.type === 'ai' && msg.content && (
                msg.content.includes('【君药】') ||
                msg.content.includes('【处方】') ||
                msg.content.includes('解锁完整处方') ||
                msg.content.includes('【臣药】')
            );
            if (hasKeyword) {
                console.log(`🎯 [DEBUG] 检测到处方关键词!`);
            }
            return hasKeyword;
        });

        console.log(`🔍 [DEBUG] 处方检测最终结果: ${hasPrescription}`);

        if (hasPrescription) {
            console.log(`⚠️ 检测到该医生的最新对话已有处方，自动创建新对话`);
            // 创建新对话，但保留旧对话的历史记录（用户可以查看）
            conversationId = this.startNewConversation(userId, newDoctorId);
            messages = []; // 新对话从空开始
            console.log(`✨ 已创建新对话: ${conversation_id}`);
        }

        return {
            conversation_id,
            messages
        };
    }

    /**
     * 开始新对话
     * @param {string} userId - 用户ID
     * @param {string} doctorId - 医生ID
     * @returns {string} conversation_id
     */
    startNewConversation(userId, doctorId) {
        console.log(`✨ 开始新对话: 医生=${doctorId}`);

        // 先结束当前对话
        if (this.currentConversationId) {
            this.endConversation(this.currentConversationId);
        }

        // 强制创建新对话
        return this.getOrCreateConversation(userId, doctorId, true);
    }

    /**
     * 获取医生的所有对话列表
     * @param {string} userId - 用户ID
     * @param {string} doctorId - 医生ID
     * @returns {Array} 对话列表
     */
    getDoctorConversations(userId, doctorId) {
        const index = this.getConversationIndex(userId);
        const conversations = Object.values(index).filter(conv =>
            conv.doctor_id === doctorId
        );

        // 按时间排序
        conversations.sort((a, b) =>
            new Date(b.last_message_at) - new Date(a.last_message_at)
        );

        return conversations;
    }

    /**
     * 结束对话
     * @param {string} conversationId - 对话ID
     */
    endConversation(conversation_id) {
        const userId = this.currentUserId;
        if (!userId) return;

        const index = this.getConversationIndex(userId);

        if (index[conversation_id]) {
            index[conversation_id].is_active = false;
            index[conversation_id].ended_at = new Date().toISOString();
            this.saveConversationIndex(userId, index);

            console.log(`🏁 结束对话: ${conversation_id}`);
        }
    }

    /**
     * 清理旧对话数据（超过30天）
     * @param {string} userId - 用户ID
     * @returns {number} 清理的对话数量
     */
    cleanupOldConversations(userId) {
        const index = this.getConversationIndex(userId);
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        let cleanedCount = 0;

        Object.keys(index).forEach(convId => {
            const conv = index[convId];
            const lastActivity = new Date(conv.last_message_at);

            if (lastActivity < thirtyDaysAgo) {
                // 删除消息数据
                localStorage.removeItem(`conversation_messages_${convId}`);
                // 从索引移除
                delete index[convId];
                cleanedCount++;
            }
        });

        if (cleanedCount > 0) {
            this.saveConversationIndex(userId, index);
            console.log(`🗑️ 清理了 ${cleanedCount} 个旧对话`);
        }

        return cleanedCount;
    }

    /**
     * 迁移旧数据到新格式
     * @param {string} userId - 用户ID
     * @returns {number} 迁移的对话数量
     */
    migrateOldConversationData(userId) {
        console.log('🔄 开始迁移旧对话数据...');

        const allKeys = Object.keys(localStorage);
        const oldHistoryKeys = allKeys.filter(key =>
            key.startsWith('tcm_doctor_history_') && key.includes(userId)
        );

        let migratedCount = 0;

        oldHistoryKeys.forEach(key => {
            try {
                const data = JSON.parse(localStorage.getItem(key));
                // 从key中提取完整的医生ID
                // key格式: tcm_doctor_history_{userId}_{doctorId}
                // 例如: tcm_doctor_history_usr_20250920_5741e17a78e8_zhang_zhongjing
                // 先去掉前缀和userId，剩下的就是doctorId
                const prefix = `tcm_doctor_history_${userId}_`;
                const doctorId = key.replace(prefix, '');

                // 提取messages
                let messages = [];
                if (data.messages) {
                    messages = data.messages;
                } else if (data.consultations && Array.isArray(data.consultations)) {
                    // consultations格式
                    data.consultations.forEach(consultation => {
                        if (consultation.messages) {
                            messages = messages.concat(consultation.messages);
                        }
                    });
                }

                if (messages.length > 0) {
                    // 创建新对话
                    const conversationId = this.generateConversationId();

                    // 保存到新格式
                    this.currentUserId = userId;
                    this.currentDoctor = doctorId;
                    this.saveConversationMessages(conversation_id, messages);

                    // 添加到索引
                    const index = this.getConversationIndex(userId);
                    index[conversation_id] = {
                        conversation_id: conversation_id,
                        doctor_id: doctorId,
                        user_id: userId,
                        created_at: data.lastUpdated || new Date().toISOString(),
                        last_message_at: data.lastUpdated || new Date().toISOString(),
                        is_active: true,
                        message_count: messages.length,
                        migrated_from_old_format: true
                    };
                    this.saveConversationIndex(userId, index);

                    console.log(`✅ 迁移了医生 ${doctorId} 的 ${messages.length} 条消息`);
                    migratedCount++;
                }

                // 备份旧数据（不删除，以防万一）
                const backupKey = `${key}_backup_${Date.now()}`;
                localStorage.setItem(backupKey, localStorage.getItem(key));

                // 删除旧数据
                localStorage.removeItem(key);

            } catch (error) {
                console.error(`迁移 ${key} 失败:`, error);
            }
        });

        console.log(`✅ 迁移完成，共迁移 ${migratedCount} 个对话`);
        return migratedCount;
    }

    /**
     * 获取当前状态信息（调试用）
     * @returns {Object} 状态信息
     */
    getDebugInfo() {
        return {
            currentConversationId: this.currentConversationId,
            currentDoctor: this.currentDoctor,
            currentUserId: this.currentUserId,
            indexSize: Object.keys(this.getConversationIndex(this.currentUserId || '')).length
        };
    }
}

// 创建全局实例
if (!window.conversationManager) {
    window.conversationManager = new ConversationManager();
    console.log('✅ ConversationManager 全局实例已创建');
}

// 暴露全局调试函数
window.showConversationDebug = function() {
    if (window.conversationManager) {
        const info = window.conversationManager.getDebugInfo();
        console.table(info);
        return info;
    }
};

// 在应用初始化时运行数据迁移（仅运行一次）
document.addEventListener('DOMContentLoaded', function() {
    // 延迟执行，确保其他脚本已加载
    setTimeout(function() {
        if (localStorage.getItem('conversation_data_migrated_v3') !== 'true') {
            console.log('🔄 首次加载，准备迁移旧数据...');

            // 获取用户ID
            let userId = null;
            if (typeof window.getCurrentUserId === 'function') {
                userId = window.getCurrentUserId();
            } else if (localStorage.getItem('currentUser')) {
                try {
                    const currentUser = JSON.parse(localStorage.getItem('currentUser'));
                    userId = currentUser.id;
                } catch (e) {
                    console.warn('获取用户ID失败:', e);
                }
            }

            if (userId && window.conversationManager) {
                const migratedCount = window.conversationManager.migrateOldConversationData(userId);
                localStorage.setItem('conversation_data_migrated_v3', 'true');

                if (migratedCount > 0) {
                    console.log(`✅ 数据迁移完成，迁移了 ${migratedCount} 个对话`);
                }
            }
        }
    }, 2000); // 延迟2秒执行
});

console.log('📦 conversation_manager.js 加载完成');
