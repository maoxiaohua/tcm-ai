/**
 * 智能问诊工作流 - 病历记录查看模块
 *
 * 本模块负责管理用户的病历记录展示和操作，包括：
 * - 病历记录模态框的创建和显示
 * - 记录过滤（全部、问诊、处方）
 * - 记录详情查看
 * - 处方复诊功能
 *
 * @module smart_workflow_records
 * @version 2.1
 */

(function() {
    'use strict';

    // ==================== 病历记录模态框 ====================

    /**
     * 显示病历记录模态框
     */
    async function showMedicalRecordsModal() {
        try {
            const getAuthHeaders = window.getAuthHeaders || function() { return { 'Content-Type': 'application/json' }; };

            // 获取用户的病历记录
            const response = await fetch('/api/medical-records/list', {
                headers: getAuthHeaders()
            });

            const result = await response.json();

            if (!result.success) {
                if (typeof showMessage === 'function') {
                    showMessage('获取病历记录失败', 'error');
                }
                return;
            }

            createMedicalRecordsModal(result.data || []);

        } catch (error) {
            console.error('获取病历记录失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 创建病历记录模态框
     * @param {Array} records - 病历记录数组
     */
    function createMedicalRecordsModal(records) {
        // 检查是否已存在模态框
        let modal = document.getElementById('medicalRecordsModal');
        if (modal) {
            modal.remove();
        }

        modal = document.createElement('div');
        modal.id = 'medicalRecordsModal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1004;
        `;

        modal.innerHTML = `
            <div style="background: white; border-radius: 16px; max-width: 800px; width: 90%; max-height: 80vh; display: flex; flex-direction: column;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 24px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 600;">我的病历记录</h3>
                    <button onclick="hideMedicalRecordsModal()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer; padding: 0; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">x</button>
                </div>
                <div style="padding: 24px; flex: 1; overflow-y: auto;">
                    <div style="display: flex; gap: 12px; margin-bottom: 20px;">
                        <button onclick="showAllRecords()" id="allRecordsBtn" style="padding: 8px 16px; border: 2px solid #3b82f6; background: #3b82f6; color: white; border-radius: 20px; cursor: pointer; font-size: 13px;">
                            全部记录
                        </button>
                        <button onclick="showConsultationRecords()" id="consultationBtn" style="padding: 8px 16px; border: 2px solid #3b82f6; background: white; color: #3b82f6; border-radius: 20px; cursor: pointer; font-size: 13px;">
                            问诊记录
                        </button>
                        <button onclick="showPrescriptionRecords()" id="prescriptionBtn" style="padding: 8px 16px; border: 2px solid #3b82f6; background: white; color: #3b82f6; border-radius: 20px; cursor: pointer; font-size: 13px;">
                            处方记录
                        </button>
                    </div>
                    <div id="recordsContainer">
                        ${records.length > 0 ? generateRecordsHTML(records) : '<div style="text-align: center; color: #6b7280; padding: 40px;">暂无病历记录</div>'}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    /**
     * 生成病历记录HTML
     * @param {Array} records - 病历记录数组
     * @returns {string} HTML字符串
     */
    function generateRecordsHTML(records) {
        return records.map(record => `
            <div style="border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 16px; background: white;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <h4 style="margin: 0; color: #1f2937; font-size: 16px;">${record.doctor_name || '医生'} - ${record.type === 'consultation' ? '问诊记录' : '处方记录'}</h4>
                        <p style="margin: 4px 0 0 0; color: #6b7280; font-size: 13px;">${new Date(record.created_at).toLocaleString()}</p>
                    </div>
                    <span style="padding: 4px 12px; background: ${record.status === 'completed' ? '#dcfce7' : '#fef3c7'}; color: ${record.status === 'completed' ? '#166534' : '#92400e'}; border-radius: 12px; font-size: 12px;">
                        ${record.status === 'completed' ? '已完成' : '进行中'}
                    </span>
                </div>

                ${record.symptoms ? `
                    <div style="margin-bottom: 12px;">
                        <strong style="color: #374151; font-size: 14px;">主要症状：</strong>
                        <span style="color: #6b7280; font-size: 14px;">${record.symptoms}</span>
                    </div>
                ` : ''}

                ${record.diagnosis ? `
                    <div style="margin-bottom: 12px;">
                        <strong style="color: #374151; font-size: 14px;">诊断结果：</strong>
                        <span style="color: #6b7280; font-size: 14px;">${record.diagnosis}</span>
                    </div>
                ` : ''}

                ${record.prescription ? `
                    <div style="margin-bottom: 12px;">
                        <strong style="color: #374151; font-size: 14px;">处方内容：</strong>
                        <div style="background: #f8fafc; border-radius: 6px; padding: 12px; margin-top: 8px; font-family: monospace; font-size: 13px; white-space: pre-wrap; max-height: 100px; overflow-y: auto;">${record.prescription}</div>
                    </div>
                ` : ''}

                ${record.payment_amount ? `
                    <div style="margin-bottom: 12px;">
                        <strong style="color: #374151; font-size: 14px;">费用：</strong>
                        <span style="color: #ef4444; font-size: 14px; font-weight: 500;">¥ ${record.payment_amount}</span>
                    </div>
                ` : ''}

                <div style="display: flex; gap: 8px; margin-top: 16px;">
                    <button onclick="viewRecordDetail('${record.id}')" style="padding: 6px 12px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 6px; font-size: 12px; cursor: pointer; color: #374151;">
                        查看详情
                    </button>
                    ${record.type === 'prescription' && record.status === 'completed' ? `
                        <button onclick="reorderPrescription('${record.id}')" style="padding: 6px 12px; background: #dbeafe; border: 1px solid #3b82f6; border-radius: 6px; font-size: 12px; cursor: pointer; color: #3b82f6;">
                            重新购买
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * 隐藏病历记录模态框
     */
    function hideMedicalRecordsModal() {
        const modal = document.getElementById('medicalRecordsModal');
        if (modal) {
            modal.remove();
        }
    }

    // ==================== 记录过滤功能 ====================

    /**
     * 显示所有记录
     */
    async function showAllRecords() {
        updateRecordFilter('all');
        const getAuthHeaders = window.getAuthHeaders || function() { return { 'Content-Type': 'application/json' }; };
        const response = await fetch('/api/medical-records/list', {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        updateRecordsContainer(result.data || []);
    }

    /**
     * 显示问诊记录
     */
    async function showConsultationRecords() {
        updateRecordFilter('consultation');
        const getAuthHeaders = window.getAuthHeaders || function() { return { 'Content-Type': 'application/json' }; };
        const response = await fetch('/api/medical-records/list?type=consultation', {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        updateRecordsContainer(result.data || []);
    }

    /**
     * 显示处方记录
     */
    async function showPrescriptionRecords() {
        updateRecordFilter('prescription');
        const getAuthHeaders = window.getAuthHeaders || function() { return { 'Content-Type': 'application/json' }; };
        const response = await fetch('/api/medical-records/list?type=prescription', {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        updateRecordsContainer(result.data || []);
    }

    /**
     * 更新记录过滤器样式
     * @param {string} type - 过滤类型 ('all', 'consultation', 'prescription')
     */
    function updateRecordFilter(type) {
        const buttons = ['allRecordsBtn', 'consultationBtn', 'prescriptionBtn'];
        buttons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                if ((type === 'all' && btnId === 'allRecordsBtn') ||
                    (type === 'consultation' && btnId === 'consultationBtn') ||
                    (type === 'prescription' && btnId === 'prescriptionBtn')) {
                    btn.style.background = '#3b82f6';
                    btn.style.color = 'white';
                } else {
                    btn.style.background = 'white';
                    btn.style.color = '#3b82f6';
                }
            }
        });
    }

    /**
     * 更新记录容器内容
     * @param {Array} records - 病历记录数组
     */
    function updateRecordsContainer(records) {
        const container = document.getElementById('recordsContainer');
        if (container) {
            container.innerHTML = records.length > 0 ? generateRecordsHTML(records) : '<div style="text-align: center; color: #6b7280; padding: 40px;">暂无相关记录</div>';
        }
    }

    // ==================== 记录详情功能 ====================

    /**
     * 查看记录详情
     * @param {string} recordId - 记录ID
     */
    async function viewRecordDetail(recordId) {
        try {
            const getAuthHeaders = window.getAuthHeaders || function() { return { 'Content-Type': 'application/json' }; };
            const response = await fetch(`/api/user/conversation/${recordId}`, {
                headers: getAuthHeaders()
            });

            if (response.ok) {
                const record = await response.json();
                showRecordDetailModal(record);
            } else {
                if (typeof showMessage === 'function') {
                    showMessage('获取记录详情失败', 'error');
                }
            }
        } catch (error) {
            console.error('获取记录详情失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 显示记录详情模态框
     * @param {Object} record - 记录对象
     */
    function showRecordDetailModal(record) {
        // 检查是否已存在模态框
        let detailModal = document.getElementById('recordDetailModal');
        if (detailModal) {
            detailModal.remove();
        }

        const getDoctorDisplayName = window.getDoctorDisplayName || function(key) { return key || '医生'; };
        const doctorName = getDoctorDisplayName(record.doctor_name);
        const visitDate = new Date(record.created_at).toLocaleString('zh-CN');

        detailModal = document.createElement('div');
        detailModal.id = 'recordDetailModal';
        detailModal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1005;
        `;

        detailModal.innerHTML = `
            <div style="background: white; border-radius: 16px; max-width: 700px; width: 90%; max-height: 80vh; display: flex; flex-direction: column;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 24px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; font-size: 18px; font-weight: 600;">对话详情 - ${doctorName}</h3>
                    <button onclick="closeRecordDetailModal()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer; padding: 0; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">x</button>
                </div>
                <div style="padding: 24px; flex: 1; overflow-y: auto;">
                    <div style="background: #f8f9ff; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                        <h4 style="margin: 0 0 12px 0; color: #667eea; font-size: 16px;">基本信息</h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div><strong>就诊时间:</strong> ${visitDate}</div>
                            <div><strong>就诊次数:</strong> 第${record.session_count || 1}次</div>
                            <div><strong>主诉:</strong> ${record.chief_complaint || '未记录'}</div>
                            <div><strong>对话轮数:</strong> ${record.total_conversations || 0}轮</div>
                        </div>
                    </div>

                    ${record.diagnosis_summary ? `
                        <div style="background: #f0f9ff; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                            <h4 style="margin: 0 0 12px 0; color: #3b82f6; font-size: 16px;">诊疗记录</h4>
                            <div style="line-height: 1.6; color: #374151;">
                                <p style="margin-bottom: 12px;"><strong>诊断摘要:</strong> ${record.diagnosis_summary}</p>
                            </div>
                        </div>
                    ` : ''}

                    ${record.prescription_given && record.prescription_given !== '未开方' ? `
                        <div style="background: #f0f9ff; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                            <h4 style="margin: 0 0 12px 0; color: #10b981; font-size: 16px;">处方内容</h4>
                            <div style="background: white; border-radius: 8px; padding: 16px; font-family: monospace; font-size: 14px; line-height: 1.5; white-space: pre-wrap; max-height: 200px; overflow-y: auto; border: 1px solid #d1d5db;">
${record.prescription_given}
                            </div>
                        </div>
                    ` : ''}

                    <div style="background: #fefce8; border-radius: 12px; padding: 20px;">
                        <h4 style="margin: 0 0 12px 0; color: #eab308; font-size: 16px;">对话状态</h4>
                        <div style="display: flex; align-items: center;">
                            <span style="padding: 6px 16px; background: ${record.session_status === 'completed' ? '#dcfce7' : '#fef3c7'}; color: ${record.session_status === 'completed' ? '#166534' : '#92400e'}; border-radius: 20px; font-size: 14px; font-weight: 500;">
                                ${record.session_status === 'completed' ? '已完成' : '进行中'}
                            </span>
                        </div>
                    </div>
                </div>
                <div style="padding: 20px 24px; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 12px;">
                    <button onclick="closeRecordDetailModal()" style="padding: 10px 20px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 8px; cursor: pointer; color: #374151;">关闭</button>
                    <button onclick="exportConversation('${record.session_id}')" style="padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer;">导出病历</button>
                </div>
            </div>
        `;

        document.body.appendChild(detailModal);
    }

    /**
     * 关闭记录详情模态框
     */
    function closeRecordDetailModal() {
        const modal = document.getElementById('recordDetailModal');
        if (modal) {
            modal.remove();
        }
    }

    // ==================== 复诊功能 ====================

    /**
     * 重新购买处方（复诊）
     * @param {string} recordId - 记录ID
     */
    async function reorderPrescription(recordId) {
        try {
            const getAuthHeaders = window.getAuthHeaders || function() { return { 'Content-Type': 'application/json' }; };
            const response = await fetch(`/api/prescription/reorder/${recordId}`, {
                method: 'POST',
                headers: getAuthHeaders()
            });

            const result = await response.json();

            if (result.success && result.data) {
                hideMedicalRecordsModal();
                if (typeof showPaymentModal === 'function') {
                    showPaymentModal(result.data.prescription_id, result.data.amount);
                }
            } else {
                if (typeof showMessage === 'function') {
                    showMessage(result.message || '重新购买失败', 'error');
                }
            }
        } catch (error) {
            console.error('重新购买失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('服务暂时不可用', 'error');
            }
        }
    }

    // ==================== 暴露到全局 ====================

    // 模态框控制
    window.showMedicalRecordsModal = showMedicalRecordsModal;
    window.createMedicalRecordsModal = createMedicalRecordsModal;
    window.hideMedicalRecordsModal = hideMedicalRecordsModal;

    // 记录生成和过滤
    window.generateRecordsHTML = generateRecordsHTML;
    window.showAllRecords = showAllRecords;
    window.showConsultationRecords = showConsultationRecords;
    window.showPrescriptionRecords = showPrescriptionRecords;
    window.updateRecordFilter = updateRecordFilter;
    window.updateRecordsContainer = updateRecordsContainer;

    // 记录详情
    window.viewRecordDetail = viewRecordDetail;
    window.showRecordDetailModal = showRecordDetailModal;
    window.closeRecordDetailModal = closeRecordDetailModal;

    // 复诊功能
    window.reorderPrescription = reorderPrescription;

    console.log('✅ smart_workflow_records.js 模块加载完成');

})();
