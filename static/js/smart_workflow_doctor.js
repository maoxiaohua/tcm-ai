/**
 * Smart Workflow Doctor Module
 * 智能工作流 - 医生管理模块
 *
 * 本模块包含所有与医生相关的功能函数，包括：
 * - 医生列表加载和渲染
 * - 医生选择和切换
 * - 医生信息显示和更新
 *
 * 依赖的全局变量（来自core模块）：
 * - window.doctors - 医生数据对象
 * - window.selectedDoctor - 当前选中的医生
 * - window.currentConversationId - 当前对话ID
 *
 * @module smart_workflow_doctor
 * @version 1.0.0
 * @date 2025-01-09
 */

(function() {
    'use strict';

    // ========================================
    // 医生头像映射
    // ========================================

    // 🔑 v4.2优化：使用constants.js中的统一定义
    // 如果constants.js已加载，使用全局常量；否则使用备用值
    const doctorAvatarMap = window.TCM_CONSTANTS?.DOCTOR_AVATAR_MAP || window.doctorAvatarMap || {
        "jin_daifu": "👨‍⚕️",
        "zhang_zhongjing": "🎯"
    };

    // ========================================
    // 医生加载函数
    // ========================================

    /**
     * 从API加载医生列表（异步更新）
     * 从/api/doctors/list获取完整医生列表并更新全局doctors对象
     */
    async function loadDoctors() {
        try {
            console.log('🔄 [API] 开始从API加载完整医生列表...');
            const response = await fetch('/api/doctors/list');
            const result = await response.json();

            if (result.success && result.doctors && result.doctors.length > 0) {
                console.log('✅ [API] API返回医生数据:', result.doctors.length, '位医生');
                // 转换为前端需要的格式（覆盖默认数据）
                const newDoctors = {};
                result.doctors.forEach(doctor => {
                    const doctorCode = doctor.doctor_code;

                    // 解析specialties（可能是JSON字符串）
                    let specialty = "中医全科";
                    if (doctor.specialties) {
                        try {
                            const specs = JSON.parse(doctor.specialties);
                            specialty = Array.isArray(specs) ? specs.join('、') : doctor.specialties;
                        } catch {
                            specialty = doctor.specialties;
                        }
                    }

                    // 修复specialty.split错误 - 确保specialty是字符串
                    const specialtyStr = String(specialty || "中医");

                    newDoctors[doctorCode] = {
                        "name": doctor.name,
                        "school": specialtyStr.split('、')[0] || "中医",
                        "avatar": doctorAvatarMap[doctorCode] || "👨‍⚕️",
                        "specialty": specialtyStr,
                        "introduction": doctor.introduction || `${doctor.name}医师，擅长${specialtyStr}等疾病的诊治。`
                    };
                });

                // 用API数据覆盖默认数据
                window.doctors = newDoctors;
                console.log('✅ [API] 医生列表更新成功:', Object.keys(window.doctors).length, '位医生');

                // 更新医生选择器
                updateDoctorSelector();
            } else {
                console.warn('⚠️ [API] API返回数据为空，继续使用默认医生数据');
                // 保持使用已初始化的默认医生数据，不做任何改变
            }
        } catch (error) {
            console.error('❌ [API] 加载医生列表异常:', error);
            console.log('⚠️ [API] 继续使用默认医生数据');
            // 保持使用已初始化的默认医生数据，不做任何改变
        }
    }

    /**
     * 加载默认医生数据
     * 注意：此函数已废弃，因为默认医生数据已在初始化时加载
     * 保留此函数仅为兼容旧代码，实际不再使用
     */
    function loadDefaultDoctors() {
        console.log('⚠️ [DEPRECATED] loadDefaultDoctors被调用，但默认数据已在初始化时加载');
        // 如果doctors为空，则重新加载
        if (!window.doctors || Object.keys(window.doctors).length === 0) {
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
            console.log('⚠️ [DEPRECATED] 重新加载默认医生数据');
        }
    }

    // ========================================
    // 医生渲染函数
    // ========================================

    /**
     * 渲染医生卡片
     * 将doctors数据渲染为可点击的医生卡片UI
     */
    function renderDoctorCards() {
        const container = document.getElementById('doctorsGrid');
        if (!container) {
            console.warn('⚠️ 找不到doctorsGrid容器');
            return;
        }
        container.innerHTML = '';

        // 直接使用医生列表
        const doctors = window.doctors || {};
        Object.entries(doctors).forEach(([key, doctor]) => {
            const card = document.createElement('div');
            card.className = 'doctor-card';
            card.onclick = () => selectDoctor(key, doctor);

            card.innerHTML = `
                <div class="doctor-header">
                    <div class="doctor-info">
                        <div class="doctor-avatar">${doctor.avatar}</div>
                        <div class="doctor-details">
                            <h3>${doctor.name}</h3>
                            <span class="doctor-school">${doctor.school}</span>
                        </div>
                    </div>
                    <div class="selection-indicator">
                        <span style="font-size: 12px;">✓</span>
                    </div>
                </div>
                <div class="doctor-specialty">
                    <strong>擅长：</strong>${doctor.specialty}
                </div>
            `;

            container.appendChild(card);
        });
    }

    /**
     * 更新医生选择器（在医生数据加载后调用）
     * 更新当前医生显示信息，处理PC端和移动端的UI更新
     */
    function updateDoctorSelector() {
        const doctors = window.doctors || {};
        const selectedDoctor = window.selectedDoctor;

        // 更新当前医生显示
        const currentDoctorDesc = document.getElementById('currentDoctorDesc');
        if (currentDoctorDesc && selectedDoctor && doctors[selectedDoctor]) {
            currentDoctorDesc.textContent = `当前医师：${doctors[selectedDoctor].name}`;
        }

        // 确保第一个医生被设为默认
        if (Object.keys(doctors).length > 0 && !selectedDoctor) {
            const firstDoctorKey = Object.keys(doctors)[0];
            window.selectedDoctor = firstDoctorKey;
        }

        // 修复：更新移动端医生显示
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            if (typeof window.renderMobileDoctorCards === 'function') {
                window.renderMobileDoctorCards();
            }

            // 更新移动端当前医生信息
            if (selectedDoctor && doctors[selectedDoctor]) {
                const doctor = doctors[selectedDoctor];
                const mobileDoctorAvatar = document.getElementById('mobileDoctorAvatar');
                const mobileDoctorName = document.getElementById('mobileDoctorName');
                const mobileDoctorDesc = document.getElementById('mobileDoctorDesc');

                if (mobileDoctorAvatar) mobileDoctorAvatar.textContent = doctor.avatar;
                if (mobileDoctorName) mobileDoctorName.textContent = doctor.name;
                if (mobileDoctorDesc) mobileDoctorDesc.textContent = doctor.school;
            }
        }
    }

    // ========================================
    // 医生选择函数
    // 🔑 v4.3 优化：拆分大函数为小函数，提高可维护性
    // ========================================

    /**
     * 更新医生信息条UI
     * @param {Object} doctor - 医生数据对象
     */
    function updateDoctorInfoBar(doctor) {
        const avatarEl = document.getElementById('currentDoctorAvatar');
        const nameEl = document.getElementById('currentDoctorName');
        const descEl = document.getElementById('currentDoctorDesc');

        if (avatarEl) avatarEl.textContent = doctor.avatar;
        if (nameEl) nameEl.textContent = `${doctor.name} - ${doctor.school}`;
        if (descEl) descEl.textContent = `擅长：${doctor.specialty}`;
    }

    /**
     * 更新医生卡片选中状态
     * @param {string} doctorKey - 医生代码
     */
    function updateDoctorCardSelection(doctorKey) {
        const doctors = window.doctors || {};
        const cards = document.querySelectorAll('.doctor-card');

        cards.forEach(card => card.classList.remove('selected'));

        cards.forEach((card, index) => {
            if (Object.keys(doctors)[index] === doctorKey) {
                card.classList.add('selected');
            }
        });
    }

    function normalizeDoctorKey(doctorKey, doctors = window.doctors || {}) {
        const raw = String(doctorKey || '').trim();
        if (!raw) return raw;
        if (doctors[raw]) return raw;

        const doctorNameMap = {
            '张仲景': 'zhang_zhongjing',
            '金大夫': 'jin_daifu',
            '叶天士': 'ye_tianshi',
            '李东垣': 'li_dongyuan',
            '刘渡舟': 'liu_duzhou',
            '郑钦安': 'zheng_qin_an',
            '朱丹溪': 'zhu_danxi'
        };

        if (doctorNameMap[raw] && doctors[doctorNameMap[raw]]) {
            return doctorNameMap[raw];
        }

        const doctorCode = Object.keys(doctors).find((key) => doctors[key]?.name === raw);
        return doctorCode || doctorNameMap[raw] || raw;
    }

    /**
     * 保存当前对话历史
     * 🔑 v4.3 修复：使用统一的 tcm_doctor_history_{userId}_{doctorKey} 格式
     * @param {string} doctorKey - 当前医生代码
     */
    function saveCurrentConversation(doctorKey) {
        const messages = window.messages || [];
        if (!doctorKey || messages.length === 0) return;

        const userId = typeof window.getCurrentUserId === 'function'
            ? window.getCurrentUserId()
            : 'default';

        // 使用统一格式保存
        const historyKey = `tcm_doctor_history_${userId}_${doctorKey}`;
        const saveCount = (parseInt(localStorage.getItem(`save_count_${historyKey}`) || '0')) + 1;

        const historyData = {
            messages: messages,
            conversation_id: window.currentConversationId,
            version: '2.1',
            lastUpdated: new Date().toISOString(),
            saveCount: saveCount
        };

        try {
            localStorage.setItem(historyKey, JSON.stringify(historyData));
            localStorage.setItem(`save_count_${historyKey}`, saveCount.toString());
            console.log(`✅ 已保存${doctorKey}医生的${messages.length}条对话记录 (第${saveCount}次保存)`);

            // 验证保存
            const verified = localStorage.getItem(historyKey);
            if (verified) {
                console.log(`✅ 保存验证成功`);
            }
        } catch (e) {
            console.error('保存对话历史失败:', e);
        }

        // 同时调用原有保存函数（兼容性）
        if (typeof window.saveCurrentDoctorHistory === 'function') {
            window.saveCurrentDoctorHistory();
        }
    }

    /**
     * 恢复对话消息到UI
     * @param {Array} messages - 消息数组
     * @param {string} doctorKey - 医生代码
     */
    async function restoreMessagesToUI(messages, doctorKey) {
        if (messages && messages.length > 0) {
            console.log(`恢复对话: ${messages.length}条历史消息`);
            for (const msg of messages) {
                if (typeof window.addMessage === 'function') {
                    await window.addMessage(msg.type, msg.content, false, false, null);
                }
            }
        } else {
            console.log('无历史记录，显示欢迎消息');
            if (typeof window.addWelcomeMessage === 'function') {
                window.addWelcomeMessage(doctorKey);
            }
        }
    }

    /**
     * 通过API切换医生（登录用户）
     * 🔑 v4.3 修复：API返回空消息时，优先使用本地历史记录
     */
    async function switchDoctorViaAPI(doctorKey, previousDoctor, messagesContainer, mobileMessagesContainer) {
        try {
            // 切换前先保存当前对话
            if (window.messages && window.messages.length > 0 && window.currentConversationId) {
                console.log(`💾 切换前保存当前对话: ${window.currentConversationId}`);
                // 保存到本地
                saveCurrentConversation(previousDoctor);
                // 保存到服务器
                if (typeof window.saveConversationToServer === 'function') {
                    await window.saveConversationToServer(window.messages, previousDoctor);
                }
            }

            // 调用API切换医生
            const result = await window.sessionManager.switchDoctor(doctorKey);

            // 清空显示
            clearMessageContainers(messagesContainer, mobileMessagesContainer);

            // 更新全局变量
            window.currentConversationId = result.conversation_id;

            // 🔑 v4.3 修复：如果API返回0条消息，尝试从本地加载
            let messages = result.messages || [];

            if (messages.length === 0) {
                console.log(`⚠️ API返回0条消息，尝试从本地加载${doctorKey}医生的历史记录...`);

                const userId = typeof window.getCurrentUserId === 'function'
                    ? window.getCurrentUserId()
                    : 'default';
                const historyKey = `tcm_doctor_history_${userId}_${doctorKey}`;
                const storedHistory = localStorage.getItem(historyKey);

                if (storedHistory) {
                    try {
                        const historyData = JSON.parse(storedHistory);
                        if (historyData.messages && historyData.messages.length > 0) {
                            messages = historyData.messages;
                            console.log(`✅ 从本地加载${doctorKey}医生的${messages.length}条历史记录`);
                        }
                    } catch (e) {
                        console.warn('解析本地历史失败:', e);
                    }
                }
            }

            window.messages = messages;

            // 恢复消息到UI
            await restoreMessagesToUI(messages, doctorKey);

            // 同步保存到本地（使用新格式）
            if (messages.length > 0) {
                saveCurrentConversation(doctorKey);
            }

        } catch (error) {
            console.error('切换医生API失败，使用本地存储:', error);
            await handleDoctorSwitchLocally(doctorKey, messagesContainer, mobileMessagesContainer);
        }
    }

    /**
     * 设置默认医生（不会有确认提示）
     * @param {string} doctorKey - 医生代码
     * @param {boolean} skipHistoryLoad - 是否跳过历史记录加载
     */
    function setDefaultDoctor(doctorKey, skipHistoryLoad = false) {
        const doctors = window.doctors || {};
        const normalizedDoctorKey = normalizeDoctorKey(doctorKey, doctors);
        const doctor = doctors[normalizedDoctorKey];
        if (!doctor) return;

        window.selectedDoctor = normalizedDoctorKey;
        updateDoctorCardSelection(normalizedDoctorKey);
        updateDoctorInfoBar(doctor);

        if (!skipHistoryLoad && typeof window.loadDoctorHistory === 'function') {
            window.loadDoctorHistory(normalizedDoctorKey);
        }
    }

    /**
     * 选择医生（支持默认医生和推荐医生）
     * 🔑 v4.3 优化：拆分为多个小函数，提高可读性
     *
     * @param {string} doctorKey - 医生代码
     * @param {Object|null} doctorData - 医生数据对象（可选）
     */
    function selectDoctor(doctorKey, doctorData = null) {
        const doctors = window.doctors || {};
        const normalizedDoctorKey = normalizeDoctorKey(doctorKey, doctors);
        const messagesContainer = document.getElementById('messagesContainer');
        const mobileMessagesContainer = document.getElementById('mobileMessagesContainer');

        // 检查是否有现有消息
        const hasExistingMessages = messagesContainer &&
            (messagesContainer.querySelectorAll('.message.user').length > 0 ||
             messagesContainer.querySelectorAll('.message.ai').length > 0);

        // 保存当前对话（如果有内容且正在切换）
        const previousDoctor = window.selectedDoctor;
        if (previousDoctor && previousDoctor !== normalizedDoctorKey && hasExistingMessages) {
            saveCurrentConversation(previousDoctor);
        }

        // 更新选中状态
        document.querySelectorAll('.doctor-card').forEach(card => card.classList.remove('selected'));
        if (event?.currentTarget) {
            event.currentTarget.classList.add('selected');
        }

        window.selectedDoctor = normalizedDoctorKey;

        // 获取医生信息
        const doctor = doctorData || doctors[normalizedDoctorKey] || {
            name: '医生', school: '中医师', avatar: '👨‍⚕️', specialty: '中医内科'
        };

        // 更新UI
        updateDoctorInfoBar(doctor);

        // 处理医生切换逻辑
        if (previousDoctor && previousDoctor !== normalizedDoctorKey) {
            console.log(`🔄 从${previousDoctor}切换到${normalizedDoctorKey}`);

            const forceFreshConversation = window.refreshConversationStrategy === 'new_conversation';
            if (forceFreshConversation) {
                startFreshConversationForDoctor(normalizedDoctorKey, messagesContainer, mobileMessagesContainer);
            } else {
                const isLoggedIn = !!(
                    (window.authManager && typeof window.authManager.getToken === 'function'
                        ? window.authManager.getToken()
                        : null) ||
                    window.userToken ||
                    localStorage.getItem('session_token') ||
                    localStorage.getItem('tcm_auth_token') ||
                    localStorage.getItem('auth_token')
                );

                if (isLoggedIn && window.sessionManager) {
                    switchDoctorViaAPI(normalizedDoctorKey, previousDoctor, messagesContainer, mobileMessagesContainer);
                } else {
                    console.log('📦 游客模式，使用本地存储切换医生');
                    handleDoctorSwitchLocally(normalizedDoctorKey, messagesContainer, mobileMessagesContainer);
                }
            }
        }

        console.log(`✅ 已切换到${doctor.name}`);

        // 显示输入框
        const inputContainer = document.querySelector('.input-container');
        if (inputContainer) inputContainer.classList.add('show');

        // 移动端：关闭医生选择浮层
        if (window.innerWidth <= 768 && typeof window.closeMobileDoctorSelector === 'function') {
            window.closeMobileDoctorSelector();
        }
    }

    /**
     * 清空消息容器
     */
    function clearMessageContainers(messagesContainer, mobileMessagesContainer) {
        if (messagesContainer) {
            messagesContainer.innerHTML = '';
            messagesContainer.removeAttribute('data-current-doctor');
        }
        if (mobileMessagesContainer) {
            mobileMessagesContainer.innerHTML = '';
            mobileMessagesContainer.removeAttribute('data-current-doctor');
        }
    }

    async function startFreshConversationForDoctor(doctorKey, messagesContainer, mobileMessagesContainer) {
        clearMessageContainers(messagesContainer, mobileMessagesContainer);

        if (typeof window.generateConversationId === 'function') {
            window.generateConversationId();
        } else {
            window.currentConversationId = generateLocalConversationId();
        }
        window.messages = [];

        const doctors = window.doctors || {};
        const doctor = doctors[doctorKey] || {
            name: '中医师',
            school: ''
        };
        const welcomeMessage = `您好！我是${doctor.name}${doctor.school ? `，${doctor.school}传人` : ''}。请详细描述您的症状，我将为您进行专业的中医分析。`;
        const isMobile = window.innerWidth <= 768;

        if (isMobile && typeof window.addMobileMessage === 'function') {
            await window.addMobileMessage('ai', welcomeMessage);
            if (typeof window.showMobileChatPage === 'function') {
                window.showMobileChatPage();
            }
        } else if (typeof window.addMessage === 'function') {
            await window.addMessage('ai', welcomeMessage, false, false, null);
        } else if (typeof window.addWelcomeMessage === 'function') {
            window.addWelcomeMessage(doctorKey);
        }
    }

    /**
     * 保存医生对话历史到本地存储
     */
    function saveDoctorMessagesToLocal(doctorKey, messages) {
        if (!doctorKey || !messages) return;
        try {
            const storageKey = `tcm_doctor_messages_${doctorKey}`;
            const data = {
                messages: messages,
                timestamp: Date.now(),
                conversation_id: window.currentConversationId
            };
            localStorage.setItem(storageKey, JSON.stringify(data));
            console.log(`💾 已保存${doctorKey}的${messages.length}条消息到本地`);
        } catch (e) {
            console.warn('保存本地消息失败:', e);
        }
    }

    /**
     * 从本地存储加载医生对话历史
     */
    function loadDoctorMessagesFromLocal(doctorKey) {
        if (!doctorKey) return null;
        try {
            const storageKey = `tcm_doctor_messages_${doctorKey}`;
            const dataStr = localStorage.getItem(storageKey);
            if (!dataStr) return null;

            const data = JSON.parse(dataStr);
            // 检查是否过期（24小时）
            if (Date.now() - data.timestamp > 24 * 60 * 60 * 1000) {
                localStorage.removeItem(storageKey);
                return null;
            }
            return data;
        } catch (e) {
            console.warn('加载本地消息失败:', e);
            return null;
        }
    }

    /**
     * 使用本地存储处理医生切换（游客模式或API失败时）
     * 🔑 v4.3 修复：使用统一的 tcm_doctor_history_{userId}_{doctorKey} 格式
     */
    async function handleDoctorSwitchLocally(doctorKey, messagesContainer, mobileMessagesContainer) {
        // 清空当前显示
        clearMessageContainers(messagesContainer, mobileMessagesContainer);

        // 🔑 修复：使用统一的历史记录格式（包含用户ID）
        const userId = typeof window.getCurrentUserId === 'function'
            ? window.getCurrentUserId()
            : 'default';
        const historyKey = `tcm_doctor_history_${userId}_${doctorKey}`;

        console.log(`📂 尝试加载历史记录: ${historyKey}`);

        let messages = [];
        let conversationId = null;

        // 优先从新格式加载
        const storedHistory = localStorage.getItem(historyKey);
        if (storedHistory) {
            try {
                const historyData = JSON.parse(storedHistory);
                if (historyData.messages && historyData.messages.length > 0) {
                    messages = historyData.messages;
                    conversationId = historyData.conversation_id || historyData.conversationId;
                    console.log(`✅ 加载${doctorKey}医生的${messages.length}条历史记录（版本：${historyData.version || '1.0'}，最后更新：${historyData.lastUpdated || '未知'}）`);

                    // 打印历史记录详情
                    if (messages.length > 0) {
                        const firstTime = messages[0].time || '未知';
                        const lastTime = messages[messages.length - 1].time || '未知';
                        console.log(`📋 历史记录详情: 第一条消息时间=${firstTime}, 最后一条消息时间=${lastTime}`);
                    }
                }
            } catch (e) {
                console.warn('解析历史记录失败:', e);
            }
        }

        // 回退：尝试从旧格式加载
        if (messages.length === 0) {
            const localData = loadDoctorMessagesFromLocal(doctorKey);
            if (localData && localData.messages && localData.messages.length > 0) {
                messages = localData.messages;
                conversationId = localData.conversation_id || localData.conversationId;
                console.log(`📂 从旧格式恢复${doctorKey}的${messages.length}条消息`);
            }
        }

        if (messages.length > 0) {
            window.messages = messages;
            window.currentConversationId = conversationId || generateLocalConversationId();

            // 恢复消息到UI
            for (const msg of messages) {
                if (typeof window.addMessage === 'function') {
                    await window.addMessage(msg.type, msg.content, false, false, null);
                }
            }

            // 🔑 保存验证
            console.log(`✅ 已保存${doctorKey}医生的${messages.length}条对话记录`);
        } else {
            // 无本地历史，开启新对话
            console.log('📝 无本地历史，开启新对话');
            window.messages = [];
            window.currentConversationId = generateLocalConversationId();

            if (typeof window.addWelcomeMessage === 'function') {
                window.addWelcomeMessage(doctorKey);
            }
        }
    }

    /**
     * 生成本地会话ID
     */
    function generateLocalConversationId() {
        return 'local_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // ========================================
    // 医生工具函数
    // ========================================

    /**
     * 为医生分配头像
     * @param {string} doctorName - 医生名称
     * @returns {string} emoji头像
     */
    function getAvatarForDoctor(doctorName) {
        const avatarMap = {
            '张仲景': '⚕️',
            '金大夫': '💊'
        };
        return avatarMap[doctorName] || '👨‍⚕️';
    }

    /**
     * 获取医生显示名称
     * @param {string} doctorKey - 医生代码
     * @returns {string} 医生显示名称
     */
    function getDoctorDisplayName(doctorKey) {
        const doctors = window.doctors || {};

        // 优先从加载的医生数据中获取
        if (doctors[doctorKey] && doctors[doctorKey].name) {
            return doctors[doctorKey].name;
        }

        // 备选：硬编码映射（兼容旧数据）
        const doctorNames = {
            'jin_daifu': '金大夫',
            'zhang_zhongjing': '张仲景'
        };
        return doctorNames[doctorKey] || doctorKey || '医生';
    }

    // ========================================
    // 暴露到全局window对象
    // ========================================

    window.loadDoctors = loadDoctors;
    window.loadDefaultDoctors = loadDefaultDoctors;
    window.renderDoctorCards = renderDoctorCards;
    window.updateDoctorSelector = updateDoctorSelector;
    window.setDefaultDoctor = setDefaultDoctor;
    window.selectDoctor = selectDoctor;
    window.normalizeDoctorKey = normalizeDoctorKey;
    window.getAvatarForDoctor = getAvatarForDoctor;
    window.getDoctorDisplayName = getDoctorDisplayName;
    window.saveDoctorMessagesToLocal = saveDoctorMessagesToLocal;
    window.loadDoctorMessagesFromLocal = loadDoctorMessagesFromLocal;

    // 同时暴露doctorAvatarMap以便其他模块使用
    window.doctorAvatarMap = doctorAvatarMap;

    console.log('✅ [Module] smart_workflow_doctor.js v4.2 加载完成');
    console.log('📋 已暴露函数: loadDoctors, selectDoctor, saveDoctorMessagesToLocal, loadDoctorMessagesFromLocal 等');

})();
