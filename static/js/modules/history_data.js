/**
 * 患者历史记录 - 数据处理层
 * 负责数据转换、清理、过滤和分组
 */

export class HistoryDataProcessor {
    constructor() {
        this.doctorInfo = {};
        this.allSessions = [];
        this.currentFilter = 'all';

        // 医生emoji映射
        this.doctorEmojiMap = {
            'jin_daifu': '👨‍⚕️',
            'zhang_zhongjing': '⚕️',
            'ye_tianshi': '🌿',
            'li_dongyuan': '🔬',
            'liu_duzhou': '📖',
            'zheng_qin_an': '🔥'
        };
    }

    /**
     * 设置医生信息
     * @param {Array} doctors - 医生列表
     */
    setDoctorInfo(doctors) {
        this.doctorInfo = {};

        doctors.forEach(doctor => {
            if (doctor.doctor_code) {
                this.doctorInfo[doctor.doctor_code] = {
                    name: doctor.name,
                    emoji: this.doctorEmojiMap[doctor.doctor_code] || '👨‍⚕️',
                    description: this.extractDescription(doctor.specialties)
                };
            }
        });

        console.log('✅ 医生信息已更新:', Object.keys(this.doctorInfo));
    }

    /**
     * 提取医生简介
     */
    extractDescription(specialties) {
        if (Array.isArray(specialties)) {
            return specialties.slice(0, 2).join('、');
        } else if (typeof specialties === 'string') {
            try {
                const arr = JSON.parse(specialties);
                return Array.isArray(arr) ? arr.slice(0, 2).join('、') : '中医诊疗';
            } catch {
                return '中医诊疗';
            }
        }
        return '中医诊疗';
    }

    /**
     * 获取医生emoji
     */
    getEmojiForDoctor(doctorCode) {
        return this.doctorEmojiMap[doctorCode] || '👨‍⚕️';
    }

    /**
     * 处理会话数据
     * @param {Object} rawData - 原始API数据
     * @returns {Array} 处理后的会话列表
     */
    processSessionData(rawData) {
        if (!rawData || !rawData.sessions) {
            return [];
        }

        this.allSessions = rawData.sessions.map((session, index) => ({
            ...session,
            session_count: index + 1,
            doctor_emoji: this.doctorEmojiMap[session.doctor_name] || '👨‍⚕️'
        }));

        return this.allSessions;
    }

    /**
     * 过滤会话
     * @param {string} filter - 过滤类型
     * @returns {Array} 过滤后的会话列表
     */
    filterSessions(filter) {
        this.currentFilter = filter;

        if (filter === 'all') {
            return this.allSessions;
        }

        if (filter === 'recent') {
            return this.allSessions.filter(session =>
                this.isRecentSession(session.created_at)
            );
        }

        // 按医生过滤
        return this.allSessions.filter(session =>
            session.doctor_name === filter
        );
    }

    /**
     * 判断是否为最近7天的会话
     */
    isRecentSession(dateString) {
        const sessionDate = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - sessionDate);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays <= 7;
    }

    /**
     * 按医生分组会话
     * @param {Array} sessions - 会话列表
     * @returns {Object} 分组后的对象 {doctor_name: [sessions]}
     */
    groupByDoctor(sessions) {
        const grouped = {};

        sessions.forEach(session => {
            const doctorName = session.doctor_name || '未知医生';
            if (!grouped[doctorName]) {
                grouped[doctorName] = [];
            }
            grouped[doctorName].push(session);
        });

        return grouped;
    }

    /**
     * 清理HTML标签
     * @param {string} html - 包含HTML的字符串
     * @returns {string} 纯文本
     */
    cleanHTML(html) {
        if (!html) return '';

        // 如果包含prescription-locked，返回提示文本
        if (html.includes('prescription-locked')) {
            return '【此问诊包含处方信息，需在智能问诊页面查看完整内容】';
        }

        // 创建临时DOM元素来提取文本
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        return tempDiv.textContent || tempDiv.innerText || '';
    }

    /**
     * 格式化日期
     * @param {string} dateString - ISO日期字符串
     * @returns {string} 格式化后的日期
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * 计算统计数据
     * @param {Array} sessions - 会话列表
     * @returns {Object} 统计数据
     */
    calculateStats(sessions) {
        const uniqueDoctors = new Set(sessions.map(s => s.doctor_name));
        const firstSessionDate = sessions.length > 0
            ? new Date(sessions[sessions.length - 1].created_at)
            : new Date();
        const daysSinceFirst = Math.ceil(
            (new Date() - firstSessionDate) / (1000 * 60 * 60 * 24)
        );

        return {
            totalSessions: sessions.length,
            doctorCount: uniqueDoctors.size,
            usageDays: daysSinceFirst
        };
    }

    /**
     * 获取有历史记录的医生列表
     * @returns {Array} 医生代码列表
     */
    getDoctorsWithData() {
        return [...new Set(this.allSessions.map(session => session.doctor_name))];
    }

    /**
     * 清理对话详情数据
     * @param {Object} detail - 原始详情数据
     * @returns {Object} 清理后的详情
     */
    cleanConversationDetail(detail) {
        return {
            ...detail,
            conversation_history: (detail.conversation_history || []).map(conv => ({
                ...conv,
                ai_response: this.cleanHTML(conv.ai_response || '')
            }))
        };
    }
}
