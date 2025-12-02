/**
 * TCM-AI 智能问诊聊天模块
 * 从 index_smart_workflow.html 提取的消息相关核心功能
 *
 * 包含功能:
 * - 消息发送和显示
 * - 消息格式化
 * - 症状相关分析
 *
 * 依赖全局变量:
 * - window.selectedDoctor - 当前选中的医生
 * - window.doctors - 医生数据对象
 * - window.currentConversationId - 当前对话ID
 * - window.currentUser - 当前用户信息
 * - window.userToken - 用户认证Token
 *
 * @version 1.0.0
 * @date 2024-01-20
 */

(function() {
    'use strict';

    // ========================================
    // 消息清理相关
    // ========================================

    /**
     * 清理所有消息
     * 清空PC端和移动端的消息容器
     */
    function clearAllMessages() {
        const containers = ['messagesContainer', 'mobileMessagesContainer'];
        containers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = '';
                console.log('[Chat] 清理消息容器:', containerId);
            }
        });
    }

    // ========================================
    // 症状相关函数
    // ========================================

    // ========================================
    // 🔑 v4.3 性能优化：预编译正则表达式
    // ========================================

    // 从constants.js获取预编译的正则模式
    const MESSAGE_PATTERNS = window.TCM_CONSTANTS?.MESSAGE_FORMAT_PATTERNS || {
        SECTION_TITLE: /【([^】]+)】/g,
        NUMBERED_TITLE: /^(\d+[.、）)])/gm,
        DOUBLE_NEWLINE: /\n\n/g,
        SINGLE_NEWLINE: /\n/g,
        BOLD_TEXT: /\*\*([^*]+)\*\*/g,
        EMPHASIS_TEXT: /\*([^*]+)\*/g,
        PRESCRIPTION_MARKER: /【(?:君药|臣药|佐药|使药|处方)】/
    };

    // 从constants.js获取症状关键词
    const SYMPTOM_KEYWORDS = window.TCM_CONSTANTS?.SYMPTOM_KEYWORDS || [
        '头痛', '头晕', '发热', '咳嗽', '胸闷', '心悸', '失眠', '腹痛',
        '腹泻', '便秘', '恶心', '呕吐', '乏力', '疲劳', '食欲', '口干',
        '口苦', '盗汗', '自汗', '气短', '胸痛', '腰痛', '关节痛', '肌肉痛',
        '水肿', '尿频', '尿急', '月经', '白带', '耳鸣', '眼花', '鼻塞',
        '流涕', '咽痛', '牙痛', '舌苔', '脉象'
    ];

    // 🔑 v4.3 优化：预编译的格式化规则（避免每次调用时创建正则）
    const FORMAT_RULES = [
        // 处方标签 - 特殊高亮
        {
            pattern: /\*\*【处方】\*\*/g,
            replacement: '<div style="background: linear-gradient(135deg, #2d5aa0, #4a7bc8); color: white; padding: 10px 15px; border-radius: 8px; margin: 15px 0; font-weight: bold; font-size: 16px; text-align: center;">📋 中药处方</div>'
        },
        // 用法/注意/禁忌/功效标签
        {
            pattern: /\*\*【(用法|注意|禁忌|功效)】\*\*/g,
            replacement: '<div style="background: #f3f4f6; color: #374151; padding: 8px 12px; border-radius: 6px; margin: 10px 0; font-weight: bold; border-left: 4px solid #6b7280;">$1</div>'
        },
        // 其他粗体标签【xxx】
        {
            pattern: /\*\*【(.*?)】\*\*/g,
            replacement: '<strong style="color: #2d5aa0; font-size: 15px; background: #e0f2fe; padding: 2px 6px; border-radius: 4px;">【$1】</strong>'
        },
        // 粗体文本
        {
            pattern: /\*\*(.*?)\*\*/g,
            replacement: '<strong style="color: #1f2937; font-weight: bold;">$1</strong>'
        },
        // 斜体文本
        {
            pattern: /\*(.*?)\*/g,
            replacement: '<em style="color: #6b7280;">$1</em>'
        },
        // #####分割线
        {
            pattern: /#{5,}/g,
            replacement: '<hr style="margin: 20px 0; border: none; border-top: 2px solid #e5e7eb; background: linear-gradient(to right, #e5e7eb, transparent);">'
        },
        // ###小标题
        {
            pattern: /###\s*(.*?)(?=\n|$)/g,
            replacement: '<h4 style="margin: 20px 0 12px 0; color: #2d5aa0; font-size: 17px; font-weight: bold; padding-left: 8px; border-left: 4px solid #2d5aa0; background: #f8fafc;">$1</h4>'
        },
        // ##中标题
        {
            pattern: /##\s*(.*?)(?=\n|$)/g,
            replacement: '<h3 style="margin: 25px 0 15px 0; color: #1f2937; font-size: 19px; font-weight: bold; padding: 8px 12px; background: linear-gradient(135deg, #f3f4f6, #e5e7eb); border-radius: 6px;">$1</h3>'
        },
        // #大标题
        {
            pattern: /^#\s*(.*?)(?=\n|$)/gm,
            replacement: '<h2 style="margin: 30px 0 20px 0; color: #111827; font-size: 22px; font-weight: bold; text-align: center; padding: 12px; background: linear-gradient(135deg, #dbeafe, #bfdbfe); border-radius: 8px;">$1</h2>'
        },
        // 药材列表
        {
            pattern: /([一-龟\u4e00-\u9fff]+)\s+(\d+)g/g,
            replacement: '<span style="display: inline-block; background: #ecfdf5; color: #065f46; padding: 2px 6px; margin: 1px 3px; border-radius: 4px; font-weight: 500; border: 1px solid #d1fae5;">$1 <strong>$2g</strong></span>'
        },
        // 段落间距
        {
            pattern: /\n\n/g,
            replacement: '<br><br>'
        },
        // 普通换行
        {
            pattern: /\n/g,
            replacement: '<br>'
        },
        // 数字列表样式
        {
            pattern: /(\d+\.\s)/g,
            replacement: '<br><span style="color: #2d5aa0; font-weight: bold;">$1</span>'
        }
    ];

    /**
     * 从文本中提取症状关键词
     * 🔑 v4.3 优化：使用预编译的症状列表
     * @param {string} text - 输入文本
     * @returns {Array<string>} 找到的症状列表
     */
    function extractSymptomsFromText(text) {
        // 扩展的症状关键词（合并constants和本地定义）
        const extendedKeywords = [
            ...SYMPTOM_KEYWORDS,
            '头疼', '眩晕', '焦虑', '抑郁', '胃痛', '胃疼', '肚子疼', '肚子痛',
            '食欲不振', '消化不良', '哮喘', '鼻炎', '气喘', '感冒', '发烧', '喉咙痛',
            '月经不调', '痛经', '白带异常', '不孕', '更年期', '妇科',
            '小儿发热', '小儿咳嗽', '小儿腹泻', '湿疹', '痤疮', '皮肤病', '青春痘',
            '颈椎病', '膝盖痛', '听力下降', '口腔溃疡', '便血', '手脚冰凉', '四肢无力'
        ];

        const foundSymptoms = [];
        for (const symptom of extendedKeywords) {
            if (text.includes(symptom)) {
                foundSymptoms.push(symptom);
            }
        }
        return foundSymptoms;
    }

    /**
     * 获取症状同义词映射
     * @returns {Object} 症状同义词字典
     */
    function getSymptomSynonyms() {
        return {
            '腹痛': ['肚子疼', '肚子痛', '腹部疼痛', '腹部不适'],
            '肚子疼': ['腹痛', '肚子痛', '腹部疼痛'],
            '头痛': ['头疼', '头部疼痛'],
            '胃痛': ['胃疼', '胃部疼痛', '胃不舒服'],
            '发热': ['发烧', '体温升高'],
            '咽痛': ['喉咙痛', '咽喉疼痛']
        };
    }

    /**
     * 检查症状是否相关（考虑同义词和医学关联）
     * @param {Array<string>} userSymptoms - 用户描述的症状
     * @param {string} aiSymptom - AI提到的症状
     * @returns {boolean} 是否相关
     */
    function isSymptomsRelated(userSymptoms, aiSymptom) {
        const synonyms = getSymptomSynonyms();

        // 直接匹配
        if (userSymptoms.includes(aiSymptom)) {
            return true;
        }

        // 同义词检查
        for (const userSymptom of userSymptoms) {
            if (synonyms[userSymptom] && synonyms[userSymptom].includes(aiSymptom)) {
                return true;
            }
            if (synonyms[aiSymptom] && synonyms[aiSymptom].includes(userSymptom)) {
                return true;
            }
        }

        // 医学关联性检查（常见的症状组合）
        const medicalAssociations = {
            '腹痛': ['腹泻', '便秘', '食欲不振', '腹胀'],
            '肚子疼': ['腹泻', '便秘', '食欲不振', '腹胀'],
            '头痛': ['头晕', '眩晕', '失眠'],
            '发热': ['乏力', '出汗'],
            '感冒': ['咳嗽', '流鼻涕', '鼻塞', '喉咙痛']
        };

        for (const userSymptom of userSymptoms) {
            if (medicalAssociations[userSymptom] && medicalAssociations[userSymptom].includes(aiSymptom)) {
                return true;
            }
        }

        return false;
    }

    // ========================================
    // 消息格式化函数
    // ========================================

    /**
     * 格式化消息内容
     * 🔑 v4.3 性能优化：使用预编译的正则规则，减少重复创建正则对象
     * 处理Markdown、特殊标签和中医处方格式
     * @param {string} content - 原始消息内容
     * @returns {string} 格式化后的HTML
     */
    function formatMessage(content) {
        if (!content) return '';

        // 检查是否包含诊疗方案XML标签
        if (content.includes('<诊疗方案>')) {
            return formatTCMPrescription(content);
        }

        // 🔑 v4.3 优化：使用预编译的规则数组进行批量替换
        let result = content;
        for (const rule of FORMAT_RULES) {
            // 重置正则表达式的lastIndex（对于带g标志的正则）
            rule.pattern.lastIndex = 0;
            result = result.replace(rule.pattern, rule.replacement);
        }

        // 移除开头的换行
        return result.replace(/^<br>/, '');
    }

    /**
     * 格式化中医处方 - 全新设计
     * @param {string} content - 处方内容
     * @returns {string} 格式化后的HTML
     */
    function formatTCMPrescription(content) {
        // 检查是否包含XML格式
        const hasXMLFormat = content.includes('<诊疗方案>');

        if (hasXMLFormat) {
            return formatXMLPrescription(content);
        } else {
            // 如果没有XML格式，尝试智能解析文本格式
            return formatTextPrescription(content);
        }
    }

    /**
     * XML格式处方解析
     * @param {string} content - XML格式的处方内容
     * @returns {string} 格式化后的HTML
     */
    function formatXMLPrescription(content) {
        const prescriptionMatch = content.match(/<诊疗方案>([\s\S]*?)<\/诊疗方案>/);
        if (!prescriptionMatch) {
            return formatTextPrescription(content);
        }

        const prescriptionContent = prescriptionMatch[1];
        let formattedHTML = '<div class="modern-tcm-report">';

        // 定义各个部分的配置
        const sections = [
            { name: '主诉', key: '主诉', icon: '🩺', color: '#ef4444' },
            { name: '现病史', key: '现病史', icon: '📋', color: '#3b82f6' },
            { name: '望诊所见', key: '望诊所见', icon: '👁️', color: '#10b981' },
            { name: '病机分析', key: '病机分析', icon: '🧠', color: '#8b5cf6' },
            { name: '证型诊断', key: '证型诊断', icon: '🎯', color: '#f59e0b' },
            { name: '治法', key: '治法', icon: '⚡', color: '#06b6d4' },
            { name: '方剂选用', key: '方剂选用', icon: '📜', color: '#84cc16' },
            { name: '处方建议', key: '处方建议', icon: '💊', color: '#ec4899', special: 'prescription' },
            { name: '煎服方法', key: '煎服方法', icon: '🔥', color: '#f97316' },
            { name: '随证加减', key: '随证加减', icon: '⚖️', color: '#6366f1' },
            { name: '生活调摄', key: '生活调摄', icon: '🌱', color: '#059669' },
            { name: '复诊建议', key: '复诊建议', icon: '📅', color: '#dc2626' }
        ];

        sections.forEach(section => {
            const regex = new RegExp(`<${section.key}>(.*?)<\/${section.key}>`, 's');
            const match = prescriptionContent.match(regex);

            if (match) {
                let sectionContent = match[1].trim()
                    .replace(/\*\*(.*?)\*\*/g, '<span class="highlight-term">$1</span>')
                    .replace(/\n/g, '<br>');

                // 特殊处理处方建议
                if (section.special === 'prescription') {
                    sectionContent = formatModernPrescription(sectionContent);
                }

                formattedHTML += `
                    <div class="modern-tcm-section" style="--section-color: ${section.color}">
                        <div class="section-header">
                            <span class="section-icon">${section.icon}</span>
                            <span class="section-title">${section.name}</span>
                        </div>
                        <div class="section-content">${sectionContent}</div>
                    </div>
                `;
            }
        });

        formattedHTML += '</div>';

        // 处理XML外的内容
        const beforeMatch = content.substring(0, content.indexOf('<诊疗方案>'));
        const afterMatch = content.substring(content.indexOf('</诊疗方案>') + 7);

        let result = '';
        if (beforeMatch.trim()) {
            result += '<div class="pre-prescription">' + formatMessage(beforeMatch) + '</div>';
        }
        result += formattedHTML;
        if (afterMatch.trim()) {
            result += '<div class="post-prescription">' + formatMessage(afterMatch) + '</div>';
        }

        return result;
    }

    /**
     * 文本格式处方智能解析
     * @param {string} content - 文本格式的处方内容
     * @returns {string} 格式化后的HTML
     */
    function formatTextPrescription(content) {
        let formattedHTML = '<div class="text-tcm-report">';

        // 按段落分析
        const paragraphs = content.split('\n\n');

        paragraphs.forEach(paragraph => {
            if (paragraph.trim()) {
                // 检查是否是标题行
                if (paragraph.includes('**') && paragraph.length < 50) {
                    formattedHTML += `<div class="text-section-header">${formatMessage(paragraph)}</div>`;
                } else {
                    formattedHTML += `<div class="text-section-content">${formatMessage(paragraph)}</div>`;
                }
            }
        });

        formattedHTML += '</div>';
        return formattedHTML;
    }

    /**
     * 现代化处方格式化
     * @param {string} prescriptionText - 处方文本
     * @returns {string} 格式化后的HTML
     */
    function formatModernPrescription(prescriptionText) {
        // 多种药材格式识别
        const herbs = [];
        let originalText = prescriptionText;

        // 模式匹配药材名称和剂量
        const patterns = [
            /<span class="highlight-term">(.*?)<\/span>\s*(\d+(?:\.\d+)?g?)/g,
            /\*\*(.*?)\*\*\s*(\d+(?:\.\d+)?g?)/g,
            /<strong>(.*?)<\/strong>\s*(\d+(?:\.\d+)?g?)/g,
            /([^\s\d，。；、\-]+)\s*(\d+(?:\.\d+)?g)/g
        ];

        let usedPattern = null;

        for (let pattern of patterns) {
            pattern.lastIndex = 0; // 重置正则表达式的lastIndex
            let match;
            let tempHerbs = [];

            while ((match = pattern.exec(originalText)) !== null) {
                const herbName = match[1].trim();
                const dosage = match[2];

                // 排除非药材词汇和重复项
                if (!['共', '煎', '服', '用', '每', '次', '日', '水', '煎服', '分服', '方', '药'].includes(herbName)
                    && herbName.length > 0 && herbName.length < 10) {

                    // 检查是否已存在
                    if (!tempHerbs.some(h => h.name === herbName)) {
                        tempHerbs.push({
                            name: herbName,
                            dosage: dosage,
                            fullMatch: match[0]
                        });
                    }
                }
            }

            if (tempHerbs.length > 0) {
                herbs.push(...tempHerbs);
                usedPattern = pattern;
                break; // 找到匹配就停止
            }
        }

        if (herbs.length > 0) {
            let modernHTML = '<div class="modern-prescription-grid">';
            herbs.forEach((herb, index) => {
                modernHTML += `
                    <div class="herb-card" style="animation-delay: ${index * 0.1}s">
                        <div class="herb-name-modern">
                            ${herb.name}
                            <span class="herb-dosage-inline">${herb.dosage}</span>
                        </div>
                    </div>
                `;
            });
            modernHTML += '</div>';

            // 移除已经显示的药材信息，避免重复
            let remainingText = originalText;
            herbs.forEach(herb => {
                // 移除各种可能的药材格式
                remainingText = remainingText
                    .replace(new RegExp(`\\*\\*${herb.name}\\*\\*\\s*${herb.dosage}[，、]*`, 'g'), '')
                    .replace(new RegExp(`<strong>${herb.name}</strong>\\s*${herb.dosage}[，、]*`, 'g'), '')
                    .replace(new RegExp(`<span class="highlight-term">${herb.name}</span>\\s*${herb.dosage}[，、]*`, 'g'), '')
                    .replace(new RegExp(`${herb.name}\\s*${herb.dosage}[，、]*`, 'g'), '');
            });

            // 清理多余的标点和空白
            remainingText = remainingText
                .replace(/<[^>]*>/g, '') // 移除HTML标签
                .replace(/\*\*/g, '') // 移除markdown标记
                .replace(/[，、]{2,}/g, '、') // 合并多个标点
                .replace(/^[，、\s]+|[，、\s]+$/g, '') // 移除首尾标点
                .trim();

            // 只有当剩余文本有实际内容时才显示
            if (remainingText && remainingText.length > 5) {
                modernHTML += `<div class="prescription-notes">${remainingText}</div>`;
            }

            return modernHTML;
        }

        // 如果没有识别到药材，返回格式化的文本
        return `<div class="prescription-text">${prescriptionText}</div>`;
    }

    // ========================================
    // 消息显示函数
    // ========================================

    /**
     * 添加消息到界面
     * 核心消息显示函数，处理用户消息和AI回复
     * @param {string} sender - 发送者类型 ('user' 或 'ai')
     * @param {string} content - 消息内容
     * @param {boolean} showFeedback - 是否显示反馈按钮
     * @param {boolean} isPaid - 处方是否已支付
     * @param {string|null} prescriptionId - 处方ID
     */
    async function addMessage(sender, content, showFeedback = false, isPaid = false, prescriptionId = null) {
        console.log('[Chat] addMessage被调用:', {
            sender,
            contentLength: content ? content.length : 0,
            contentPreview: content ? content.substring(0, 50) + '...' : 'null',
            showFeedback,
            isPaid,
            prescriptionId
        });

        const container = document.getElementById('messagesContainer');
        if (!container) {
            console.error('[Chat] 找不到messagesContainer');
            return;
        }

        // 防重复机制：检查最后一条消息是否与当前消息相同
        const lastMessage = container.querySelector('.message:last-child');
        if (lastMessage) {
            const lastSender = lastMessage.classList.contains('user') ? 'user' : 'ai';
            const lastText = lastMessage.querySelector('.message-text');
            const lastContent = lastText ? lastText.textContent.trim() : '';

            // 如果发送者和内容都相同，则跳过
            if (lastSender === sender && lastContent === content.trim()) {
                console.warn('[Chat] 检测到重复消息，跳过添加:', {sender, contentPreview: content.substring(0, 50)});
                return;
            }
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

        // 使用处方渲染器处理内容
        let processedContent = content;
        if (sender === 'ai') {
            console.log('[Chat] 处方渲染检查:', {
                prescriptionRenderer存在: !!window.prescriptionRenderer,
                isPaid: isPaid,
                prescriptionId: prescriptionId,
                内容长度: content.length
            });

            if (window.simplePrescriptionManager) {
                // 使用简化版处方管理器
                console.log('[Chat] 使用简化版处方管理器处理内容');
                processedContent = await window.simplePrescriptionManager.processContent(content, prescriptionId);
            } else if (window.prescriptionContentRenderer) {
                // 备用：使用原来的处方渲染器（兼容层）
                console.log('[Chat] 使用备用处方渲染器（兼容层）');
                processedContent = await window.prescriptionContentRenderer.renderContent(content, prescriptionId);

                // 保存原始内容用于支付后解锁
                if (prescriptionId && content) {
                    // 将原始内容保存到即将创建的消息元素中
                    setTimeout(() => {
                        const messages = document.querySelectorAll('.message.ai');
                        const lastMessage = messages[messages.length - 1];
                        if (lastMessage) {
                            const messageTextEl = lastMessage.querySelector('.message-text');
                            if (messageTextEl && !messageTextEl.getAttribute('data-original-content')) {
                                messageTextEl.setAttribute('data-original-content', content);
                                console.log('[Chat] 已保存原始内容用于支付后解锁');
                            }
                        }
                    }, 100);
                }
            } else {
                // 最终备用方案：直接格式化内容
                console.log('[Chat] 简化版处方管理器不存在，使用基础格式化');
                processedContent = formatMessage(content);
            }
        }

        // 如果有处方ID，保存到元素属性中
        if (prescriptionId) {
            messageDiv.setAttribute('data-prescription-id', prescriptionId);
        }

        // 获取医生头像
        const selectedDoctor = window.selectedDoctor;
        const doctors = window.doctors || {};
        const doctorAvatar = selectedDoctor && doctors[selectedDoctor] ? doctors[selectedDoctor].avatar : '🤖';

        messageDiv.innerHTML = `
            <div class="message-avatar">${sender === 'user' ? '👤' : doctorAvatar}</div>
            <div class="message-content">
                <div class="message-text">${processedContent}</div>
                <div class="message-time">${timeStr}</div>
                ${sender === 'ai' && showFeedback ? `
                    <div class="feedback-controls">
                        <div class="feedback-label">这个回答有帮助吗？</div>
                        <div class="rating-buttons">
                            <button class="rating-btn" onclick="rateFeedback(this, 5)">😊 很好</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 4)">👍 不错</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 3)">👌 还行</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 2)">👎 不好</button>
                            <button class="rating-btn" onclick="rateFeedback(this, 1)">😞 很差</button>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;

        // 自动朗读AI回复
        const autoSpeakCheckbox = document.getElementById('autoSpeak');
        if (sender === 'ai' && autoSpeakCheckbox && autoSpeakCheckbox.checked) {
            if (typeof window.speakText === 'function') {
                window.speakText(content);
            }
        }

        // 自动保存当前医生的对话历史
        if (selectedDoctor) {
            setTimeout(() => {
                if (typeof window.saveCurrentDoctorHistory === 'function') {
                    window.saveCurrentDoctorHistory();
                }
            }, 100);

            // 自动更新ChatGPT风格对话管理系统
            setTimeout(() => {
                if (typeof window.updateConversationListAfterMessage === 'function') {
                    window.updateConversationListAfterMessage();
                }
            }, 200);
        }
    }

    /**
     * 直接添加消息（不经过处方管理器处理）
     * 用于恢复历史会话时保持原始格式
     * @param {string} type - 消息类型 ('user' 或 'ai')
     * @param {string} senderName - 发送者名称
     * @param {string} htmlContent - HTML格式的消息内容
     */
    function addMessageDirectly(type, senderName, htmlContent) {
        const container = document.getElementById('messagesContainer');
        if (!container) {
            console.error('[Chat] 找不到messagesContainer');
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

        // 获取医生头像
        const selectedDoctor = window.selectedDoctor;
        const doctors = window.doctors || {};
        const doctorAvatar = selectedDoctor && doctors[selectedDoctor] ? doctors[selectedDoctor].avatar : '🤖';

        // 直接使用innerHTML渲染，保持HTML格式
        messageDiv.innerHTML = `
            <div class="message-avatar">${type === 'user' ? '👤' : doctorAvatar}</div>
            <div class="message-content">
                <div class="message-text">${htmlContent}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;

        container.appendChild(messageDiv);

        // 滚动到底部
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }

    // ========================================
    // 消息发送函数
    // ========================================

    /**
     * 发送消息到后端
     * 核心消息发送函数，处理与后端API的通信
     */
    async function sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        const selectedDoctor = window.selectedDoctor;

        if (!message || !selectedDoctor) {
            if (!selectedDoctor) {
                alert('请先选择一位医师');
            }
            return;
        }

        // 状态管理集成：分析用户消息并更新状态
        if (window.conversationStateManager) {
            const analysis = window.conversationStateManager.analyzeMessage(message, false);
            if (analysis.suggestedNextState) {
                window.conversationStateManager.setState(
                    analysis.suggestedNextState,
                    `用户消息分析: ${analysis.isEndingMessage ? '结束意图' : '继续问诊'}`
                );
            }
        }

        // 添加用户消息
        await addMessage('user', message);
        input.value = '';

        // 调整输入框高度
        if (typeof window.adjustTextareaHeight === 'function') {
            window.adjustTextareaHeight();
        }

        // 显示加载状态
        const sendBtn = document.getElementById('sendBtn');
        const loading = document.getElementById('loading');
        if (sendBtn) sendBtn.disabled = true;
        if (loading) loading.style.display = 'block';

        // 检查网络状态
        if (typeof window.checkNetworkStatus === 'function' && !window.checkNetworkStatus()) {
            if (sendBtn) sendBtn.disabled = false;
            return;
        }

        try {
            // 获取当前对话历史以维持上下文连续性
            let conversationHistory = [];
            if (typeof window.getCurrentConversationHistory === 'function') {
                conversationHistory = window.getCurrentConversationHistory();
            }

            // 获取认证头
            let headers = { 'Content-Type': 'application/json' };
            if (typeof window.getAuthHeaders === 'function') {
                headers = window.getAuthHeaders();
            }

            // 获取用户ID
            let userId = null;
            if (typeof window.getCurrentUserId === 'function') {
                userId = window.getCurrentUserId();
            }

            const response = await fetch('/api/consultation/chat', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    message: message,
                    conversation_id: window.currentConversationId,
                    selected_doctor: selectedDoctor,
                    patient_id: userId,
                    conversation_history: conversationHistory
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const responseData = await response.json();

            // 调试：打印完整API响应
            console.log('[Chat] PC端API完整响应:', responseData);

            // 处理新的API响应格式
            let aiReply;
            if (responseData.success && responseData.data && responseData.data.reply) {
                aiReply = responseData.data.reply;
                console.log('[Chat] PC端使用新格式，回复内容长度:', aiReply.length);
            } else if (responseData.reply) {
                aiReply = responseData.reply; // 兼容旧格式
                console.log('[Chat] PC端使用旧格式，回复内容长度:', aiReply.length);
            } else {
                console.error('[Chat] PC端API响应格式错误，响应结构:', Object.keys(responseData));
                throw new Error('API响应格式错误: 未找到reply字段');
            }

            // 医疗安全检查
            if (typeof window.checkMedicalSafety === 'function') {
                const aiWarnings = window.checkMedicalSafety(aiReply);
                if (aiWarnings.length > 0) {
                    if (typeof window.showMedicalWarnings === 'function') {
                        window.showMedicalWarnings(aiWarnings);
                    }
                    // 记录AI响应中的安全问题
                    aiWarnings.forEach(warning => {
                        if (typeof window.logSecurityEvent === 'function') {
                            window.logSecurityEvent(`ai_${warning.type}`, aiReply, warning);
                        }
                    });
                }
            }

            // 检查症状编造
            if (typeof window.detectSymptomFabrication === 'function') {
                window.detectSymptomFabrication(message, aiReply);
            }

            // 处方检测和支付状态分离管理
            let containsActualPrescription = false;
            if (typeof window.containsPrescription === 'function') {
                containsActualPrescription = window.containsPrescription(aiReply);
            }

            const isTemporaryAdvice = window.prescriptionContentRenderer ?
                window.prescriptionContentRenderer.containsPrescription(aiReply) === false : false;

            // 智能判断是否显示点评 - 所有AI回复都可以点评
            const shouldShowFeedback = true;

            // 处方相关状态管理
            let prescriptionId = responseData.data?.prescription_id || null;
            const isPaid = responseData.data?.is_paid || false;

            // 如果有真实处方ID，存储映射关系和状态
            if (prescriptionId && responseData.data?.contains_prescription) {
                window.lastRealPrescriptionId = prescription_id;
                window.lastPrescriptionData = responseData.data.prescription_data || {};
                window.lastPrescriptionData.prescription_id = prescription_id;

                console.log(`[Chat] 获取到真实处方ID: ${prescription_id}`);
                console.log(`[Chat] 处方数据:`, window.lastPrescriptionData);
            }

            console.log('[Chat] 前端处方状态分析:', {
                containsActualPrescription: containsActualPrescription,
                isTemporaryAdvice: isTemporaryAdvice,
                prescription_id: prescription_id,
                isPaid: isPaid,
                backendContainsPrescription: responseData.data?.contains_prescription
            });

            // 完整处方且未付费时需要支付
            const needsPayment = containsActualPrescription && !isTemporaryAdvice && !isPaid;

            // 状态管理集成：分析AI消息并更新状态
            if (window.conversationStateManager) {
                const analysis = window.conversationStateManager.analyzeMessage(aiReply, true);
                if (analysis.suggestedNextState) {
                    window.conversationStateManager.setState(
                        analysis.suggestedNextState,
                        `AI回复分析: ${analysis.containsPrescription ? '包含处方' : '普通回复'}`
                    );
                }
            }

            console.log('[Chat] PC端即将添加AI消息:', {
                aiReply: aiReply.substring(0, 100) + '...',
                shouldShowFeedback,
                containsActualPrescription,
                isTemporaryAdvice,
                needsPayment,
                isPaid,
                prescriptionId
            });

            // 根据处方状态决定显示模式
            await addMessage('ai', aiReply, shouldShowFeedback, isPaid, prescriptionId);

            // 记录诊断阶段
            if (shouldShowFeedback) {
                console.log('[Chat] 检测到处方内容，显示点评功能，处方ID:', prescriptionId, '支付状态:', isPaid);
            } else {
                console.log('[Chat] 普通对话，不显示点评');
            }

        } catch (error) {
            await addMessage('ai', `抱歉，服务暂时不可用：${error.message}`);
        } finally {
            if (sendBtn) sendBtn.disabled = false;
            if (loading) loading.style.display = 'none';
            input.focus();
        }
    }

    // ========================================
    // 暴露到全局window对象
    // ========================================

    // 消息清理
    window.clearAllMessages = clearAllMessages;

    // 症状相关
    window.extractSymptomsFromText = extractSymptomsFromText;
    window.getSymptomSynonyms = getSymptomSynonyms;
    window.isSymptomsRelated = isSymptomsRelated;

    // 消息格式化
    window.formatMessage = formatMessage;
    window.formatTCMPrescription = formatTCMPrescription;
    window.formatXMLPrescription = formatXMLPrescription;
    window.formatTextPrescription = formatTextPrescription;
    window.formatModernPrescription = formatModernPrescription;

    // 消息显示
    window.addMessage = addMessage;
    window.addMessageDirectly = addMessageDirectly;

    // 消息发送
    window.sendMessage = sendMessage;

    console.log('[Chat] smart_workflow_chat.js 模块加载完成');
    console.log('[Chat] 已暴露的函数:', [
        'clearAllMessages',
        'extractSymptomsFromText',
        'getSymptomSynonyms',
        'isSymptomsRelated',
        'formatMessage',
        'formatTCMPrescription',
        'formatXMLPrescription',
        'formatTextPrescription',
        'formatModernPrescription',
        'addMessage',
        'addMessageDirectly',
        'sendMessage'
    ]);

})();
