/**
 * 恢复未完成的处方对话功能
 *
 * 功能：页面加载时检查是否有已生成但未审核的处方
 * 如果有，自动恢复该处方对应的对话内容，并保持原有格式
 */

(async function() {
    'use strict';

    console.log('🔍 检查是否有未完成的处方...');

    const AUTO_RESTORE_KEY = 'tcm_auto_restore_pending_prescription';
    const FORCE_NEW_STRATEGY = window.refreshConversationStrategy === 'new_conversation';

    if (FORCE_NEW_STRATEGY) {
        console.log('🧹 当前策略为刷新=新会话，跳过待处理处方恢复提示');
        return;
    }

    const getCurrentUserId = () => {
        const user = window.authManager ? window.authManager.getCurrentUser() : null;
        if (user) {
            return user.id || user.global_user_id || user.user_id;
        }

        const userData = localStorage.getItem('currentUser') || localStorage.getItem('userData');
        if (userData) {
            try {
                const parsed = JSON.parse(userData);
                return parsed.id || parsed.global_user_id || parsed.user_id;
            } catch (e) {
                console.error('解析用户数据失败:', e);
            }
        }

        return localStorage.getItem('device_id') || null;
    };

    const normalizeDoctorCode = (rawDoctorValue) => {
        const raw = String(rawDoctorValue || '').trim();
        if (!raw) return null;

        if (typeof window.normalizeDoctorKey === 'function') {
            const normalized = window.normalizeDoctorKey(raw);
            return normalized || raw;
        }

        const fallbackMap = {
            '张仲景': 'zhang_zhongjing',
            '金大夫': 'jin_daifu',
            '叶天士': 'ye_tianshi',
            '李东垣': 'li_dongyuan',
            '刘渡舟': 'liu_duzhou',
            '郑钦安': 'zheng_qin_an',
            '朱丹溪': 'zhu_danxi'
        };

        return fallbackMap[raw] || raw;
    };

    const pickLatestPendingPrescription = (prescriptions) => {
        if (!Array.isArray(prescriptions) || prescriptions.length === 0) return null;

        const pending = prescriptions.filter((item) =>
            ['ai_generated', 'pending_review'].includes(item?.status) &&
            item?.payment_status === 'pending'
        );

        if (pending.length === 0) return null;

        const getTs = (item) => {
            const candidate = item?.updated_at || item?.created_at || item?.timestamp || '';
            const parsed = Date.parse(candidate);
            if (!Number.isNaN(parsed)) return parsed;
            const idNum = Number(item?.id);
            return Number.isFinite(idNum) ? idNum : 0;
        };

        pending.sort((a, b) => getTs(b) - getTs(a));
        return pending[0];
    };

    async function loadConsultationDetail(pendingPrescription) {
        const consultationId = pendingPrescription?.consultation_id || pendingPrescription?.conversation_id;
        if (!consultationId) {
            return null;
        }

        const consultationResponse = await fetch(`/api/user/conversation/${consultationId}`);
        const consultationData = await consultationResponse.json();

        if (consultationData?.success === false) {
            return null;
        }

        if (consultationData?.data) {
            return consultationData.data;
        }

        if (consultationData?.conversation_id || consultationData?.session_id) {
            return consultationData;
        }

        return null;
    }

    async function restorePendingConversation(pendingPrescription) {
        try {
            const consultation = await loadConsultationDetail(pendingPrescription);
            if (!consultation) {
                console.warn('⚠️ 无法获取待处理处方关联对话详情');
                return;
            }

            const doctorSource =
                consultation.selected_doctor_id ||
                consultation.doctor_id ||
                consultation.doctor_name ||
                consultation.doctor_display_name;
            const doctorCode = normalizeDoctorCode(doctorSource);
            if (doctorCode) {
                if (typeof window.setDefaultDoctor === 'function') {
                    window.setDefaultDoctor(doctorCode, true);
                } else if (typeof window.selectDoctor === 'function') {
                    window.selectDoctor(doctorCode);
                } else {
                    window.selectedDoctor = doctorCode;
                }
                await new Promise((resolve) => setTimeout(resolve, 300));
            }

            const conversationHistory = Array.isArray(consultation.conversation_history)
                ? consultation.conversation_history
                : [];
            if (conversationHistory.length === 0) {
                console.warn('⚠️ 待处理处方的对话为空');
                return;
            }

            const messagesContainer = document.getElementById('messagesContainer');
            const mobileMessagesContainer = document.getElementById('mobileMessagesContainer');
            if (messagesContainer) messagesContainer.innerHTML = '';
            if (mobileMessagesContainer) mobileMessagesContainer.innerHTML = '';

            const restoredMessages = [];
            for (const turn of conversationHistory) {
                if (turn?.patient_query) {
                    restoredMessages.push({ type: 'user', content: turn.patient_query });
                }
                if (turn?.ai_response) {
                    restoredMessages.push({ type: 'ai', content: turn.ai_response });
                }
            }

            window.currentConversationId =
                consultation.session_id ||
                consultation.conversation_id ||
                pendingPrescription.consultation_id ||
                `restored_${Date.now()}`;
            window.messages = restoredMessages;

            for (const message of restoredMessages) {
                const isMobile = window.innerWidth <= 768;
                if (isMobile && typeof window.addMobileMessage === 'function') {
                    await window.addMobileMessage(
                        message.type,
                        message.content,
                        false,
                        false,
                        pendingPrescription?.id || null
                    );
                } else if (typeof window.addMessage === 'function') {
                    await window.addMessage(
                        message.type,
                        message.content,
                        false,
                        false,
                        pendingPrescription?.id || null
                    );
                } else {
                    addMessageFallback(message.type, message.content);
                }
            }

            if (window.innerWidth <= 768 && typeof window.showMobileChatPage === 'function') {
                window.showMobileChatPage();
            }

            if (typeof window.saveCurrentDoctorHistory === 'function') {
                window.saveCurrentDoctorHistory();
            }

            console.log(`✅ 已恢复最近待处理处方对话: #${pendingPrescription?.id || 'unknown'}`);
        } catch (error) {
            console.error('❌ 手动恢复待处理处方对话失败:', error);
        }
    }

    const userId = getCurrentUserId();
    if (!userId) {
        console.log('⚠️ 未找到用户ID，跳过处方检查');
        return;
    }

    try {
        const response = await fetch(`/api/prescription/patient/${userId}/prescriptions`);
        const result = await response.json();

        if (!result.success || !Array.isArray(result.prescriptions) || result.prescriptions.length === 0) {
            console.log('✅ 没有待处理的处方');
            return;
        }

        const pendingPrescription = pickLatestPendingPrescription(result.prescriptions);
        if (!pendingPrescription) {
            console.log('✅ 没有待支付的处方');
            return;
        }

        console.log('🔍 发现最近待处理处方:', pendingPrescription.id);

        const shouldAutoRestore = localStorage.getItem(AUTO_RESTORE_KEY) === '1';
        if (shouldAutoRestore) {
            await restorePendingConversation(pendingPrescription);
        } else {
            showPrescriptionReminder(pendingPrescription, restorePendingConversation);
        }
    } catch (error) {
        console.error('❌ 检查待处理处方失败:', error);
    }

    // 降级方案：直接添加消息
    function addMessageFallback(type, content) {
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const avatar = type === 'user' ? '👤' : '🤖';
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${content}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
    }

    // 显示处方待支付提示
    function showPrescriptionReminder(prescription, restoreHandler) {
        const existing = document.getElementById('pending-prescription-reminder');
        if (existing) {
            existing.remove();
        }

        const reminder = document.createElement('div');
        reminder.id = 'pending-prescription-reminder';
        reminder.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fff3cd;
            border: 2px solid #ffeb3b;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            max-width: 350px;
            animation: slideIn 0.3s ease-out;
        `;

        reminder.innerHTML = `
            <div style="display: flex; align-items: start; gap: 12px;">
                <div style="font-size: 32px;">💊</div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 8px 0; color: #856404; font-size: 16px;">处方待支付</h3>
                    <p style="margin: 0 0 12px 0; color: #856404; font-size: 14px; line-height: 1.5;">
                        检测到最近待处理处方 #${prescription?.id || '未知'}，可选择恢复该次问诊。
                    </p>
                    <div style="display: flex; gap: 8px;">
                        <button id="restorePendingConversationBtn"
                                style="flex: 1; padding: 8px; border: 1px solid #856404; background: white;
                                       color: #856404; border-radius: 6px; cursor: pointer; font-size: 14px;">
                            恢复问诊
                        </button>
                        <button id="closePendingConversationBtn"
                                style="flex: 1; padding: 8px; border: none; background: #ffc107;
                                       color: #856404; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px;">
                            先不恢复
                        </button>
                    </div>
                </div>
                <button onclick="this.closest('div').parentElement.remove()"
                        style="background: none; border: none; font-size: 20px; cursor: pointer;
                               color: #856404; padding: 0; line-height: 1;">×</button>
            </div>
        `;

        document.body.appendChild(reminder);

        const restoreBtn = document.getElementById('restorePendingConversationBtn');
        const closeBtn = document.getElementById('closePendingConversationBtn');

        if (restoreBtn && typeof restoreHandler === 'function') {
            restoreBtn.addEventListener('click', async () => {
                reminder.remove();
                await restoreHandler(prescription);
            });
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                reminder.remove();
            });
        }

        // 10秒后自动消失
        setTimeout(() => {
            if (reminder.parentElement) {
                reminder.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => reminder.remove(), 300);
            }
        }, 10000);
    }

    // 添加动画样式
    if (!document.getElementById('prescription-reminder-styles')) {
        const style = document.createElement('style');
        style.id = 'prescription-reminder-styles';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }

})();
