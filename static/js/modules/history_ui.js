/**
 * 患者历史记录 - UI渲染层
 * 负责所有DOM操作和界面渲染
 */

export class HistoryUI {
    constructor(containerEl) {
        this.container = containerEl;
    }

    /**
     * 渲染会话列表
     * @param {Object} sessionsByDoctor - 按医生分组的会话
     * @param {Object} dataProcessor - 数据处理器实例
     */
    renderSessionList(sessionsByDoctor, dataProcessor) {
        let html = '';

        for (const [doctorName, sessions] of Object.entries(sessionsByDoctor)) {
            html += this.renderDoctorGroup(doctorName, sessions, dataProcessor);
        }

        this.container.innerHTML = html || this.renderEmptyState();
    }

    /**
     * 渲染医生分组
     */
    renderDoctorGroup(doctorName, sessions, dataProcessor) {
        const emoji = dataProcessor.getEmojiForDoctor(doctorName);
        const doctorDisplayName = dataProcessor.doctorInfo[doctorName]?.name || doctorName;

        return `
            <div class="doctor-group expanded">
                <div class="doctor-header" onclick="toggleDoctorGroup(this.parentElement)">
                    <div class="doctor-info">
                        <div class="doctor-avatar">${emoji}</div>
                        <div class="doctor-details">
                            <div class="doctor-name">${doctorDisplayName}</div>
                            <div class="session-count">${sessions.length}次问诊</div>
                        </div>
                    </div>
                    <div class="expand-icon">▼</div>
                </div>
                <div class="sessions-list">
                    ${sessions.map(s => this.renderSessionItem(s, dataProcessor)).join('')}
                </div>
            </div>
        `;
    }

    /**
     * 渲染单个会话项
     */
    renderSessionItem(session, dataProcessor) {
        const recentClass = dataProcessor.isRecentSession(session.created_at) ? 'recent' : '';
        const statusClass = session.status === 'completed' ? 'completed' : 'active';
        const statusText = session.status === 'completed' ? '已完成' : '进行中';

        // 🔍 调试日志：检查session_id
        console.log('🔍 renderSessionItem - session数据:', {
            session_id: session.session_id,
            session_count: session.session_count,
            chief_complaint: session.chief_complaint
        });

        // 🛡️ 安全检查：如果session_id为空，禁用详情和恢复按钮
        const hasValidSessionId = session.session_id && session.session_id.trim() !== '';
        const detailButton = hasValidSessionId
            ? `<button class="btn-detail" onclick="showConversationDetail('${session.session_id}')" title="查看详情">📋 详情</button>`
            : `<button class="btn-detail" disabled title="数据异常，无法查看" style="opacity: 0.5; cursor: not-allowed;">📋 详情</button>`;
        const restoreButton = hasValidSessionId
            ? `<button class="btn-detail" onclick="viewSession('${session.session_id}')" title="恢复对话" style="margin-left: 5px;">💬 恢复</button>`
            : `<button class="btn-detail" disabled title="数据异常，无法恢复" style="margin-left: 5px; opacity: 0.5; cursor: not-allowed;">💬 恢复</button>`;

        return `
            <div class="session-item ${recentClass}">
                <div class="session-header">
                    <div class="session-title">第${session.session_count}次问诊</div>
                    <div class="session-date">${dataProcessor.formatDate(session.created_at)}</div>
                </div>
                <div class="session-complaint">
                    主诉：${session.chief_complaint || '未记录'}
                </div>
                <div class="session-footer">
                    <div class="conversation-count">${session.total_conversations || 0}轮对话</div>
                    <div class="session-actions">
                        ${detailButton}
                        ${restoreButton}
                        <div class="session-status ${statusClass}">
                            ${statusText}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 渲染空状态
     */
    renderEmptyState() {
        return `
            <div class="empty-state">
                <div class="icon">🏥</div>
                <h3>还没有问诊记录</h3>
                <p>开始您的第一次AI中医问诊，建立专属健康档案</p>
                <button class="btn-primary" onclick="startNewConsultation()">
                    💬 开始问诊
                </button>
            </div>
        `;
    }

    /**
     * 渲染错误状态
     */
    renderError(message) {
        this.container.innerHTML = `
            <div class="error-state">
                <div class="icon">⚠️</div>
                <h3>加载失败</h3>
                <p>${message}</p>
                <button class="btn-primary" onclick="location.reload()">
                    🔄 重新加载
                </button>
            </div>
        `;
    }

    /**
     * 渲染加载状态
     */
    renderLoading(message = '正在加载您的问诊历史...') {
        this.container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * 更新统计信息
     */
    updateStats(stats) {
        const totalEl = document.getElementById('totalSessions');
        const doctorEl = document.getElementById('doctorCount');
        const daysEl = document.getElementById('usageDays');

        if (totalEl) totalEl.textContent = stats.totalSessions;
        if (doctorEl) doctorEl.textContent = stats.doctorCount;
        if (daysEl) daysEl.textContent = stats.usageDays;
    }

    /**
     * 显示对话详情弹窗
     */
    showConversationDetailModal(detail, dataProcessor) {
        const doctorName = dataProcessor.doctorInfo[detail.doctor_name]?.name || detail.doctor_name;

        const modal = this.createModal(`
            <div class="modal-content" style="max-width: 900px; max-height: 90vh;">
                <div class="modal-header">
                    <h2>📋 问诊详情 - ${doctorName}</h2>
                    <span class="close" onclick="this.closest('.modal').remove()">&times;</span>
                </div>
                <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                    ${this.renderDetailContent(detail, dataProcessor)}
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal').remove()">关闭</button>
                    <button class="btn-primary" onclick="viewSession('${detail.session_id}')">恢复对话</button>
                </div>
            </div>
        `);

        document.body.appendChild(modal);
    }

    /**
     * 渲染详情内容
     */
    renderDetailContent(detail, dataProcessor) {
        const conversationHistory = (detail.conversation_history || []).map((conv, index) => {
            const cleanResponse = dataProcessor.cleanHTML(conv.ai_response || '');

            return `
                <div class="conversation-turn">
                    <div class="patient-message">
                        <strong>患者 (第${index + 1}轮):</strong>
                        <p>${conv.patient_query || '未记录'}</p>
                    </div>
                    <div class="doctor-message">
                        <strong>${dataProcessor.doctorInfo[detail.doctor_name]?.name || '医生'}:</strong>
                        <p style="white-space: pre-wrap;">${cleanResponse}</p>
                    </div>
                    ${conv.timestamp ? `<div class="turn-timestamp">${dataProcessor.formatDate(conv.timestamp)}</div>` : ''}
                </div>
            `;
        }).join('') || '<p>暂无详细对话记录</p>';

        return `
            <div class="detail-section">
                <h3>📊 基本信息</h3>
                <div class="detail-grid">
                    <div><strong>开始时间:</strong> ${dataProcessor.formatDate(detail.created_at)}</div>
                    <div><strong>问诊状态:</strong> ${detail.status === 'completed' ? '✅ 已完成' : '⏳ 进行中'}</div>
                </div>
            </div>
            <div class="detail-section">
                <h3>💬 主诉</h3>
                <p>${detail.chief_complaint || '未记录'}</p>
            </div>
            <div class="detail-section">
                <h3>🩺 诊断分析</h3>
                <p>${detail.diagnosis_summary || '暂无诊断信息'}</p>
            </div>
            <div class="detail-section">
                <h3>📝 对话记录</h3>
                ${conversationHistory}
            </div>
        `;
    }

    /**
     * 创建模态框
     */
    createModal(content) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        modal.innerHTML = content;

        // 点击背景关闭
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        };

        return modal;
    }

    /**
     * 创建加载模态框
     */
    createLoadingModal(message) {
        return this.createModal(`
            <div class="modal-content" style="max-width: 400px; text-align: center;">
                <div class="modal-body">
                    <div class="spinner" style="margin: 20px auto;"></div>
                    <p>${message}</p>
                </div>
            </div>
        `);
    }

    /**
     * 更新医生筛选标签
     */
    updateDoctorTabs(doctorsWithData, dataProcessor) {
        const filterTabs = document.querySelector('.filter-tabs');
        if (!filterTabs) return;

        // 保留固定标签
        const fixedTabs = `
            <button class="filter-tab active" onclick="filterSessions('all')">全部</button>
            <button class="filter-tab" onclick="filterSessions('recent')">最近7天</button>
        `;

        // 添加医生标签(只显示有数据且活跃的医生)
        const doctorTabs = doctorsWithData
            .filter(doctorCode => dataProcessor.doctorInfo[doctorCode])
            .map(doctorCode => {
                const info = dataProcessor.doctorInfo[doctorCode];
                return `<button class="filter-tab" onclick="filterSessions('${doctorCode}')">${info.name}</button>`;
            })
            .join('');

        filterTabs.innerHTML = fixedTabs + doctorTabs;
    }
}
