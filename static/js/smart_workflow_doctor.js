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

    /**
     * 医生头像映射表
     * 用于根据医生代码获取对应的emoji头像
     */
    const doctorAvatarMap = {
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
    // ========================================

    /**
     * 设置默认医生（不会有确认提示）
     * @param {string} doctorKey - 医生代码
     * @param {boolean} skipHistoryLoad - 是否跳过历史记录加载
     */
    function setDefaultDoctor(doctorKey, skipHistoryLoad = false) {
        const doctors = window.doctors || {};
        const doctor = doctors[doctorKey];
        if (!doctor) return;

        window.selectedDoctor = doctorKey;

        // 更新UI显示
        const cards = document.querySelectorAll('.doctor-card');
        cards.forEach((card, index) => {
            if (Object.keys(doctors)[index] === doctorKey) {
                card.classList.add('selected');
            }
        });

        // 更新顶部医生信息条
        const avatarEl = document.getElementById('currentDoctorAvatar');
        const nameEl = document.getElementById('currentDoctorName');
        const descEl = document.getElementById('currentDoctorDesc');

        if (avatarEl) avatarEl.textContent = doctor.avatar;
        if (nameEl) nameEl.textContent = `${doctor.name} - ${doctor.school}`;
        if (descEl) descEl.textContent = `擅长：${doctor.specialty}`;

        // 修复重复加载问题：只在非跳过模式下加载历史记录
        if (!skipHistoryLoad && typeof window.loadDoctorHistory === 'function') {
            window.loadDoctorHistory(doctorKey);
        }
    }

    /**
     * 选择医生（支持默认医生和推荐医生）
     * 这是医生选择的核心函数，处理所有医生切换逻辑
     *
     * @param {string} doctorKey - 医生代码
     * @param {Object|null} doctorData - 医生数据对象（可选）
     */
    function selectDoctor(doctorKey, doctorData = null) {
        const doctors = window.doctors || {};
        const messagesContainer = document.getElementById('messagesContainer');
        const mobileMessagesContainer = document.getElementById('mobileMessagesContainer');

        // 检查是否有真正的对话内容（用户消息或AI回复）
        const userMessages = messagesContainer ? messagesContainer.querySelectorAll('.message.user') : [];
        const aiMessages = messagesContainer ? messagesContainer.querySelectorAll('.message.ai') : [];
        const hasExistingMessages = userMessages.length > 0 || aiMessages.length > 0;

        // 切换医生时保存当前医生的对话历史
        if (window.selectedDoctor && window.selectedDoctor !== doctorKey && hasExistingMessages) {
            // 保存当前医生的对话历史
            if (typeof window.saveCurrentDoctorHistory === 'function') {
                window.saveCurrentDoctorHistory();
            }
        }

        // 移除之前的选中状态
        document.querySelectorAll('.doctor-card').forEach(card => {
            card.classList.remove('selected');
        });

        // 添加新的选中状态
        if (event && event.currentTarget) {
            event.currentTarget.classList.add('selected');
        }

        const previousDoctor = window.selectedDoctor;
        window.selectedDoctor = doctorKey;

        // 获取医生信息（优先使用传入的doctorData，然后是默认doctors对象）
        const doctor = doctorData || doctors[doctorKey] || {
            name: '医生',
            school: '中医师',
            avatar: '👨‍⚕️',
            specialty: '中医内科'
        };

        // 更新顶部医生信息条
        const avatarEl = document.getElementById('currentDoctorAvatar');
        const nameEl = document.getElementById('currentDoctorName');
        const descEl = document.getElementById('currentDoctorDesc');

        if (avatarEl) avatarEl.textContent = doctor.avatar;
        if (nameEl) nameEl.textContent = `${doctor.name} - ${doctor.school}`;
        if (descEl) descEl.textContent = `擅长：${doctor.specialty}`;

        // 切换医生时的关键修复：
        if (previousDoctor && previousDoctor !== doctorKey) {
            // 1. 清空当前显示的消息（开始全新对话）
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
                messagesContainer.removeAttribute('data-current-doctor');
            }
            if (mobileMessagesContainer) {
                mobileMessagesContainer.innerHTML = '';
                mobileMessagesContainer.removeAttribute('data-current-doctor');
            }
            console.log(`🧹 切换医生：清空当前对话，准备开始与${doctor.name}的新对话`);

            // 2. 生成新的对话ID，强制开始新对话
            if (typeof window.generateConversationId === 'function') {
                window.generateConversationId();
                console.log(`🆕 生成新对话ID: ${window.currentConversationId}`);
            }
        }

        // 修复：不自动加载历史记录，让用户开始全新对话
        // 如果需要查看历史，用户可以通过历史记录功能查看
        console.log(`✅ 已切换到${doctor.name}，准备开始新对话`);

        // 显示输入框
        const inputContainer = document.querySelector('.input-container');
        if (inputContainer) {
            inputContainer.classList.add('show');
        }

        // 移动端：关闭医生选择浮层
        if (window.innerWidth <= 768 && typeof window.closeMobileDoctorSelector === 'function') {
            window.closeMobileDoctorSelector();
        }
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
    window.getAvatarForDoctor = getAvatarForDoctor;
    window.getDoctorDisplayName = getDoctorDisplayName;

    // 同时暴露doctorAvatarMap以便其他模块使用
    window.doctorAvatarMap = doctorAvatarMap;

    console.log('✅ [Module] smart_workflow_doctor.js 加载完成');
    console.log('📋 已暴露函数: loadDoctors, loadDefaultDoctors, renderDoctorCards, updateDoctorSelector, setDefaultDoctor, selectDoctor, getAvatarForDoctor, getDoctorDisplayName');

})();
