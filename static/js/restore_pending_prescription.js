/**
 * 恢复未完成的处方对话功能
 *
 * 功能：页面加载时检查是否有已生成但未审核的处方
 * 如果有，自动恢复该处方对应的对话内容，并保持原有格式
 */

(async function() {
    'use strict';

    console.log('🔍 检查是否有未完成的处方...');

    // 获取当前用户
    const getCurrentUserId = () => {
        const user = window.authManager ? window.authManager.getCurrentUser() : null;
        if (user) {
            return user.id || user.global_user_id || user.user_id;
        }

        // 降级方案
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

    const userId = getCurrentUserId();
    if (!userId) {
        console.log('⚠️ 未找到用户ID，跳过处方检查');
        return;
    }

    try {
        // 查询用户的所有处方，找到最新的未审核处方
        const response = await fetch(`/api/prescription/patient/${userId}/prescriptions`);
        const result = await response.json();

        if (!result.success || !result.prescriptions || result.prescriptions.length === 0) {
            console.log('✅ 没有待处理的处方');
            return;
        }

        // 找到最新的未审核处方 (status='ai_generated' 或 'pending_review'，且payment_status='pending')
        const pendingPrescription = result.prescriptions.find(p =>
            (p.status === 'ai_generated' || p.status === 'pending_review') &&
            p.payment_status === 'pending'
        );

        if (!pendingPrescription) {
            console.log('✅ 没有待支付的处方');
            return;
        }

        console.log('🔍 发现未完成的处方:', pendingPrescription.id);

        // 获取该处方对应的consultation对话记录
        const consultationId = pendingPrescription.consultation_id;
        if (!consultationId) {
            console.warn('⚠️ 处方没有关联consultation，无法恢复对话');
            return;
        }

        // 查询consultation详情
        const consultationResponse = await fetch(`/api/user/conversation/${consultationId}`);
        const consultationData = await consultationResponse.json();

        if (!consultationData.success || !consultationData.data) {
            console.warn('⚠️ 无法获取对话详情');
            return;
        }

        console.log('✅ 找到对话记录，开始恢复...');

        const consultation = consultationData.data;
        const conversationHistory = consultation.conversation_history || [];

        if (conversationHistory.length === 0) {
            console.warn('⚠️ 对话记录为空');
            return;
        }

        // 恢复医生选择
        if (consultation.doctor_name && window.selectDoctor) {
            const doctorCode = consultation.doctor_name;
            setTimeout(() => {
                window.selectDoctor(doctorCode);
                console.log(`✅ 已选择医生: ${doctorCode}`);
            }, 500);
        }

        // 恢复对话内容
        setTimeout(() => {
            const messagesContainer = document.getElementById('messagesContainer');
            if (!messagesContainer) {
                console.error('❌ 找不到messagesContainer');
                return;
            }

            // 清空现有对话
            messagesContainer.innerHTML = '';

            // 使用addMessageDirectly函数恢复每条消息（保持HTML格式）
            conversationHistory.forEach((message, index) => {
                // 添加用户消息
                if (message.patient_query) {
                    if (typeof window.addMessageDirectly === 'function') {
                        window.addMessageDirectly('user', '您', message.patient_query);
                    } else {
                        // 降级方案
                        addMessageFallback('user', message.patient_query);
                    }
                }

                // 添加AI回复
                if (message.ai_response) {
                    const doctorName = consultation.doctor_display_name || '中医专家';
                    if (typeof window.addMessageDirectly === 'function') {
                        window.addMessageDirectly('ai', doctorName, message.ai_response);
                    } else {
                        // 降级方案
                        addMessageFallback('ai', message.ai_response);
                    }
                }
            });

            console.log(`✅ 已恢复${conversationHistory.length}条对话记录`);

            // 显示处方提示
            setTimeout(() => {
                showPrescriptionReminder(pendingPrescription);
            }, 500);

        }, 1000);

    } catch (error) {
        console.error('❌ 恢复对话失败:', error);
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
    function showPrescriptionReminder(prescription) {
        const reminder = document.createElement('div');
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
                        您有一份AI生成的处方待支付。支付后将提交医生审核。
                    </p>
                    <div style="display: flex; gap: 8px;">
                        <button onclick="this.closest('div').parentElement.parentElement.remove()"
                                style="flex: 1; padding: 8px; border: 1px solid #856404; background: white;
                                       color: #856404; border-radius: 6px; cursor: pointer; font-size: 14px;">
                            稍后处理
                        </button>
                        <button onclick="window.location.href='/patient-portal?tab=prescriptions'"
                                style="flex: 1; padding: 8px; border: none; background: #ffc107;
                                       color: #856404; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px;">
                            去支付
                        </button>
                    </div>
                </div>
                <button onclick="this.closest('div').parentElement.remove()"
                        style="background: none; border: none; font-size: 20px; cursor: pointer;
                               color: #856404; padding: 0; line-height: 1;">×</button>
            </div>
        `;

        document.body.appendChild(reminder);

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
