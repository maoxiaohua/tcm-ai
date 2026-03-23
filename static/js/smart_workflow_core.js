/**
 * smart_workflow_core.js
 * TCM-AI 智能工作流核心模块
 *
 * 功能说明：
 * - 全局变量声明和初始化
 * - 用户状态管理（登录/访客/切换）
 * - 对话ID生成和管理
 * - 用户数据清理和隔离
 *
 * 依赖：无外部依赖，作为基础模块最先加载
 *
 * @version 1.0.0
 * @date 2025-11-20
 */

// ============================================
// 全局变量声明
// ============================================

// 对话相关变量
window.currentConversationId = '';
window.selectedDoctor = 'jin_daifu'; // 默认金大夫

// 语音功能变量
window.isVoiceRecording = false;
window.mediaRecorder = null;
window.audioChunks = [];

// 认证相关变量
window.currentUser = null;
window.userToken = null;

// 用户状态追踪变量
window.lastKnownUser = null;

// 医生数据（动态加载）
// Chrome浏览器兼容性修复：立即初始化默认医生数据，确保页面加载时医生列表可用
// 后续会通过API异步更新为完整的医生列表
window.doctors = {
    "jin_daifu": {
        "name": "金大夫",
        "school": "经方大师",
        "avatar": "👨‍⚕️",
        "specialty": "经方应用、疑难杂症、综合诊疗",
        "introduction": "经方大师，深通古典医学，擅长运用经典方剂解决现代疑难杂症，临床经验丰富。"
    },
    "zhang_zhongjing": {
        "name": "张仲景",
        "school": "伤寒派",
        "avatar": "🎯",
        "specialty": "外感病、内伤杂病、急症",
        "introduction": "伤寒派以《伤寒论》为理论基础，擅长六经辨证，治疗外感热病和内伤杂病。用药精准，方证对应。"
    }
};

// 🔑 v4.2优化：医生头像映射已移至constants.js，通过window.doctorAvatarMap访问
// 如果constants.js未加载，提供备用值
if (!window.doctorAvatarMap) {
    window.doctorAvatarMap = {
        "jin_daifu": "👨‍⚕️",
        "zhang_zhongjing": "🎯"
    };
}

// 🔑 v4.2优化：移除冗余的本地变量引用
// 所有全局变量通过 window.variableName 直接访问，避免同步问题

// ============================================
// 核心函数
// ============================================

/**
 * 生成对话ID - 基于用户ID隔离
 */
function generateConversationId() {
    const userId = getCurrentUserId();

    window.currentConversationId = 'xxxx-xxxx-4xxx-yxxx-xxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });

    // 同步本地变量
    currentConversationId = window.currentConversationId;

    // 使用用户ID作为存储key，确保不同用户隔离
    const storageKey = `conversationId_${userId}`;
    localStorage.setItem(storageKey, window.currentConversationId);

    return window.currentConversationId;
}

/**
 * 获取当前用户ID
 * 智能工作流页面(index_smart_workflow.html)只使用登录用户数据
 * 这确保与游客页面的数据完全隔离
 */
function getCurrentUserId() {
    // 检查URL参数中的用户ID（从历史页面跳转）
    const urlParams = new URLSearchParams(window.location.search);
    const urlUserId = urlParams.get('user_id');
    if (urlUserId && urlUserId !== 'anonymous') {
        console.log('🔗 从URL参数获取用户ID:', urlUserId);
        // 将URL用户ID存储到localStorage，确保后续使用
        localStorage.setItem('currentUserId', urlUserId);
        // 清理URL参数，避免刷新时重复处理
        if (window.history && window.history.replaceState) {
            const newUrl = window.location.pathname;
            window.history.replaceState({}, document.title, newUrl);
        }
        return urlUserId;
    }

    // 优先使用真实登录用户信息 - 检查多个存储位置
    let realUser = null;

    // 优先检查currentUser存储（更可靠）
    const currentUserData = JSON.parse(localStorage.getItem('currentUser') || '{}');
    if (currentUserData.id || currentUserData.user_id || currentUserData.global_user_id) {
        // 过滤掉临时用户ID，只使用真实登录用户
        const userId = currentUserData.global_user_id || currentUserData.user_id || currentUserData.id;
        if (userId && !userId.startsWith('temp_user_') && !userId.startsWith('smart_user_') && userId !== 'anonymous') {
            realUser = currentUserData;
            console.log('🔑 从currentUser获取真实用户:', realUser);
        }
    }

    // 检查userData存储（备选）
    if (!realUser) {
        const userData = JSON.parse(localStorage.getItem('userData') || '{}');
        if (userData.id || userData.user_id || userData.global_user_id) {
            const userId = userData.global_user_id || userData.user_id || userData.id;
            if (userId && userId !== 'anonymous') {
                realUser = userData;
                console.log('🔑 从userData获取真实用户:', realUser);
            }
        }
    }

    // 如果找到真实用户
    if (realUser) {
        // 优先使用global_user_id，然后是user_id，最后是id
        const userId = realUser.global_user_id || realUser.user_id || realUser.id;
        if (userId && userId !== 'undefined' && userId !== null) {
            console.log('🔑 使用真实登录用户ID:', userId);
            return userId; // 直接返回用户ID，不加前缀避免混淆
        }
    }

    // 访客模式 - 智能工作流程页面的临时用户ID
    const smartUser = localStorage.getItem('currentUserId');
    if (smartUser) {
        console.log('🔄 使用已有临时访客用户ID:', smartUser);
        return smartUser; // 已有smart_user_前缀
    }

    // 关键修复：检查是否有对话ID相关的用户信息
    // 如果用户之前进行过问诊，尝试从对话ID中恢复用户ID
    const allStorageKeys = Object.keys(localStorage);
    const conversationKeys = allStorageKeys.filter(key => key.startsWith('conversationId_'));

    if (conversationKeys.length > 0) {
        // 从对话ID key中提取用户ID（格式：conversationId_{userId}）
        const existingUserId = conversationKeys[0].replace('conversationId_', '');
        console.log('🔄 从对话ID恢复用户ID:', existingUserId);
        localStorage.setItem('currentUserId', existingUserId);
        return existingUserId;
    }

    // 关键修复：检查历史记录键，尝试恢复用户ID
    const historyKeys = allStorageKeys.filter(key => key.startsWith('tcm_doctor_history_'));
    if (historyKeys.length > 0) {
        // 从历史记录key中提取用户ID（格式：tcm_doctor_history_{userId}_{doctorId}）
        const historyKey = historyKeys[0];
        const parts = historyKey.split('_');
        if (parts.length >= 4) {
            const existingUserId = parts.slice(3, -1).join('_'); // 处理用户ID中可能包含下划线的情况
            console.log('🔄 从历史记录恢复用户ID:', existingUserId);
            localStorage.setItem('currentUserId', existingUserId);
            return existingUserId;
        }
    }

    // 生成新的访客用户ID（只有在完全没有历史记录时）
    const newSmartId = 'smart_user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('currentUserId', newSmartId);
    console.log('🆕 生成全新访客用户ID:', newSmartId);
    return newSmartId;
}

/**
 * 清理当前用户的所有数据（用于登出）
 */
function clearCurrentUserData() {
    try {
        const currentUserId = getCurrentUserId();
        console.log('🧹 开始清理用户数据，用户ID:', currentUserId);

        // 1. 清理当前用户的所有历史记录
        const keys = Object.keys(localStorage);
        const userHistoryKeys = keys.filter(key =>
            key.includes(`_${currentUserId}_`) ||
            key.endsWith(`_${currentUserId}`) ||
            key.startsWith(`tcm_doctor_history_${currentUserId}`) ||
            key.startsWith(`conversationId_${currentUserId}`)
        );

        let cleanedCount = 0;
        userHistoryKeys.forEach(key => {
            localStorage.removeItem(key);
            cleanedCount++;
            console.log('🗑️ 删除用户数据:', key);
        });

        // 2. 清理用户认证信息
        localStorage.removeItem('currentUser');
        localStorage.removeItem('userToken');
        localStorage.removeItem('currentUserId');

        // 3. 重置全局变量
        window.currentUser = null;
        window.userToken = null;
        window.currentConversationId = null;
        window.selectedDoctor = null;

        // 同步本地变量
        currentUser = null;
        userToken = null;
        currentConversationId = null;
        selectedDoctor = null;

        // 4. 清理UI状态（如果函数存在）
        if (typeof clearAllMessages === 'function') {
            clearAllMessages();
        }
        if (typeof resetDoctorSelection === 'function') {
            resetDoctorSelection();
        }

        console.log(`✅ 用户数据清理完成，共删除 ${cleanedCount} 项数据`);
        return cleanedCount;

    } catch (error) {
        console.error('❌ 清理用户数据失败:', error);
        return 0;
    }
}

/**
 * 切换用户时的数据隔离处理
 */
function switchUserContext() {
    try {
        // 清理之前用户的UI状态
        if (typeof clearAllMessages === 'function') {
            clearAllMessages();
        }
        if (typeof resetDoctorSelection === 'function') {
            resetDoctorSelection();
        }

        // 重新初始化新用户的状态
        const newUserId = getCurrentUserId();
        console.log('🔄 切换到用户上下文:', newUserId);

        // 加载新用户的历史记录
        setTimeout(() => {
            if (typeof loadUserHistoryForAllDoctors === 'function') {
                loadUserHistoryForAllDoctors();
            }
        }, 100);

    } catch (error) {
        console.error('❌ 切换用户上下文失败:', error);
    }
}

/**
 * 检测用户状态变化
 */
function detectUserChange() {
    const currentStoredUser = localStorage.getItem('currentUser');
    const lastKnownUser = window.lastKnownUser || null;

    if (currentStoredUser !== lastKnownUser) {
        console.log('🔍 检测到用户状态变化');
        console.log('之前用户:', lastKnownUser);
        console.log('当前用户:', currentStoredUser);

        window.lastKnownUser = currentStoredUser;

        // 用户状态发生变化，执行切换处理
        handleUserSwitch();
        return true;
    }

    return false;
}

/**
 * 处理用户切换
 */
function handleUserSwitch() {
    console.log('🔄 开始处理用户切换...');

    // 🔑 关键修复：先获取新用户信息，再决定是否清理
    const newUserStr = localStorage.getItem('currentUser');
    const newUser = newUserStr ? JSON.parse(newUserStr) : {};
    const hasNewUser = !!(newUser.id || newUser.user_id);

    // 1. 清理当前页面状态（UI）
    if (typeof clearAllMessages === 'function') {
        clearAllMessages();
    }
    if (typeof resetDoctorSelection === 'function') {
        resetDoctorSelection();
    }

    // 2. 只有在切换到不同用户或登出时才清理旧数据
    // 🔑 修复：如果有新用户登录，不要清除用户认证信息
    if (!hasNewUser) {
        // 用户登出了，清理所有数据
        clearCurrentUserData();
    } else {
        // 用户切换，只清理历史数据缓存，保留认证信息
        console.log('🔄 用户切换，保留新用户认证信息');
    }

    // 3. 重新初始化当前用户
    if (newUser.id || newUser.user_id) {
        window.currentUser = newUser;
        currentUser = newUser;
        console.log('🔑 切换到认证用户:', newUser.username || newUser.display_name);

        // 4. 重新加载该用户的数据
        if (typeof loadConversationHistory === 'function') {
            loadConversationHistory();
        }
        if (typeof updateUserInterface === 'function') {
            updateUserInterface(true);
        }
    } else {
        console.log('⚠️ 切换到访客模式');
        window.currentUser = null;
        window.userToken = null;
        currentUser = null;
        userToken = null;
        if (typeof updateUserInterface === 'function') {
            updateUserInterface(false);
        }
    }

    // 5. 显示切换通知
    if (typeof showMessage === 'function') {
        showMessage('用户身份已更新', 'info');
    }
}

/**
 * 清理旧用户数据（确保数据隔离）
 * 清理旧格式的历史记录（不含用户ID的）
 */
function cleanupOldUserData() {
    const keys = Object.keys(localStorage);
    const oldHistoryKeys = keys.filter(key =>
        key.startsWith('tcm_doctor_history_') &&
        !key.includes('guest_portal_') &&
        !key.includes('smart_user_') &&
        !key.match(/tcm_doctor_history_[\w\-]+_[\w\-]+/)  // 不匹配新格式 userId_doctorId
    );

    oldHistoryKeys.forEach(key => {
        localStorage.removeItem(key);
        console.log('智能工作流页面已清理旧历史记录:', key);
    });
}

// ============================================
// 暴露函数到全局作用域
// ============================================

window.generateConversationId = generateConversationId;
window.getCurrentUserId = getCurrentUserId;
window.clearCurrentUserData = clearCurrentUserData;
window.switchUserContext = switchUserContext;
window.detectUserChange = detectUserChange;
window.handleUserSwitch = handleUserSwitch;
window.cleanupOldUserData = cleanupOldUserData;

// 模块加载完成日志
console.log('✅ [smart_workflow_core.js] 核心模块加载完成');
console.log('   - 全局变量已初始化');
console.log('   - 核心函数已暴露到window对象');
