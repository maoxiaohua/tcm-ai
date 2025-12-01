/**
 * TCM-AI 应用全局常量定义
 *
 * 统一管理所有常量，避免重复定义
 * @version 1.0.0
 * @date 2025-11-28
 */

(function() {
    'use strict';

    // ============================================
    // 医生头像映射
    // ============================================
    const DOCTOR_AVATAR_MAP = {
        "jin_daifu": "👨‍⚕️",
        "zhang_zhongjing": "🎯",
        "ye_tianshi": "🌟",
        "li_dongyuan": "🏥",
        "zheng_qin_an": "⚡",
        "liu_dushui": "📚"
    };

    // ============================================
    // 处方相关常量
    // ============================================
    const PRESCRIPTION_KEYWORDS = [
        '【君药】',
        '【处方】',
        '【臣药】',
        '【佐药】',
        '【使药】',
        '解锁完整处方',
        '处方信息'
    ];

    const PRESCRIPTION_STATUS = {
        PENDING: 'pending',
        REVIEWED: 'reviewed',
        APPROVED: 'approved',
        REJECTED: 'rejected',
        PAID: 'paid',
        COMPLETED: 'completed'
    };

    // ============================================
    // API配置
    // ============================================
    const API_CONFIG = {
        TIMEOUT: 30000,           // 30秒超时
        RETRY_COUNT: 3,           // 重试次数
        RETRY_DELAY: 1000,        // 重试延迟1秒
        POLLING_INTERVAL: 30000   // 轮询间隔30秒
    };

    // ============================================
    // 存储键前缀
    // ============================================
    const STORAGE_KEYS = {
        CURRENT_USER: 'currentUser',
        USER_DATA: 'userData',
        AUTH_TOKEN: 'tcm_auth_token',
        CONVERSATION_ID: 'conversationId_',
        DOCTOR_HISTORY: 'tcm_doctor_history_',
        DOCTOR_MESSAGES: 'tcm_doctor_messages_',
        CONVERSATION_LIST: 'conversation_list_',
        CONVERSATION_MESSAGES: 'conversation_messages_',
        PRESCRIPTION_ORIGINAL: 'prescription_original_content_'
    };

    // ============================================
    // 初始化延迟时间（毫秒）
    // ============================================
    const INIT_DELAYS = {
        DOCTOR_RENDER: 1000,
        CHROME_FIX: 2000,
        POLLED_REFRESH: 3000,
        BACKGROUND_SYNC: 5000,
        USER_DISPLAY_UPDATE: 500
    };

    // ============================================
    // 对话阶段
    // ============================================
    const CONVERSATION_STAGES = {
        INQUIRY: 'inquiry',
        DIAGNOSIS: 'diagnosis',
        PRESCRIPTION: 'prescription',
        COMPLETED: 'completed'
    };

    // ============================================
    // 消息类型
    // ============================================
    const MESSAGE_TYPES = {
        USER: 'user',
        AI: 'ai',
        SYSTEM: 'system'
    };

    // ============================================
    // 症状关键词（用于快速检测）
    // ============================================
    const SYMPTOM_KEYWORDS = [
        '头痛', '头晕', '发热', '咳嗽', '胸闷', '心悸', '失眠', '腹痛',
        '腹泻', '便秘', '恶心', '呕吐', '乏力', '疲劳', '食欲', '口干',
        '口苦', '盗汗', '自汗', '气短', '胸痛', '腰痛', '关节痛', '肌肉痛',
        '水肿', '尿频', '尿急', '月经', '白带', '耳鸣', '眼花', '鼻塞',
        '流涕', '咽痛', '牙痛', '舌苔', '脉象'
    ];

    // ============================================
    // 消息格式化正则表达式（预编译提升性能）
    // ============================================
    const MESSAGE_FORMAT_PATTERNS = {
        // 标题格式化
        SECTION_TITLE: /【([^】]+)】/g,
        NUMBERED_TITLE: /^(\d+[.、）)])/gm,

        // 换行处理
        DOUBLE_NEWLINE: /\n\n/g,
        SINGLE_NEWLINE: /\n/g,

        // 特殊格式
        BOLD_TEXT: /\*\*([^*]+)\*\*/g,
        EMPHASIS_TEXT: /\*([^*]+)\*/g,

        // 处方检测
        PRESCRIPTION_MARKER: /【(?:君药|臣药|佐药|使药|处方)】/
    };

    // ============================================
    // 🔑 v4.3 新增：localStorage安全处理工具
    // ============================================

    /**
     * 安全读取localStorage
     * @param {string} key - 存储键
     * @param {*} defaultValue - 默认值
     * @returns {*} 解析后的值或默认值
     */
    function safeGetItem(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            if (item === null || item === undefined) {
                return defaultValue;
            }
            // 尝试解析JSON
            try {
                return JSON.parse(item);
            } catch {
                // 不是JSON，返回原始字符串
                return item;
            }
        } catch (error) {
            console.warn(`[Storage] 读取 ${key} 失败:`, error);
            return defaultValue;
        }
    }

    /**
     * 安全写入localStorage
     * @param {string} key - 存储键
     * @param {*} value - 要存储的值
     * @returns {boolean} 是否成功
     */
    function safeSetItem(key, value) {
        try {
            const serialized = typeof value === 'string' ? value : JSON.stringify(value);
            localStorage.setItem(key, serialized);
            return true;
        } catch (error) {
            console.warn(`[Storage] 写入 ${key} 失败:`, error);
            // 可能是存储空间不足，尝试清理过期数据
            if (error.name === 'QuotaExceededError') {
                cleanupExpiredStorage();
                try {
                    localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
                    return true;
                } catch {
                    return false;
                }
            }
            return false;
        }
    }

    /**
     * 安全删除localStorage项
     * @param {string} key - 存储键
     */
    function safeRemoveItem(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.warn(`[Storage] 删除 ${key} 失败:`, error);
        }
    }

    /**
     * 清理过期的localStorage数据
     * 删除超过24小时的临时数据
     */
    function cleanupExpiredStorage() {
        try {
            const now = Date.now();
            const expiryTime = 24 * 60 * 60 * 1000; // 24小时
            const keysToRemove = [];

            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (!key) continue;

                // 检查带时间戳的数据
                if (key.startsWith('tcm_doctor_messages_') || key.startsWith('original_content_')) {
                    try {
                        const data = JSON.parse(localStorage.getItem(key) || '{}');
                        if (data.timestamp && (now - data.timestamp) > expiryTime) {
                            keysToRemove.push(key);
                        }
                    } catch {
                        // 解析失败的数据也删除
                        keysToRemove.push(key);
                    }
                }
            }

            keysToRemove.forEach(key => localStorage.removeItem(key));

            if (keysToRemove.length > 0) {
                console.log(`[Storage] 清理了 ${keysToRemove.length} 个过期项`);
            }
        } catch (error) {
            console.warn('[Storage] 清理过期数据失败:', error);
        }
    }

    /**
     * 获取localStorage使用情况
     * @returns {Object} 使用情况统计
     */
    function getStorageUsage() {
        try {
            let totalSize = 0;
            const items = {};

            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (!key) continue;
                const value = localStorage.getItem(key) || '';
                const size = (key.length + value.length) * 2; // UTF-16编码
                totalSize += size;
                items[key] = size;
            }

            return {
                totalSize,
                totalSizeKB: (totalSize / 1024).toFixed(2),
                itemCount: localStorage.length,
                items
            };
        } catch (error) {
            console.warn('[Storage] 获取使用情况失败:', error);
            return { totalSize: 0, totalSizeKB: '0', itemCount: 0, items: {} };
        }
    }

    // Storage工具对象
    const StorageUtils = {
        get: safeGetItem,
        set: safeSetItem,
        remove: safeRemoveItem,
        cleanup: cleanupExpiredStorage,
        getUsage: getStorageUsage
    };

    // ============================================
    // 暴露到全局
    // ============================================
    window.TCM_CONSTANTS = {
        DOCTOR_AVATAR_MAP,
        PRESCRIPTION_KEYWORDS,
        PRESCRIPTION_STATUS,
        API_CONFIG,
        STORAGE_KEYS,
        INIT_DELAYS,
        CONVERSATION_STAGES,
        MESSAGE_TYPES,
        SYMPTOM_KEYWORDS,
        MESSAGE_FORMAT_PATTERNS
    };

    // 向后兼容：直接暴露医生头像映射
    window.doctorAvatarMap = DOCTOR_AVATAR_MAP;

    // 🔑 v4.3 新增：暴露存储工具
    window.StorageUtils = StorageUtils;

    console.log('✅ [Constants] 常量模块加载完成');
    console.log('📦 [Constants] 已暴露 StorageUtils 工具');

})();
