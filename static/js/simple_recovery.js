/**
 * 简化版处方恢复系统
 * 替代复杂的多系统架构，提供可靠的单一数据源恢复
 */

class SimpleRecoverySystem {
    constructor() {
        this.isRecovering = false;
        this.recoveryAttempts = 0;
        this.maxRetries = 3;
        this.apiBase = '';
        
        console.log('🔧 简化版处方恢复系统初始化');
    }
    
    /**
     * 获取当前用户ID - 直接调用主系统函数
     */
    getCurrentUserId() {
        try {
            // 🔑 优先使用主系统的getCurrentUserId函数（如果存在）
            if (typeof window.getCurrentUserId === 'function') {
                const userId = window.getCurrentUserId();
                if (userId) {
                    console.log('🔑 简化系统从主系统获取用户ID:', userId);
                    return userId;
                }
            }
            
            // 🔑 备用：使用与主系统完全相同的用户ID获取逻辑
            
            // 1. 检查URL参数中的用户ID（从历史页面跳转）
            const urlParams = new URLSearchParams(window.location.search);
            const urlUserId = urlParams.get('user_id');
            if (urlUserId && urlUserId !== 'anonymous') {
                console.log('🔗 从URL参数获取用户ID:', urlUserId);
                return urlUserId;
            }
            
            // 2. 优先使用真实登录用户信息 - 检查多个存储位置
            let realUser = null;
            
            // 2.1 优先检查currentUser存储（更可靠）
            const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
            console.log('🔍 检查currentUser存储:', currentUser);
            if (currentUser.id || currentUser.user_id || currentUser.global_user_id) {
                // 过滤掉临时用户ID，只使用真实登录用户
                const userId = currentUser.global_user_id || currentUser.user_id || currentUser.id;
                if (userId && !userId.startsWith('temp_user_') && !userId.startsWith('smart_user_') && userId !== 'anonymous') {
                    realUser = currentUser;
                    console.log('🔑 从currentUser获取真实用户:', realUser);
                }
            }
            
            // 2.2 检查userData存储（备选）
            if (!realUser) {
                const userData = JSON.parse(localStorage.getItem('userData') || '{}');
                console.log('🔍 检查userData存储:', userData);
                if (userData.id || userData.user_id || userData.global_user_id) {
                    const userId = userData.global_user_id || userData.user_id || userData.id;
                    if (userId && userId !== 'anonymous') {
                        realUser = userData;
                        console.log('🔑 从userData获取真实用户:', realUser);
                    }
                }
            }
            
            // 2.3 如果找到真实用户
            if (realUser) {
                const userId = realUser.global_user_id || realUser.user_id || realUser.id;
                if (userId && userId !== 'undefined' && userId !== null) {
                    console.log('🔑 恢复系统使用真实登录用户ID:', userId);
                    return userId;
                }
            }
            
            // 3. 访客模式 - 智能工作流程页面的临时用户ID
            const smartUser = localStorage.getItem('currentUserId');
            if (smartUser) {
                console.log('🔄 使用已有临时访客用户ID:', smartUser);
                return smartUser;
            }
            
            // 4. 检查是否有对话ID相关的用户信息
            const allStorageKeys = Object.keys(localStorage);
            const conversationKeys = allStorageKeys.filter(key => key.startsWith('conversationId_'));
            
            if (conversationKeys.length > 0) {
                const existingUserId = conversationKeys[0].replace('conversationId_', '');
                console.log('🔄 从对话ID恢复用户ID:', existingUserId);
                return existingUserId;
            }
            
            // 5. 检查历史记录键，尝试恢复用户ID
            const historyKeys = allStorageKeys.filter(key => key.startsWith('tcm_doctor_history_'));
            if (historyKeys.length > 0) {
                const historyKey = historyKeys[0];
                const parts = historyKey.split('_');
                if (parts.length >= 4) {
                    const existingUserId = parts.slice(3, -1).join('_');
                    console.log('🔄 从历史记录恢复用户ID:', existingUserId);
                    return existingUserId;
                }
            }
            
            console.warn('⚠️ 无法获取用户ID - 所有方法都失败了');
            return null;
        } catch (error) {
            console.error('❌ 获取用户ID失败:', error);
            return null;
        }
    }
    
    /**
     * 获取认证头
     */
    getAuthHeaders() {
        const token = localStorage.getItem('authToken') || 
                     localStorage.getItem('userToken') || 
                     localStorage.getItem('doctorToken');
        
        if (token) {
            return {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            };
        }
        
        return {
            'Content-Type': 'application/json'
        };
    }
    
    /**
     * 从服务器获取处方列表
     */
    async fetchPrescriptions(userId) {
        try {
            console.log(`📡 获取用户 ${userId} 的处方列表...`);
            
            const response = await fetch(`/api/prescription/patient/${userId}/prescriptions`, {
                method: 'GET',
                headers: this.getAuthHeaders()
            });
            
            if (!response.ok) {
                throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || '服务器返回失败状态');
            }
            
            console.log(`✅ 成功获取 ${result.prescriptions?.length || 0} 个处方`);
            return result.prescriptions || [];
            
        } catch (error) {
            console.error('❌ 获取处方列表失败:', error);
            throw error;
        }
    }
    
    /**
     * 创建处方消息HTML
     */
    createPrescriptionMessage(prescription) {
        const { id, status, payment_status, doctor_prescription, ai_prescription, doctor_notes, created_at } = prescription;
        
        const finalPrescription = doctor_prescription || ai_prescription || '处方内容获取中...';
        const createTime = new Date(created_at).toLocaleString();
        
        if (status === 'doctor_approved' || status === 'doctor_modified') {
            // 审核通过的处方
            return `
                <div class="message ai" data-prescription-id="${id}" data-prescription-status="approved">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <div class="message-text">
                            <div style="padding: 20px; background: linear-gradient(135deg, #dcfce7, #bbf7d0); border-radius: 12px; border-left: 4px solid #22c55e; margin: 15px 0;">
                                <div style="text-align: center; margin-bottom: 15px;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">✅</div>
                                    <h3 style="color: #15803d; margin: 0; font-size: 18px;">医生审核通过</h3>
                                </div>
                                
                                <div style="background: white; border-radius: 8px; padding: 15px; margin: 15px 0; border: 1px solid #bbf7d0;">
                                    <h4 style="color: #15803d; margin: 0 0 10px 0; font-size: 16px;">📋 最终处方</h4>
                                    <div style="background: #f8f9fa; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">
${finalPrescription}
                                    </div>
                                </div>
                                
                                ${doctor_notes ? `
                                    <div style="background: rgba(21, 128, 61, 0.1); border-radius: 8px; padding: 12px; margin: 10px 0;">
                                        <p style="margin: 0; color: #15803d; font-size: 14px;"><strong>医生备注:</strong> ${doctor_notes}</p>
                                    </div>
                                ` : ''}
                                
                                <div style="font-size: 12px; color: #059669; text-align: center; margin-top: 10px;">
                                    处方ID: ${id} | 状态: ${status === 'doctor_modified' ? '医生已调整' : '审核通过'} | ${createTime}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (payment_status === 'paid' && status === 'pending_review') {
            // 等待审核的处方
            return `
                <div class="message ai" data-prescription-id="${id}" data-prescription-status="pending_review">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <div class="message-text">
                            <div style="padding: 20px; background: linear-gradient(135deg, #fef3c7, #fde68a); border-radius: 12px; border-left: 4px solid #f59e0b; margin: 15px 0;">
                                <div style="text-align: center; margin-bottom: 15px;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">⏳</div>
                                    <h3 style="color: #92400e; margin: 0; font-size: 18px;">处方等待医生审核中</h3>
                                </div>
                                
                                <div style="background: rgba(146, 64, 14, 0.1); border-radius: 8px; padding: 15px; margin: 10px 0;">
                                    <p style="margin: 0; color: #92400e; font-size: 14px; line-height: 1.5;">
                                        ✅ <strong>支付已完成</strong><br>
                                        ⏳ 处方正在等待医生审核确认<br>
                                        📱 审核完成后将自动通知您
                                    </p>
                                </div>
                                
                                <div style="text-align: center; margin-top: 15px;">
                                    <button onclick="simpleRecovery.checkPrescriptionStatus('${id}')" 
                                            style="background: #f59e0b; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                                        🔍 查看审核状态
                                    </button>
                                </div>
                                
                                <div style="font-size: 12px; color: #92400e; text-align: center; margin-top: 10px; opacity: 0.8;">
                                    处方ID: ${id} | 创建时间: ${createTime}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return null; // 其他状态不显示
    }
    
    /**
     * 查看处方审核状态
     */
    async checkPrescriptionStatus(prescriptionId) {
        try {
            console.log(`🔍 查看处方 ${prescription_id} 的审核状态...`);
            
            const userId = this.getCurrentUserId();
            if (!userId) {
                throw new Error('无法获取用户ID');
            }
            
            const prescriptions = await this.fetchPrescriptions(userId);
            const prescription = prescriptions.find(p => p.id == prescriptionId);
            
            if (!prescription) {
                throw new Error('处方不存在');
            }
            
            const statusMap = {
                'pending_review': '等待医生审核',
                'doctor_approved': '医生审核通过',
                'doctor_modified': '医生已调整',
                'completed': '已完成'
            };
            
            const statusText = statusMap[prescription.status] || prescription.status;
            alert(`处方审核状态：${statusText}\n\n处方ID: ${prescription_id}\n支付状态: ${prescription.payment_status}\n创建时间: ${new Date(prescription.created_at).toLocaleString()}`);
            
            // 如果状态已更新，刷新页面显示
            if (prescription.status === 'doctor_approved' || prescription.status === 'doctor_modified') {
                console.log('🔄 处方状态已更新，刷新显示...');
                this.performRecovery();
            }
            
        } catch (error) {
            console.error('❌ 查看审核状态失败:', error);
            alert(`无法获取审核状态，请重试\n\n错误信息: ${error.message}`);
        }
    }
    
    /**
     * 获取最新的单个处方
     * 只恢复最后一个处方，而不是整个会话的处方
     */
    getLatestSinglePrescription(prescriptions) {
        if (!prescriptions || prescriptions.length === 0) {
            return [];
        }
        
        // 按创建时间排序，找出最新的处方记录
        const sortedPrescriptions = prescriptions.sort((a, b) => 
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        
        // 只返回最新的单个处方
        const latestPrescription = sortedPrescriptions[0];
        
        console.log(`🎯 只恢复最新的单个处方:`);
        console.log(`   - 处方ID: ${latestPrescription.id}`);
        console.log(`   - 状态: ${latestPrescription.status}`);
        console.log(`   - 支付状态: ${latestPrescription.payment_status}`);
        console.log(`   - 创建时间: ${latestPrescription.created_at}`);
        console.log(`   - 会话ID: ${latestPrescription.consultation_id || latestPrescription.conversation_id}`);
        
        return [latestPrescription];
    }
    
    /**
     * 执行恢复操作 - 只恢复最新的单个处方
     */
    async performRecovery() {
        if (this.isRecovering) {
            console.log('⏳ 恢复操作正在进行中，跳过...');
            return;
        }
        
        try {
            this.isRecovering = true;
            this.recoveryAttempts++;
            
            console.log(`🔄 开始第 ${this.recoveryAttempts} 次恢复尝试...`);
            
            // 1. 获取用户ID
            const userId = this.getCurrentUserId();
            if (!userId) {
                throw new Error('无法获取用户ID');
            }
            
            // 2. 检查消息容器
            const messagesContainer = document.getElementById('messagesContainer') || 
                                    document.getElementById('mobileMessagesContainer');
            if (!messagesContainer) {
                console.warn('⚠️ 消息容器未找到，1秒后重试...');
                if (this.recoveryAttempts < this.maxRetries) {
                    setTimeout(() => {
                        this.isRecovering = false;
                        this.performRecovery();
                    }, 1000);
                }
                return;
            }
            
            // 3. 获取所有处方列表
            const allPrescriptions = await this.fetchPrescriptions(userId);
            
            if (allPrescriptions.length === 0) {
                console.log('ℹ️ 用户暂无处方记录');
                this.showNotification('ℹ️ 暂无处方记录', 'info');
                return;
            }
            
            // 4. 🎯 关键修改：只获取最新的单个处方
            const latestSinglePrescription = this.getLatestSinglePrescription(allPrescriptions);
            
            console.log(`📊 数据统计:`);
            console.log(`   - 用户总处方数: ${allPrescriptions.length}`);
            console.log(`   - 恢复处方数: ${latestSinglePrescription.length} (只恢复最新的一个)`);
            
            // 5. 恢复最新的单个处方消息
            let restoredCount = 0;
            
            for (const prescription of latestSinglePrescription) {
                const prescriptionId = prescription.id;
                
                // 检查是否已存在
                const existingMsg = messagesContainer.querySelector(`[data-prescription-id="${prescription_id}"]`);
                if (existingMsg) {
                    console.log(`ℹ️ 处方 ${prescription_id} 已存在，跳过创建`);
                    continue;
                }
                
                // 创建新消息
                const messageHtml = this.createPrescriptionMessage(prescription);
                if (messageHtml) {
                    messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
                    console.log(`✅ 恢复了处方 ${prescription_id} (${prescription.status})`);
                    restoredCount++;
                }
            }
            
            // 6. 显示结果
            if (restoredCount > 0) {
                this.showNotification(`✅ 已从云端恢复最新的 ${restoredCount} 条处方状态`, 'success');
                this.scrollToBottom();
            } else {
                this.showNotification('ℹ️ 最新处方不需要恢复或已存在', 'info');
            }
            
            console.log(`🎉 恢复完成！共恢复最新的 ${restoredCount} 个处方`);
            
        } catch (error) {
            console.error('❌ 恢复失败:', error);
            this.showNotification(`❌ 恢复失败: ${error.message}`, 'error');
            
            // 重试逻辑
            if (this.recoveryAttempts < this.maxRetries) {
                console.log(`🔄 将在2秒后进行第 ${this.recoveryAttempts + 1} 次重试...`);
                setTimeout(() => {
                    this.isRecovering = false;
                    this.performRecovery();
                }, 2000);
            }
        } finally {
            this.isRecovering = false;
        }
    }
    
    /**
     * 显示通知
     */
    showNotification(message, type = 'info') {
        // 如果存在现有的通知函数，使用它
        if (typeof showSyncNotification === 'function') {
            showSyncNotification(message, type);
            return;
        }
        
        // 否则创建简单的通知
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 16px;
            border-radius: 8px;
            color: white;
            font-size: 14px;
            z-index: 10000;
            max-width: 300px;
            background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#3b82f6'};
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    /**
     * 滚动到底部
     */
    scrollToBottom() {
        try {
            if (typeof scrollToBottom === 'function') {
                scrollToBottom();
            } else {
                const messagesContainer = document.getElementById('messagesContainer') || 
                                        document.getElementById('mobileMessagesContainer');
                if (messagesContainer) {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            }
        } catch (error) {
            console.warn('⚠️ 滚动到底部失败:', error);
        }
    }
    
    /**
     * 初始化恢复系统
     */
    init() {
        console.log('🚫 简化版处方恢复系统已禁用，由主系统统一管理恢复功能');
        
        // 🔑 禁用独立恢复系统，避免与主系统冲突
        // setTimeout(() => {
        //     this.performRecovery();
        // }, 3000);
    }
}

// 创建全局实例
window.simpleRecovery = new SimpleRecoverySystem();

// 页面加载完成后自动启动
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.simpleRecovery.init();
    });
} else {
    window.simpleRecovery.init();
}