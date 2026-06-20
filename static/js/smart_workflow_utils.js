/**
 * TCM-AI 智能工作流工具函数库
 * Smart Workflow Utility Functions
 *
 * 本模块包含智能工作流页面的通用工具函数，包括：
 * - 星级评价系统
 * - 反馈提交
 * - 安全事件记录
 * - 随访提醒管理
 * - 图片上传
 * - 语音输入
 * - 用户认证
 * - 键盘事件处理
 *
 * @author TCM-AI Development Team
 * @version 1.0.0
 * @date 2025-11-20
 */

(function() {
    'use strict';

    // ===================== 星级评价系统 =====================

    /**
     * 初始化星级评价组件
     * 为所有星星添加点击和hover效果
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
     * 处理模态框的关闭逻辑
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
                const modal = document.getElementById('evaluationModal');
                if (modal && modal.style.display === 'flex') {
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

    // ===================== 反馈提交 =====================

    /**
     * 提交用户反馈评价
     * @param {number} rating - 评分 (1-5)
     */
    async function submitFeedback(rating) {
        // 检查网络状态
        if (typeof window.checkNetworkStatus === 'function' && !window.checkNetworkStatus()) {
            return;
        }

        try {
            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const userId = typeof window.resolveUserId === 'function'
                ? window.resolveUserId(window.currentUser)
                : (window.currentUser ? (window.currentUser.id || window.currentUser.user_id) : null);

            const response = await fetch('/api/review/feedback', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    conversation_id: window.currentConversationId,
                    doctor_id: window.selectedDoctor,
                    rating: rating,
                    feedback_type: 'consultation',
                    user_id: userId,
                    timestamp: new Date().toISOString()
                }),
            });

            const result = await response.json();

            if (result.success) {
                if (typeof window.showMessage === 'function') {
                    window.showMessage(`感谢您的${rating}星评价！`, 'success');
                }
            } else {
                console.error('反馈提交失败:', result.message);
            }

        } catch (error) {
            console.error('Error submitting feedback:', error);
        }
    }

    // ===================== 安全事件记录 =====================

    /**
     * 记录安全事件到服务器
     * @param {string} eventType - 事件类型
     * @param {string} content - 事件内容
     * @param {Object} details - 详细信息
     */
    async function logSecurityEvent(eventType, content, details = {}) {
        try {
            const eventMessage = typeof window.resolveMessageText === 'function'
                ? window.resolveMessageText(content, '')
                : (typeof content === 'string' ? content : '');
            const userId = typeof window.resolveUserId === 'function'
                ? window.resolveUserId(window.currentUser)
                : (window.currentUser ? (window.currentUser.id || window.currentUser.user_id) : null);

            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const response = await fetch('/api/security/log-event', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    event_type: eventType,
                    message: eventMessage,
                    content: eventMessage,
                    details: details,
                    user_id: userId,
                    conversation_id: window.currentConversationId,
                    timestamp: new Date().toISOString()
                })
            });

            const result = await response.json();
            if (!result.success) {
                console.error('安全事件记录失败:', result.message);
            }

        } catch (error) {
            console.error('安全事件记录失败:', error);
        }
    }

    // ===================== 随访提醒系统 =====================

    /**
     * 检查随访提醒
     */
    async function checkFollowUpReminders() {
        if (!window.currentUser || !window.userToken) return;

        try {
            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const response = await fetch('/api/follow-up/reminders', {
                headers: headers
            });

            const result = await response.json();

            if (result.success && result.data && result.data.length > 0) {
                // 显示随访提醒
                if (typeof window.showFollowUpReminders === 'function') {
                    window.showFollowUpReminders(result.data);
                }
            }

        } catch (error) {
            console.error('获取随访提醒失败:', error);
        }
    }

    /**
     * 显示随访管理模态框
     */
    async function showFollowUpModal() {
        try {
            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const response = await fetch('/api/follow-up/list', {
                headers: headers
            });

            const result = await response.json();

            if (!result.success) {
                if (typeof window.showMessage === 'function') {
                    window.showMessage('获取随访记录失败', 'error');
                }
                return;
            }

            if (typeof window.createFollowUpModal === 'function') {
                window.createFollowUpModal(result.data || []);
            }

        } catch (error) {
            console.error('获取随访记录失败:', error);
            if (typeof window.showMessage === 'function') {
                window.showMessage('服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 创建随访提醒
     * @param {string} title - 随访标题
     * @param {number} days - 几天后提醒
     * @param {string} message - 提醒内容
     */
    async function createFollowUpReminder(title, days, message) {
        try {
            const normalizedMessage = typeof window.resolveMessageText === 'function'
                ? window.resolveMessageText({ message }, '')
                : message;
            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const response = await fetch('/api/follow-up/create', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    title: title,
                    message: normalizedMessage,
                    content: normalizedMessage,
                    days_after: days,
                    doctor_id: window.selectedDoctor,
                    related_consultation_id: window.currentConversationId
                })
            });

            const result = await response.json();

            if (result.success) {
                if (typeof window.showMessage === 'function') {
                    window.showMessage(`随访提醒已设置，将在${days}天后提醒`, 'success');
                }
                // 如果随访模态框打开，刷新内容
                const modal = document.getElementById('followUpModal');
                if (modal) {
                    showFollowUpModal(); // 重新加载
                }
            } else {
                if (typeof window.showMessage === 'function') {
                    window.showMessage(result.message || '设置随访提醒失败', 'error');
                }
            }

        } catch (error) {
            console.error('创建随访提醒失败:', error);
            if (typeof window.showMessage === 'function') {
                window.showMessage('服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 完成随访
     * @param {string} followUpId - 随访ID
     */
    async function completeFollowUp(followUpId) {
        try {
            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const response = await fetch(`/api/follow-up/${followUpId}/complete`, {
                method: 'POST',
                headers: headers
            });

            const result = await response.json();

            if (result.success) {
                if (typeof window.showMessage === 'function') {
                    window.showMessage('随访已标记完成', 'success');
                }
                showFollowUpModal(); // 刷新列表
            } else {
                if (typeof window.showMessage === 'function') {
                    window.showMessage(result.message || '操作失败', 'error');
                }
            }

        } catch (error) {
            console.error('完成随访失败:', error);
            if (typeof window.showMessage === 'function') {
                window.showMessage('服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 延期随访
     * @param {string} followUpId - 随访ID
     */
    async function postponeFollowUp(followUpId) {
        const days = prompt('延期几天?', '3');
        if (!days || isNaN(days)) return;

        try {
            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const response = await fetch(`/api/follow-up/${followUpId}/postpone`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    postpone_days: parseInt(days)
                })
            });

            const result = await response.json();

            if (result.success) {
                if (typeof window.showMessage === 'function') {
                    window.showMessage(`随访已延期${days}天`, 'success');
                }
                showFollowUpModal(); // 刷新列表
            } else {
                if (typeof window.showMessage === 'function') {
                    window.showMessage(result.message || '延期失败', 'error');
                }
            }

        } catch (error) {
            console.error('延期随访失败:', error);
            if (typeof window.showMessage === 'function') {
                window.showMessage('服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 显示待随访列表
     */
    async function showActiveFollowUps() {
        if (typeof window.updateFollowUpFilter === 'function') {
            window.updateFollowUpFilter('active');
        }

        try {
            const headers = typeof window.getAuthHeaders === 'function'
                ? window.getAuthHeaders()
                : { 'Content-Type': 'application/json' };

            const response = await fetch('/api/follow-up/list?status=pending', {
                headers: headers
            });
            const result = await response.json();

            if (typeof window.updateFollowUpContainer === 'function') {
                window.updateFollowUpContainer(result.data || []);
            }
        } catch (error) {
            console.error('获取待随访列表失败:', error);
        }
    }

    // ===================== 图片上传 =====================

    /**
     * 上传多张图片（舌诊和面诊）
     */
    async function uploadImages() {
        // 检查是否有图片需要上传
        if (!window.tongueImage && !window.faceImage) {
            return;
        }

        // 检查网络状态
        if (typeof window.checkNetworkStatus === 'function' && !window.checkNetworkStatus()) {
            return;
        }

        const formData = new FormData();
        formData.append('conversation_id', window.currentConversationId);

        // 根据图片类型分别添加
        if (window.tongueImage) {
            formData.append('tongue_image', window.tongueImage);
        }
        if (window.faceImage) {
            formData.append('face_image', window.faceImage);
        }

        try {
            // 构建上传提示消息
            let uploadMessage = '正在分析';
            if (window.tongueImage && window.faceImage) {
                uploadMessage += '舌诊和面诊图片...';
            } else if (window.tongueImage) {
                uploadMessage += '舌诊图片...';
            } else if (window.faceImage) {
                uploadMessage += '面诊图片...';
            }

            if (typeof window.addMessage === 'function') {
                window.addMessage('user', uploadMessage);
            }

            const response = await fetch('/analyze_images', {
                method: 'POST',
                body: formData,
                // 添加超时控制
                signal: AbortSignal.timeout(120000), // 2分钟超时
                headers: {
                    // 不设置Content-Type，让浏览器自动设置multipart/form-data
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const analysisResult = `图像分析结果：
${data.analysis_result}`;

            const shouldShowImageFeedback = typeof window.containsPrescription === 'function'
                ? window.containsPrescription(analysisResult)
                : false;

            if (typeof window.addMessage === 'function') {
                window.addMessage('ai', analysisResult, shouldShowImageFeedback);
            }

            // 分析完成后清空图片缓存，允许用户重新上传
            if (typeof window.resetImageUploads === 'function') {
                window.resetImageUploads();
            }

        } catch (error) {
            console.error('图像上传完整错误信息:', error);

            let errorMessage = '图像分析失败：';

            if (error.message.includes('502')) {
                errorMessage += '服务器暂时无法处理请求 (502)。可能原因：\n';
                errorMessage += '- AI服务暂时繁忙，请稍后重试\n';
                errorMessage += '- 图片处理超时\n';
                errorMessage += '- 请检查网络连接';
            } else if (error.message.includes('timeout')) {
                errorMessage += '请求超时。请检查：\n';
                errorMessage += '- 网络连接是否稳定\n';
                errorMessage += '- 图片大小是否过大\n';
                errorMessage += '- 稍后重试';
            } else if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
                errorMessage += '网络连接问题。请检查：\n';
                errorMessage += '- 网络连接是否正常\n';
                errorMessage += '- 是否使用了代理或VPN\n';
                errorMessage += '- 刷新页面后重试';
            } else {
                errorMessage += error.message;
            }

            // 添加调试信息（仅在开发环境显示）
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                errorMessage += `\n\n[调试信息]\n对话ID: ${window.currentConversationId}\n错误类型: ${error.constructor.name}\n时间: ${new Date().toLocaleString()}`;
            }

            if (typeof window.addMessage === 'function') {
                window.addMessage('ai', errorMessage);
            }

            // 重置上传状态，允许用户重试
            if (typeof window.resetImageUploads === 'function') {
                window.resetImageUploads();
            }
        }
    }

    /**
     * 上传单张图片（兼容性支持，已废弃）
     * @param {File} file - 图片文件
     * @deprecated 请使用 uploadImages 函数
     */
    async function uploadImage(file) {
        console.warn('uploadImage函数已废弃，请使用uploadImages函数');
        // 为了兼容性，将单图片转换为多图片模式
        window.tongueImage = file; // 假设单图片默认为舌诊
        uploadImages();
    }

    // ===================== 语音输入 =====================

    /**
     * 开始语音录制
     */
    async function startVoiceRecording() {
        // 检查网络状态
        if (typeof window.checkNetworkStatus === 'function' && !window.checkNetworkStatus()) {
            const sendBtn = document.getElementById('sendBtn');
            if (sendBtn) sendBtn.disabled = false;
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            window.mediaRecorder = new MediaRecorder(stream);
            window.audioChunks = [];

            window.mediaRecorder.ondataavailable = event => {
                window.audioChunks.push(event.data);
            };

            window.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(window.audioChunks, { type: 'audio/webm' });
                await processVoiceInput(audioBlob);
            };

            window.mediaRecorder.start();
            window.isVoiceRecording = true;

            const voiceBtn = document.getElementById('voiceBtn');
            if (voiceBtn) {
                voiceBtn.textContent = '停止录音';
                voiceBtn.classList.add('recording');
            }

        } catch (error) {
            alert('无法访问麦克风，请检查权限设置');
        }
    }

    /**
     * 处理语音输入
     * @param {Blob} audioBlob - 音频数据
     */
    async function processVoiceInput(audioBlob) {
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'voice.webm');

        // 检查网络状态
        if (typeof window.checkNetworkStatus === 'function' && !window.checkNetworkStatus()) {
            const sendBtn = document.getElementById('sendBtn');
            if (sendBtn) sendBtn.disabled = false;
            return;
        }

        try {
            const response = await fetch('/speech_to_text', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.text) {
                const messageInput = document.getElementById('messageInput');
                if (messageInput) {
                    messageInput.value = data.text;
                    adjustTextareaHeight();
                }
            }

        } catch (error) {
            if (typeof window.addMessage === 'function') {
                window.addMessage('ai', `语音识别失败：${error.message}`);
            }
        }
    }

    // ===================== 用户认证 =====================

    /**
     * 验证token并加载用户数据
     * @param {string} token - 用户token
     */
    async function verifyTokenAndLoadUserData(token) {
        console.log('验证token并加载用户数据...');

        if (window.authManager && typeof window.authManager.verifyToken === 'function') {
            const user = await window.authManager.verifyToken(token);

            if (user) {
                window.currentUser = user;
                window.userToken = token;
                console.log('从后端验证成功，用户:', user.username || user.display_name);

                if (typeof window.updateUserInterface === 'function') {
                    window.updateUserInterface(true);
                }
            } else {
                console.log('Token验证失败，清除数据');

                if (window.authManager && typeof window.authManager.clearLoginState === 'function') {
                    window.authManager.clearLoginState();
                }

                // 跳转到登录页
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
            }
        } else {
            console.error('authManager不可用');
        }
    }

    /**
     * 执行登录
     */
    async function performLogin() {
        const usernameInput = document.getElementById('loginUsername');
        const passwordInput = document.getElementById('loginPassword');
        const errorDiv = document.getElementById('loginError');

        if (!usernameInput || !passwordInput) {
            console.error('登录表单元素不存在');
            return;
        }

        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        if (!username || !password) {
            if (errorDiv) {
                errorDiv.textContent = '请输入用户名和密码';
                errorDiv.style.display = 'block';
            }
            return;
        }

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const result = await response.json();

            if (result.success && result.user) {
                // 🔑 关键修复：使用authManager统一管理登录状态
                if (window.authManager) {
                    window.authManager.saveLoginState(result.user, result.token, false);
                } else {
                    // Fallback：如果authManager不可用，使用旧方式
                    localStorage.setItem('currentUser', JSON.stringify(result.user));
                    localStorage.setItem('session_token', result.token);
                }

                // 🔑 同步到全局变量
                window.currentUser = result.user;
                window.userToken = result.token;

                console.log('✅ 登录成功:', result.user.username || result.user.name);

                // 🔑 更新用户显示
                if (typeof window.updateUserDisplay === 'function') {
                    window.updateUserDisplay();
                }

                // 更新界面（向后兼容）
                if (typeof window.updateUserInterface === 'function') {
                    window.updateUserInterface(true);
                }

                // 关闭登录模态框
                if (typeof window.hideLoginModal === 'function') {
                    window.hideLoginModal();
                }

                // 显示欢迎消息
                const welcomeName = result.user.username || result.user.name || result.user.phone || '用户';
                if (typeof window.showMessage === 'function') {
                    window.showMessage(`欢迎回来，${welcomeName}！`, 'success');
                }

                // 🔑 刷新页面以确保所有模块使用新的登录状态
                setTimeout(() => {
                    window.location.reload();
                }, 1000);

            } else {
                if (errorDiv) {
                    errorDiv.textContent = result.message || '登录失败，请检查用户名和密码';
                    errorDiv.style.display = 'block';
                }
            }
        } catch (error) {
            console.error('登录请求失败:', error);
            if (errorDiv) {
                errorDiv.textContent = '网络错误，请检查网络连接';
                errorDiv.style.display = 'block';
            }
        }
    }

    /**
     * 打开注册页面
     */
    function openRegisterPage() {
        window.open('/nav', '_blank');
    }

    /**
     * 打开病历记录页面
     */
    function openHistoryPage() {
        // 移动端在当前窗口打开，避免被浏览器阻止
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            window.location.href = '/history';
        } else {
            window.open('/history', '_blank');
        }
    }

    /**
     * 退出登录
     * 清除所有用户数据并跳转到登录页面
     */
    function logout() {
        console.log('🚪 用户退出登录');

        // 使用统一认证管理器清除登录状态
        if (window.authManager && typeof window.authManager.clearLoginState === 'function') {
            window.authManager.clearLoginState();
        }

        // 清除所有用户相关的localStorage数据
        const keysToRemove = [
            'userData',
            'userToken',
            'currentUser',
            'patientToken',
            'doctorToken',
            'adminToken',
            'auth_token',
            'session_token'
        ];

        keysToRemove.forEach(key => {
            localStorage.removeItem(key);
            console.log(`🧹 已清除: ${key}`);
        });

        // 清除所有对话相关数据
        const allKeys = Object.keys(localStorage);
        const conversationKeys = allKeys.filter(key =>
            key.startsWith('tcm_doctor_history_') ||
            key.startsWith('conversationId_') ||
            key.startsWith('followup_shown_') ||
            key.includes('conversation')
        );

        conversationKeys.forEach(key => {
            localStorage.removeItem(key);
            console.log(`🧹 已清除对话数据: ${key}`);
        });

        // 清空sessionStorage
        sessionStorage.clear();

        console.log('✅ 用户数据清除完成');

        // 显示退出提示并跳转到登录页面
        alert('已退出登录');
        setTimeout(() => {
            window.location.href = '/login';
        }, 500);
    }

    // ===================== 键盘事件处理 =====================

    /**
     * 处理键盘按键事件
     * @param {KeyboardEvent} event - 键盘事件
     */
    function handleKeyPress(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            if (typeof window.sendMessage === 'function') {
                window.sendMessage();
            }
        }
    }

    /**
     * 调整文本框高度
     */
    function adjustTextareaHeight() {
        const textarea = document.getElementById('messageInput');
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
        }
    }

    // ===================== 暴露到全局 =====================

    // 星级评价系统
    window.initializeStarRatings = initializeStarRatings;
    window.bindEvaluationModalEvents = bindEvaluationModalEvents;

    // 反馈提交
    window.submitFeedback = submitFeedback;

    // 安全事件记录
    window.logSecurityEvent = logSecurityEvent;

    // 随访提醒系统
    window.checkFollowUpReminders = checkFollowUpReminders;
    window.showFollowUpModal = showFollowUpModal;
    window.createFollowUpReminder = createFollowUpReminder;
    window.completeFollowUp = completeFollowUp;
    window.postponeFollowUp = postponeFollowUp;
    window.showActiveFollowUps = showActiveFollowUps;

    // 图片上传
    window.uploadImages = uploadImages;
    window.uploadImage = uploadImage;

    // 语音输入
    window.startVoiceRecording = startVoiceRecording;
    window.processVoiceInput = processVoiceInput;

    // 用户认证
    window.verifyTokenAndLoadUserData = verifyTokenAndLoadUserData;
    window.performLogin = performLogin;
    window.logout = logout;
    window.openRegisterPage = openRegisterPage;
    window.openHistoryPage = openHistoryPage;

    // 键盘事件处理
    window.handleKeyPress = handleKeyPress;
    window.adjustTextareaHeight = adjustTextareaHeight;

    // ===================== 移动端图片上传 =====================

    /**
     * 关闭移动端图片上传模态框
     */
    window.closeMobileImageModal = function() {
        const modal = document.getElementById('mobileImageModal');
        if (modal) {
            modal.classList.add('mobile-modal-hidden');
        }
    };

    /**
     * 触发移动端舌诊图片上传
     */
    window.triggerMobileTongueUpload = function() {
        window.closeMobileImageModal();
        const input = document.getElementById('mobileTongueUpload');
        if (input) {
            input.click();
        }
    };

    /**
     * 处理移动端舌诊图片上传
     */
    window.handleMobileTongueUpload = function(event) {
        const file = event.target.files[0];
        if (file) {
            window.tongueImage = file;
            updateMobileUploadStatus();
            uploadImages();
        }
    };

    /**
     * 触发移动端面诊图片上传
     */
    window.triggerMobileFaceUpload = function() {
        window.closeMobileImageModal();
        const input = document.getElementById('mobileFaceUpload');
        if (input) {
            input.click();
        }
    };

    /**
     * 处理移动端面诊图片上传
     */
    window.handleMobileFaceUpload = function(event) {
        const file = event.target.files[0];
        if (file) {
            window.faceImage = file;
            updateMobileUploadStatus();
            uploadImages();
        }
    };

    /**
     * 更新移动端上传状态显示
     */
    function updateMobileUploadStatus() {
        const mobileTongueStatus = document.getElementById('mobileTongueStatus');
        const mobileFaceStatus = document.getElementById('mobileFaceStatus');

        if (mobileTongueStatus) {
            const span = mobileTongueStatus.querySelector('span');
            if (span) {
                span.textContent = window.tongueImage ? '已上传' : '未上传';
            }
        }

        if (mobileFaceStatus) {
            const span = mobileFaceStatus.querySelector('span');
            if (span) {
                span.textContent = window.faceImage ? '已上传' : '未上传';
            }
        }

        // 更新触发按钮文本
        const uploadText = document.getElementById('mobileUploadText');
        if (uploadText) {
            const uploadedCount = (window.tongueImage ? 1 : 0) + (window.faceImage ? 1 : 0);
            if (uploadedCount > 0) {
                uploadText.textContent = `已选择 ${uploadedCount} 张图片`;
            }
        }
    }

    // ===================== PC端图片上传 =====================

    /**
     * 触发PC端舌诊图片上传
     */
    window.triggerTongueUpload = function() {
        const input = document.getElementById('tongueImageUpload');
        if (input) {
            input.click();
        } else {
            console.warn('tongueImageUpload input not found');
        }
    };

    /**
     * 处理PC端舌诊图片上传
     */
    window.handleTongueImageUpload = function(event) {
        const file = event.target.files[0];
        if (file) {
            window.tongueImage = file;
            const uploadArea = document.getElementById('tongueUploadArea');
            if (uploadArea) {
                uploadArea.classList.add('has-file');
                uploadArea.innerHTML = `
                    <div class="upload-icon">✅</div>
                    <div class="upload-text">舌诊照片已选择</div>
                `;
            }
            updateUploadStatus();
            uploadImages();
        }
    };

    /**
     * 触发PC端面诊图片上传
     */
    window.triggerFaceUpload = function() {
        const input = document.getElementById('faceImageUpload');
        if (input) {
            input.click();
        } else {
            console.warn('faceImageUpload input not found');
        }
    };

    /**
     * 处理PC端面诊图片上传
     */
    window.handleFaceImageUpload = function(event) {
        const file = event.target.files[0];
        if (file) {
            window.faceImage = file;
            const uploadArea = document.getElementById('faceUploadArea');
            if (uploadArea) {
                uploadArea.classList.add('has-file');
                uploadArea.innerHTML = `
                    <div class="upload-icon">✅</div>
                    <div class="upload-text">面诊照片已选择</div>
                `;
            }
            updateUploadStatus();
            uploadImages();
        }
    };

    /**
     * 更新上传状态显示（PC端）
     */
    function updateUploadStatus() {
        const statusDiv = document.getElementById('uploadStatus');
        const tongueStatus = document.getElementById('tongueStatus');
        const faceStatus = document.getElementById('faceStatus');

        if (tongueStatus) {
            const span = tongueStatus.querySelector('span');
            if (span) span.textContent = window.tongueImage ? '已上传' : '未上传';
        }

        if (faceStatus) {
            const span = faceStatus.querySelector('span');
            if (span) span.textContent = window.faceImage ? '已上传' : '未上传';
        }

        if (statusDiv && (window.tongueImage || window.faceImage)) {
            statusDiv.style.display = 'block';
        }
    }

    // ===================== 语音输入功能 =====================

    // 语音录制状态
    let isVoiceRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];

    /**
     * 切换语音录制状态
     */
    window.toggleVoiceRecording = function() {
        if (isVoiceRecording) {
            stopVoiceRecording();
        } else {
            startVoiceRecordingInternal();
        }
    };

    /**
     * 开始语音录制
     */
    async function startVoiceRecordingInternal() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                await processVoiceInputInternal(audioBlob);
                // 停止所有音轨
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            isVoiceRecording = true;

            const voiceBtn = document.getElementById('voiceBtn');
            if (voiceBtn) {
                voiceBtn.textContent = '🔴 停止录音';
                voiceBtn.classList.add('recording');
            }

            console.log('🎤 开始语音录制');

        } catch (error) {
            console.error('语音录制失败:', error);
            alert('无法访问麦克风，请检查权限设置');
        }
    }

    /**
     * 停止语音录制
     */
    function stopVoiceRecording() {
        if (mediaRecorder && isVoiceRecording) {
            mediaRecorder.stop();
            isVoiceRecording = false;

            const voiceBtn = document.getElementById('voiceBtn');
            if (voiceBtn) {
                voiceBtn.textContent = '🎤 开始语音输入';
                voiceBtn.classList.remove('recording');
            }

            console.log('🛑 停止语音录制');
        }
    }

    /**
     * 处理语音输入
     */
    async function processVoiceInputInternal(audioBlob) {
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'voice.webm');

        try {
            const response = await fetch('/speech_to_text', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`语音识别失败: ${response.status}`);
            }

            const data = await response.json();
            if (data.text) {
                const messageInput = document.getElementById('messageInput');
                if (messageInput) {
                    messageInput.value = data.text;
                    messageInput.focus();
                }
                console.log('✅ 语音识别结果:', data.text);
            } else {
                alert('语音识别结果为空，请重试');
            }

        } catch (error) {
            console.error('语音识别失败:', error);
            alert('语音识别失败: ' + error.message);
        }
    }

    console.log('Smart Workflow Utils loaded successfully (PC upload + mobile upload + voice)');

})();
