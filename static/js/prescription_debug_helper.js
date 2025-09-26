/**
 * 处方调试助手
 * 帮助诊断处方支付显示问题
 */

// 在控制台中添加调试函数
window.debugPrescription = {
    // 查看所有localStorage中的支付相关数据
    checkLocalStorage: function() {
        console.log('=== localStorage 支付状态检查 ===');
        const keys = Object.keys(localStorage);
        const prescriptionKeys = keys.filter(k => k.includes('prescription_paid'));
        
        console.log('支付相关的localStorage keys:', prescriptionKeys);
        prescriptionKeys.forEach(key => {
            console.log(`${key}: ${localStorage.getItem(key)}`);
        });
        
        return prescriptionKeys;
    },
    
    // 清除所有支付状态
    clearPaymentStatus: function() {
        const keys = this.checkLocalStorage();
        keys.forEach(key => {
            localStorage.removeItem(key);
            console.log(`已清除: ${key}`);
        });
        console.log('所有支付状态已清除');
    },
    
    // 模拟支付成功
    simulatePayment: function(prescriptionId) {
        prescriptionId = prescriptionId || 'test-' + Date.now();
        console.log('模拟支付成功:', prescriptionId);
        
        if (window.prescriptionPaymentManager) {
            window.prescriptionPaymentManager.handlePaymentSuccess(prescriptionId);
        } else {
            localStorage.setItem(`prescription_paid_${prescriptionId}`, 'true');
        }
        
        return prescriptionId;
    },
    
    // 查看当前页面的处方消息
    findPrescriptionMessages: function() {
        console.log('=== 查找处方消息 ===');
        const messages = document.querySelectorAll('.message.ai');
        let prescriptionMessages = [];
        
        messages.forEach((msg, index) => {
            const content = msg.querySelector('.message-text')?.innerText || '';
            const prescriptionId = msg.getAttribute('data-prescription-id');
            
            if (content.includes('处方') || content.includes('方剂') || prescriptionId) {
                prescriptionMessages.push({
                    index,
                    prescriptionId,
                    content: content.substring(0, 100) + '...',
                    element: msg
                });
                
                console.log(`消息 ${index}:`, {
                    prescriptionId,
                    contentPreview: content.substring(0, 100) + '...'
                });
            }
        });
        
        return prescriptionMessages;
    },
    
    // 强制重新渲染所有处方消息
    reRenderPrescriptions: function() {
        console.log('=== 强制重新渲染处方 ===');
        const prescriptionMessages = this.findPrescriptionMessages();
        
        prescriptionMessages.forEach((msgInfo) => {
            const { element, prescriptionId } = msgInfo;
            const contentEl = element.querySelector('.message-text');
            
            if (contentEl && window.prescriptionContentRenderer) {
                const originalContent = contentEl.innerText;
                console.log(`重新渲染处方 ${prescriptionId}`);
                
                const newContent = window.prescriptionContentRenderer.renderContent(
                    originalContent, 
                    prescriptionId
                );
                
                contentEl.innerHTML = newContent;
            }
        });
        
        console.log(`已重新渲染 ${prescriptionMessages.length} 个处方消息`);
    },
    
    // 检查新的处方管理系统状态
    checkNewSystem: function() {
        console.log('=== 新处方管理系统状态 ===');
        console.log('prescriptionPaymentManager:', !!window.prescriptionPaymentManager);
        console.log('prescriptionContentRenderer:', !!window.prescriptionContentRenderer);
        
        if (window.prescriptionPaymentManager) {
            console.log('支付状态缓存:', window.prescriptionPaymentManager.paymentStatus);
        }
        
        if (window.prescriptionContentRenderer) {
            console.log('内容渲染器可用');
        }
    },
    
    // 完整调试流程
    fullDebug: function() {
        console.log('🔍 开始完整调试流程...');
        this.checkNewSystem();
        this.checkLocalStorage();
        this.findPrescriptionMessages();
        console.log('🔍 调试完成，请查看上方日志');
    }
};

// 自动执行基本检查
setTimeout(() => {
    if (window.debugPrescription) {
        console.log('💡 调试助手已加载，使用 window.debugPrescription.fullDebug() 进行完整调试');
        window.debugPrescription.checkNewSystem();
    }
}, 1000);

console.log('✅ 处方调试助手已加载');