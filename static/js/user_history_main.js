/**
 * 患者历史记录 - 主入口文件
 * 整合API、数据处理和UI渲染层
 */

import { HistoryAPI } from './modules/history_api.js';
import { HistoryDataProcessor } from './modules/history_data.js';
import { HistoryUI } from './modules/history_ui.js';

class UserHistoryApp {
    constructor() {
        this.api = new HistoryAPI();
        this.dataProcessor = new HistoryDataProcessor();
        this.ui = new HistoryUI(document.getElementById('historyContent'));

        this.currentUserId = null;
    }

    /**
     * 初始化应用
     */
    async init() {
        console.log('🚀 用户历史记录应用初始化...');

        try {
            // 1. 加载医生信息
            await this.loadDoctorInfo();

            // 2. 获取当前用户
            await this.loadCurrentUser();

            // 3. 加载会话列表
            await this.loadSessions();

            // 4. 绑定全局事件
            this.bindGlobalEvents();

            console.log('✅ 应用初始化完成');
        } catch (error) {
            console.error('❌ 应用初始化失败:', error);
            this.ui.renderError('加载失败，请刷新页面重试');
        }
    }

    /**
     * 加载医生信息
     */
    async loadDoctorInfo() {
        try {
            const data = await this.api.loadDoctorInfo();
            if (data.success && data.doctors) {
                this.dataProcessor.setDoctorInfo(data.doctors);
            }
        } catch (error) {
            console.warn('⚠️ 加载医生信息失败，使用默认配置');
        }
    }

    /**
     * 加载当前用户
     */
    async loadCurrentUser() {
        try {
            console.log('🔄 loadCurrentUser: 开始加载用户信息...');
            const user = await this.api.getCurrentUser();
            console.log('🔄 loadCurrentUser: API返回用户数据:', user);

            if (user) {
                // 🔧 v4.2修复：与问诊页面保持一致，优先使用id字段
                // 问诊页面使用 id (usr_xxx) 作为患者ID保存到数据库
                this.currentUserId = user.id || user.user_id || user.global_user_id || user.username;
                console.log('✅ 当前用户ID:', this.currentUserId);

                // 🔑 关键修复：确保调用updateUserInfo
                console.log('🔄 loadCurrentUser: 调用updateUserInfo更新UI...');
                this.updateUserInfo(user);
                console.log('✅ loadCurrentUser: UI更新完成');
            } else {
                // 未登录，使用设备ID
                this.currentUserId = localStorage.getItem('device_id') || 'guest';
                console.warn('⚠️ 无用户数据，使用设备ID:', this.currentUserId);
            }
        } catch (error) {
            console.error('❌ 获取用户信息失败:', error);
            this.currentUserId = localStorage.getItem('device_id') || 'guest';
        }
    }

    /**
     * 加载会话列表
     */
    async loadSessions() {
        console.log('🔄 loadSessions: 开始加载会话列表...');
        this.ui.renderLoading();

        try {
            console.log('🔄 loadSessions: 调用 getSessions API, userId =', this.currentUserId);
            const data = await this.api.getSessions(this.currentUserId);
            console.log('✅ loadSessions: API返回数据', data);

            if (!data || !data.sessions || data.sessions.length === 0) {
                console.log('⚠️ loadSessions: 无会话数据，显示空状态');
                this.ui.renderEmptyState();
                this.ui.updateStats({ totalSessions: 0, doctorCount: 0, usageDays: 0 });
                return;
            }

            // 处理数据
            console.log('🔄 loadSessions: 处理会话数据...');
            const sessions = this.dataProcessor.processSessionData(data);
            console.log('✅ loadSessions: 数据处理完成，会话数:', sessions.length);

            // 计算统计
            console.log('🔄 loadSessions: 计算统计信息...');
            const stats = this.dataProcessor.calculateStats(sessions);
            console.log('✅ loadSessions: 统计信息:', stats);
            this.ui.updateStats(stats);

            // 渲染列表
            console.log('🔄 loadSessions: 渲染会话列表...');
            this.renderSessionHistory();
            console.log('✅ loadSessions: 列表渲染完成');

            // 更新医生标签
            console.log('🔄 loadSessions: 更新医生标签...');
            const doctorsWithData = this.dataProcessor.getDoctorsWithData();
            console.log('✅ loadSessions: 医生列表:', doctorsWithData);
            this.ui.updateDoctorTabs(doctorsWithData, this.dataProcessor);

            console.log('✅ ===== loadSessions 完成 =====');

        } catch (error) {
            console.error('❌ 加载会话失败:', error);
            console.error('❌ 错误堆栈:', error.stack);
            this.ui.renderError(`加载失败: ${error.message}`);
        }
    }

    /**
     * 渲染会话历史
     */
    renderSessionHistory() {
        const filtered = this.dataProcessor.filterSessions(this.dataProcessor.currentFilter);
        const grouped = this.dataProcessor.groupByDoctor(filtered);
        this.ui.renderSessionList(grouped, this.dataProcessor);
    }

    /**
     * 更新用户信息UI
     */
    updateUserInfo(user) {
        const avatarEl = document.getElementById('userAvatar');
        const nameEl = document.getElementById('userName');
        const typeEl = document.getElementById('userType');

        // 🔧 修复：优先使用display_name显示用户名称，而不是username（登录名）
        // username是登录凭据（如jingdaifu），display_name是显示名称（如金大夫）
        const displayName = user.display_name || user.username || user.phone_number || user.phone || user.name || '游客用户';
        const avatarText = displayName.charAt(0).toUpperCase();

        console.log('🔍 updateUserInfo - 用户数据:', {
            username: user.username,
            display_name: user.display_name,
            name: user.name,
            phone_number: user.phone_number,
            phone: user.phone,
            最终显示名: displayName
        });

        if (avatarEl) {
            avatarEl.textContent = avatarText;
            console.log('✅ 更新头像:', avatarText);
        }
        if (nameEl) {
            nameEl.textContent = displayName;
            console.log('✅ 更新用户名:', displayName);
        }
        if (typeEl) {
            const userType = (user.phone_number || user.phone) ? '已绑定手机' : '设备用户';
            typeEl.textContent = userType;
            console.log('✅ 更新用户类型:', userType);
        }
    }

    /**
     * 绑定全局事件
     */
    bindGlobalEvents() {
        // 暴露全局函数供HTML调用
        window.filterSessions = this.filterSessions.bind(this);
        window.toggleDoctorGroup = this.toggleDoctorGroup.bind(this);
        window.showConversationDetail = this.showConversationDetail.bind(this);
        window.viewSession = this.viewSession.bind(this);
        window.startNewConsultation = this.startNewConsultation.bind(this);
        window.exportHistory = this.exportHistory.bind(this);
        window.clearHistory = this.clearHistory.bind(this);
        window.upgradeAccount = this.upgradeAccount.bind(this);
    }

    /**
     * 过滤会话
     */
    filterSessions(filter) {
        this.dataProcessor.currentFilter = filter;

        // 更新按钮状态
        document.querySelectorAll('.filter-tab').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');

        // 重新渲染
        this.renderSessionHistory();
    }

    /**
     * 切换医生分组展开/折叠
     */
    toggleDoctorGroup(element) {
        element.classList.toggle('expanded');
    }

    /**
     * 显示对话详情
     */
    async showConversationDetail(sessionId) {
        console.log('🔍 showConversationDetail - 接收到的sessionId:', sessionId, '类型:', typeof sessionId);

        // 🛡️ 安全检查：验证sessionId有效性
        if (!sessionId || sessionId.trim() === '') {
            console.error('❌ sessionId无效:', sessionId);
            alert('数据异常：无法加载对话详情（会话ID为空）');
            return;
        }

        const loadingModal = this.ui.createLoadingModal('正在加载对话详情...');
        document.body.appendChild(loadingModal);

        try {
            console.log('🔍 准备调用getConversationDetail，sessionId:', sessionId);
            const detail = await this.api.getConversationDetail(sessionId);
            loadingModal.remove();

            // 清理HTML标签
            const cleanedDetail = this.dataProcessor.cleanConversationDetail(detail);

            // 显示详情弹窗
            this.ui.showConversationDetailModal(cleanedDetail, this.dataProcessor);

        } catch (error) {
            console.error('❌ 获取对话详情失败:', error);
            loadingModal.remove();
            alert('获取对话详情失败，请重试');
        }
    }

    /**
     * 恢复对话
     */
    viewSession(sessionId) {
        // 🛡️ 安全检查：验证sessionId有效性
        if (!sessionId || sessionId.trim() === '') {
            console.error('❌ sessionId无效:', sessionId);
            alert('数据异常：无法恢复对话（会话ID为空）');
            return;
        }

        const restoreUrl = `/smart?restore_session=${encodeURIComponent(sessionId)}`;

        if (confirm('是否在新窗口中查看完整的问诊对话（包括已解锁的处方内容）？\n\n点击"确定"新窗口打开，点击"取消"当前窗口跳转')) {
            window.open(restoreUrl, '_blank');
        } else {
            window.location.href = restoreUrl;
        }
    }

    /**
     * 开始新问诊
     */
    startNewConsultation() {
        window.location.href = '/smart';
    }

    /**
     * 导出历史记录
     */
    async exportHistory() {
        try {
            const blob = await this.api.exportHistory();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `问诊历史_${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            alert('导出失败：' + error.message);
        }
    }

    /**
     * 清空历史记录
     */
    async clearHistory() {
        if (!confirm('确定要清空所有问诊历史吗？此操作不可恢复！')) {
            return;
        }

        try {
            await this.api.clearHistory();
            alert('历史记录已清空');
            location.reload();
        } catch (error) {
            alert('清空失败：' + error.message);
        }
    }

    /**
     * 升级账户
     */
    upgradeAccount() {
        window.location.href = '/phone-binding';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    const app = new UserHistoryApp();
    app.init();
});
