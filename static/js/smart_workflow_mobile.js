/**
 * TCM-AI 智能问诊系统 - 移动端模块
 *
 * 本模块包含所有移动端相关的功能代码，从 index_smart_workflow.html 提取而来
 * 所有函数均暴露到 window 对象，以便全局调用
 *
 * 功能模块:
 * 1. 移动端检测与适配
 * 2. 移动端导航与交互
 * 3. 移动端消息系统
 * 4. 微信环境检测与优化
 * 5. Chrome移动版调试工具
 * 6. 网络状态监控
 *
 * @version 1.0.0
 * @date 2025-11-20
 */

(function() {
    'use strict';

    // ========== 移动端检测逻辑 ==========

    /**
     * 检测是否为移动端设备
     * @returns {boolean} 是否为移动端
     */
    function isMobileDevice() {
        return window.innerWidth <= 768;
    }

    /**
     * 获取设备类型信息
     * @returns {Object} 设备信息对象
     */
    function getDeviceInfo() {
        return {
            isMobile: window.innerWidth <= 768,
            screenWidth: window.innerWidth,
            screenHeight: window.innerHeight,
            userAgent: navigator.userAgent,
            isChrome: /Chrome/.test(navigator.userAgent),
            isSafari: /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent),
            isWechat: /MicroMessenger/i.test(navigator.userAgent)
        };
    }

    // ========== 移动端导航系统 ==========

    /**
     * 显示移动端简化导航
     * 提供患者服务导航面板
     */
    function showMobileNavigation() {
        const navigationHtml = `
            <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;" onclick="this.remove()">
                <div style="background: white; border-radius: 12px; padding: 20px; max-width: 90%; max-height: 80%; overflow-y: auto;" onclick="event.stopPropagation()">
                    <div style="text-align: center; font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #374151;">
                        患者服务导航
                    </div>

                    <div style="margin-bottom: 20px;">
                        <button style="display: block; width: 100%; padding: 12px; margin-bottom: 8px; background: #f8f9fa; border: none; border-radius: 8px; text-align: left;" onclick="window.open('/', '_blank'); this.parentElement.parentElement.parentElement.remove();">主页 - AI中医问诊</button>
                        <button style="display: block; width: 100%; padding: 12px; margin-bottom: 8px; background: #f8f9fa; border: none; border-radius: 8px; text-align: left;" onclick="window.open('/nav', '_blank'); this.parentElement.parentElement.parentElement.remove();">用户注册</button>
                        <button style="display: block; width: 100%; padding: 12px; margin-bottom: 8px; background: #f8f9fa; border: none; border-radius: 8px; text-align: left;" onclick="window.open('/history', '_blank'); this.parentElement.parentElement.parentElement.remove();">历史记录</button>
                    </div>

                    <button style="width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 8px; font-weight: 500;" onclick="this.parentElement.parentElement.remove()">关闭</button>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', navigationHtml);
    }

    // ========== 对话管理功能 ==========

    /**
     * 开始新对话 - 清空当前医生的所有对话记录
     * 包括本地存储和服务器端数据
     */
    async function startNewChat() {
        if (!window.selectedDoctor) {
            alert('请先选择医生再清空对话记录');
            return;
        }

        const choice = confirm('清空对话记录\n\n这将清空当前医生的所有对话记录，包括：\n- 本地存储的消息\n- 服务器端的对话历史\n- 已保存的问诊状态\n\n确定要清空吗？');

        if (choice) {
            try {
                const userId = window.getCurrentUserId ? window.getCurrentUserId() : 'anonymous';

                // 1. 清空本地存储
                const historyKey = `tcm_doctor_history_${userId}_${window.selectedDoctor}`;
                localStorage.removeItem(historyKey);

                // 2. 清空服务器端对话记录
                const headers = window.getAuthHeaders ? window.getAuthHeaders() : { 'Content-Type': 'application/json' };
                const response = await fetch('/api/conversation/clear', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({
                        user_id: userId,
                        doctor_id: window.selectedDoctor,
                        clear_type: 'all'
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        console.log(`已清空${window.selectedDoctor}医生的完整对话记录`);
                        if (window.showMessage) {
                            const doctorName = window.getDoctorDisplayName ?
                                window.getDoctorDisplayName(window.selectedDoctor) : window.selectedDoctor;
                            window.showMessage(`已清空${doctorName}的对话记录`, 'success');
                        }
                    } else {
                        console.warn('服务器清空失败，但本地已清空');
                        if (window.showMessage) {
                            window.showMessage('本地记录已清空，服务器清空失败', 'warning');
                        }
                    }
                } else {
                    console.warn('服务器清空请求失败，但本地已清空');
                    if (window.showMessage) {
                        window.showMessage('本地记录已清空，服务器清空失败', 'warning');
                    }
                }

                // 3. 生成新的对话ID
                if (window.generateConversationId) {
                    window.generateConversationId();
                }

                // 4. 清空页面显示并重新加载空白状态
                if (window.clearAllMessages) {
                    window.clearAllMessages();
                }
                if (window.loadDoctorHistory) {
                    window.loadDoctorHistory(window.selectedDoctor);
                }

            } catch (error) {
                console.error('清空对话记录失败:', error);
                if (window.showMessage) {
                    window.showMessage('清空失败，请重试', 'error');
                }
            }
        } else {
            // 用户选择保持历史记录
            console.log('用户选择保持历史记录不变');

            // 隐藏输入框
            const inputContainer = document.querySelector('.input-container');
            if (inputContainer) {
                inputContainer.classList.remove('show');
            }
        }
    }

    /**
     * 导出单个对话为HTML文件
     * @param {string} sessionId - 会话ID
     */
    async function exportConversation(sessionId) {
        try {
            const response = await fetch(`/api/user/conversation/${sessionId}/export`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `TCM_病历_${sessionId.slice(0,8)}_${new Date().toISOString().split('T')[0]}.html`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                // 关闭详情模态框
                if (window.closeRecordDetailModal) {
                    window.closeRecordDetailModal();
                }
                if (window.showMessage) {
                    window.showMessage('导出成功', 'success');
                }
            } else {
                if (window.showMessage) {
                    window.showMessage('导出失败，请重试', 'error');
                }
            }
        } catch (error) {
            console.error('导出失败:', error);
            if (window.showMessage) {
                window.showMessage('导出失败，请检查网络连接', 'error');
            }
        }
    }

    // ========== 移动端消息系统 ==========

    /**
     * 移动端添加消息
     * @param {string} sender - 发送者类型 ('user' 或 'ai')
     * @param {string} content - 消息内容
     * @param {boolean} showFeedback - 是否显示反馈按钮
     * @param {boolean} isPaid - 是否已支付
     * @param {string} prescriptionId - 处方ID
     */
    async function addMobileMessage(sender, content, showFeedback = false, isPaid = false, prescriptionId = null) {
        const container = document.getElementById('mobileMessagesContainer');

        // 防重复机制：检查最后一条消息是否与当前消息相同
        if (container) {
            const lastMessage = container.querySelector('.message:last-child');
            if (lastMessage) {
                const lastSender = lastMessage.classList.contains('user') ? 'user' : 'ai';
                const lastText = lastMessage.querySelector('.message-text');
                const lastContent = lastText ? lastText.textContent.trim() : '';

                if (lastSender === sender && lastContent === content.trim()) {
                    console.warn('移动端检测到重复消息，跳过添加:', {sender, contentPreview: content.substring(0, 50)});
                    return;
                }
            }
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        console.log('[addMobileMessage] sender:', sender, 'className:', messageDiv.className);

        // 使用简化版处方管理器处理内容
        let processedContent = content;
        if (sender === 'ai') {
            if (window.simplePrescriptionManager) {
                try {
                    processedContent = await window.simplePrescriptionManager.processContent(content, prescriptionId);
                    console.log('[移动端] 处方内容已通过simplePrescriptionManager处理');
                } catch (error) {
                    console.error('[移动端] 处方内容处理失败:', error);
                    processedContent = window.formatMessage ? window.formatMessage(content) : content;
                }
            } else {
                console.warn('[移动端] simplePrescriptionManager未加载，使用备用方案');
                processedContent = window.formatMessage ? window.formatMessage(content) : content;
            }
        }

        // 如果有处方ID，保存到元素属性中
        if (prescriptionId) {
            messageDiv.setAttribute('data-prescription-id', prescriptionId);
        }

        const messageContent = `
            <div class="message-avatar">
                ${sender === 'user' ? '' : ''}
            </div>
            <div class="message-content">
                <div class="message-text">${processedContent}</div>
                ${sender === 'ai' && showFeedback ? `
                    <div class="feedback-controls">
                        <div class="feedback-label">这个回答有帮助吗？</div>
                        <div class="rating-buttons">
                            <button class="rating-btn" onclick="rateFeedback(this, 5)">很好</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 4)">不错</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 3)">还行</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 2)">不好</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 1)">很差</button>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        messageDiv.innerHTML = messageContent;

        // 强制设置inline样式，确保移动端显示正确
        messageDiv.style.display = 'flex';
        messageDiv.style.alignItems = 'flex-end';
        messageDiv.style.gap = '8px';
        messageDiv.style.width = '100%';
        messageDiv.style.marginBottom = '16px';

        if (sender === 'user') {
            messageDiv.style.justifyContent = 'flex-end';
            messageDiv.style.flexDirection = 'row-reverse';
            console.log('[addMobileMessage] 用户消息 - 强制右对齐');
        } else if (sender === 'ai') {
            messageDiv.style.justifyContent = 'flex-start';
            messageDiv.style.flexDirection = 'row';
            console.log('[addMobileMessage] AI消息 - 强制左对齐');
        }

        container.appendChild(messageDiv);

        // 为移动端保存原始内容用于支付后解锁
        if (sender === 'ai' && prescriptionId && content && window.prescriptionContentRenderer) {
            const messageTextEl = messageDiv.querySelector('.message-text');
            if (messageTextEl && !messageTextEl.getAttribute('data-original-content')) {
                messageTextEl.setAttribute('data-original-content', content);
                console.log('移动端已保存原始内容用于支付后解锁');
            }
        }

        // 平滑滚动到底部
        setTimeout(() => {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);

        // 自动保存移动端对话历史
        if (window.selectedDoctor) {
            setTimeout(() => {
                if (window.saveCurrentDoctorHistory) {
                    window.saveCurrentDoctorHistory();
                }
                if (window.updateConversationListAfterMessage) {
                    window.updateConversationListAfterMessage();
                }
            }, 200);
        }
    }

    /**
     * 移动端发送消息
     */
    function normalizeMobileConsultationResponse(responseData) {
        const data = responseData && typeof responseData === 'object' ? (responseData.data || {}) : {};
        const resolvedReply = typeof window.resolveMessageText === 'function'
            ? (window.resolveMessageText(data) || window.resolveMessageText(responseData))
            : (data.reply || (responseData ? responseData.reply : ''));
        return {
            reply: resolvedReply || '',
            prescriptionId: data.prescription_id || (responseData ? responseData.prescription_id : null) || null,
            isPaid: Boolean(
                (data.is_paid !== undefined ? data.is_paid : undefined) ??
                (responseData ? responseData.is_paid : false) ??
                false
            )
        };
    }

    async function sendMobileMessage() {
        const input = document.getElementById('mobileMessageInput');
        const message = input.value.trim();
        const doctorId = window.selectedDoctor;

        if (!message || !doctorId) {
            if (!doctorId) {
                alert('请先选择一位医师');
            }
            return;
        }

        // 添加用户消息
        addMobileMessage('user', message);
        input.value = '';
        adjustMobileTextareaHeight();

        // 显示加载状态
        const sendBtn = document.getElementById('mobileSendBtn');
        sendBtn.disabled = true;

        // 添加"正在分析"的临时消息
        const loadingMessage = document.createElement('div');
        loadingMessage.className = 'message ai loading-message';
        loadingMessage.innerHTML = `
            <div class="loading-spinner" style="display: inline-block; width: 16px; height: 16px; border: 2px solid #f3f4f6; border-radius: 50%; border-top: 2px solid #667eea; animation: spin 1s linear infinite; margin-right: 8px;"></div>
            AI正在分析您的症状...
        `;
        const container = document.getElementById('mobileMessagesContainer');
        container.appendChild(loadingMessage);
        container.scrollTop = container.scrollHeight;

        // 创建带超时的AbortController
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
        }, 45000);

        // 检查网络状态
        if (!checkNetworkStatus()) {
            sendBtn.disabled = false;
            return;
        }

        try {
            // 获取当前对话历史以维持上下文连续性
            const conversationHistory = window.getCurrentConversationHistory ?
                window.getCurrentConversationHistory() : [];

            const headers = window.getAuthHeaders ? window.getAuthHeaders() : { 'Content-Type': 'application/json' };
            let userId = window.getCurrentUserId ? window.getCurrentUserId() : 'anonymous';
            if (typeof window.resolveUserId === 'function') {
                userId = window.resolveUserId(userId, window.currentUser);
            }
            const conversationId = window.currentConversationId || '';

            const response = await fetch('/api/consultation/chat', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId,
                    doctor_id: doctorId,
                    selected_doctor: doctorId,
                    patient_id: userId,
                    conversation_history: conversationHistory
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // 移除加载消息
            const loadingMsg = document.querySelector('.loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }

            console.log('移动端API完整响应:', data);

            // 处理API响应格式
            const normalizedResponse = normalizeMobileConsultationResponse(data);
            const aiReply = normalizedResponse.reply;
            if (!aiReply) {
                console.error('移动端API响应格式错误，响应结构:', Object.keys(data));
                throw new Error('API响应格式错误: 未找到reply字段');
            }
            console.log('移动端回复内容长度:', aiReply.length);

            if (aiReply) {
                const containsActualPrescription = window.containsPrescription ?
                    window.containsPrescription(aiReply) : false;
                const isTemporaryAdvice = window.prescriptionContentRenderer ?
                    !window.prescriptionContentRenderer.containsPrescription(aiReply) : false;

                const shouldShowFeedback = true;

                let prescriptionId = normalizedResponse.prescriptionId;
                const isPaid = normalizedResponse.isPaid;

                const needsPayment = containsActualPrescription && !isTemporaryAdvice && !isPaid;

                console.log('移动端即将添加AI消息:', {
                    aiReply: aiReply.substring(0, 100) + '...',
                    shouldShowFeedback,
                    containsActualPrescription,
                    isTemporaryAdvice,
                    needsPayment,
                    isPaid,
                    prescriptionId
                });

                await addMobileMessage('ai', aiReply, shouldShowFeedback, isPaid, prescriptionId);

                if (shouldShowFeedback) {
                    console.log('移动端检测到处方内容，显示点评功能，处方ID:', prescriptionId, '支付状态:', isPaid);
                }
            } else {
                await addMobileMessage('ai', '抱歉，我现在无法回答您的问题，请稍后再试。');
            }

            // 保存移动端对话历史
            setTimeout(() => {
                if (window.saveCurrentDoctorHistory) {
                    window.saveCurrentDoctorHistory();
                }
                if (window.updateConversationListAfterMessage) {
                    window.updateConversationListAfterMessage();
                }
            }, 200);

        } catch (error) {
            console.error('Mobile API Error:', error);

            // 移除加载消息
            const loadingMsg = document.querySelector('.loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }

            // 详细的错误信息
            let errorMsg = '网络请求失败';
            if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                errorMsg = '网络连接错误，请检查网络状态';
            } else if (error.message.includes('timeout')) {
                errorMsg = '请求超时，请稍后再试';
            } else if (error.message.includes('HTTP error')) {
                errorMsg = `服务器错误: ${error.message}`;
            } else {
                errorMsg = `连接失败: ${error.message}`;
            }

            await addMobileMessage('ai', errorMsg);
        } finally {
            sendBtn.disabled = false;
        }
    }

    /**
     * 移动端输入框高度调整
     */
    function adjustMobileTextareaHeight() {
        const textarea = document.getElementById('mobileMessageInput');
        if (!textarea) return;

        textarea.style.height = '44px';
        const newHeight = Math.min(textarea.scrollHeight, 100);
        textarea.style.height = newHeight + 'px';
    }

    /**
     * 移动端键盘事件处理
     * @param {KeyboardEvent} event - 键盘事件
     */
    function handleMobileKeyPress(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMobileMessage();
        }
    }

    /**
     * 确保移动端输入框可见
     */
    function ensureMobileInputVisible() {
        const container = document.getElementById('mobileMessagesContainer');

        setTimeout(() => {
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }, 100);
    }

    /**
     * 移动端输入框失焦处理
     */
    function handleMobileInputBlur() {
        setTimeout(() => {
            const container = document.getElementById('mobileMessagesContainer');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }, 200);
    }

    /**
     * 移动端渲染医生卡片
     */
    function renderMobileDoctorCards() {
        console.log('[DEBUG] 渲染移动端医生卡片 - 开始');

        const container = document.getElementById('mobileDoctorsGrid');
        if (!container) {
            console.error('[DEBUG] 未找到移动端医生容器 mobileDoctorsGrid');
            return;
        }

        console.log('[DEBUG] 找到容器 mobileDoctorsGrid');

        // 清空容器
        container.innerHTML = '';

        // 强制显示容器
        container.style.display = 'block';
        container.style.visibility = 'visible';
        container.style.opacity = '1';

        // 检查医生数据
        const doctors = window.doctors || {};
        if (Object.keys(doctors).length === 0) {
            console.error('[DEBUG] doctors对象为空！尝试加载默认医生数据');
            if (window.loadDefaultDoctors) {
                window.loadDefaultDoctors();
            }
            return;
        }

        // 渲染医生卡片
        let cardCount = 0;
        Object.entries(doctors).forEach(([key, doctor]) => {
            console.log(`[DEBUG] 创建医生卡片: ${key} - ${doctor.name}`);

            const card = document.createElement('div');
            card.className = 'mobile-doctor-card';
            card.onclick = () => {
                if (window.selectMobileDoctor) {
                    window.selectMobileDoctor(key, doctor);
                }
            };

            card.innerHTML = `
                <div class="mobile-doctor-info">
                    <div class="mobile-doctor-avatar">${doctor.avatar}</div>
                    <div class="mobile-doctor-details">
                        <h3>${doctor.name}</h3>
                        <div class="school">${doctor.school}</div>
                    </div>
                </div>
                <div class="mobile-doctor-specialty">
                    <strong>擅长：</strong>${doctor.specialty}
                </div>
            `;

            container.appendChild(card);
            cardCount++;
        });

        console.log(`[DEBUG] 移动端医生卡片渲染完成，共${cardCount}张卡片`);
    }

    /**
     * 移动端设置默认医生
     * @param {string} doctorKey - 医生标识符
     */
    function setMobileDefaultDoctor(doctorKey) {
        const doctors = window.doctors || {};
        const doctor = doctors[doctorKey];
        if (!doctor) return;

        window.selectedDoctor = doctorKey;

        // 更新移动端医生信息
        const avatarEl = document.getElementById('mobileDoctorAvatar');
        const nameEl = document.getElementById('mobileDoctorName');
        const descEl = document.getElementById('mobileDoctorDesc');

        if (avatarEl) avatarEl.textContent = doctor.avatar;
        if (nameEl) nameEl.textContent = doctor.name;
        if (descEl) descEl.textContent = doctor.school;

        // 添加欢迎消息到移动端
        const mobileContainer = document.getElementById('mobileMessagesContainer');
        if (mobileContainer && !mobileContainer.querySelector('.message')) {
            addMobileMessage('ai', `您好！我是${doctor.name}，${doctor.school}传人。请详细描述您的症状，我将为您进行专业的中医分析。`);
        }
    }

    // ========== 微信环境检测与优化 ==========

    /**
     * 检测是否在微信环境中
     * @returns {boolean} 是否为微信浏览器
     */
    function isWechat() {
        return /MicroMessenger/i.test(navigator.userAgent);
    }

    /**
     * 检测微信公众号来源
     * @returns {Object} 微信来源信息
     */
    function detectWechatSource() {
        const urlParams = new URLSearchParams(window.location.search);
        const fromWechat = urlParams.get('from') === 'wechat';
        const wechatSource = urlParams.get('source') || 'unknown';

        return {
            fromWechat: fromWechat,
            source: wechatSource,
            isWechatBrowser: isWechat()
        };
    }

    /**
     * 处理微信公众号访问
     */
    function handleWechatPublicAccount() {
        const wechatInfo = detectWechatSource();

        if (wechatInfo.fromWechat || wechatInfo.isWechatBrowser) {
            console.log('微信公众号用户访问，来源:', wechatInfo.source);

            // 记录微信访问统计
            fetch('/api/log_wechat_visit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source: wechatInfo.source,
                    from_wechat: wechatInfo.fromWechat,
                    is_wechat_browser: wechatInfo.isWechatBrowser,
                    timestamp: new Date().toISOString(),
                    page: 'main_app'
                })
            }).catch(err => console.log('微信访问记录失败:', err));

            // 显示微信专属欢迎信息
            if (wechatInfo.fromWechat && wechatInfo.source === 'menu') {
                setTimeout(() => showWechatWelcome(), 1000);
            }

            // 微信内优化：隐藏不必要的分享按钮
            if (wechatInfo.isWechatBrowser) {
                const shareButtons = document.querySelectorAll('.share-button, .external-share');
                shareButtons.forEach(btn => btn.style.display = 'none');
            }
        }
    }

    /**
     * 显示微信专属欢迎信息
     */
    function showWechatWelcome() {
        const welcomeHTML = `
            <div id="wechatWelcome" style="
                position: fixed;
                top: 60px;
                left: 50%;
                transform: translateX(-50%);
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                padding: 12px 20px;
                border-radius: 25px;
                font-size: 13px;
                z-index: 9999;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                animation: slideInDown 0.6s ease-out;
                text-align: center;
                max-width: 280px;
            ">
                欢迎从公众号访问！<br>
                <small>5大中医流派，专业AI问诊</small>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', welcomeHTML);

        // 4秒后淡出
        setTimeout(() => {
            const welcome = document.getElementById('wechatWelcome');
            if (welcome) {
                welcome.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
                welcome.style.opacity = '0';
                welcome.style.transform = 'translateX(-50%) translateY(-20px)';
                setTimeout(() => welcome.remove(), 500);
            }
        }, 4000);
    }

    /**
     * 初始化微信环境保护机制
     */
    function initWechatProtection() {
        if (isWechat()) {
            // 动态设置分享信息
            document.title = "AI中医智能问诊助手";

            // 添加微信分享元信息
            var metaDesc = document.querySelector('meta[name="description"]');
            if (metaDesc) {
                metaDesc.content = "专业AI中医诊断助手，智能症状分析，证候判断，个性化方剂推荐";
            }

            // 记录微信分享统计
            window.addEventListener('load', function() {
                fetch('/api/wechat_visit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        page: 'main_app',
                        is_shared: document.referrer.includes('wechat'),
                        timestamp: new Date().toISOString()
                    })
                }).catch(() => {});
            });

            // 页面关闭或刷新时保存历史记录
            window.addEventListener('beforeunload', function(event) {
                if (window.selectedDoctor && window.saveCurrentDoctorHistory) {
                    window.saveCurrentDoctorHistory();
                    console.log('页面关闭前已保存历史记录');
                }
            });

            // 页面可见性变化时也保存
            document.addEventListener('visibilitychange', function() {
                if (document.visibilityState === 'hidden' && window.selectedDoctor && window.saveCurrentDoctorHistory) {
                    window.saveCurrentDoctorHistory();
                    console.log('页面隐藏时已保存历史记录');
                }
            });

            // 增强历史记录保护 - 定期自动保存
            setInterval(() => {
                if (window.selectedDoctor && window.saveCurrentDoctorHistory) {
                    const messagesContainer = document.getElementById(window.innerWidth <= 768 ? 'mobileMessagesContainer' : 'messagesContainer');
                    if (messagesContainer && messagesContainer.children.length > 0) {
                        window.saveCurrentDoctorHistory();
                        console.log('定期自动保存历史记录');
                    }
                }
            }, 30000);

            // 浏览器焦点变化时保存
            window.addEventListener('blur', function() {
                if (window.selectedDoctor && window.saveCurrentDoctorHistory) {
                    window.saveCurrentDoctorHistory();
                    console.log('浏览器失去焦点时保存历史记录');
                }
            });

            // 页面卸载前强制保存
            window.addEventListener('pagehide', function() {
                if (window.selectedDoctor && window.saveCurrentDoctorHistory) {
                    window.saveCurrentDoctorHistory();
                    console.log('页面卸载前保存历史记录');
                }
            });
        }
    }

    // ========== localStorage管理功能 ==========

    /**
     * 检查localStorage使用量
     */
    function checkLocalStorageUsage() {
        try {
            let totalSize = 0;
            for (let key in localStorage) {
                if (localStorage.hasOwnProperty(key)) {
                    totalSize += localStorage[key].length + key.length;
                }
            }
            const sizeInMB = (totalSize / 1024 / 1024).toFixed(2);
            console.log(`LocalStorage使用量: ${sizeInMB}MB`);

            // 如果超过4MB，发出警告
            if (totalSize > 4 * 1024 * 1024) {
                console.warn('LocalStorage使用量较大，可能需要清理');
            }
        } catch (error) {
            console.error('检查localStorage使用量失败:', error);
        }
    }

    /**
     * 清理旧的历史记录
     */
    function cleanOldHistoryRecords() {
        try {
            const keys = Object.keys(localStorage);
            const userId = window.getCurrentUserId ? window.getCurrentUserId() : 'anonymous';
            const historyKeys = keys.filter(key => key.startsWith(`tcm_doctor_history_${userId}_`));

            // 如果有超过10个医生的历史记录，清理最旧的
            if (historyKeys.length > 10) {
                const keysWithTime = historyKeys.map(key => {
                    try {
                        const data = JSON.parse(localStorage.getItem(key));
                        const lastUpdated = data.lastUpdated || data.timestamp || 0;
                        return { key, lastUpdated };
                    } catch {
                        return { key, lastUpdated: 0 };
                    }
                });

                // 按时间排序，删除最旧的
                keysWithTime.sort((a, b) => new Date(a.lastUpdated) - new Date(b.lastUpdated));
                const keysToDelete = keysWithTime.slice(0, historyKeys.length - 8);

                keysToDelete.forEach(({ key }) => {
                    localStorage.removeItem(key);
                    console.log(`已清理旧历史记录: ${key}`);
                });
            }
        } catch (error) {
            console.error('清理旧历史记录失败:', error);
        }
    }

    /**
     * 历史记录诊断功能
     */
    function diagnoseHistoryIssues() {
        console.log('=== 历史记录诊断 ===');
        console.log('当前医生:', window.selectedDoctor);
        console.log('浏览器信息:', navigator.userAgent);
        console.log('屏幕尺寸:', window.innerWidth + 'x' + window.innerHeight);

        const keys = Object.keys(localStorage);
        const userId = window.getCurrentUserId ? window.getCurrentUserId() : 'anonymous';
        const historyKeys = keys.filter(key => key.startsWith(`tcm_doctor_history_${userId}_`));
        console.log('历史记录数量:', historyKeys.length);

        // 用户历史记录调试信息
        if (window.debugUserIdAndHistory) {
            window.debugUserIdAndHistory();
        }

        historyKeys.forEach(key => {
            try {
                const data = localStorage.getItem(key);
                const parsed = JSON.parse(data);
                const messageCount = Array.isArray(parsed) ? parsed.length : (parsed.messages ? parsed.messages.length : 0);
                console.log(`${key}: ${messageCount}条消息, 大小=${(data.length/1024).toFixed(1)}KB`);
            } catch (error) {
                console.error(`${key}: 数据损坏`, error);
            }
        });

        checkLocalStorageUsage();

        // 测试localStorage写入
        try {
            const testKey = 'tcm_test_' + Date.now();
            localStorage.setItem(testKey, 'test');
            localStorage.removeItem(testKey);
            console.log('localStorage写入测试成功');
        } catch (error) {
            console.error('localStorage写入测试失败:', error);
        }
    }

    // ========== 网络状态监控 ==========

    /**
     * 检查网络状态
     * @returns {boolean} 网络是否正常
     */
    function checkNetworkStatus() {
        if (!navigator.onLine) {
            addMobileMessage('ai', '检测到网络连接中断，请检查您的网络设置。');
            return false;
        }
        return true;
    }

    /**
     * 初始化网络状态监听
     */
    function initNetworkMonitor() {
        window.addEventListener('online', function() {
            console.log('Network is back online');
        });

        window.addEventListener('offline', function() {
            console.log('Network is offline');
            addMobileMessage('ai', '网络连接已断开，请检查您的网络设置。');
        });
    }

    // ========== Chrome移动版调试工具 ==========

    /**
     * 调试日志函数
     * @param {string} msg - 日志消息
     * @param {string} type - 日志类型 ('info', 'error', 'success', 'warn')
     */
    function debugLog(msg, type = 'info') {
        const logDiv = document.getElementById('chromeDebugLog');
        if (!logDiv) return;

        const time = new Date().toLocaleTimeString();
        const color = type === 'error' ? '#f44' : type === 'success' ? '#4f4' : type === 'warn' ? '#fa0' : '#0f0';
        logDiv.innerHTML += `<div style="color: ${color}; margin: 2px 0;">[${time}] ${msg}</div>`;
        logDiv.scrollTop = logDiv.scrollHeight;
        console.log(`[DEBUG] ${msg}`);
    }

    /**
     * 初始化Chrome移动版调试工具
     */
    function initChromeDebugTool() {
        const isMobile = window.innerWidth <= 768;
        const isChrome = /Chrome/.test(navigator.userAgent);

        // 只在移动端Chrome显示调试按钮
        if (isMobile && isChrome) {
            const debugBtn = document.getElementById('chromeDebugBtn');
            if (debugBtn) {
                debugBtn.style.display = 'block';
            }
        }

        // 页面加载完成后检查
        document.addEventListener('DOMContentLoaded', function() {
            if (!isMobile || !isChrome) return;

            debugLog('页面加载完成', 'success');
            debugLog(`屏幕尺寸: ${window.innerWidth}x${window.innerHeight}`, 'info');
            debugLog(`User Agent: ${navigator.userAgent.substring(0, 80)}...`, 'info');

            // 检查医生数据
            setTimeout(function() {
                try {
                    debugLog('开始执行延迟检查...', 'info');
                    debugLog(`doctors对象: ${typeof window.doctors}, 键数: ${Object.keys(window.doctors || {}).length}`, 'info');

                    // 检查容器
                    const mobileContainer = document.getElementById('mobilePageContainer');
                    const doctorsGrid = document.getElementById('mobileDoctorsGrid');

                    if (mobileContainer) {
                        const styles = getComputedStyle(mobileContainer);
                        debugLog(`mobilePageContainer - display: ${styles.display}, visibility: ${styles.visibility}`, styles.display === 'none' ? 'error' : 'success');
                    } else {
                        debugLog('未找到mobilePageContainer', 'error');
                    }

                    if (doctorsGrid) {
                        const styles = getComputedStyle(doctorsGrid);
                        const children = doctorsGrid.children.length;
                        debugLog(`mobileDoctorsGrid - 子元素数: ${children}, display: ${styles.display}`, children > 0 ? 'success' : 'warn');

                        if (children === 0) {
                            debugLog('医生卡片容器为空！尝试手动渲染...', 'warn');
                            // Chrome修复：多次重试渲染
                            let retryCount = 0;
                            const maxRetries = 5;
                            const retryRender = function() {
                                retryCount++;
                                debugLog(`第${retryCount}次尝试渲染医生卡片...`, 'warn');

                                if (typeof renderMobileDoctorCards === 'function') {
                                    renderMobileDoctorCards();

                                    // 检查是否渲染成功
                                    setTimeout(function() {
                                        const newChildren = doctorsGrid.children.length;
                                        if (newChildren > 0) {
                                            debugLog(`渲染成功！医生卡片数: ${newChildren}`, 'success');
                                        } else if (retryCount < maxRetries) {
                                            debugLog(`第${retryCount}次渲染失败，继续重试...`, 'error');
                                            setTimeout(retryRender, 500);
                                        } else {
                                            debugLog(`已达最大重试次数(${maxRetries})，渲染失败`, 'error');
                                            debugLog(`请点击页面刷新或联系技术支持`, 'error');
                                        }
                                    }, 100);
                                }
                            };
                            retryRender();
                        }
                    } else {
                        debugLog('未找到mobileDoctorsGrid', 'error');
                    }

                    // 检查按钮
                    const backBtn = document.querySelector('.mobile-back-btn');
                    const guidanceBtn = document.querySelector('.mobile-guidance-trigger');
                    debugLog(`按钮检测 - 返回: ${!!backBtn}, 指导: ${!!guidanceBtn}`, backBtn && guidanceBtn ? 'success' : 'warn');

                } catch (error) {
                    debugLog(`检查过程出错: ${error.message}`, 'error');
                    debugLog(`错误堆栈: ${error.stack}`, 'error');
                }
            }, 1000);
        });
    }

    // ========== 调试模式检测 ==========

    /**
     * 检测是否为调试模式
     * @returns {boolean} 是否为调试模式
     */
    function isDebugMode() {
        const urlParams = new URLSearchParams(window.location.search);
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const hasDebugParam = urlParams.has('debug');
        const isDevPort = window.location.port === '7789' || window.location.port === '3000';

        return isLocalhost || hasDebugParam || isDevPort;
    }

    /**
     * 初始化调试手势检测
     */
    function initDebugGesture() {
        let clickSequence = [];
        let debugVisible = false;

        document.addEventListener('click', function(e) {
            // 记录点击位置（分为9宫格）
            const x = Math.floor(e.clientX / (window.innerWidth / 3));
            const y = Math.floor(e.clientY / (window.innerHeight / 3));
            const position = y * 3 + x;

            clickSequence.push(position);
            if (clickSequence.length > 5) clickSequence.shift();

            // 特殊序列：左上-右上-左下-右下-中心 (0-2-6-8-4)
            const debugSequence = [0, 2, 6, 8, 4];
            const isDebugSequence = clickSequence.length === 5 &&
                clickSequence.every((pos, idx) => pos === debugSequence[idx]);

            if (isDebugSequence && (isDebugMode() || window.location.hostname.includes('dev'))) {
                debugVisible = !debugVisible;
                const versionInfo = document.getElementById('mobileVersionInfo');
                if (versionInfo) {
                    versionInfo.style.display = debugVisible ? 'block' : 'none';
                }
                clickSequence = [];

                if (debugVisible) {
                    setTimeout(() => {
                        if (versionInfo) {
                            versionInfo.style.display = 'none';
                        }
                        debugVisible = false;
                    }, 10000);
                }
            }

            // 清空序列
            setTimeout(() => { clickSequence = []; }, 3000);
        });
    }

    // ========== 移动端页面切换 ==========

    /**
     * 显示移动端聊天页面
     */
    function showMobileChatPage() {
        const doctorPage = document.querySelector('.mobile-doctor-page');
        const chatPage = document.querySelector('.mobile-chat-page');

        if (doctorPage) doctorPage.style.display = 'none';
        if (chatPage) chatPage.style.display = 'flex';

        console.log('📱 切换到移动端聊天页面');

        // 确保输入框可见
        setTimeout(() => ensureMobileInputVisible(), 300);
    }

    /**
     * 显示移动端医生选择页面
     */
    function showMobileDoctorPage() {
        const doctorPage = document.querySelector('.mobile-doctor-page');
        const chatPage = document.querySelector('.mobile-chat-page');

        if (chatPage) chatPage.style.display = 'none';
        if (doctorPage) doctorPage.style.display = 'block';

        console.log('📱 切换到移动端医生选择页面');
    }

    /**
     * 移动端医生选择
     * @param {string} doctorKey - 医生标识符
     * @param {Object} doctor - 医生信息对象（可选）
     */
    function selectMobileDoctor(doctorKey, doctor) {
        console.log('📱 移动端选择医生:', doctorKey);

        // 获取医生信息
        const doctors = window.doctors || {};
        const doctorInfo = doctor || doctors[doctorKey];

        if (!doctorInfo) {
            console.error('❌ 未找到医生信息:', doctorKey);
            return;
        }

        // 保存当前医生的对话历史（如果有）
        if (window.selectedDoctor && window.selectedDoctor !== doctorKey) {
            if (typeof window.saveCurrentDoctorHistory === 'function') {
                window.saveCurrentDoctorHistory();
            }
        }

        // 设置当前医生
        window.selectedDoctor = doctorKey;

        // 更新移动端医生信息显示
        const avatarEl = document.getElementById('mobileDoctorAvatar');
        const nameEl = document.getElementById('mobileDoctorName');
        const descEl = document.getElementById('mobileDoctorDesc');

        if (avatarEl) avatarEl.textContent = doctorInfo.avatar || '👨‍⚕️';
        if (nameEl) nameEl.textContent = doctorInfo.name || '医师';
        if (descEl) descEl.textContent = doctorInfo.school || doctorInfo.specialty || '';

        // 生成新的对话ID
        if (typeof window.generateConversationId === 'function') {
            window.generateConversationId();
        } else {
            window.currentConversationId = `mobile_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }

        const forceFreshConversation = window.refreshConversationStrategy === 'new_conversation';
        if (forceFreshConversation) {
            const container = document.getElementById('mobileMessagesContainer');
            if (container) {
                container.innerHTML = '';
            }
            window.messages = [];
            addMobileMessage('ai', `您好！我是${doctorInfo.name}，${doctorInfo.school || ''}传人。请详细描述您的症状，我将为您进行专业的中医分析。`);
        } else if (typeof window.loadDoctorHistory === 'function') {
            // 加载该医生的历史对话
            window.loadDoctorHistory(doctorKey);
        } else {
            // 清空消息容器并添加欢迎消息
            const container = document.getElementById('mobileMessagesContainer');
            if (container) {
                container.innerHTML = '';
            }
            addMobileMessage('ai', `您好！我是${doctorInfo.name}，${doctorInfo.school || ''}传人。请详细描述您的症状，我将为您进行专业的中医分析。`);
        }

        // 切换到聊天页面
        showMobileChatPage();

        // 确保输入框可见
        setTimeout(() => ensureMobileInputVisible(), 500);
    }

    // ========== 问诊指导功能 ==========

    /**
     * 显示问诊指导
     */
    function showGuidance() {
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'guidance-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:999;';
        overlay.onclick = hideGuidance;
        document.body.appendChild(overlay);

        // 检查是否有现有的指导面板，没有则创建
        let guidancePanel = document.getElementById('guidanceTips');
        if (!guidancePanel) {
            guidancePanel = createGuidancePanel();
            document.body.appendChild(guidancePanel);
        }

        guidancePanel.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }

    /**
     * 隐藏问诊指导
     */
    function hideGuidance() {
        const guidancePanel = document.getElementById('guidanceTips');
        if (guidancePanel) {
            guidancePanel.style.display = 'none';
        }
        const overlay = document.querySelector('.guidance-overlay');
        if (overlay) {
            overlay.remove();
        }
        document.body.style.overflow = 'auto';
    }

    /**
     * 创建问诊指导面板
     */
    function createGuidancePanel() {
        const panel = document.createElement('div');
        panel.id = 'guidanceTips';
        panel.className = 'guidance-tips';
        panel.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border-radius: 16px;
            padding: 20px;
            max-width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        `;

        panel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                <h4 style="margin:0;color:#1e40af;">💡 问诊指导</h4>
                <button onclick="hideGuidance()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#666;">×</button>
            </div>
            <div style="font-size:14px;line-height:1.8;">
                <div style="margin-bottom:15px;">
                    <h5 style="color:#059669;margin-bottom:8px;">🔍 主要症状描述</h5>
                    <ul style="margin:0;padding-left:20px;color:#374151;">
                        <li>主要不适感觉（疼痛、发热、咳嗽等）</li>
                        <li>症状持续时间（几天、几周、几个月）</li>
                        <li>症状程度（轻微、中等、严重）</li>
                        <li>发作规律（持续性、间歇性、特定时间）</li>
                    </ul>
                </div>
                <div style="margin-bottom:15px;">
                    <h5 style="color:#059669;margin-bottom:8px;">🩺 伴随症状</h5>
                    <ul style="margin:0;padding-left:20px;color:#374151;">
                        <li>睡眠情况（入睡困难、易醒、多梦）</li>
                        <li>食欲状况（食欲不振、消化不良）</li>
                        <li>大小便情况（便秘、腹泻、尿频等）</li>
                        <li>情绪状态（焦虑、抑郁、易怒）</li>
                    </ul>
                </div>
                <div style="margin-bottom:15px;">
                    <h5 style="color:#059669;margin-bottom:8px;">📋 既往病史</h5>
                    <ul style="margin:0;padding-left:20px;color:#374151;">
                        <li>是否有慢性病（高血压、糖尿病等）</li>
                        <li>过敏史（药物、食物过敏）</li>
                        <li>手术史</li>
                        <li>家族病史</li>
                    </ul>
                </div>
                <div style="background:#f0fdf4;padding:12px;border-radius:8px;margin-top:10px;">
                    <p style="margin:0;color:#166534;font-size:13px;">
                        💡 <strong>提示：</strong>描述越详细，AI分析越准确。可以上传舌苔和面部照片辅助诊断。
                    </p>
                </div>
            </div>
        `;

        return panel;
    }

    // ========== 图片上传功能 ==========

    /**
     * 显示移动端图片选择弹窗
     */
    function showMobileImageOptions() {
        console.log('📷 显示移动端图片选择弹窗');

        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'mobile-image-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:999;';
        overlay.onclick = () => overlay.remove();

        // 创建选择面板
        const panel = document.createElement('div');
        panel.style.cssText = `
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            border-radius: 16px 16px 0 0;
            padding: 20px;
            z-index: 1000;
            animation: slideUp 0.3s ease;
        `;

        panel.innerHTML = `
            <style>
                @keyframes slideUp {
                    from { transform: translateY(100%); }
                    to { transform: translateY(0); }
                }
            </style>
            <div style="text-align:center;margin-bottom:20px;">
                <h3 style="margin:0 0 8px 0;color:#1e40af;">📷 选择图片类型</h3>
                <p style="margin:0;color:#6b7280;font-size:14px;">上传舌象或面象照片辅助诊断</p>
            </div>
            <div style="display:flex;gap:15px;margin-bottom:15px;">
                <button onclick="selectMobileImage('tongue')" style="
                    flex:1;
                    padding:20px;
                    background:linear-gradient(135deg,#ec4899,#db2777);
                    color:white;
                    border:none;
                    border-radius:12px;
                    font-size:16px;
                    cursor:pointer;
                ">
                    👅<br><span style="font-size:14px;margin-top:8px;display:block;">舌诊照片</span>
                </button>
                <button onclick="selectMobileImage('face')" style="
                    flex:1;
                    padding:20px;
                    background:linear-gradient(135deg,#3b82f6,#2563eb);
                    color:white;
                    border:none;
                    border-radius:12px;
                    font-size:16px;
                    cursor:pointer;
                ">
                    😊<br><span style="font-size:14px;margin-top:8px;display:block;">面诊照片</span>
                </button>
            </div>
            <button onclick="this.parentElement.previousElementSibling.remove();this.parentElement.remove();" style="
                width:100%;
                padding:15px;
                background:#f3f4f6;
                color:#374151;
                border:none;
                border-radius:12px;
                font-size:16px;
                cursor:pointer;
            ">取消</button>
        `;

        overlay.appendChild(panel);
        document.body.appendChild(overlay);
    }

    /**
     * 选择移动端图片类型
     */
    function selectMobileImage(type) {
        console.log('📷 选择图片类型:', type);

        // 移除弹窗
        const overlay = document.querySelector('.mobile-image-overlay');
        if (overlay) overlay.remove();

        // 触发对应的文件选择
        if (type === 'tongue') {
            const input = document.getElementById('mobileTongueUpload');
            if (input) input.click();
        } else if (type === 'face') {
            const input = document.getElementById('mobileFaceUpload');
            if (input) input.click();
        }
    }

    // ========== 模块初始化 ==========

    /**
     * 初始化所有移动端功能
     */
    function initMobileModule() {
        // 初始化微信环境
        handleWechatPublicAccount();
        initWechatProtection();

        // 初始化网络监控
        initNetworkMonitor();

        // 初始化Chrome调试工具
        initChromeDebugTool();

        // 初始化调试手势
        initDebugGesture();

        console.log('移动端模块初始化完成');
    }

    // DOMContentLoaded时初始化
    document.addEventListener('DOMContentLoaded', initMobileModule);

    // ========== 暴露到window对象 ==========

    // 移动端检测
    window.isMobileDevice = isMobileDevice;
    window.getDeviceInfo = getDeviceInfo;

    // 导航与对话管理
    window.showMobileNavigation = showMobileNavigation;
    window.startNewChat = startNewChat;
    window.exportConversation = exportConversation;

    // 移动端页面切换与医生选择
    window.showMobileChatPage = showMobileChatPage;
    window.showMobileDoctorPage = showMobileDoctorPage;
    window.selectMobileDoctor = selectMobileDoctor;

    // 问诊指导与图片上传
    window.showGuidance = showGuidance;
    window.hideGuidance = hideGuidance;
    window.showMobileImageOptions = showMobileImageOptions;
    window.selectMobileImage = selectMobileImage;

    // 移动端消息系统
    window.addMobileMessage = addMobileMessage;
    window.sendMobileMessage = sendMobileMessage;
    window.adjustMobileTextareaHeight = adjustMobileTextareaHeight;
    window.handleMobileKeyPress = handleMobileKeyPress;
    window.ensureMobileInputVisible = ensureMobileInputVisible;
    window.handleMobileInputBlur = handleMobileInputBlur;
    window.renderMobileDoctorCards = renderMobileDoctorCards;
    window.setMobileDefaultDoctor = setMobileDefaultDoctor;

    // 微信环境
    window.isWechat = isWechat;
    window.detectWechatSource = detectWechatSource;
    window.handleWechatPublicAccount = handleWechatPublicAccount;
    window.showWechatWelcome = showWechatWelcome;
    window.initWechatProtection = initWechatProtection;

    // localStorage管理
    window.checkLocalStorageUsage = checkLocalStorageUsage;
    window.cleanOldHistoryRecords = cleanOldHistoryRecords;
    window.diagnoseHistoryIssues = diagnoseHistoryIssues;

    // 网络监控
    window.checkNetworkStatus = checkNetworkStatus;

    // 调试工具
    window.debugLog = debugLog;
    window.isDebugMode = isDebugMode;

    // 模块初始化
    window.initMobileModule = initMobileModule;

})();
