/**
 * 智能工作流初始化模块
 * Smart Workflow Initialization Module
 *
 * 该模块负责应用程序的初始化，包括：
 * - 用户状态检测和管理
 * - 医生数据加载和渲染
 * - 对话历史同步
 * - 用户数据隔离
 * - 调试功能初始化
 *
 * 注意：此模块应该作为最后一个加载的模块，
 * 因为它依赖于其他所有模块的功能
 *
 * @module smart_workflow_init
 * @requires smart_workflow_core - 核心功能模块
 * @requires smart_workflow_doctors - 医生管理模块
 * @requires smart_workflow_conversation - 对话管理模块
 * @requires smart_workflow_ui - UI管理模块
 */

(function() {
    'use strict';

    // ===================== 初始化星级评价交互 =====================

    /**
     * 初始化星级评价交互
     * 为评价模态框中的星星添加点击和悬停效果
     */
    function initializeStarRatings() {
        // 为所有星星添加点击事件
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('star')) {
                const ratingGroup = e.target.closest('.star-rating');
                if (ratingGroup) {
                    const category = ratingGroup.getAttribute('data-category');
                    const stars = ratingGroup.querySelectorAll('.star');
                    const rating = Array.from(stars).indexOf(e.target) + 1;

                    if (typeof window.handleStarRating === 'function') {
                        window.handleStarRating(category, rating);
                    }
                }
            }
        });

        // 为星星添加hover效果
        document.addEventListener('mouseover', function(e) {
            if (e.target.classList.contains('star')) {
                const ratingGroup = e.target.closest('.star-rating');
                if (ratingGroup) {
                    const stars = ratingGroup.querySelectorAll('.star');
                    const hoverIndex = Array.from(stars).indexOf(e.target);

                    stars.forEach((star, index) => {
                        if (index <= hoverIndex) {
                            star.style.color = '#ffd700';
                        } else {
                            star.style.color = '#ddd';
                        }
                    });
                }
            }
        });

        // 恢复星星原本的状态（鼠标离开时）
        document.addEventListener('mouseout', function(e) {
            if (e.target.classList.contains('star')) {
                const ratingGroup = e.target.closest('.star-rating');
                if (ratingGroup) {
                    const stars = ratingGroup.querySelectorAll('.star');
                    const currentRating = parseInt(ratingGroup.getAttribute('data-rating') || '0');

                    stars.forEach((star, index) => {
                        if (index < currentRating) {
                            star.style.color = '#ffd700';
                        } else {
                            star.style.color = '#ddd';
                        }
                    });
                }
            }
        });
    }

    /**
     * 绑定评价模态框事件
     * 包括背景点击关闭和ESC键关闭
     */
    function bindEvaluationModalEvents() {
        // 点击模态框背景关闭
        const modal = document.getElementById('evaluationModal');
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    if (typeof window.hideEvaluationModal === 'function') {
                        window.hideEvaluationModal();
                    }
                }
            });
        }

        // ESC键关闭模态框
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const evalModal = document.getElementById('evaluationModal');
                if (evalModal && evalModal.style.display === 'flex') {
                    if (typeof window.hideEvaluationModal === 'function') {
                        window.hideEvaluationModal();
                    }
                }

                const statsModal = document.getElementById('statisticsModal');
                if (statsModal) {
                    if (typeof window.closeStatisticsModal === 'function') {
                        window.closeStatisticsModal();
                    }
                }
            }
        });
    }

    // ===================== 数据清理函数 =====================

    /**
     * 清理旧的localStorage数据，确保数据隔离
     */
    function cleanupOldUserData() {
        // 清理旧格式的历史记录（不含用户ID的）
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

    /**
     * 更新页面用户显示
     * 根据当前登录状态更新UI元素
     */
    function updateUserDisplay() {
        // 🔑 正确的元素ID（从HTML中确认）
        const authButtons = document.getElementById('authButtons');  // 登录/注册按钮容器
        const userInfo = document.getElementById('userInfo');        // 用户信息容器
        const userName = document.getElementById('userName');        // 用户名显示
        const userAvatar = document.getElementById('userAvatar');    // 用户头像

        // 使用authManager获取用户信息
        const currentUser = window.authManager ? window.authManager.getCurrentUser() : null;
        const isLoggedIn = window.authManager ? window.authManager.isLoggedIn() : false;

        console.log('🔄 更新用户显示，登录状态:', isLoggedIn, '用户:', currentUser);

        if (isLoggedIn && currentUser) {
            // 已登录：隐藏登录/注册按钮，显示用户信息
            if (authButtons) {
                authButtons.style.display = 'none';
                console.log('✅ 隐藏登录/注册按钮');
            }
            if (userInfo) {
                userInfo.style.display = 'flex';
                console.log('✅ 显示用户信息');
            }

            // 设置用户名显示
            const displayName = currentUser.username || currentUser.display_name || currentUser.name || '用户';
            if (userName) {
                userName.textContent = displayName;
                console.log('✅ 设置用户名:', displayName);
            }

            // 设置头像
            if (userAvatar) {
                userAvatar.textContent = currentUser.avatar || '👤';
            }

            console.log('✅ 已登录用户显示已更新:', displayName);
        } else {
            // 未登录：显示登录/注册按钮，隐藏用户信息
            if (authButtons) {
                authButtons.style.display = 'flex';
                console.log('ℹ️ 显示登录/注册按钮');
            }
            if (userInfo) {
                userInfo.style.display = 'none';
                console.log('ℹ️ 隐藏用户信息');
            }

            console.log('ℹ️ 游客模式');
        }
    }

    // ===================== 主初始化函数 =====================

    /**
     * 🔑 v4.3 优化：拆分initializeApp为多个小函数，提高可维护性
     */

    /**
     * 初始化用户状态
     * @returns {Object} 包含currentUser, userToken, hasRealUser的对象
     */
    function initializeUserState() {
        const currentUser = window.authManager ? window.authManager.getCurrentUser() : null;
        const userToken = window.authManager ? window.authManager.getToken() : null;
        const hasRealUser = !!(currentUser && (currentUser.id || currentUser.user_id));

        // 同步到全局变量
        window.currentUser = currentUser;
        window.userToken = userToken;
        window.lastKnownUser = currentUser ? JSON.stringify(currentUser) : null;

        console.log('👤 用户状态检测:', hasRealUser ? '真实登录用户' : '访客模式');
        if (hasRealUser) {
            console.log('🔑 登录用户信息:', currentUser.username || currentUser.name || currentUser.id);
        }

        return { currentUser, userToken, hasRealUser };
    }

    /**
     * 处理URL参数中的会话恢复请求
     */
    function handleSessionRestoreFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const restoreSessionId = urlParams.get('restore_session');

        if (restoreSessionId) {
            console.log('🔄 检测到会话恢复请求:', restoreSessionId);
            setTimeout(() => {
                if (typeof window.restoreSessionFromHistory === 'function') {
                    window.restoreSessionFromHistory(restoreSessionId);
                }
            }, 2000);

            // 清除URL参数
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }

    /**
     * 初始化医生列表和渲染
     */
    async function initializeDoctors() {
        console.log('🔄 开始加载医生列表...');

        if (typeof window.loadDoctors === 'function') {
            await window.loadDoctors();
        }

        if (typeof window.renderDoctorCards === 'function') {
            window.renderDoctorCards();
        }

        // Chrome移动端兼容性修复
        const isMobile = window.innerWidth <= 768;
        if (isMobile && typeof window.renderMobileDoctorCards === 'function') {
            window.renderMobileDoctorCards();
            initializeMobileDoctorsFallback();
        }
    }

    /**
     * 移动端医生卡片渲染的Chrome兼容性修复
     */
    function initializeMobileDoctorsFallback() {
        setTimeout(function() {
            const grid = document.getElementById('mobileDoctorsGrid');
            if (grid && grid.children.length === 0) {
                console.warn('⚠️ [Chrome修复] 医生卡片为空，重新渲染');
                if (typeof window.renderMobileDoctorCards === 'function') {
                    window.renderMobileDoctorCards();
                }

                // 再次延迟检查
                setTimeout(function() {
                    if (grid.children.length === 0 && typeof window.renderMobileDoctorCards === 'function') {
                        window.renderMobileDoctorCards();
                    }
                }, 2000);
            }
        }, 1000);
    }

    /**
     * 初始化对话系统
     */
    function initializeConversationSystem() {
        if (typeof window.loadConversationHistory === 'function') {
            window.loadConversationHistory();
        }

        if (typeof window.initConversationManager === 'function') {
            window.initConversationManager();
        }

        if (typeof window.setDefaultDoctor === 'function') {
            window.setDefaultDoctor('jin_daifu', true);
        }
    }

    /**
     * 自动恢复对话历史（支持登录用户和游客）
     * 🔑 v4.3 修复：优先使用本地存储，确保切换医生时保留对话
     */
    async function autoRestoreConversationHistory() {
        const defaultDoctor = window.selectedDoctor || 'jin_daifu';
        const userId = typeof window.getCurrentUserId === 'function'
            ? window.getCurrentUserId()
            : 'default';

        console.log(`🔄 页面初始化：自动加载${defaultDoctor}医生的对话历史...`);

        let messages = [];
        let conversationId = null;

        // 1. 优先从本地存储加载（最可靠）
        const historyKey = `tcm_doctor_history_${userId}_${defaultDoctor}`;
        const storedHistory = localStorage.getItem(historyKey);

        if (storedHistory) {
            try {
                const historyData = JSON.parse(storedHistory);
                if (historyData.messages && historyData.messages.length > 0) {
                    messages = historyData.messages;
                    conversationId = historyData.conversationId;
                    console.log(`✅ 从本地加载${defaultDoctor}医生的${messages.length}条历史记录（版本：${historyData.version || '1.0'}）`);
                }
            } catch (e) {
                console.warn('解析本地历史失败:', e);
            }
        }

        // 2. 如果本地没有，尝试从API加载（仅登录用户）
        const isLoggedIn = !!(window.userToken || localStorage.getItem('tcm_auth_token'));
        if (messages.length === 0 && isLoggedIn && window.sessionManager) {
            try {
                const result = await window.sessionManager.switchDoctor(defaultDoctor);
                console.log(`📡 API返回: conversationId=${result.conversationId}, messages=${result.messages?.length || 0}`);

                conversationId = result.conversationId;
                if (result.messages && result.messages.length > 0) {
                    messages = result.messages;
                }
            } catch (error) {
                console.warn('API加载失败，使用本地数据:', error);
            }
        }

        // 3. 更新全局变量
        window.currentConversationId = conversationId || `local_${Date.now()}`;
        window.messages = messages;

        // 4. 渲染消息到UI
        if (messages.length > 0) {
            console.log(`📝 页面初始化：恢复 ${messages.length} 条历史消息到UI`);
            for (const msg of messages) {
                if (typeof window.addMessage === 'function') {
                    await window.addMessage(msg.type, msg.content, false, false, null);
                }
            }
        } else {
            console.log('📝 无历史记录，显示欢迎消息');
            if (typeof window.addWelcomeMessage === 'function') {
                window.addWelcomeMessage(defaultDoctor);
            }
        }
    }

    /**
     * 初始化调试功能
     */
    function initializeDebugMode() {
        if (typeof window.isDebugMode !== 'function' || !window.isDebugMode()) return;

        console.log('🔧 调试模式已启用');
        console.log('📋 可用调试命令: diagnoseHistoryIssues, checkLocalStorageUsage, cleanOldHistoryRecords');

        setTimeout(() => {
            if (typeof window.diagnoseHistoryIssues === 'function') {
                console.log('\n🔍 自动历史记录诊断:');
                window.diagnoseHistoryIssues();
            }
        }, 1000);
    }

    /**
     * 启动后台数据同步任务
     */
    function startBackgroundSyncTasks() {
        setTimeout(() => {
            console.log('🔄 开始后台数据同步...');

            if (typeof window.restoreAllPendingPrescriptions === 'function') {
                window.restoreAllPendingPrescriptions();
            }

            if (typeof syncHistoryFromDatabase === 'function') {
                syncHistoryFromDatabase();
            }

            if (window.simplePrescriptionManager?.syncPaidPrescriptionsFromServer) {
                window.simplePrescriptionManager.syncPaidPrescriptionsFromServer();
            }

            // 🔑 v4.3 新增：输出localStorage使用量
            if (window.StorageUtils && typeof window.StorageUtils.getUsage === 'function') {
                const usage = window.StorageUtils.getUsage();
                console.log(`📊 LocalStorage使用量: ${(usage.totalSize / 1024 / 1024).toFixed(2)}MB`);
            }

            console.log('✅ 后台数据同步任务已启动');
        }, 3000);
    }

    /**
     * 主应用初始化函数
     * 🔑 v4.3 优化：拆分为多个小函数，提高可读性和可维护性
     */
    async function initializeApp() {
        console.log('🚀 初始化TCM-AI智能工作流系统');

        // 1. 初始化用户状态
        initializeUserState();
        updateUserDisplay();

        // 2. 处理URL参数的会话恢复
        handleSessionRestoreFromURL();

        // 3. 清理旧数据
        cleanupOldUserData();

        // 4. 启动用户状态变化监控
        setInterval(() => {
            if (typeof window.detectUserChange === 'function') {
                window.detectUserChange();
            }
        }, 5000);

        // 5. 加载并渲染医生列表
        await initializeDoctors();

        // 6. 初始化对话系统
        initializeConversationSystem();

        // 7. 自动恢复对话历史（登录用户）
        await autoRestoreConversationHistory();

        // 8. 暴露全局函数
        window.clearCurrentUserData = clearCurrentUserData;
        window.switchUserContext = switchUserContext;

        // 9. 添加用户管理控制
        if (typeof window.addUserManagementControls === 'function') {
            window.addUserManagementControls();
        }

        // 10. 初始化调试模式
        initializeDebugMode();

        // 11. 初始化UI组件
        initializeStarRatings();
        bindEvaluationModalEvents();

        // 12. 延迟更新用户显示（确保DOM完全渲染）
        setTimeout(() => updateUserDisplay(), 500);

        // 13. 启动处方状态轮询
        if (typeof window.startPrescriptionStatusPolling === 'function') {
            window.startPrescriptionStatusPolling();
            console.log('✅ 处方状态轮询已启动');
        }

        console.log('✅ TCM-AI智能工作流系统初始化完成');

        // 14. 启动Session认证验证器 (v4.1新增)
        if (window.authValidator) {
            window.authValidator.setupGlobalErrorHandler();  // 全局401拦截
            window.authValidator.startHeartbeat();           // 定期心跳检查
            console.log('✅ Session认证验证器已启动');
        }

        // 15. 启动后台同步任务
        startBackgroundSyncTasks();
    }

    // ===================== 用户数据管理函数 =====================

    /**
     * 清理当前用户的所有数据（用于登出）
     * @returns {number} 清理的数据项数量
     */
    function clearCurrentUserData() {
        try {
            const currentUserId = typeof window.getCurrentUserId === 'function'
                ? window.getCurrentUserId()
                : null;
            console.log('🧹 开始清理用户数据，用户ID:', currentUserId);

            if (!currentUserId) {
                console.warn('⚠️ 无法获取当前用户ID');
                return 0;
            }

            // 1. 清理当前用户的所有历史记录
            const keys = Object.keys(localStorage);
            const userHistoryKeys = keys.filter(key =>
                key.includes(`_${currentUserId}_`) ||
                key.endsWith(`_${currentUserId}`)
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

            // 4. 清理UI状态
            clearAllMessages();
            resetDoctorSelection();

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
            clearAllMessages();
            resetDoctorSelection();

            // 重新初始化新用户的状态
            const newUserId = typeof window.getCurrentUserId === 'function'
                ? window.getCurrentUserId()
                : null;
            console.log('🔄 切换到用户上下文:', newUserId);

            // 加载新用户的历史记录
            setTimeout(() => {
                if (typeof window.loadUserHistoryForAllDoctors === 'function') {
                    window.loadUserHistoryForAllDoctors();
                }
            }, 100);

        } catch (error) {
            console.error('❌ 切换用户上下文失败:', error);
        }
    }

    /**
     * 清理所有消息
     */
    function clearAllMessages() {
        const containers = ['messagesContainer', 'mobileMessagesContainer'];
        containers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = '';
                console.log('🗑️ 清理消息容器:', containerId);
            }
        });
    }

    /**
     * 重置医生选择状态
     */
    function resetDoctorSelection() {
        window.selectedDoctor = null;

        // 重置医生选择UI
        const doctorCards = document.querySelectorAll('.doctor-card');
        doctorCards.forEach(card => {
            card.classList.remove('selected');
        });

        // 重置手机版医生选择
        const mobileDoctorSelect = document.getElementById('mobileDoctorSelect');
        if (mobileDoctorSelect) {
            mobileDoctorSelect.value = '';
        }

        console.log('🔄 医生选择状态已重置');
    }

    /**
     * 旧的统一处方恢复机制（已禁用）
     * 功能已转移到 /static/js/simple_recovery.js
     */
    function startUnifiedPrescriptionRecovery() {
        console.log('⚠️ 旧的统一恢复机制已禁用，请使用简化版恢复系统');
        // 功能已转移到 /static/js/simple_recovery.js
    }

    /**
     * 🔑 从历史记录页面恢复会话
     * 从后端API获取会话详情并渲染到问诊页面
     * @param {string} sessionId - 会话ID
     */
    async function restoreSessionFromHistory(sessionId) {
        console.log('🔄 开始恢复会话:', sessionId);

        try {
            // 获取认证头
            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken || ''}`
            };

            // 从后端API获取会话详情
            const response = await fetch(`/api/user/conversation/${sessionId}`, {
                headers: headers
            });

            if (!response.ok) {
                throw new Error(`获取会话详情失败: ${response.status}`);
            }

            const result = await response.json();
            console.log('🔍 API返回结果:', result);

            // 🔑 关键修复：API可能返回两种格式
            // 格式1: {success: false, error: "..."} - 错误情况
            // 格式2: {conversation_id: "...", doctor_name: "...", ...} - 成功情况（直接返回数据，没有success字段）

            let conversation;
            if (result.success === false) {
                // 明确的错误响应
                throw new Error(result.error || '获取会话详情失败');
            } else if (result.data) {
                // 标准格式：{success: true, data: {...}}
                conversation = result.data;
            } else if (result.conversation_id || result.session_id) {
                // 直接返回对话数据（没有包装）
                conversation = result;
            } else {
                // 无法识别的格式
                console.error('❌ 无法解析API返回数据:', result);
                throw new Error('API返回数据格式错误');
            }

            console.log('📋 解析后的会话详情:', conversation);

            // 清空当前显示
            if (typeof clearAllMessages === 'function') {
                clearAllMessages();
            }

            // 设置对话状态
            window.currentConversationId = sessionId;

            // 设置医生
            const doctorId = conversation.doctor_id || conversation.selected_doctor_id || 'jin_daifu';
            window.selectedDoctor = doctorId;

            if (typeof window.setDefaultDoctor === 'function') {
                window.setDefaultDoctor(doctorId, true);  // true = 跳过欢迎消息
            }

            // 渲染消息历史 - 支持多种格式
            // 🔑 格式1: conversation_history (API实际返回格式)
            const conversationHistory = conversation.conversation_history || [];

            // 格式2: conversation_messages (旧格式)
            const messages = conversation.conversation_messages || conversation.messages || conversation.conversation_log || [];

            let restoredCount = 0;

            // 优先处理 conversation_history 格式
            if (Array.isArray(conversationHistory) && conversationHistory.length > 0) {
                console.log(`📋 开始恢复 conversation_history 格式: ${conversationHistory.length} 轮对话`);

                for (const turn of conversationHistory) {
                    // 渲染患者问题
                    if (turn.patient_query) {
                        if (typeof window.addMessage === 'function') {
                            await window.addMessage('user', turn.patient_query);
                            restoredCount++;
                        }
                    }

                    // 渲染AI回复
                    if (turn.ai_response) {
                        if (typeof window.addMessage === 'function') {
                            await window.addMessage('ai', turn.ai_response);
                            restoredCount++;
                        }
                    }
                }
                console.log(`✅ 会话恢复成功: ${restoredCount} 条消息`);
            }
            // 处理 conversation_messages 格式
            else if (Array.isArray(messages) && messages.length > 0) {
                console.log(`📋 开始恢复 conversation_messages 格式: ${messages.length} 条消息`);

                for (const message of messages) {
                    const sender = message.role || message.sender || message.type;
                    const content = message.content || message.message || '';

                    if (sender === 'user') {
                        if (typeof window.addMessage === 'function') {
                            await window.addMessage('user', content);
                            restoredCount++;
                        }
                    } else if (sender === 'assistant' || sender === 'ai') {
                        if (typeof window.addMessage === 'function') {
                            // 检查是否包含处方
                            const prescriptionData = message.prescription_data || message.prescriptionData || null;
                            await window.addMessage('ai', content, false, false, prescriptionData);
                            restoredCount++;
                        }
                    }
                }
                console.log(`✅ 会话恢复成功: ${restoredCount} 条消息`);
            } else {
                console.warn('⚠️ 会话没有消息历史，尝试从conversation_log解析');

                // 尝试解析conversation_log字段（可能是JSON字符串）
                if (conversation.conversation_log && typeof conversation.conversation_log === 'string') {
                    try {
                        const logData = JSON.parse(conversation.conversation_log);
                        const logMessages = logData.messages || logData.conversation_history || [];

                        for (const message of logMessages) {
                            const sender = message.role || message.sender || message.type;
                            const content = message.content || message.message || '';

                            if (sender === 'user' && typeof window.addMessage === 'function') {
                                await window.addMessage('user', content);
                            } else if ((sender === 'assistant' || sender === 'ai') && typeof window.addMessage === 'function') {
                                await window.addMessage('ai', content);
                            }
                        }
                        console.log(`✅ 从conversation_log恢复: ${logMessages.length} 条消息`);
                    } catch (parseError) {
                        console.error('❌ 解析conversation_log失败:', parseError);
                    }
                }
            }

            // 更新window.messages数组用于后续AI上下文
            if (typeof window.updateCurrentMessages === 'function') {
                window.updateCurrentMessages();
            }

            // 显示成功消息
            if (typeof showMessage === 'function') {
                showMessage('会话恢复成功', 'success');
            }

        } catch (error) {
            console.error('❌ 恢复会话失败:', error);

            if (typeof showMessage === 'function') {
                showMessage(`恢复会话失败: ${error.message}`, 'error');
            } else {
                alert(`恢复会话失败: ${error.message}`);
            }
        }
    }

    /**
     * 🔑 获取当前对话历史（用于AI上下文维护）- v3.0 使用ConversationManager
     * 将前端消息格式转换为后端API期望的格式
     * @returns {Array} 对话历史数组，格式: [{role: "user"|"assistant", content: "..."}]
     */
    function getCurrentConversationHistory() {
        try {
            // 🔑 优先使用ConversationManager加载当前对话历史
            const conversationId = window.currentConversationId;

            if (conversationId && window.conversationManager) {
                const messages = window.conversationManager.loadConversationMessages(conversationId);

                if (messages && messages.length > 0) {
                    // 转换为后端期望的格式
                    const conversationHistory = messages.map(msg => {
                        // 清理HTML标签，只保留纯文本内容
                        let content = msg.content || '';

                        // 移除HTML标签（保留基本结构）
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = content;
                        content = tempDiv.textContent || tempDiv.innerText || content;

                        return {
                            role: msg.type === 'user' ? 'user' : 'assistant',
                            content: content.trim()
                        };
                    }).filter(msg => msg.content.length > 0); // 过滤空消息

                    console.log(`📋 从ConversationManager加载对话 ${conversationId}: ${conversationHistory.length}条历史`);

                    // 返回最近20轮对话（后端会进一步限制为10轮）
                    return conversationHistory.slice(-20);
                }
            }

            // 降级方案：使用window.messages（兼容性）
            const messages = window.messages || [];

            if (!messages || messages.length === 0) {
                console.log('📝 当前无对话历史');
                return [];
            }

            // 转换为后端期望的格式
            const conversationHistory = messages.map(msg => {
                // 清理HTML标签，只保留纯文本内容
                let content = msg.content || '';

                // 移除HTML标签（保留基本结构）
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = content;
                content = tempDiv.textContent || tempDiv.innerText || content;

                return {
                    role: msg.type === 'user' ? 'user' : 'assistant',
                    content: content.trim()
                };
            }).filter(msg => msg.content.length > 0); // 过滤空消息

            console.log(`📝 从window.messages获取对话历史: ${conversationHistory.length} 条消息`);

            // 返回最近20轮对话（后端会进一步限制为10轮）
            return conversationHistory.slice(-20);

        } catch (error) {
            console.error('❌ 获取对话历史失败:', error);
            return [];
        }
    }

    // ===================== 暴露到全局 =====================

    // 暴露主初始化函数
    window.initializeApp = initializeApp;

    // 暴露用户数据管理函数
    window.clearCurrentUserData = clearCurrentUserData;
    window.switchUserContext = switchUserContext;
    window.clearAllMessages = clearAllMessages;
    window.resetDoctorSelection = resetDoctorSelection;
    window.startUnifiedPrescriptionRecovery = startUnifiedPrescriptionRecovery;

    // 暴露辅助函数
    window.initializeStarRatings = initializeStarRatings;
    window.bindEvaluationModalEvents = bindEvaluationModalEvents;
    window.cleanupOldUserData = cleanupOldUserData;
    window.updateUserDisplay = updateUserDisplay;  // 🔑 暴露用户显示更新函数
    window.getCurrentConversationHistory = getCurrentConversationHistory;  // 🔑 暴露对话历史获取函数
    window.restoreSessionFromHistory = restoreSessionFromHistory;  // 🔑 暴露会话恢复函数

    // ===================== DOMContentLoaded事件监听 =====================

    /**
     * 在DOM加载完成后初始化应用
     * 这是应用程序的主入口点
     */
    document.addEventListener('DOMContentLoaded', function() {
        initializeApp();
    });

    console.log('📦 智能工作流初始化模块已加载');

})();
