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
     * 主应用初始化函数
     * 在DOMContentLoaded时调用，负责初始化整个应用
     */
    async function initializeApp() {
        console.log('🚀 初始化TCM-AI智能工作流系统');

        // 🔍 用户状态检测和管理 - 使用authManager统一管理
        // 🔑 关键修复：使用authManager而不是直接读localStorage
        const currentUser = window.authManager ? window.authManager.getCurrentUser() : null;
        const userToken = window.authManager ? window.authManager.getToken() : null;
        const hasRealUser = !!(currentUser && (currentUser.id || currentUser.user_id));

        // 🔑 同步到全局变量，确保其他模块可以访问
        window.currentUser = currentUser;
        window.userToken = userToken;

        console.log('👤 用户状态检测:', hasRealUser ? '真实登录用户' : '访客模式');
        if (hasRealUser) {
            console.log('🔑 登录用户信息:', currentUser.username || currentUser.name || currentUser.id);
            console.log('🔑 Token状态:', userToken ? `已获取(${userToken.substring(0, 10)}...)` : '未获取');
        }

        // 设置初始用户状态
        window.lastKnownUser = currentUser ? JSON.stringify(currentUser) : null;

        // 🔑 关键修复：更新页面用户显示
        updateUserDisplay();

        // 🔑 新增：检查URL参数是否需要恢复会话
        const urlParams = new URLSearchParams(window.location.search);
        const restoreSessionId = urlParams.get('restore_session');
        if (restoreSessionId) {
            console.log('🔄 检测到会话恢复请求:', restoreSessionId);
            // 延迟恢复，等待页面完全初始化
            setTimeout(() => {
                if (typeof window.restoreSessionFromHistory === 'function') {
                    window.restoreSessionFromHistory(restoreSessionId);
                }
            }, 2000);

            // 清除URL参数避免重复恢复
            const newUrl = window.location.pathname;
            window.history.replaceState({}, document.title, newUrl);
        }

        // 首先清理旧数据，确保数据隔离
        cleanupOldUserData();

        // 🔄 定期检测用户状态变化（每5秒检查一次）
        setInterval(() => {
            if (typeof window.detectUserChange === 'function') {
                window.detectUserChange();
            }
        }, 5000);

        // 🔧 先加载医生列表，再渲染医生卡片
        console.log('🔄 [DEBUG] 开始加载医生列表...');
        if (typeof window.loadDoctors === 'function') {
            await window.loadDoctors();
        }
        console.log('✅ [DEBUG] 医生列表加载完成，doctors对象:', window.doctors);
        console.log('✅ [DEBUG] doctors对象键:', Object.keys(window.doctors || {}));

        if (typeof window.renderDoctorCards === 'function') {
            window.renderDoctorCards();
        }

        // 🔑 Chrome浏览器兼容性修复：确保移动端医生卡片在数据加载完成后渲染
        const isMobile = window.innerWidth <= 768;
        console.log('🔍 [DEBUG] 设备检测:', {
            windowWidth: window.innerWidth,
            isMobile: isMobile
        });

        if (isMobile) {
            console.log('✅ [DEBUG] 移动端模式 - 准备渲染医生卡片');
            console.log('✅ [DEBUG] 调用renderMobileDoctorCards之前，doctors:', window.doctors);
            if (typeof window.renderMobileDoctorCards === 'function') {
                window.renderMobileDoctorCards();
            }

            // 🔧 Chrome修复：延迟再次渲染，确保DOM完全ready
            setTimeout(function() {
                console.log('🔄 [Chrome修复] 延迟1秒后再次渲染医生卡片');
                const grid = document.getElementById('mobileDoctorsGrid');
                if (grid && grid.children.length === 0) {
                    console.warn('⚠️ [Chrome修复] 医生卡片为空，重新渲染');
                    if (typeof window.renderMobileDoctorCards === 'function') {
                        window.renderMobileDoctorCards();
                    }

                    // 再延迟2秒检查
                    setTimeout(function() {
                        if (grid.children.length === 0) {
                            console.error('❌ [Chrome修复] 第2次渲染后仍为空，最后尝试');
                            if (typeof window.renderMobileDoctorCards === 'function') {
                                window.renderMobileDoctorCards();
                            }
                        } else {
                            console.log('✅ [Chrome修复] 第1次延迟渲染成功');
                        }
                    }, 2000);
                } else {
                    console.log('✅ [Chrome修复] 医生卡片已正常渲染');
                }
            }, 1000);
        }

        // 🔑 修复：所有用户（包括访客）都尝试从数据库恢复历史记录
        if (typeof window.syncHistoryFromDatabase === 'function') {
            await window.syncHistoryFromDatabase();
        }

        // 🔑 如果数据库没有记录，再从localStorage加载
        if (typeof window.loadConversationHistory === 'function') {
            window.loadConversationHistory(); // 这个函数内部会调用generateConversationId如果需要
        }

        // 🔄 初始化ChatGPT风格对话管理系统
        if (typeof window.initConversationManager === 'function') {
            window.initConversationManager();
        }

        // 设置默认医生 - 金大夫（经方大师）
        // 🔧 修复重复欢迎消息：跳过历史记录加载，因为loadConversationHistory已经处理了
        if (typeof window.setDefaultDoctor === 'function') {
            window.setDefaultDoctor('jin_daifu', true);
        }

        // 🧹 暴露全局清理函数（供外部调用）
        window.clearCurrentUserData = clearCurrentUserData;
        window.switchUserContext = switchUserContext;

        // 🔑 修复：确保在页面完全准备好后再恢复处方状态
        // 🔑 旧的统一恢复机制已禁用，使用新的简化版恢复系统
        console.log('🔄 将使用简化版处方恢复系统...');

        // 🔗 添加页面级用户管理控制
        if (typeof window.addUserManagementControls === 'function') {
            window.addUserManagementControls();
        }

        // 添加调试功能（仅在开发环境或特定条件下）
        if (typeof window.isDebugMode === 'function' && window.isDebugMode()) {
            console.log('🔧 调试模式已启用');
            console.log('📋 可用调试命令:');
            console.log('  - diagnoseHistoryIssues(): 诊断历史记录问题');
            console.log('  - checkLocalStorageUsage(): 检查存储使用情况');
            console.log('  - cleanOldHistoryRecords(): 清理旧的历史记录');
            console.log('  - clearCurrentUserData(): 清理当前用户数据');
            console.log('  - switchUserContext(): 切换用户上下文');

            // 将调试函数暴露到全局
            if (typeof window.diagnoseHistoryIssues === 'function') {
                window.diagnoseHistoryIssues = window.diagnoseHistoryIssues;
            }
            if (typeof window.checkLocalStorageUsage === 'function') {
                window.checkLocalStorageUsage = window.checkLocalStorageUsage;
            }
            if (typeof window.cleanOldHistoryRecords === 'function') {
                window.cleanOldHistoryRecords = window.cleanOldHistoryRecords;
            }

            // 页面加载后自动运行一次诊断
            setTimeout(() => {
                console.log('\n🔍 自动历史记录诊断:');
                if (typeof window.diagnoseHistoryIssues === 'function') {
                    window.diagnoseHistoryIssues();
                }
            }, 1000);
        }

        // 初始化星级评价和评价模态框
        initializeStarRatings();
        bindEvaluationModalEvents();

        // 🔑 关键修复：延迟再次调用updateUserDisplay，确保DOM完全渲染
        setTimeout(() => {
            console.log('🔄 延迟500ms后再次更新用户显示，确保DOM完全渲染');
            updateUserDisplay();
        }, 500);

        // 🔑 启动处方状态轮询机制 - 每30秒检查一次待审核处方状态
        if (typeof window.startPrescriptionStatusPolling === 'function') {
            window.startPrescriptionStatusPolling();
            console.log('✅ 处方状态轮询已启动（每30秒检查一次）');
        } else {
            console.warn('⚠️ startPrescriptionStatusPolling 函数未找到');
        }

        // 🔑 恢复所有待审核处方状态 - 页面刷新后立即检查
        if (typeof window.restoreAllPendingPrescriptions === 'function') {
            setTimeout(() => {
                window.restoreAllPendingPrescriptions();
                console.log('✅ 待审核处方状态恢复检查已执行');
            }, 2000); // 延迟2秒，确保页面完全加载
        }

        console.log('✅ TCM-AI智能工作流系统初始化完成');
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
     * 🔑 获取当前对话历史（用于AI上下文维护）
     * 将前端消息格式转换为后端API期望的格式
     * @returns {Array} 对话历史数组，格式: [{role: "user"|"assistant", content: "..."}]
     */
    function getCurrentConversationHistory() {
        try {
            // 获取当前消息数组
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

            console.log(`📝 获取对话历史: ${conversationHistory.length} 条消息`);

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
