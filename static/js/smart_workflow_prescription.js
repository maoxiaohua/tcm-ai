/**
 * smart_workflow_prescription.js
 *
 * 处方管理模块 - 从 index_smart_workflow.html 提取
 * 处理处方创建、确认、支付的所有核心逻辑
 *
 * 创建时间: 2025-11-20
 * 文件来源: /opt/tcm-ai/static/index_smart_workflow.html
 */

(function() {
    'use strict';

    // ===================== 辅助函数依赖说明 =====================
    // 本模块依赖以下外部函数（需要在主文件中定义）：
    // - getAuthHeaders() - 获取认证头
    // - showMessage(message, type) - 显示提示消息
    // - showLoginModal() - 显示登录模态框
    // - getCurrentUserId() - 获取当前用户ID
    // - generateConversationId() - 生成对话ID
    // - getCurrentDoctorHistory() - 获取当前医生对话历史
    // - saveCurrentDoctorHistory() - 保存当前医生对话历史
    // - formatMessage(content) - 格式化消息内容
    //
    // 全局变量依赖：
    // - currentUser - 当前用户对象
    // - userToken - 用户认证token
    // - currentConversationId - 当前对话ID
    // - selectedDoctor - 选择的医生
    // =====================================================

    // ===================== 处方管理系统 =====================

    /**
     * 从对话历史中提取症状和诊断信息
     * @returns {Object} {symptoms: string, diagnosis: string}
     */
    function extractConversationSummary() {
        const container = document.getElementById('messagesContainer');
        let symptoms = '';
        let diagnosis = '';

        if (container) {
            const messages = container.querySelectorAll('.message');
            const userMessages = [];
            const aiMessages = [];

            messages.forEach(messageEl => {
                const textEl = messageEl.querySelector('.message-text');
                if (textEl) {
                    const content = textEl.textContent.trim();
                    if (messageEl.classList.contains('user')) {
                        userMessages.push(content);
                    } else if (messageEl.classList.contains('ai')) {
                        aiMessages.push(content);
                    }
                }
            });

            // 提取用户描述的症状
            symptoms = userMessages.join(' | ').substring(0, 500); // 限制长度

            // 提取AI的诊断信息
            const lastAiMessage = aiMessages[aiMessages.length - 1] || '';
            if (lastAiMessage.includes('证候') || lastAiMessage.includes('诊断')) {
                diagnosis = lastAiMessage.substring(0, 300); // 提取诊断信息
            }
        }

        return {
            symptoms: symptoms || '患者症状描述',
            diagnosis: diagnosis || 'AI中医诊断'
        };
    }

    /**
     * 确认处方并支付
     * @param {string} encodedPrescription - Base64编码的处方内容
     */
    async function confirmPrescription(encodedPrescription) {
        try {
            const prescriptionContent = decodeURIComponent(atob(encodedPrescription));

            // 检查是否已登录
            if (!window.currentUser || !window.userToken) {
                if (typeof showMessage === 'function') {
                    showMessage('请先登录后再确认处方', 'error');
                }
                if (typeof showLoginModal === 'function') {
                    showLoginModal();
                }
                return;
            }

            // 创建处方确认模态框
            showPrescriptionConfirmModal(prescriptionContent);

        } catch (error) {
            console.error('处方确认失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('处方数据解析失败', 'error');
            }
        }
    }

    /**
     * 显示处方确认模态框
     * @param {string} prescriptionContent - 处方内容
     */
    function showPrescriptionConfirmModal(prescriptionContent) {
        // 检查是否已存在模态框
        let modal = document.getElementById('prescriptionModal');
        if (!modal) {
            // 创建处方确认模态框
            modal = document.createElement('div');
            modal.id = 'prescriptionModal';
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
                z-index: 1001;
            `;

            modal.innerHTML = `
                <div style="background: white; border-radius: 16px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 24px; border-radius: 16px 16px 0 0;">
                        <h3 style="margin: 0; font-size: 20px; font-weight: 600;">处方确认</h3>
                    </div>
                    <div style="padding: 24px;">
                        <div style="background: #f8fafc; border-radius: 8px; padding: 16px; margin-bottom: 20px; border-left: 4px solid #3b82f6;">
                            <h4 style="margin: 0 0 12px 0; color: #374151;">处方内容：</h4>
                            <div id="prescriptionContent" style="font-family: monospace; white-space: pre-wrap; line-height: 1.6; color: #1f2937;"></div>
                        </div>

                        <div style="background: #fef3c7; border-radius: 8px; padding: 16px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                            <h4 style="margin: 0 0 12px 0; color: #92400e;">重要提醒：</h4>
                            <ul style="margin: 0; padding-left: 20px; color: #92400e; font-size: 14px;">
                                <li>此为AI生成的建议处方，仅供参考</li>
                                <li>确认处方将进入支付流程，支付后可联系代煎服务</li>
                                <li>建议在专业医生指导下使用</li>
                                <li>如有不适，请立即停药并就医</li>
                            </ul>
                        </div>

                        <div style="background: #e0f2fe; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                            <h4 style="margin: 0 0 12px 0; color: #0277bd;">费用说明：</h4>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <span>处方费用：</span>
                                <span style="font-weight: bold;">￥ 50.00</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <span>代煎费用：</span>
                                <span style="font-weight: bold;">￥ 30.00</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding-top: 8px; border-top: 1px solid #b3e5fc;">
                                <span style="font-weight: bold;">总计：</span>
                                <span style="font-weight: bold; color: #0277bd; font-size: 18px;">￥ 80.00</span>
                            </div>
                        </div>

                        <div style="display: flex; gap: 12px;">
                            <button onclick="hidePrescriptionModal()" style="flex: 1; padding: 12px; border: 1px solid #d1d5db; background: #f9fafb; color: #374151; border-radius: 8px; cursor: pointer;">
                                取消
                            </button>
                            <button onclick="proceedToPayment()" style="flex: 1; padding: 12px; border: none; background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; border-radius: 8px; cursor: pointer; font-weight: 500;">
                                确认并支付 ￥80.00
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
        }

        // 更新处方内容
        const contentDiv = modal.querySelector('#prescriptionContent');
        contentDiv.textContent = prescriptionContent;

        // 显示模态框
        modal.style.display = 'flex';
    }

    /**
     * 隐藏处方确认模态框
     */
    function hidePrescriptionModal() {
        const modal = document.getElementById('prescriptionModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * 进入支付流程 - 核心处方创建逻辑
     */
    async function proceedToPayment() {
        try {
            // 获取处方内容
            const prescriptionContent = document.getElementById('prescriptionContent').textContent;

            // 确保用户信息存在
            if (!window.currentUser) {
                if (typeof showMessage === 'function') {
                    showMessage('用户信息缺失，请重新登录', 'error');
                }
                return;
            }

            // 从对话历史中提取症状和诊断信息
            const conversationSummary = extractConversationSummary();

            // 准备请求数据
            const userId = typeof window.resolveUserId === 'function'
                ? window.resolveUserId(window.currentUser, (typeof getCurrentUserId === 'function' ? getCurrentUserId() : null))
                : (typeof getCurrentUserId === 'function' ? getCurrentUserId() : (window.currentUser.id || window.currentUser.user_id));
            const conversationId = window.currentConversationId || (typeof generateConversationId === 'function' ? generateConversationId() : Date.now().toString());

            const requestData = {
                patient_id: userId,
                conversation_id: conversationId,
                patient_name: window.currentUser.username || window.currentUser.display_name || window.currentUser.name || '患者',
                patient_phone: window.currentUser.phone || '',
                symptoms: conversationSummary.symptoms,
                diagnosis: conversationSummary.diagnosis,
                ai_prescription: prescriptionContent
            };

            // 调试信息
            console.log('发送处方创建请求:', requestData);

            // 获取认证头
            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            console.log('认证头:', headers);

            // 按照后端API格式发送数据
            const response = await fetch('/api/prescription/create', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(requestData)
            });

            // 检查响应状态
            console.log('响应状态:', response.status, response.statusText);

            const result = await response.json();

            // 调试信息
            console.log('处方创建响应:', result);

            if (result.success && result.prescription_id) {
                // 处方创建成功后更新问诊状态为完成
                if (typeof updateConsultationStatus === 'function') {
                    await updateConsultationStatus('completed', result.prescription_id);
                }

                // 处方创建成功，进入支付流程
                hidePrescriptionModal();
                showPaymentModal(result.prescription_id, 80.00);
            } else {
                // 显示详细错误信息
                const errorMsg = result.message || result.detail || '处方创建失败';
                console.error('处方创建失败:', result);
                if (typeof showMessage === 'function') {
                    showMessage(errorMsg, 'error');
                }
            }

        } catch (error) {
            console.error('支付流程启动失败:', error);
            // 检查是否是网络错误
            if (error instanceof TypeError && error.message.includes('fetch')) {
                if (typeof showMessage === 'function') {
                    showMessage('网络连接失败，请检查网络状态', 'error');
                }
            } else {
                if (typeof showMessage === 'function') {
                    showMessage(`服务暂时不可用: ${error.message}`, 'error');
                }
            }
        }
    }

    /**
     * 保存处方
     * @param {string} encodedPrescription - Base64编码的处方内容
     */
    async function savePrescription(encodedPrescription) {
        try {
            const prescriptionContent = decodeURIComponent(atob(encodedPrescription));

            if (!window.currentUser) {
                if (typeof showMessage === 'function') {
                    showMessage('请先登录后再保存处方', 'error');
                }
                if (typeof showLoginModal === 'function') {
                    showLoginModal();
                }
                return;
            }

            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const response = await fetch('/api/prescription/save', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    message: prescriptionContent,
                    content: prescriptionContent,
                    doctor_id: window.selectedDoctor,
                    status: 'saved'
                })
            });

            const result = await response.json();

            if (result.success) {
                if (typeof showMessage === 'function') {
                    showMessage('处方已保存到您的病历记录中', 'success');
                }
            } else {
                if (typeof showMessage === 'function') {
                    showMessage(result.message || '处方保存失败', 'error');
                }
            }

        } catch (error) {
            console.error('保存处方失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('保存服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 获取处方内容的辅助函数
     * @returns {string} 处方内容
     */
    function getPrescriptionContent() {
        // 从最新的AI消息中获取处方内容
        const messages = document.querySelectorAll('.message');
        let prescriptionContent = '';

        // 从后往前查找包含处方的AI消息
        for (let i = messages.length - 1; i >= 0; i--) {
            const message = messages[i];
            const messageText = message.querySelector('.message-text');

            if (message.classList.contains('ai-message') && messageText) {
                const content = messageText.textContent || messageText.innerText || '';

                // 检查是否包含处方相关内容
                if (content.includes('处方') || content.includes('方剂') || content.includes('药材') ||
                    content.includes('君药') || content.includes('臣药') || content.includes('佐药') || content.includes('使药')) {
                    prescriptionContent = content;
                    break;
                }
            }
        }

        return prescriptionContent;
    }

    /**
     * 显示支付模态框
     * @param {string} prescriptionId - 处方ID
     * @param {number} amount - 支付金额
     */
    function showPaymentModal(prescriptionId, amount) {
        // 获取处方内容
        const prescriptionContent = getPrescriptionContent();
        let formattedContent = '';

        if (prescriptionContent && window.prescriptionContentRenderer) {
            formattedContent = window.prescriptionContentRenderer.formatRegularContent(prescriptionContent);
        } else {
            formattedContent = '<p class="no-content">正在加载处方内容...</p>';
        }

        // 检查是否已存在模态框
        let modal = document.getElementById('paymentModal');
        if (!modal) {
            // 创建支付模态框
            modal = document.createElement('div');
            modal.id = 'paymentModal';
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
                z-index: 1002;
            `;

            modal.innerHTML = `
                <div style="background: white; border-radius: 16px; max-width: 600px; width: 90%; max-height: 90vh; overflow-y: auto;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 24px; border-radius: 16px 16px 0 0; text-align: center; position: sticky; top: 0; z-index: 1;">
                        <h3 style="margin: 0; font-size: 20px; font-weight: 600;">处方确认与支付</h3>
                    </div>

                    <div style="padding: 24px;">
                        <div style="margin-bottom: 24px; background: #f8fafc; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb;">
                            <h4 style="margin: 0 0 16px 0; color: #374151; font-size: 18px; display: flex; align-items: center; gap: 8px;">
                                问诊汇总信息
                            </h4>
                            <div id="prescriptionModalContent">
                                ${formattedContent}
                            </div>
                        </div>

                        <div style="text-align: center; margin-bottom: 24px; padding: 20px; background: linear-gradient(135deg, #f0f9ff, #e0f2fe); border-radius: 12px; border: 1px solid #3b82f6;">
                            <div style="font-size: 32px; font-weight: bold; color: #1e40af; margin-bottom: 8px;">￥ ${amount.toFixed(2)}</div>
                            <div style="font-size: 14px; color: #1e40af;">包含：处方诊疗费 + 代煎服务费</div>
                        </div>

                        <div style="margin-bottom: 24px;">
                            <button onclick="payWithAlipay('${prescriptionId}', ${amount})"
                                    style="width: 100%; padding: 16px; border: 2px solid #1677ff; background: #f0f8ff; color: #1677ff; border-radius: 8px; font-size: 16px; font-weight: 500; cursor: pointer; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; gap: 8px;">
                                支付宝支付
                            </button>
                            <button onclick="payWithWechat('${prescriptionId}', ${amount})"
                                    style="width: 100%; padding: 16px; border: 2px solid #07c160; background: #f0fff4; color: #07c160; border-radius: 8px; font-size: 16px; font-weight: 500; cursor: pointer; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; gap: 8px;">
                                微信支付
                            </button>
                        </div>

                        <div style="text-align: center;">
                            <button onclick="hidePaymentModal()"
                                    style="color: #6b7280; background: none; border: none; cursor: pointer; text-decoration: underline; font-size: 14px;">
                                取消支付
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
        } else {
            // 更新已存在的模态框内容
            const contentDiv = modal.querySelector('#prescriptionModalContent');
            if (contentDiv) {
                contentDiv.innerHTML = formattedContent;
            }
        }

        // 显示模态框
        modal.style.display = 'flex';
    }

    /**
     * 隐藏支付模态框
     */
    function hidePaymentModal() {
        const modal = document.getElementById('paymentModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * 支付宝支付
     * @param {string} prescriptionId - 处方ID
     * @param {number} amount - 支付金额
     */
    async function payWithAlipay(prescriptionId, amount) {
        try {
            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const response = await fetch('/api/payment/alipay/create', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    prescription_id: prescriptionId,
                    amount: amount,
                    payment_method: 'alipay'
                })
            });

            const result = await response.json();

            if (result.success && result.data) {
                // 显示支付宝操作选择
                hidePaymentModal();
                showAlipayOptions(result.data.payment_url, result.data.payment_id, prescriptionId);
            } else {
                if (typeof showMessage === 'function') {
                    showMessage(result.message || '支付创建失败', 'error');
                }
            }

        } catch (error) {
            console.error('支付宝支付失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('支付服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 显示支付宝操作选择
     * @param {string} paymentUrl - 支付URL
     * @param {string} paymentId - 支付ID
     * @param {string} prescriptionId - 处方ID
     */
    function showAlipayOptions(paymentUrl, paymentId, prescriptionId) {
        let modal = document.getElementById('alipayOptionsModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'alipayOptionsModal';
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
                z-index: 1003;
            `;
            document.body.appendChild(modal);
        }

        modal.innerHTML = `
            <div style="background: white; border-radius: 16px; padding: 32px; text-align: center; max-width: 400px;">
                <h3 style="margin: 0 0 20px 0; color: #1677ff;">支付宝支付</h3>
                <div style="background: #f5f5f5; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                    <div style="font-size: 60px;">￥</div>
                    <div style="margin-top: 12px; color: #666; font-size: 14px;">请选择支付方式</div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <button onclick="window.open('${paymentUrl}', '_blank'); pollPaymentStatus('${paymentId}'); hideAlipayOptionsModal();"
                            style="padding: 12px 20px; background: #1677ff; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
                        跳转支付宝网页支付
                    </button>
                    <button onclick="testAlipayPaymentSuccess('${paymentId}', '${prescriptionId}')"
                            style="padding: 12px 20px; background: #52c41a; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
                        测试支付成功
                    </button>
                    <button onclick="hideAlipayOptionsModal()"
                            style="padding: 8px 20px; background: #f0f0f0; border: 1px solid #ddd; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        取消支付
                    </button>
                </div>
            </div>
        `;

        modal.style.display = 'flex';
    }

    /**
     * 隐藏支付宝选项模态框
     */
    function hideAlipayOptionsModal() {
        const modal = document.getElementById('alipayOptionsModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * 测试支付宝支付成功
     * @param {string} paymentId - 支付ID
     * @param {string} prescriptionId - 处方ID
     */
    async function testAlipayPaymentSuccess(paymentId, prescriptionId) {
        try {
            // 检查登录状态 (调试信息)
            console.log('用户登录状态 - Token:', !!window.userToken, 'User:', !!window.currentUser);

            const encodedOrderNo = encodeURIComponent(paymentId);
            console.log('测试支付宝支付成功，order_no:', paymentId);

            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const response = await fetch(`/api/payment/alipay/test-success?order_no=${encodedOrderNo}`, {
                method: 'POST',
                headers: headers
            });

            console.log('支付宝API响应状态:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('支付宝API错误响应:', errorText);
                if (typeof showMessage === 'function') {
                    showMessage(`支付API错误: ${response.status}`, 'error');
                }
                return;
            }

            const result = await response.json();
            console.log('支付宝API响应结果:', result);

            if (result.success) {
                hideAlipayOptionsModal();
                if (typeof showMessage === 'function') {
                    showMessage('测试支付成功！您的处方已解锁', 'success');
                }

                // 更新UI中的处方状态为已支付
                await markPrescriptionAsPaid(result.prescription_id || prescriptionId);

                // 显示代煎服务信息
                setTimeout(() => {
                    showDecorationInfo(result.prescription_id || prescriptionId);
                }, 2000);
            } else {
                console.error('支付宝支付测试失败:', result);
                if (typeof showMessage === 'function') {
                    showMessage(result.message || result.error?.message || '测试支付失败', 'error');
                }
            }

        } catch (error) {
            console.error('测试支付宝支付失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('测试支付服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 微信支付
     * @param {string} prescriptionId - 处方ID
     * @param {number} amount - 支付金额
     */
    async function payWithWechat(prescriptionId, amount) {
        try {
            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const response = await fetch('/api/payment/wechat/create', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    prescription_id: prescriptionId,
                    amount: amount,
                    payment_method: 'wechat'
                })
            });

            const result = await response.json();

            if (result.success && result.data) {
                // 显示微信支付二维码
                hidePaymentModal();
                showWechatQRCode(result.data.qr_code, result.data.payment_id);
            } else {
                if (typeof showMessage === 'function') {
                    showMessage(result.message || '支付创建失败', 'error');
                }
            }

        } catch (error) {
            console.error('微信支付失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('支付服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 显示微信支付二维码
     * @param {string} qrCode - 二维码数据
     * @param {string} paymentId - 支付ID
     */
    function showWechatQRCode(qrCode, paymentId) {
        let modal = document.getElementById('wechatQRModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'wechatQRModal';
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
                z-index: 1003;
            `;

            modal.innerHTML = `
                <div style="background: white; border-radius: 16px; padding: 32px; text-align: center; max-width: 350px;">
                    <h3 style="margin: 0 0 20px 0; color: #07c160;">微信支付</h3>
                    <div style="background: #f5f5f5; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                        <div style="font-size: 100px;">QR</div>
                        <div style="margin-top: 12px; color: #666; font-size: 14px;">请使用微信扫描二维码支付</div>
                    </div>
                    <div style="color: #666; font-size: 12px; margin-bottom: 20px;">
                        支付完成后页面将自动更新
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: center;">
                        <button onclick="testWechatPaymentSuccess('${paymentId}')"
                                style="padding: 8px 16px; background: #07c160; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">
                            测试支付成功
                        </button>
                        <button onclick="hideWechatQRModal()"
                                style="padding: 8px 16px; background: #f0f0f0; border: 1px solid #ddd; border-radius: 6px; cursor: pointer; font-size: 12px;">
                            取消支付
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
        }

        // 显示模态框并开始轮询支付状态
        modal.style.display = 'flex';
        pollPaymentStatus(paymentId);
    }

    /**
     * 隐藏微信支付二维码
     */
    function hideWechatQRModal() {
        const modal = document.getElementById('wechatQRModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * 轮询支付状态
     * @param {string} paymentId - 支付ID
     */
    async function pollPaymentStatus(paymentId) {
        const maxAttempts = 60; // 最多轮询60次 (5分钟)
        let attempts = 0;

        const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${window.userToken}`
        };

        const poll = async () => {
            try {
                const response = await fetch(`/api/payment/status/${paymentId}`, {
                    headers: headers
                });

                const result = await response.json();

                if (result.success && result.data) {
                    if (result.data.status === 'paid') {
                        // 支付成功
                        hideWechatQRModal();
                        hidePaymentModal();
                        if (typeof showMessage === 'function') {
                            showMessage('支付成功！您的处方已确认', 'success');
                        }

                        // 更新UI中的处方状态为已支付
                        await markPrescriptionAsPaid(result.data.prescription_id);

                        // 显示代煎服务信息
                        setTimeout(() => {
                            showDecorationInfo(result.data.prescription_id);
                        }, 2000);

                        return;
                    } else if (result.data.status === 'failed' || result.data.status === 'cancelled') {
                        // 支付失败
                        hideWechatQRModal();
                        hidePaymentModal();
                        if (typeof showMessage === 'function') {
                            showMessage('支付失败，请重试', 'error');
                        }
                        return;
                    }
                }

                // 继续轮询
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 5000); // 5秒后再次轮询
                } else {
                    // 超时
                    hideWechatQRModal();
                    hidePaymentModal();
                    if (typeof showMessage === 'function') {
                        showMessage('支付超时，请重试', 'error');
                    }
                }

            } catch (error) {
                console.error('支付状态查询失败:', error);
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 5000);
                }
            }
        };

        // 开始轮询
        poll();
    }

    /**
     * 测试微信支付成功
     * @param {string} paymentId - 支付ID
     */
    async function testWechatPaymentSuccess(paymentId) {
        try {
            // 检查登录状态 (调试信息)
            console.log('用户登录状态 - Token:', !!window.userToken, 'User:', !!window.currentUser);

            // 从paymentId中提取order_no (paymentId实际上就是order_no)
            const encodedOrderNo = encodeURIComponent(paymentId);
            console.log('测试微信支付成功，order_no:', paymentId);

            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const response = await fetch(`/api/payment/wechat/test-success?order_no=${encodedOrderNo}`, {
                method: 'POST',
                headers: headers
            });

            console.log('微信支付API响应状态:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('微信支付API错误响应:', errorText);
                if (typeof showMessage === 'function') {
                    showMessage(`支付API错误: ${response.status}`, 'error');
                }
                return;
            }

            const result = await response.json();
            console.log('微信支付API响应结果:', result);

            if (result.success) {
                hideWechatQRModal();
                hidePaymentModal();
                if (typeof showMessage === 'function') {
                    showMessage('测试支付成功！您的处方已解锁', 'success');
                }

                // 更新UI中的处方状态为已支付
                await markPrescriptionAsPaid(result.prescription_id);

                // 显示代煎服务信息
                setTimeout(() => {
                    showDecorationInfo(result.prescription_id);
                }, 2000);
            } else {
                console.error('微信支付测试失败:', result);
                if (typeof showMessage === 'function') {
                    showMessage(result.message || result.error?.message || '测试支付失败', 'error');
                }
            }

        } catch (error) {
            console.error('测试微信支付失败:', error);
            if (typeof showMessage === 'function') {
                showMessage('测试支付服务暂时不可用', 'error');
            }
        }
    }

    /**
     * 显示代煎服务信息
     * @param {string} prescriptionId - 处方ID
     */
    function showDecorationInfo(prescriptionId) {
        if (typeof showMessage === 'function') {
            showMessage('代煎服务已启动，我们将在24小时内联系您安排配送', 'success');
        }

        // 可以在这里添加更多代煎服务的详细信息
        // 例如跳转到订单页面等
    }

    // ===================== 处方状态管理系统 =====================

    /**
     * 标记处方为已支付状态并重新渲染完整内容
     * @param {string} prescriptionId - 处方ID
     */
    async function markPrescriptionAsPaid(prescriptionId) {
        console.log('标记处方为已支付:', prescriptionId);

        // 支付成功后将处方提交给医生审核
        try {
            console.log('支付成功，正在提交处方给医生审核...', { prescriptionId, type: typeof prescriptionId });

            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const submitResponse = await fetch('/api/prescription-review/payment-confirm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...headers
                },
                body: JSON.stringify({
                    prescription_id: prescriptionId,
                    payment_amount: 80.00,
                    payment_method: 'alipay'
                })
            });

            const submitResult = await submitResponse.json();
            console.log('处方提交审核结果:', submitResult);

            if (submitResult.success) {
                console.log('处方已成功提交医生审核');
                // 显示审核等待提示
                if (typeof showMessage === 'function') {
                    showMessage('支付成功！处方已提交医生审核，审核完成后即可配药', 'success');
                }

                // 如果提交审核成功，不显示完整处方，只显示等待审核状态
                updatePrescriptionToReviewStatus(prescriptionId);

                // 同步状态到服务器
                await syncPrescriptionStatusToServer(prescriptionId, 'pending_review', {
                    action: 'payment_confirmed',
                    timestamp: new Date().toISOString()
                });

                return; // 提前返回，不执行后面的完整处方显示逻辑
            } else {
                console.warn('处方提交审核失败:', submitResult.message);
            }
        } catch (error) {
            console.error('处方提交审核异常:', error);
        }

        // 检测当前是移动端还是PC端
        const isMobile = window.innerWidth <= 768;
        console.log('屏幕检测:', { windowWidth: window.innerWidth, isMobile });

        // 优先尝试PC端容器，再尝试移动端容器
        let messagesContainer = document.getElementById('messagesContainer');
        let containerType = 'PC';

        if (!messagesContainer) {
            messagesContainer = document.getElementById('mobileMessagesContainer');
            containerType = 'Mobile';
        }

        console.log('使用容器类型:', containerType);

        if (!messagesContainer) {
            console.error('未找到任何消息容器');
            return;
        }

        // 查找包含处方的AI消息
        const aiMessages = messagesContainer.querySelectorAll('.message.ai');

        console.log('找到AI消息数量:', aiMessages.length);

        for (let i = 0; i < aiMessages.length; i++) {
            const messageDiv = aiMessages[i];

            // 检查是否有处方ID匹配或支付按钮
            const msgPrescriptionId = messageDiv.getAttribute('data-prescription-id');
            const hasPaymentButton = messageDiv.querySelector('.prescription-actions');

            console.log(`消息 ${i+1}:`, {
                msgPrescriptionId,
                hasPaymentButton: !!hasPaymentButton,
                targetPrescriptionId: prescriptionId
            });

            // 检查消息是否包含处方内容
            const messageContent = messageDiv.innerHTML || '';
            const hasUnlockButton = messageContent.includes('解锁完整处方') || messageContent.includes('确认处方并支付');
            const hasPrescriptionContent = messageContent.includes('处方') || messageContent.includes('方剂') || messageContent.includes('药材');

            console.log(`消息 ${i+1} 内容检查:`, {
                hasUnlockButton,
                hasPrescriptionContent,
                contentLength: messageContent.length
            });

            // 如果指定了处方ID，优先匹配ID
            if (prescriptionId && msgPrescriptionId && msgPrescriptionId !== prescriptionId) {
                console.log(`跳过消息 ${i+1} - ID不匹配`);
                continue; // 跳过不匹配的处方
            }

            // 如果没有明确的处方ID，检查是否有处方相关内容
            const shouldProcess = msgPrescriptionId || hasPaymentButton || hasUnlockButton ||
                (hasPrescriptionContent && messageContent.length > 1000); // 长内容很可能是处方

            if (!shouldProcess) {
                console.log(`跳过消息 ${i+1} - 不是处方相关消息`);
                continue;
            }

            console.log(`处理消息 ${i+1} - 开始获取原始处方内容`);

            // 获取原始处方内容（异步从API获取）
            let originalContent = await getOriginalPrescriptionContent(messageDiv, prescriptionId);

            // 如果API获取失败，尝试获取完整处方内容
            if (!originalContent) {
                try {
                    console.log('[支付] 尝试获取完整处方内容...');
                    const fullContentResponse = await fetch(`/api/prescription/${prescriptionId}/full-content`);
                    if (fullContentResponse.ok) {
                        const fullContentData = await fullContentResponse.json();
                        if (fullContentData.success && fullContentData.prescription) {
                            originalContent = fullContentData.prescription.full_content;
                            console.log('[支付] 获取到完整处方内容，长度:', originalContent.length);
                        }
                    }
                } catch (fullContentError) {
                    console.log('[支付] 获取完整内容失败:', fullContentError);
                }
            }

            // 最终fallback：使用DOM内容
            if (!originalContent) {
                console.log('API获取失败，使用DOM内容作为备用');
                const contentDiv = messageDiv.querySelector('.message-text') || messageDiv.querySelector('.message-content');
                if (contentDiv) {
                    originalContent = contentDiv.innerHTML;
                    console.log('从DOM获取内容长度:', originalContent.length);
                }
            }

            if (originalContent) {
                console.log('重新渲染处方内容为已支付状态');

                // 直接显示完整原始内容，绕过处方渲染器的复杂逻辑
                console.log('直接显示完整处方内容（已支付）');
                console.log('原始处方内容预览:', originalContent.substring(0, 200) + '...');

                let newContent;

                // 如果原始内容已经包含HTML，直接使用
                if (originalContent.includes('<div') || originalContent.includes('<p')) {
                    newContent = originalContent;
                } else {
                    // 如果是纯文本，进行格式化
                    newContent = typeof formatMessage === 'function' ? formatMessage(originalContent) : originalContent;
                }

                // 移除任何隐藏的内容标记和预览限制
                newContent = newContent.replace(/\*\*\*/g, '15');
                newContent = newContent.replace(/解锁查看/g, '');
                newContent = newContent.replace(/\+ \d+ 味药材/g, '');
                newContent = newContent.replace(/方剂组成预览/g, '完整方剂组成');
                newContent = newContent.replace(/预览/g, '完整');

                // 移除支付相关的按钮和提示
                newContent = newContent.replace(/<div[^>]*解锁完整处方[^>]*>.*?<\/div>/gs, '');
                newContent = newContent.replace(/<button[^>]*确认处方并支付[^>]*>.*?<\/button>/gs, '');
                newContent = newContent.replace(/解锁完整处方/g, '');
                newContent = newContent.replace(/确认处方并支付.*?￥\d+/g, '');

                // 如果内容太短，可能是被过度处理了，尝试恢复
                if (newContent.length < 500 && originalContent.length > 1000) {
                    console.log('处理后内容过短，使用原始内容');
                    newContent = originalContent;
                }

                console.log('内容处理结果:', {
                    原始长度: originalContent.length,
                    处理后长度: newContent.length,
                    包含药材: newContent.includes('药材') || newContent.includes('方剂')
                });

                // 添加支付成功标识
                newContent += `
                    <div class="prescription-paid" style="margin-top: 15px; padding: 12px; background: #f0f9ff; border-radius: 8px; border-left: 4px solid #10b981;">
                        <div style="font-size: 13px; color: #059669; margin-bottom: 8px;">
                            <strong>处方已解锁</strong> - 支付成功，完整处方内容已显示
                        </div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button onclick="showDecorationInfo('${prescriptionId || 'unknown'}')"
                                    style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 8px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s;">
                                联系代煎服务
                            </button>
                        </div>
                    </div>
                `;

                // 更新消息内容 - 尝试多个可能的选择器
                let contentDiv = messageDiv.querySelector('.message-text');
                if (!contentDiv) {
                    contentDiv = messageDiv.querySelector('.message-content .message-text');
                }
                if (!contentDiv) {
                    contentDiv = messageDiv.querySelector('.content');
                }
                if (!contentDiv) {
                    contentDiv = messageDiv.querySelector('.message-content');
                }

                console.log('找到内容容器:', !!contentDiv, contentDiv?.className);

                if (contentDiv) {
                    console.log('更新处方内容 - 原长度:', contentDiv.innerHTML.length, '新长度:', newContent.length);
                    contentDiv.innerHTML = newContent;
                } else {
                    console.error('未找到内容容器，无法更新处方');
                }

                // 标记处方ID和支付状态
                if (prescriptionId) {
                    messageDiv.setAttribute('data-prescription-id', prescriptionId);
                    messageDiv.setAttribute('data-paid', 'true');
                }

                console.log('已更新处方内容为已支付状态');
            }
        }

        // 立即保存更新后的状态
        if (window.selectedDoctor && typeof saveCurrentDoctorHistory === 'function') {
            saveCurrentDoctorHistory();
            console.log('已保存支付状态到历史记录');
        }
    }

    /**
     * 更新处方显示为等待审核状态
     * @param {string} prescriptionId - 处方ID
     */
    function updatePrescriptionToReviewStatus(prescriptionId) {
        console.log('更新处方为等待审核状态:', prescriptionId);

        // 查找包含处方的消息
        const messagesContainer = document.getElementById('messagesContainer') || document.getElementById('mobileMessagesContainer');
        if (!messagesContainer) return;

        const aiMessages = messagesContainer.querySelectorAll('.message.ai');

        for (let messageDiv of aiMessages) {
            const msgPrescriptionId = messageDiv.getAttribute('data-prescription-id');
            const messageContent = messageDiv.innerHTML || '';
            const hasPrescriptionContent = messageContent.includes('处方') || messageContent.includes('方剂');

            // 如果是目标处方消息
            if ((prescriptionId && msgPrescriptionId === prescriptionId) ||
                (!prescriptionId && hasPrescriptionContent)) {

                const contentDiv = messageDiv.querySelector('.message-text') || messageDiv.querySelector('.message-content');
                if (contentDiv) {
                    // 替换为等待审核状态
                    contentDiv.innerHTML = `
                        <div class="prescription-review-waiting" style="padding: 20px; background: linear-gradient(135deg, #fef3c7, #fde68a); border-radius: 12px; border-left: 4px solid #f59e0b; margin: 15px 0;">
                            <div style="text-align: center; margin-bottom: 15px;">
                                <div style="font-size: 2em; margin-bottom: 10px;">...</div>
                                <h3 style="color: #92400e; margin: 0; font-size: 18px;">处方等待医生审核中</h3>
                            </div>

                            <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 8px; margin: 10px 0;">
                                <p style="margin: 0; color: #78350f; font-size: 14px; line-height: 1.6;">
                                    <strong>支付已完成</strong><br>
                                    处方正在由专业医生审核中<br>
                                    审核完成后您将收到通知<br>
                                    审核通过后即可配药
                                </p>
                            </div>

                            <div style="text-align: center; margin-top: 15px;">
                                <button onclick="checkPrescriptionStatus('${prescriptionId}')"
                                        style="background: #f59e0b; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                                    查看审核状态
                                </button>
                            </div>

                            <div style="font-size: 12px; color: #92400e; text-align: center; margin-top: 10px; opacity: 0.8;">
                                处方ID: ${prescriptionId}
                            </div>
                        </div>
                    `;

                    // 标记处方状态
                    messageDiv.setAttribute('data-prescription-status', 'pending_review');
                    messageDiv.setAttribute('data-prescription-id', prescriptionId);

                    // 同步状态到localStorage，确保刷新后能恢复
                    syncPrescriptionStatusToStorage(prescriptionId, 'pending_review');

                    console.log('已更新处方显示为等待审核状态');
                }
                break;
            }
        }
    }

    /**
     * 同步处方状态到本地存储
     * @param {string} prescriptionId - 处方ID
     * @param {string} status - 处方状态
     */
    function syncPrescriptionStatusToStorage(prescriptionId, status) {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : 'default';
            const storageKey = `prescription_status_${userId}`;
            let prescriptionStatuses = JSON.parse(localStorage.getItem(storageKey) || '{}');

            prescriptionStatuses[prescriptionId] = {
                status: status,
                timestamp: Date.now(),
                lastUpdated: new Date().toISOString()
            };

            localStorage.setItem(storageKey, JSON.stringify(prescriptionStatuses));
            console.log('已同步处方状态到本地存储:', prescriptionId, status);

        } catch (error) {
            console.error('同步处方状态失败:', error);
        }
    }

    /**
     * 从本地存储获取处方状态
     * @param {string} prescriptionId - 处方ID
     * @returns {string|null} 处方状态
     */
    function getPrescriptionStatusFromStorage(prescriptionId) {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : 'default';
            const storageKey = `prescription_status_${userId}`;
            const prescriptionStatuses = JSON.parse(localStorage.getItem(storageKey) || '{}');

            const statusData = prescriptionStatuses[prescriptionId];
            return statusData ? statusData.status : null;

        } catch (error) {
            console.error('获取处方状态失败:', error);
            return null;
        }
    }

    /**
     * 检查处方审核状态 - 增强实时同步
     * @param {string} prescriptionId - 处方ID
     */
    async function checkPrescriptionStatus(prescriptionId) {
        try {
            console.log('检查处方审核状态:', prescriptionId);

            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const response = await fetch(`/api/prescription-review/status/${prescriptionId}`, {
                headers: headers
            });

            if (response.ok) {
                const result = await response.json();
                console.log('处方状态:', result);

                if (result.success && result.data) {
                    const statusData = result.data;
                    const normalizedStatus = String(statusData.status || '').toLowerCase();
                    const normalizedReviewStatus = String(statusData.review_status || '').toLowerCase();
                    const actionRequired = String(statusData.action_required || '').toLowerCase();
                    const isReviewed = Boolean(statusData.is_reviewed) ||
                        ['approved', 'completed', 'doctor_approved', 'doctor_modified'].includes(normalizedStatus) ||
                        ['approved', 'doctor_approved'].includes(normalizedReviewStatus) ||
                        actionRequired === 'completed';

                    if (isReviewed) {
                        // 审核完成，显示最终处方
                        if (typeof showMessage === 'function') {
                            showMessage('处方审核已完成！', 'success');
                        }
                        await markPrescriptionAsCompleted(prescriptionId, statusData);

                        // 同步状态更新到本地存储
                        syncPrescriptionStatusToStorage(prescriptionId, 'approved');
                    } else {
                        // 仍在审核中，保持当前对话内容不变
                        if (typeof showMessage === 'function') {
                            showMessage(`处方仍在审核中，状态：${statusData.status_description || statusData.status || 'pending_review'}`, 'info');
                        }
                    }
                }
            } else {
                // 改进错误处理，提供更具体的错误信息
                const result = await response.json();
                const errorMsg = result.message || '无法获取处方状态';
                if (result.error_code === 'PRESCRIPTION_NOT_FOUND') {
                    console.warn('处方不存在:', prescriptionId);
                    if (typeof showMessage === 'function') {
                        showMessage(`处方记录不存在(ID: ${prescriptionId})`, 'warning');
                    }
                } else {
                    if (typeof showMessage === 'function') {
                        showMessage(errorMsg, 'error');
                    }
                }
            }
        } catch (error) {
            console.error('检查处方状态失败:', error);
            // 区分不同类型的网络错误
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                if (typeof showMessage === 'function') {
                    showMessage('网络连接失败，请检查网络设置', 'error');
                }
            } else if (error.name === 'SyntaxError') {
                if (typeof showMessage === 'function') {
                    showMessage('服务器响应格式错误', 'error');
                }
            } else {
                if (typeof showMessage === 'function') {
                    showMessage('网络错误，请稍后重试', 'error');
                }
            }
        }
    }

    /**
     * 静默检查处方状态（不显示UI提示）
     * @param {string} prescriptionId - 处方ID
     */
    async function checkPrescriptionStatusSilently(prescriptionId) {
        try {
            const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.userToken}`
            };

            const response = await fetch(`/api/prescription-review/status/${prescriptionId}`, {
                headers: headers
            });

            if (response.ok) {
                const result = await response.json();
                const statusData = result && result.data ? result.data : null;
                const normalizedStatus = String(statusData?.status || '').toLowerCase();
                const normalizedReviewStatus = String(statusData?.review_status || '').toLowerCase();
                const actionRequired = String(statusData?.action_required || '').toLowerCase();
                const isReviewed = Boolean(statusData?.is_reviewed) ||
                    ['approved', 'completed', 'doctor_approved', 'doctor_modified'].includes(normalizedStatus) ||
                    ['approved', 'doctor_approved'].includes(normalizedReviewStatus) ||
                    actionRequired === 'completed';

                if (result.success && statusData && isReviewed) {
                    // 审核完成，自动更新界面
                    console.log('检测到处方审核完成:', prescriptionId);
                    if (typeof showMessage === 'function') {
                        showMessage('您有处方审核完成，正在更新显示...', 'success');
                    }

                    await markPrescriptionAsCompleted(prescriptionId, statusData);
                    syncPrescriptionStatusToStorage(prescriptionId, 'approved');

                    // 播放通知音效（如果可能）
                    if ('Audio' in window) {
                        try {
                            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFAg+ltryxnkpBSl+zPLZizEIGGS57OObTgwKT6fh8LZnHgg2jdXzzn8vBSF0xe/ekkILElyx5+2rWRUGPJPY88p9KwUme8rx2o4yBxZiturjpVITC0ml4e+3aB4GMIzU8tGAMgUfcsLu45hEDBFYrOLtrVwWBDqU2fLIfSwGJHfH8N+QQAoUXrTp6qtWFAg+ltrzxnkpBSl+zPLZizEIGGS56+OcTgwKT6fh8LZnHgg2jdT0z4AuBSJ0xe/gkkILElyx5+2rWRUGPJPY88p9KwUme8rx2o4yBxZiturjpVITC0ml4e+3aB4GMIzU8tGAMgUfcsLu45hEDBFYrOLtrVwWBDqU2fLIfSwGJHfH8N+QQAoUXrTp6qtWFAg+ltrzxnkpBSl+zPLZizEIGGS56+OcTgwKT6fh8LZnHgg2jdT0z4AuBSJ0xe/gkkILElyx5+2rWRUGPJPY88p9KwUme8rx2o4yBxZiturjpVITC0ml4e+3aB4GMIzU8tGAMgUfcsLu45hEDBFYrOLtrVwWBDqU2fLIfSwGJHfH8N+QQAoUXrTp6qtWFAg+ltrzxnkpBSl+zPLZizEIGGS56+OcTgwKT6fh8LZnHgg2jdT0z4AuBSJ0xe/gkkILElyx5+2rWRUGPJPY88p9KwUme8rx2o4yBxZiturjpVITC0ml4e+3aB4=');
                            audio.volume = 0.3;
                            audio.play();
                        } catch (e) {
                            // 忽略音效播放错误
                        }
                    }
                }
            }
        } catch (error) {
            console.warn('静默检查处方状态失败:', prescriptionId, error);
            // 如果是处方不存在的错误，从本地存储中移除
            if (error.message && error.message.includes('不存在')) {
                try {
                    const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : 'default';
                    const storageKey = `prescription_status_${userId}`;
                    const prescriptionStatuses = JSON.parse(localStorage.getItem(storageKey) || '{}');
                    if (prescriptionStatuses[prescriptionId]) {
                        delete prescriptionStatuses[prescriptionId];
                        localStorage.setItem(storageKey, JSON.stringify(prescriptionStatuses));
                        console.log('已清理无效处方ID:', prescriptionId);
                    }
                } catch (cleanupError) {
                    console.warn('清理无效处方ID失败:', cleanupError);
                }
            }
        }
    }

    /**
     * 标记处方为审核完成状态
     * @param {string} prescriptionId - 处方ID
     * @param {Object} statusData - 状态数据
     */
    async function markPrescriptionAsCompleted(prescriptionId, statusData) {
        console.log('处方审核完成，显示最终处方');

        // 医生审核完成后才显示完整处方，不走支付流程
        try {
            // 查找处方消息元素
            const messagesContainer = document.getElementById('messagesContainer') || document.getElementById('mobileMessagesContainer');
            if (!messagesContainer) return;

            const messageElements = messagesContainer.querySelectorAll('.message.ai');

            for (let messageDiv of messageElements) {
                const msgPrescriptionId = messageDiv.getAttribute('data-prescription-id');
                if (msgPrescriptionId === prescriptionId) {
                    const contentDiv = messageDiv.querySelector('.message-text') || messageDiv.querySelector('.message-content');
                    if (contentDiv) {
                        // 获取审核后的完整处方内容
                        const finalPrescription = statusData.final_prescription || statusData.doctor_prescription || "审核完成的处方内容";

                        contentDiv.innerHTML = `
                            <div class="prescription-approved" style="padding: 20px; background: linear-gradient(135deg, #dcfce7, #bbf7d0); border-radius: 12px; border-left: 4px solid #22c55e; margin: 15px 0;">
                                <div style="text-align: center; margin-bottom: 15px;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">OK</div>
                                    <h3 style="color: #15803d; margin: 0; font-size: 18px;">医生审核通过</h3>
                                </div>

                                <div style="background: rgba(255,255,255,0.9); padding: 20px; border-radius: 8px; margin: 15px 0;">
                                    <div style="color: #15803d; font-size: 16px; font-weight: 600; margin-bottom: 15px;">
                                        审核通过的处方：
                                    </div>
                                    <div style="color: #374151; line-height: 1.6; white-space: pre-wrap;">
                                        ${finalPrescription}
                                    </div>
                                </div>

                                <div style="text-align: center; margin-top: 15px;">
                                    <div style="color: #059669; font-size: 14px; margin-bottom: 10px;">
                                        医生审核已完成<br>
                                        您可以凭此处方配药
                                    </div>
                                </div>

                                <div style="font-size: 12px; color: #059669; text-align: center; margin-top: 10px;">
                                    处方ID: ${prescriptionId}
                                </div>
                            </div>
                        `;

                        // 标记为审核完成状态
                        messageDiv.setAttribute('data-prescription-status', 'approved');
                        syncPrescriptionStatusToStorage(prescriptionId, 'approved');

                        console.log('已显示审核通过的最终处方');
                    }
                    break;
                }
            }
        } catch (error) {
            console.error('显示审核完成处方失败:', error);
        }
    }

    /**
     * 获取原始处方内容的辅助函数（从API获取）
     * @param {HTMLElement} messageDiv - 消息元素
     * @param {string} prescriptionId - 处方ID
     * @returns {Promise<string|null>} 处方内容
     */
    async function getOriginalPrescriptionContent(messageDiv, prescriptionId) {
        // 优先从API获取原始处方内容
        if (prescriptionId) {
            try {
                console.log('从API获取处方详情:', prescriptionId);

                const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${window.userToken}`
                };

                const response = await fetch(`/api/prescription/${prescriptionId}`, {
                    headers: headers
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.success && result.prescription) {
                        const prescriptionData = result.prescription;
                        // 返回AI处方内容（原始内容）
                        const originalContent = prescriptionData.ai_prescription || prescriptionData.doctor_prescription;
                        if (originalContent) {
                            console.log('从API成功获取原始处方内容');
                            return originalContent;
                        }
                    }
                }
            } catch (error) {
                console.error('API获取处方内容失败:', error);
            }
        }

        // 备用方案1：从历史记录获取原始内容
        if (typeof getCurrentDoctorHistory === 'function') {
            const currentHistory = getCurrentDoctorHistory();
            if (currentHistory && currentHistory.length > 0) {
                // 从最近的消息中查找处方内容
                for (let i = currentHistory.length - 1; i >= 0; i--) {
                    const msg = currentHistory[i];
                    if (msg.type === 'ai' && (msg.prescriptionId === prescriptionId || msg.prescriptionData?.prescriptionId === prescriptionId)) {
                        console.log('从历史记录找到原始处方内容');
                        return msg.originalContent || msg.content;
                    }
                }
            }
        }

        // 备用方案2：从DOM获取（可能已经被处方渲染器修改过）
        const contentDiv = messageDiv.querySelector('.message-text');
        if (contentDiv) {
            // 尝试获取未修改的文本内容
            const textContent = contentDiv.textContent || contentDiv.innerText;
            if (textContent && textContent.length > 100) {
                console.log('从DOM获取处方内容（可能不完整）');
                return textContent;
            }
        }

        console.warn('无法获取原始处方内容');
        return null;
    }

    /**
     * 处方状态云端同步函数
     * @param {string} prescriptionId - 处方ID
     * @param {string} status - 状态
     * @param {Object} additionalData - 附加数据
     * @returns {Promise<boolean>} 同步结果
     */
    async function syncPrescriptionStatusToServer(prescriptionId, status, additionalData = {}) {
        try {
            console.log(`同步处方状态到服务器: ID=${prescriptionId}, status=${status}`);

            // 这里可以调用服务器API同步状态
            // 暂时只做日志记录，稀后实现具体的同步逻辑
            console.log('处方状态同步数据:', { prescriptionId, status, ...additionalData });

            return true;
        } catch (error) {
            console.error('同步处方状态到服务器失败:', error);
            return false;
        }
    }

    /**
     * 启动实时同步检查机制
     */
    function startPrescriptionStatusPolling() {
        const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : 'default';
        const storageKey = `prescription_status_${userId}`;

        // 每30秒检查一次处方状态
        setInterval(async () => {
            try {
                const prescriptionStatuses = JSON.parse(localStorage.getItem(storageKey) || '{}');

                // 检查所有待审核的处方
                for (const [prescriptionId, statusData] of Object.entries(prescriptionStatuses)) {
                    if (statusData.status === 'pending_review') {
                        // 检查是否已过期（超过24小时不再检查）
                        const hoursAgo = (Date.now() - statusData.timestamp) / (1000 * 60 * 60);
                        if (hoursAgo < 24 && prescriptionId && prescriptionId !== 'undefined') {
                            await checkPrescriptionStatusSilently(prescriptionId);
                        }
                    }
                }
            } catch (error) {
                console.warn('定期检查处方状态失败:', error);
            }
        }, 30000); // 30秒检查一次

        console.log('已启动处方状态实时同步检查');
    }

    /**
     * 恢复所有待审核处方状态 - 页面刷新后确保状态一致性
     */
    function restoreAllPendingPrescriptions() {
        try {
            const userId = typeof getCurrentUserId === 'function' ? getCurrentUserId() : null;
            if (!userId) return;

            const storageKey = `prescription_status_${userId}`;
            const prescriptionStatuses = JSON.parse(localStorage.getItem(storageKey) || '{}');

            console.log('检查并恢复所有待审核处方状态:', prescriptionStatuses);

            // 遍历所有本地存储的处方状态
            for (const [prescriptionId, statusData] of Object.entries(prescriptionStatuses)) {
                if (statusData.status === 'pending_review') {
                    console.log('恢复待审核处方:', prescriptionId);
                    updatePrescriptionToReviewStatus(prescriptionId);
                }
            }

            console.log('处方状态恢复检查完成');

        } catch (error) {
            console.error('恢复处方状态失败:', error);
        }
    }

    // ===================== 导出到window对象 =====================

    // 处方确认和保存
    window.confirmPrescription = confirmPrescription;
    window.savePrescription = savePrescription;
    window.showPrescriptionConfirmModal = showPrescriptionConfirmModal;
    window.hidePrescriptionModal = hidePrescriptionModal;

    // 支付相关
    window.proceedToPayment = proceedToPayment;
    window.payWithAlipay = payWithAlipay;
    window.payWithWechat = payWithWechat;
    window.testAlipayPaymentSuccess = testAlipayPaymentSuccess;
    window.testWechatPaymentSuccess = testWechatPaymentSuccess;
    window.pollPaymentStatus = pollPaymentStatus;
    window.showPaymentModal = showPaymentModal;
    window.hidePaymentModal = hidePaymentModal;
    window.showAlipayOptions = showAlipayOptions;
    window.hideAlipayOptionsModal = hideAlipayOptionsModal;
    window.showWechatQRCode = showWechatQRCode;
    window.hideWechatQRModal = hideWechatQRModal;
    window.showDecorationInfo = showDecorationInfo;

    // 状态管理
    window.checkPrescriptionStatus = checkPrescriptionStatus;
    window.checkPrescriptionStatusSilently = checkPrescriptionStatusSilently;
    window.markPrescriptionAsPaid = markPrescriptionAsPaid;
    window.markPrescriptionAsCompleted = markPrescriptionAsCompleted;
    window.getOriginalPrescriptionContent = getOriginalPrescriptionContent;
    window.updatePrescriptionToReviewStatus = updatePrescriptionToReviewStatus;
    window.syncPrescriptionStatusToStorage = syncPrescriptionStatusToStorage;
    window.getPrescriptionStatusFromStorage = getPrescriptionStatusFromStorage;
    window.syncPrescriptionStatusToServer = syncPrescriptionStatusToServer;
    window.startPrescriptionStatusPolling = startPrescriptionStatusPolling;
    window.restoreAllPendingPrescriptions = restoreAllPendingPrescriptions;

    // 辅助函数
    window.extractConversationSummary = extractConversationSummary;
    window.getPrescriptionContent = getPrescriptionContent;

    console.log('smart_workflow_prescription.js 模块加载完成');
    console.log('已暴露到window的函数:', [
        'confirmPrescription', 'savePrescription', 'proceedToPayment',
        'payWithAlipay', 'payWithWechat', 'testAlipayPaymentSuccess',
        'testWechatPaymentSuccess', 'pollPaymentStatus', 'checkPrescriptionStatus',
        'checkPrescriptionStatusSilently', 'markPrescriptionAsPaid',
        'markPrescriptionAsCompleted', 'getOriginalPrescriptionContent'
    ]);

})();
