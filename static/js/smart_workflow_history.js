/**
 * 智能问诊工作流 - 对话历史和会话管理模块
 *
 * 本模块负责管理用户的对话历史记录和会话，包括：
 * - 会话的创建、加载、删除
 * - 本地存储和服务器同步
 * - 医生历史记录管理
 * - 对话索引维护
 *
 * @module smart_workflow_history
 * @version 2.1
 */

(function() {
    'use strict';

    // ==================== 会话管理核心函数 ====================

    /**
     * 初始化会话管理器
     * 加载对话索引并渲染会话列表
     */
    function initConversationManager() {
        loadConversationIndex();
        if (typeof renderConversationList === 'function') {
            renderConversationList();
        }
    }

    /**
     * 创建新对话（ChatGPT风格）- v3.0 使用ConversationManager
     * 保存当前对话到历史记录，清空显示，创建新的对话ID
     */
    async function createNewConversation() {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;
            const currentDoctor = window.selectedDoctor;

            if (!userId || !currentDoctor) {
                console.error('❌ 无法创建新对话：缺少用户ID或医生ID');
                if (typeof showMessage === 'function') {
                    showMessage('创建新对话失败：缺少必要信息', 'error');
                }
                return;
            }

            // 🔑 如果当前有对话内容，先保存
            if (window.messages && window.messages.length > 0 && window.currentConversationId) {
                if (window.conversationManager) {
                    window.conversationManager.saveConversationMessages(
                        window.currentConversationId,
                        window.messages
                    );
                    console.log(`💾 已保存当前对话: ${window.messages.length}条消息`);
                }
            }

            // 🔑 使用ConversationManager创建新对话
            if (window.conversationManager) {
                const newConversationId = window.conversationManager.startNewConversation(
                    userId,
                    currentDoctor
                );

                // 更新全局变量
                window.currentConversationId = newConversationId;
                window.messages = [];

                console.log(`✨ 创建新对话: ${newConversationId}`);
            } else {
                // 降级方案：使用旧方法
                if (typeof generateConversationId === 'function') {
                    generateConversationId();
                }
                window.messages = [];
                console.log('⚠️ ConversationManager不可用，使用旧方法生成对话ID');
            }

            // 清空当前对话显示
            if (typeof clearAllMessages === 'function') {
                clearAllMessages();
            }

            // 显示欢迎消息
            if (typeof window.addWelcomeMessage === 'function') {
                window.addWelcomeMessage(currentDoctor);
            }

            // 重置对话状态
            if (typeof resetConversationState === 'function') {
                resetConversationState();
            }

            console.log('✅ 新对话创建成功');
            if (typeof showMessage === 'function') {
                showMessage('新对话已开始', 'success');
            }

        } catch (error) {
            console.error('❌ 创建新对话失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('创建新对话失败', 'error');
            }
        }
    }

    /**
     * 加载指定对话
     * @param {string} conversationId - 对话ID
     */
    async function loadConversation(conversation_id) {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;
            if (!userId) return;

            // 保存当前对话（如果有内容）
            const isMobile = window.innerWidth <= 768;
            const containerSelector = isMobile ? 'mobileMessagesContainer' : 'messagesContainer';
            const messagesContainer = document.getElementById(containerSelector);
            if (messagesContainer && messagesContainer.children.length > 0 && window.currentConversationId !== conversation_id) {
                await saveCurrentConversationToHistory();
            }

            // 从localStorage加载对话数据
            const storageKey = `conversation_${userId}_${conversation_id}`;
            const conversationData = localStorage.getItem(storageKey);

            if (!conversationData) {
                if (typeof showMessage === 'function') {
                    showMessage('对话记录不存在', 'error');
                }
                return;
            }

            const conversation = JSON.parse(conversationData);

            // 清空当前显示
            if (typeof clearAllMessages === 'function') {
                clearAllMessages();
            }

            // 设置对话状态
            window.currentConversationId = conversation_id;
            window.selectedDoctor = conversation.doctor;

            // 更新UI
            if (typeof updateDoctorSelection === 'function') {
                updateDoctorSelection(conversation.doctor);
            }

            // 重新渲染消息
            conversation.messages.forEach(message => {
                const sender = message.sender || message.type;
                if (sender === 'user') {
                    if (typeof addMessage === 'function') {
                        addMessage('user', message.content);
                    }
                } else if (sender === 'ai') {
                    if (typeof addMessage === 'function') {
                        addMessage('ai', message.content, false, false, message.prescriptionData);
                    }
                }
            });

            // 更新对话列表显示
            if (typeof renderConversationList === 'function') {
                renderConversationList();
            }

            // 保存当前对话ID
            const storageKeyConv = `conversationId_${userId}`;
            localStorage.setItem(storageKeyConv, conversation_id);

            console.log('✅ 对话加载成功:', conversation.title);
            if (typeof showMessage === 'function') {
                showMessage('对话已切换', 'success');
            }

        } catch (error) {
            console.error('❌ 加载对话失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('加载对话失败', 'error');
            }
        }
    }

    /**
     * 删除对话
     * @param {string} conversationId - 对话ID
     */
    async function deleteConversation(conversation_id) {
        if (!confirm('确定要删除这个对话吗？此操作不可恢复。')) {
            return;
        }

        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;
            if (!userId) return;

            // 从localStorage删除对话数据
            const storageKey = `conversation_${userId}_${conversation_id}`;
            localStorage.removeItem(storageKey);

            // 从索引中移除
            const indexKey = `conversation_index_${userId}`;
            let index = JSON.parse(localStorage.getItem(indexKey) || '[]');
            index = index.filter(item => item.id !== conversation_id);
            localStorage.setItem(indexKey, JSON.stringify(index));

            // 更新内存中的历史记录
            if (window.conversationHistory) {
                window.conversationHistory = index;
            }

            // 如果删除的是当前对话，创建新对话
            if (window.currentConversationId === conversation_id) {
                if (typeof clearAllMessages === 'function') {
                    clearAllMessages();
                }
                if (typeof generateConversationId === 'function') {
                    generateConversationId();
                }
                if (typeof resetConversationState === 'function') {
                    resetConversationState();
                }
            }

            // 重新渲染列表
            if (typeof renderConversationList === 'function') {
                renderConversationList();
            }

            console.log('🗑️ 对话已删除:', conversation_id);
            if (typeof showMessage === 'function') {
                showMessage('对话已删除', 'success');
            }

        } catch (error) {
            console.error('❌ 删除对话失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('删除对话失败', 'error');
            }
        }
    }

    /**
     * 保存当前对话到历史记录
     */
    async function saveCurrentConversationToHistory() {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;
            const selectedDoctor = window.selectedDoctor;
            if (!userId || !selectedDoctor) {
                return;
            }

            // 从DOM中提取当前消息
            const isMobile = window.innerWidth <= 768;
            const containerSelector = isMobile ? 'mobileMessagesContainer' : 'messagesContainer';
            const messagesContainer = document.getElementById(containerSelector);

            if (!messagesContainer || messagesContainer.children.length === 0) {
                return;
            }

            // 提取消息内容
            const extractedMessages = [];
            const messageElements = messagesContainer.querySelectorAll('.message');

            messageElements.forEach((messageEl, index) => {
                const isUser = messageEl.classList.contains('user');
                const messageTextEl = messageEl.querySelector('.message-text');
                const content = messageTextEl ? messageTextEl.textContent.trim() : '';

                if (content) {
                    extractedMessages.push({
                        id: `msg_${Date.now()}_${index}`,
                        sender: isUser ? 'user' : 'ai',
                        content: content,
                        timestamp: new Date().toISOString(),
                        doctorKey: selectedDoctor
                    });
                }
            });

            if (extractedMessages.length === 0) {
                return;
            }

            const getDoctorDisplayName = window.getDoctorDisplayName || function(key) { return key; };

            const conversation = {
                id: window.currentConversationId || (typeof generateConversationId === 'function' ? generateConversationId() : Date.now().toString()),
                title: generateConversationTitle(extractedMessages),
                doctor: selectedDoctor,
                doctorName: getDoctorDisplayName(selectedDoctor),
                messages: extractedMessages,
                createdAt: extractedMessages[0]?.timestamp || new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                messageCount: extractedMessages.length
            };

            // 保存到localStorage
            const storageKey = `conversation_${userId}_${conversation.id}`;
            localStorage.setItem(storageKey, JSON.stringify(conversation));

            // 更新对话索引
            await updateConversationIndex(userId, conversation);

            console.log('💾 对话已保存到历史记录:', conversation.title);

        } catch (error) {
            console.error('❌ 保存对话历史失败:', error);
        }
    }

    /**
     * 保存对话到服务器
     * @param {Array} messages - 消息数组
     * @param {string} doctorId - 医生ID
     */
    async function saveConversationToServer(messages, doctorId) {
        // 只为已登录用户保存到服务器
        const currentUser = window.currentUser;
        const userToken = window.userToken;
        if (!currentUser || !userToken) {
            console.log('📝 访客用户，跳过服务器保存');
            return;
        }

        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;

            // 检查是否是临时用户ID
            if (userId && (userId.startsWith('temp_user_') || userId.startsWith('smart_user_') || userId.startsWith('guest_'))) {
                console.log('📝 临时用户，跳过服务器保存');
                return;
            }

            // 提取主要症状（从第一条用户消息）
            const firstUserMessage = messages.find(msg => msg.type === 'user');
            const chiefComplaint = firstUserMessage ? firstUserMessage.content.substring(0, 100) : '问诊咨询';

            // 构建服务器保存的数据
            const serverData = {
                consultation_id: window.currentConversationId,
                patient_id: userId,
                doctor_id: doctorId,
                conversation_log: JSON.stringify(messages),
                status: 'completed',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            };

            const response = await fetch('/api/consultation/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${userToken}`
                },
                body: JSON.stringify(serverData)
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    console.log('✅ 对话已保存到服务器数据库:', window.currentConversationId);
                } else {
                    console.warn('⚠️ 服务器保存响应异常:', result.message);
                }
            } else {
                const errorText = await response.text();
                console.warn('⚠️ 服务器保存失败，状态码:', response.status, '错误:', errorText);
            }

        } catch (error) {
            console.error('❌ 保存到服务器失败:', error);
        }
    }

    /**
     * 从数据库同步历史记录到本地
     */
    async function syncHistoryFromDatabase() {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;

            if (!userId) {
                console.warn('⚠️ 无法获取用户ID，跳过数据库同步');
                return;
            }

            console.log('🔄 开始从数据库同步历史记录...用户ID:', userId);

            const response = await fetch(`/api/consultation/patient/history?user_id=${userId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.warn('⚠️ 获取历史记录失败:', response.status);
                return;
            }

            const result = await response.json();

            if (result.success && result.data && result.data.consultation_history && result.data.consultation_history.length > 0) {
                const consultations = result.data.consultation_history;
                console.log(`✅ 从数据库获取到 ${consultations.length} 条历史记录`);

                // v3.0 修改：不再自动恢复UI，只保存数据到ConversationManager
                // UI恢复由用户主动切换医生时触发
                console.log('📋 数据库历史记录仅保存到ConversationManager，不自动恢复UI');

                // 🔑 v3.0 使用ConversationManager保存历史记录
                if (window.conversationManager) {
                    consultations.forEach(consultation => {
                        try {
                            if (consultation.conversation_history && consultation.conversation_history.length > 0) {
                                const doctorId = consultation.doctor_id;
                                const conversationId = consultation.consultation_id || consultation.uuid || window.conversationManager.generateConversationId();

                                // 转换conversation_history格式为messages格式
                                const messages = [];
                                consultation.conversation_history.forEach(turn => {
                                    if (turn.patient_query) {
                                        messages.push({
                                            type: 'user',
                                            content: turn.patient_query,
                                            time: new Date(turn.timestamp || Date.now()).toLocaleTimeString(),
                                            timestamp: turn.timestamp || Date.now()
                                        });
                                    }
                                    if (turn.ai_response) {
                                        messages.push({
                                            type: 'ai',
                                            content: turn.ai_response,
                                            time: new Date(turn.timestamp || Date.now()).toLocaleTimeString(),
                                            timestamp: turn.timestamp || Date.now()
                                        });
                                    }
                                });

                                if (messages.length > 0) {
                                    // 使用ConversationManager保存
                                    window.conversationManager.currentUserId = userId;
                                    window.conversationManager.currentDoctor = doctorId;
                                    window.conversationManager.saveConversationMessages(conversation_id, messages);

                                    // 更新索引
                                    const index = window.conversationManager.getConversationIndex(userId);
                                    if (!index[conversation_id]) {
                                        index[conversation_id] = {
                                            conversation_id: conversation_id,
                                            doctor_id: doctorId,
                                            user_id: userId,
                                            created_at: consultation.created_at || new Date().toISOString(),
                                            last_message_at: consultation.updated_at || consultation.created_at || new Date().toISOString(),
                                            is_active: true,
                                            message_count: messages.length,
                                            synced_from_db: true
                                        };
                                        window.conversationManager.saveConversationIndex(userId, index);
                                    }

                                    console.log(`💾 ConversationManager保存数据库同步的对话 ${conversation_id} (${doctorId}): ${messages.length}条消息`);
                                }
                            }
                        } catch (err) {
                            console.warn('⚠️ 处理历史记录失败:', err);
                        }
                    });

                    console.log('✅ 历史记录已同步到ConversationManager');
                } else {
                    // 降级方案：使用旧格式保存
                    console.warn('⚠️ ConversationManager不可用，使用旧格式保存');
                    const historyByDoctor = {};

                    consultations.forEach(consultation => {
                        try {
                            if (consultation.conversation_history && consultation.conversation_history.length > 0) {
                                const doctorId = consultation.doctor_id;

                                if (!historyByDoctor[doctorId]) {
                                    historyByDoctor[doctorId] = [];
                                }

                                historyByDoctor[doctorId].push({
                                    consultation_id: consultation.consultation_id,
                                    messages: consultation.conversation_history,
                                    created_at: consultation.created_at,
                                    updated_at: consultation.updated_at || consultation.created_at,
                                    symptoms_analysis: consultation.symptoms_analysis,
                                    tcm_syndrome: consultation.tcm_syndrome
                                });
                            }
                        } catch (err) {
                            console.warn('⚠️ 处理历史记录失败:', err);
                        }
                    });

                    // 保存每个医生的完整历史记录列表（旧格式）
                    Object.keys(historyByDoctor).forEach(doctorId => {
                        try {
                            const historyKey = `tcm_doctor_history_${userId}_${doctorId}`;
                            const dataToSave = {
                                doctor: doctorId,
                                consultations: historyByDoctor[doctorId],
                                lastUpdated: new Date().toISOString(),
                                version: '2.3',
                            syncedFromDB: true
                        };
                        localStorage.setItem(historyKey, JSON.stringify(dataToSave));
                        console.log(`💾 已备份医生 ${doctorId} 的 ${historyByDoctor[doctorId].length} 条历史记录到localStorage`);
                    } catch (err) {
                        console.warn(`⚠️ 备份医生 ${doctorId} 的历史记录失败:`, err);
                    }
                });

                console.log('✅ 历史记录同步完成');
            }
        } else {
            console.log('📝 数据库中暂无历史记录');
        }

        } catch (error) {
            console.error('❌ 从数据库同步历史记录失败:', error);
        }
    }

    /**
     * 加载对话历史索引
     */
    function loadConversationIndex() {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;
            if (!userId) return;

            const indexKey = `conversation_index_${userId}`;
            window.conversationHistory = JSON.parse(localStorage.getItem(indexKey) || '[]');

            console.log(`📋 加载了${window.conversationHistory.length}个历史对话`);

        } catch (error) {
            console.error('❌ 加载对话历史失败:', error);
            window.conversationHistory = [];
        }
    }

    /**
     * 更新对话索引
     * @param {string} userId - 用户ID
     * @param {Object} conversation - 对话对象
     */
    async function updateConversationIndex(userId, conversation) {
        try {
            const indexKey = `conversation_index_${userId}`;
            let index = JSON.parse(localStorage.getItem(indexKey) || '[]');

            // 检查是否已存在
            const existingIndex = index.findIndex(item => item.id === conversation.id);

            const indexItem = {
                id: conversation.id,
                title: conversation.title,
                doctor: conversation.doctor,
                doctorName: conversation.doctorName,
                createdAt: conversation.createdAt,
                updatedAt: conversation.updatedAt,
                messageCount: conversation.messageCount
            };

            if (existingIndex >= 0) {
                index[existingIndex] = indexItem;
            } else {
                index.unshift(indexItem);
            }

            // 保持最多50个对话记录
            if (index.length > 50) {
                const removedItems = index.slice(50);
                index = index.slice(0, 50);

                // 清理被移除的对话数据
                removedItems.forEach(item => {
                    const storageKey = `conversation_${userId}_${item.id}`;
                    localStorage.removeItem(storageKey);
                });
            }

            localStorage.setItem(indexKey, JSON.stringify(index));
            window.conversationHistory = index;

        } catch (error) {
            console.error('❌ 更新对话索引失败:', error);
        }
    }

    /**
     * 生成对话标题
     * @param {Array} messages - 消息数组
     * @returns {string} 生成的标题
     */
    function generateConversationTitle(messages) {
        if (!messages || messages.length === 0) {
            return '新对话';
        }

        // 从第一条用户消息中提取关键词作为标题
        const firstUserMessage = messages.find(msg => msg.sender === 'user' || msg.type === 'user');
        if (firstUserMessage && firstUserMessage.content) {
            let title = firstUserMessage.content.slice(0, 20);
            if (firstUserMessage.content.length > 20) {
                title += '...';
            }
            return title;
        }

        return `对话 ${new Date().toLocaleDateString()}`;
    }

    /**
     * 完整清理所有对话数据
     * @param {string} userId - 用户ID
     */
    async function clearAllConversationData(userId) {
        try {
            const selectedDoctor = window.selectedDoctor;
            if (!selectedDoctor) {
                console.log('⚠️ 没有选择医生，跳过数据清理');
                return;
            }

            console.log(`🧹 开始清理用户 ${userId} 与医生 ${selectedDoctor} 的所有对话数据`);

            // 1. 清理localStorage中的医生历史记录
            const historyKey = `tcm_doctor_history_${userId}_${selectedDoctor}`;
            localStorage.removeItem(historyKey);
            console.log(`🗑️ 清理localStorage医生历史记录: ${historyKey}`);

            // 2. 清理ChatGPT风格对话记录（当前对话）
            if (window.currentConversationId) {
                const conversationKey = `conversation_${userId}_${window.currentConversationId}`;
                localStorage.removeItem(conversationKey);
                console.log(`🗑️ 清理ChatGPT对话记录: ${conversationKey}`);
            }

            // 3. 清理对话索引中的相关记录
            const indexKey = `conversation_index_${userId}`;
            let index = JSON.parse(localStorage.getItem(indexKey) || '[]');
            const originalLength = index.length;
            index = index.filter(item => item.doctor !== selectedDoctor);
            if (index.length !== originalLength) {
                localStorage.setItem(indexKey, JSON.stringify(index));
                console.log(`🗑️ 清理对话索引，删除了 ${originalLength - index.length} 条记录`);
            }

            // 4. 清理消息容器的医生标记
            const containers = ['messagesContainer', 'mobileMessagesContainer'];
            containers.forEach(containerId => {
                const container = document.getElementById(containerId);
                if (container) {
                    container.removeAttribute('data-current-doctor');
                    console.log(`🗑️ 清理容器标记: ${containerId}`);
                }
            });

            // 5. 清理服务端数据
            try {
                const response = await fetch('/api/conversation/clear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        user_id: userId,
                        doctor_id: selectedDoctor,
                        clear_type: 'all'
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    console.log(`✅ 服务端数据清理成功: ${result.message}`);
                } else {
                    console.warn('⚠️ 服务端数据清理失败，但继续执行');
                }
            } catch (error) {
                console.warn('⚠️ 服务端数据清理出错，但继续执行:', error);
            }

            console.log('✅ 所有对话数据清理完成');

        } catch (error) {
            console.error('❌ 清理对话数据失败:', error);
            throw error;
        }
    }

    /**
     * 消息发送后更新对话列表
     */
    async function updateConversationListAfterMessage() {
        try {
            // 重建messages数组（从DOM获取当前所有消息）
            const messageElements = document.querySelectorAll('.message');
            const currentMessages = [];

            messageElements.forEach(messageEl => {
                const isUser = messageEl.classList.contains('user');
                const textEl = messageEl.querySelector('.message-text');
                const timeEl = messageEl.querySelector('.message-time');
                const prescriptionData = messageEl.getAttribute('data-prescription-id');

                if (textEl) {
                    const messageData = {
                        type: isUser ? 'user' : 'ai',
                        content: textEl.textContent.trim(),
                        time: timeEl ? timeEl.textContent : new Date().toLocaleTimeString(),
                        timestamp: new Date().toISOString()
                    };

                    if (prescriptionData) {
                        messageData.prescriptionData = { prescription_id: prescriptionData };
                    }

                    currentMessages.push(messageData);
                }
            });

            // 更新全局messages数组
            window.messages = currentMessages;

            // 如果有消息，自动保存当前对话
            if (currentMessages.length > 0) {
                await saveCurrentConversationToHistory();
                if (typeof renderConversationList === 'function') {
                    renderConversationList();
                }
            }

        } catch (error) {
            console.error('❌ 更新对话列表失败:', error);
        }
    }

    // ==================== 医生历史记录管理 ====================

    /**
     * 保存当前医生的对话历史 - v3.0 使用ConversationManager
     */
    function saveCurrentDoctorHistory() {
        const selectedDoctor = window.selectedDoctor;
        const conversationId = window.currentConversationId;

        if (!selectedDoctor || !conversation_id) {
            console.warn('⚠️ 缺少selectedDoctor或conversationId，跳过保存');
            return;
        }

        try {
            const messages = [];

            // 检测当前是移动端还是PC端
            const isMobile = window.innerWidth <= 768;
            const containerSelector = isMobile ? 'mobileMessagesContainer' : 'messagesContainer';
            const messagesContainer = document.getElementById(containerSelector);

            if (!messagesContainer) {
                console.warn('未找到消息容器，跳过保存');
                return;
            }

            // 提取所有消息
            messagesContainer.querySelectorAll('.message').forEach(messageEl => {
                const isUser = messageEl.classList.contains('user');
                const textEl = messageEl.querySelector('.message-text');
                const timeEl = messageEl.querySelector('.message-time');

                if (textEl && textEl.innerHTML.trim()) {
                    const messageData = {
                        type: isUser ? 'user' : 'ai',
                        content: textEl.innerHTML,
                        time: timeEl ? timeEl.textContent : new Date().toLocaleTimeString(),
                        timestamp: Date.now()
                    };

                    // 如果是AI消息且包含处方，保存处方状态
                    if (!isUser) {
                        const prescriptionId = messageEl.getAttribute('data-prescription-id');
                        const isPaid = messageEl.querySelector('.prescription-paid') !== null;
                        const hasActions = messageEl.querySelector('.prescription-actions') !== null;

                        if (prescriptionId || isPaid || hasActions) {
                            messageData.prescriptionData = {
                                prescription_id: prescription_id,
                                isPaid: isPaid,
                                hasActions: hasActions
                            };

                            // 如果处方已支付，尝试获取并保存原始完整内容
                            if (isPaid) {
                                const originalContent = messageEl.getAttribute('data-original-content');
                                if (originalContent) {
                                    messageData.originalContent = originalContent;
                                    console.log('💾 保存了已支付处方的原始内容');
                                }
                            }
                        }
                    }

                    messages.push(messageData);
                }
            });

            // 如果没有消息则不保存
            if (messages.length === 0) {
                console.log('没有消息需要保存');
                return;
            }

            // 限制历史记录数量
            const maxMessages = 50;
            const trimmedMessages = messages.slice(-maxMessages);

            // 🔑 使用ConversationManager保存
            if (window.conversationManager) {
                window.conversationManager.saveConversationMessages(conversation_id, trimmedMessages);
                // 同步到window.messages用于其他函数访问
                window.messages = trimmedMessages;
                console.log(`💾 ConversationManager保存对话 ${conversation_id}: ${trimmedMessages.length}条消息`);
            } else {
                // 降级方案：使用旧方法保存
                const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : 'default';
                const historyKey = `tcm_doctor_history_${userId}_${selectedDoctor}`;
                const dataToSave = JSON.stringify({
                    messages: trimmedMessages,
                    lastUpdated: new Date().toISOString(),
                    doctor: selectedDoctor,
                    version: '2.1',
                    saveCount: (JSON.parse(localStorage.getItem(historyKey) || '{}').saveCount || 0) + 1
            });

            // 验证localStorage可用性
            if (typeof(Storage) === "undefined") {
                console.error('浏览器不支持localStorage');
                return;
            }

            localStorage.setItem(historyKey, dataToSave);
            console.log(`✅ 已保存${selectedDoctor}医生的${trimmedMessages.length}条对话记录`);

            // 自动保存到服务器数据库
            saveConversationToServer(trimmedMessages, selectedDoctor);
            }

        } catch (error) {
            console.error('❌ 保存历史记录失败:', error);
        }
    }

    /**
     * 加载医生历史记录
     * @param {string} doctorKey - 医生标识
     */
    async function loadDoctorHistory(doctorKey) {
        const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : 'default';

        // 对于临时用户或设备用户，直接使用本地模式
        if (userId.startsWith('temp_user_') || userId.startsWith('device_')) {
            console.log(`📱 临时用户(${userId})，直接使用本地模式加载${doctorKey}医生历史`);
        } else {
            // 优先从服务器加载特定医生的历史
            const serverLoaded = await loadDoctorHistoryFromServer(doctorKey, userId);

            if (serverLoaded) {
                console.log(`✅ 从服务器成功加载${doctorKey}医生的历史记录`);
                return;
            }

            console.log(`⚠️ 服务器加载失败，降级到本地模式加载${doctorKey}医生历史`);
        }

        // 检测当前是移动端还是PC端
        const isMobile = window.innerWidth <= 768;
        const containerSelector = isMobile ? 'mobileMessagesContainer' : 'messagesContainer';
        const messagesContainer = document.getElementById(containerSelector);

        if (!messagesContainer) return;

        // 检查是否需要清空消息容器
        const currentMessages = messagesContainer.querySelectorAll('.message');
        const currentDoctorAttr = messagesContainer.getAttribute('data-current-doctor');
        const isNewConversation = !window.currentConversationId || window.currentConversationId.length === 0;

        const shouldClearMessages = currentMessages.length === 0 ||
                                   !currentDoctorAttr ||
                                   currentDoctorAttr !== doctorKey ||
                                   isNewConversation;

        if (shouldClearMessages) {
            messagesContainer.innerHTML = '';
            console.log(`🧹 清空消息容器，准备加载${doctorKey}医生的历史记录`);
        } else {
            console.log(`⚡ 保持当前${doctorKey}医生的消息，跳过重新加载`);
            messagesContainer.setAttribute('data-current-doctor', doctorKey);
            return;
        }

        // 标记当前医生
        messagesContainer.setAttribute('data-current-doctor', doctorKey);

        // 移动端需要重置样式
        if (isMobile) {
            messagesContainer.style.display = 'block';
            messagesContainer.style.alignItems = 'flex-start';
            messagesContainer.style.justifyContent = 'flex-start';
        }

        // 智能加载策略 - 优先使用本地数据
        let messages = [];
        let loadedFromServer = false;
        let loadedFromLocal = false;

        // 首先检查localStorage是否有数据
        const historyKey = `tcm_doctor_history_${userId}_${doctorKey}`;
        const storedHistory = localStorage.getItem(historyKey);

        if (storedHistory) {
            try {
                const historyData = JSON.parse(storedHistory);
                if (historyData.messages && historyData.messages.length > 0) {
                    messages = historyData.messages;
                    loadedFromLocal = true;
                    console.log(`📱 从localStorage加载${doctorKey}医生的${messages.length}条对话历史`);
                }
            } catch (error) {
                console.warn('解析本地历史记录失败:', error);
            }
        }

        // 如果本地没有数据，再尝试从服务器加载
        if (!loadedFromLocal && !userId.startsWith('temp_user_') && !userId.startsWith('device_')) {
            try {
                console.log(`🌐 本地无数据，从服务器加载${doctorKey}医生的对话历史...`);
                const apiUrl = `/api/conversation/history/${userId}?doctor_id=${doctorKey}`;

                const response = await fetch(apiUrl);

                if (response.ok) {
                    const result = await response.json();

                    if (result.success && result.data && result.data.messages && result.data.messages.length > 0) {
                        messages = result.data.messages;
                        loadedFromServer = true;
                        console.log(`✅ 从服务器加载${doctorKey}医生的${messages.length}条对话历史`);
                    }
                }
            } catch (error) {
                console.warn('服务器加载对话历史失败:', error);
            }
        }

        // 渲染加载的对话历史
        if (messages.length > 0) {
            for (const msg of messages) {
                const shouldShowFeedback = msg.type === 'ai' && (typeof containsPrescription === 'function' ? containsPrescription(msg.content) : false);
                const prescriptionData = msg.prescriptionData;
                const isPaid = prescriptionData ? prescriptionData.isPaid : false;
                const prescriptionId = prescriptionData ? prescriptionData.prescription_id : null;

                let displayContent = msg.content;
                if (isPaid && prescriptionData && msg.type === 'ai') {
                    displayContent = msg.content
                        .replace(/\*\*\*/g, '15')
                        .replace(/解锁查看/g, '')
                        .replace(/\+ \d+ 味药材/g, '')
                        .replace(/方剂组成预览/g, '完整方剂组成')
                        .replace(/预览/g, '完整');
                }

                if (isMobile) {
                    if (typeof addMobileMessage === 'function') {
                        await addMobileMessage(msg.type, displayContent, shouldShowFeedback, isPaid, prescription_id);
                    }
                } else {
                    if (typeof addMessageWithTime === 'function') {
                        addMessageWithTime(msg.type, displayContent, msg.time, shouldShowFeedback, isPaid, prescription_id);
                    }
                }
            }

            console.log(`历史记录详情: 共${messages.length}条消息`);
        } else {
            // 没有历史记录，显示欢迎消息
            console.log(`${doctorKey}医生没有历史记录，显示欢迎消息`);
            if (typeof addWelcomeMessage === 'function') {
                addWelcomeMessage(doctorKey);
            }
        }
    }

    /**
     * 从服务器加载特定医生的历史记录
     * @param {string} doctorKey - 医生标识
     * @param {string} userId - 用户ID
     * @returns {boolean} 是否成功加载
     */
    async function loadDoctorHistoryFromServer(doctorKey, userId) {
        try {
            console.log(`🌐 从服务器加载${doctorKey}医生的历史记录...`);

            // 添加超时控制
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const getAuthHeaders = window.getAuthHeaders || function() { return { 'Content-Type': 'application/json' }; };

            const response = await fetch(`/api/conversation/history/${userId}?doctor_id=${doctorKey}`, {
                headers: getAuthHeaders(),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                console.warn(`❌ 服务器请求失败: ${response.status}`);
                return false;
            }

            const result = await response.json();
            console.log('📋 医生历史记录响应:', result);

            if (result.success && result.data && result.data.messages) {
                const messages = result.data.messages;

                if (messages.length > 0) {
                    console.log(`📥 恢复${doctorKey}医生的 ${messages.length} 条消息`);

                    // 清空当前消息
                    if (typeof clearAllMessages === 'function') {
                        clearAllMessages();
                    }

                    // 逐条恢复消息
                    if (typeof processServerMessages === 'function') {
                        await processServerMessages(messages);
                    }

                    return true;
                } else {
                    console.log(`📭 ${doctorKey}医生暂无历史对话记录`);
                    return true;
                }
            }

            return false;

        } catch (error) {
            if (error.name === 'AbortError') {
                console.warn(`⏰ 加载${doctorKey}医生历史超时，切换到本地模式`);
            } else {
                console.error(`❌ 从服务器加载${doctorKey}医生历史失败:`, error);
            }
            return false;
        }
    }

    // ==================== 暴露到全局 ====================

    // 会话管理核心函数
    window.initConversationManager = initConversationManager;
    window.createNewConversation = createNewConversation;
    window.loadConversation = loadConversation;
    window.deleteConversation = deleteConversation;
    window.saveCurrentConversationToHistory = saveCurrentConversationToHistory;
    window.saveConversationToServer = saveConversationToServer;
    window.syncHistoryFromDatabase = syncHistoryFromDatabase;
    window.loadConversationIndex = loadConversationIndex;
    window.updateConversationIndex = updateConversationIndex;
    window.generateConversationTitle = generateConversationTitle;
    window.clearAllConversationData = clearAllConversationData;
    window.updateConversationListAfterMessage = updateConversationListAfterMessage;

    // 医生历史记录管理
    window.saveCurrentDoctorHistory = saveCurrentDoctorHistory;
    window.saveDoctorHistory = saveCurrentDoctorHistory; // 别名
    window.loadDoctorHistory = loadDoctorHistory;
    window.loadDoctorHistoryFromServer = loadDoctorHistoryFromServer;

    console.log('✅ smart_workflow_history.js 模块加载完成');

})();
