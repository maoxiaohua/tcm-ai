/**
 * 存储工具模块
 * 提供 localStorage 和 sessionStorage 的封装和管理
 */

export class StorageUtils {
    /**
     * 获取当前用户ID
     * @returns {string} 用户ID
     */
    static getCurrentUserId() {
        // 优先从 sessionStorage 获取
        let userId = sessionStorage.getItem('current_user_id');

        if (!userId) {
            // 尝试从 localStorage 获取
            userId = localStorage.getItem('current_user_id');
        }

        if (!userId) {
            // 尝试从 device_id 获取
            userId = localStorage.getItem('device_id');
        }

        if (!userId) {
            // 生成新的设备ID
            userId = 'device_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('device_id', userId);
            localStorage.setItem('current_user_id', userId);
        }

        return userId;
    }

    /**
     * 设置当前用户ID
     * @param {string} userId - 用户ID
     */
    static setCurrentUserId(userId) {
        sessionStorage.setItem('current_user_id', userId);
        localStorage.setItem('current_user_id', userId);
    }

    /**
     * 生成会话ID
     * @returns {string} UUID格式的会话ID
     */
    static generateConversationId() {
        return 'xxxx-xxxx-4xxx-yxxx-xxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * 保存用户数据到 localStorage（带用户ID前缀）
     * @param {string} key - 存储键
     * @param {any} value - 存储值
     * @param {boolean} useUserPrefix - 是否使用用户ID前缀
     */
    static saveUserData(key, value, useUserPrefix = true) {
        const userId = this.getCurrentUserId();
        const storageKey = useUserPrefix ? `${userId}_${key}` : key;

        if (typeof value === 'object') {
            localStorage.setItem(storageKey, JSON.stringify(value));
        } else {
            localStorage.setItem(storageKey, value);
        }
    }

    /**
     * 获取用户数据从 localStorage
     * @param {string} key - 存储键
     * @param {boolean} useUserPrefix - 是否使用用户ID前缀
     * @param {any} defaultValue - 默认值
     * @returns {any} 存储的值
     */
    static getUserData(key, useUserPrefix = true, defaultValue = null) {
        const userId = this.getCurrentUserId();
        const storageKey = useUserPrefix ? `${userId}_${key}` : key;

        const value = localStorage.getItem(storageKey);

        if (value === null) {
            return defaultValue;
        }

        // 尝试解析JSON
        try {
            return JSON.parse(value);
        } catch {
            return value;
        }
    }

    /**
     * 删除用户数据
     * @param {string} key - 存储键
     * @param {boolean} useUserPrefix - 是否使用用户ID前缀
     */
    static removeUserData(key, useUserPrefix = true) {
        const userId = this.getCurrentUserId();
        const storageKey = useUserPrefix ? `${userId}_${key}` : key;
        localStorage.removeItem(storageKey);
    }

    /**
     * 清理当前用户的所有数据
     */
    static clearCurrentUserData() {
        const userId = this.getCurrentUserId();
        const keys = Object.keys(localStorage);

        // 删除所有带用户ID前缀的数据
        const userHistoryKeys = keys.filter(key =>
            key.startsWith(userId + '_') ||
            key.startsWith('conversationId_') ||
            key.startsWith('tcm_doctor_history_')
        );

        userHistoryKeys.forEach(key => localStorage.removeItem(key));

        // 清除 sessionStorage
        sessionStorage.clear();

        console.log(`✅ 已清除用户 ${userId} 的 ${userHistoryKeys.length} 条数据`);
    }

    /**
     * 清理旧格式的用户数据（不含用户ID的历史记录）
     */
    static cleanupOldUserData() {
        const currentUserId = this.getCurrentUserId();
        const keys = Object.keys(localStorage);

        // 查找旧格式的历史记录键
        const oldHistoryKeys = keys.filter(key =>
            key.startsWith('tcm_doctor_history_') &&
            !key.includes(currentUserId)
        );

        if (oldHistoryKeys.length > 0) {
            console.log(`🧹 发现 ${oldHistoryKeys.length} 条旧格式历史记录，准备迁移...`);

            // 迁移到新格式
            oldHistoryKeys.forEach(oldKey => {
                try {
                    const data = localStorage.getItem(oldKey);
                    const newKey = `${currentUserId}_${oldKey}`;
                    localStorage.setItem(newKey, data);
                    localStorage.removeItem(oldKey);
                } catch (error) {
                    console.error(`迁移失败: ${oldKey}`, error);
                }
            });

            console.log('✅ 数据迁移完成');
        }
    }

    /**
     * 清理旧的历史记录（保留最近N条）
     * @param {number} keepCount - 保留的记录数
     */
    static cleanOldHistoryRecords(keepCount = 50) {
        try {
            const keys = Object.keys(localStorage);
            const userId = this.getCurrentUserId();

            // 找出所有会话记录
            const conversationKeys = keys.filter(key =>
                key.startsWith('conversationId_') ||
                key.startsWith(`${userId}_conversationId_`)
            );

            if (conversationKeys.length > keepCount) {
                // 按时间戳排序
                const sortedKeys = conversationKeys.sort((a, b) => {
                    const timeA = this.getUserData(a, false)?.timestamp || 0;
                    const timeB = this.getUserData(b, false)?.timestamp || 0;
                    return timeB - timeA; // 降序
                });

                // 删除旧记录
                const keysToDelete = sortedKeys.slice(keepCount);
                keysToDelete.forEach(key => localStorage.removeItem(key));

                console.log(`🧹 清理了 ${keysToDelete.length} 条旧记录`);
            }
        } catch (error) {
            console.error('清理历史记录失败:', error);
        }
    }

    /**
     * 获取所有会话记录
     * @returns {Array} 会话记录数组
     */
    static getAllConversations() {
        const keys = Object.keys(localStorage);
        const userId = this.getCurrentUserId();

        const conversationKeys = keys.filter(key =>
            key.startsWith('conversationId_') ||
            key.startsWith(`${userId}_conversationId_`)
        );

        return conversationKeys.map(key => {
            try {
                return this.getUserData(key, false);
            } catch {
                return null;
            }
        }).filter(conv => conv !== null);
    }

    /**
     * 保存处方状态
     * @param {string} prescriptionId - 处方ID
     * @param {string} status - 状态（unlocked/locked）
     */
    static savePrescriptionStatus(prescriptionId, status) {
        const userId = this.getCurrentUserId();
        const storageKey = `prescription_status_${userId}`;

        let statusMap = this.getUserData(storageKey, false, {});
        statusMap[prescriptionId] = {
            status: status,
            timestamp: new Date().toISOString()
        };

        this.saveUserData(storageKey, statusMap, false);
    }

    /**
     * 获取处方状态
     * @param {string} prescriptionId - 处方ID
     * @returns {Object|null} 处方状态对象
     */
    static getPrescriptionStatus(prescriptionId) {
        const userId = this.getCurrentUserId();
        const storageKey = `prescription_status_${userId}`;

        const statusMap = this.getUserData(storageKey, false, {});
        return statusMap[prescriptionId] || null;
    }

    /**
     * 获取存储统计信息
     * @returns {Object} 统计信息
     */
    static getStorageStats() {
        const keys = Object.keys(localStorage);
        const userId = this.getCurrentUserId();

        return {
            totalKeys: keys.length,
            userKeys: keys.filter(k => k.startsWith(userId)).length,
            conversationKeys: keys.filter(k => k.startsWith('conversationId_')).length,
            historyKeys: keys.filter(k => k.startsWith('tcm_doctor_history_')).length,
            prescriptionKeys: keys.filter(k => k.startsWith('prescription_')).length
        };
    }
}
