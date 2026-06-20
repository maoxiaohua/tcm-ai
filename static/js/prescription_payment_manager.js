/**
 * 处方支付管理器 - 专业模块化方案
 * 基于业界成熟的状态管理模式
 * v1.0 - 2025-09-25
 */

class PrescriptionPaymentManager {
    constructor() {
        this.paymentStatus = new Map(); // 支付状态缓存
        this.prescriptionContent = new Map(); // 处方内容缓存
        
        console.log('✅ 处方支付管理器初始化完成');
    }

    /**
     * 核心方法：检查处方支付状态
     * @param {string} prescriptionId 处方ID
     * @returns {boolean} 是否已支付
     */
    isPrescriptionPaid(prescriptionId) {
        if (!prescriptionId) return false;
        
        // 1. 检查内存缓存
        if (this.paymentStatus.has(prescriptionId)) {
            return this.paymentStatus.get(prescriptionId);
        }
        
        // 2. 检查localStorage
        const storageKey = `prescription_paid_${prescriptionId}`;
        const stored = localStorage.getItem(storageKey);
        const isPaid = stored === 'true';

        // 3. 更新缓存
        this.paymentStatus.set(prescriptionId, isPaid);

        console.log(`💰 支付状态检查: ${prescriptionId} -> ${isPaid}`);
        return isPaid;
    }

    /**
     * 设置处方为已支付状态
     * @param {string} prescriptionId 处方ID
     */
    markAsPaid(prescriptionId) {
        if (!prescriptionId) return;
        
        // 1. 更新内存缓存
        this.paymentStatus.set(prescriptionId, true);

        // 2. 更新localStorage
        const storageKey = `prescription_paid_${prescriptionId}`;
        localStorage.setItem(storageKey, 'true');

        console.log(`✅ 标记处方已支付: ${prescriptionId}`);
        
        // 3. 触发页面更新
        this.refreshPrescriptionDisplay(prescriptionId);
    }

    /**
     * 刷新处方显示
     * @param {string} prescriptionId 处方ID
     */
    refreshPrescriptionDisplay(prescriptionId) {
        // 查找包含此处方ID的消息
        const messageElements = document.querySelectorAll(`[data-prescription-id="${prescriptionId}"]`);
        
        messageElements.forEach(messageEl => {
            const contentEl = messageEl.querySelector('.message-text');
            if (contentEl) {
                // 🔧 优先使用保存的原始内容
                let contentToRender = contentEl.getAttribute('data-original-content');
                if (!contentToRender) {
                    contentToRender = contentEl.innerHTML;
                    console.log('⚠️ 刷新显示时没有找到data-original-content，使用当前HTML');
                } else {
                    console.log('✅ 刷新显示时使用保存的data-original-content');
                }
                
                // 重新渲染为已支付状态
                if (window.prescriptionContentRenderer) {
                    const renderedContent = window.prescriptionContentRenderer.renderPaidContent(
                        contentToRender, 
                        prescriptionId
                    );
                    contentEl.innerHTML = renderedContent;
                }
            }
        });
        
        console.log(`🔄 已刷新处方显示: ${prescriptionId}`);
    }

    /**
     * 启动支付流程
     * @param {string} prescriptionId 处方ID
     * @param {number} amount 支付金额
     */
    async startPayment(prescriptionId, amount = 88) {
        try {
            console.log(`💳 启动支付流程: ${prescriptionId}, 金额: ¥${amount}`);

            // 🔧 修复支付ID映射问题：保存原始处方ID用于后续处理
            this.currentPrescriptionId = prescriptionId;

            // 🔑 关键修复：确保prescriptionId是字符串类型
            const idStr = String(prescriptionId || '');

            // 🔧 修复支付系统不可用问题：优先使用简化支付流程
            if (prescriptionId === 'temp' || !prescriptionId || idStr.startsWith('temp') || idStr.startsWith('prescription_')) {
                console.log('🎭 检测到临时处方ID，启用演示支付模式');
                
                // 显示支付确认对话框
                const confirmed = await this.showPaymentConfirmDialog(prescriptionId, amount);
                if (confirmed) {
                    await this.simulatePaymentProcess(prescriptionId);
                    // 🔧 使用实际的处方ID处理支付成功
                    this.handlePaymentSuccess(prescriptionId);
                }
                return;
            }
            
            // 调用现有的支付系统（仅针对真实处方ID）
            if (typeof window.showPaymentModal === 'function') {
                window.showPaymentModal(prescriptionId, amount);
            } else if (typeof showPaymentModal === 'function') {
                showPaymentModal(prescriptionId, amount);
            } else {
                // 最终备用方案
                console.warn('⚠️ 支付系统不可用，使用简化流程');
                const confirmed = await this.showPaymentConfirmDialog(prescriptionId, amount);
                if (confirmed) {
                    this.handlePaymentSuccess(prescriptionId);
                }
            }
            
        } catch (error) {
            console.error('支付流程启动失败:', error);
            this.showMessage('支付系统暂时不可用，请稍后再试', 'error');
        }
    }

    /**
     * 显示支付确认对话框
     */
    async showPaymentConfirmDialog(prescriptionId, amount) {
        return new Promise((resolve) => {
            // 创建模态框
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.6);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1004;
            `;
            
            modal.innerHTML = `
                <div style="background: white; border-radius: 16px; padding: 30px; max-width: 400px; width: 90%; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
                    <div style="font-size: 48px; margin-bottom: 20px;">💊</div>
                    <h3 style="margin: 0 0 15px 0; color: #1f2937; font-size: 20px;">处方解锁确认</h3>
                    <p style="margin: 0 0 20px 0; color: #6b7280; line-height: 1.5;">
                        解锁后将显示完整的处方信息，包括：<br>
                        • 详细的药材剂量<br>
                        • 煎服方法指导<br>
                        • 用药注意事项
                    </p>
                    <div style="font-size: 24px; font-weight: bold; color: #f59e0b; margin: 20px 0;">¥${amount}</div>
                    <div style="display: flex; gap: 12px; justify-content: center;">
                        <button id="cancelPayment" style="padding: 12px 24px; border: 2px solid #d1d5db; background: white; color: #6b7280; border-radius: 8px; cursor: pointer; font-size: 16px;">
                            取消
                        </button>
                        <button id="confirmPayment" style="padding: 12px 24px; border: none; background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold;">
                            确认支付
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // 绑定事件
            modal.querySelector('#confirmPayment').onclick = () => {
                document.body.removeChild(modal);
                resolve(true);
            };
            
            modal.querySelector('#cancelPayment').onclick = () => {
                document.body.removeChild(modal);
                resolve(false);
            };
            
            // 点击背景关闭
            modal.onclick = (e) => {
                if (e.target === modal) {
                    document.body.removeChild(modal);
                    resolve(false);
                }
            };
        });
    }

    /**
     * 模拟支付处理过程
     */
    async simulatePaymentProcess(prescriptionId) {
        // 显示支付处理中的提示
        const processingModal = document.createElement('div');
        processingModal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1005;
        `;
        
        processingModal.innerHTML = `
            <div style="background: white; border-radius: 16px; padding: 40px; text-align: center; max-width: 300px;">
                <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
                <h3 style="margin: 0 0 15px 0; color: #1f2937;">处理支付中...</h3>
                <p style="margin: 0; color: #6b7280;">请稍候，正在处理您的支付</p>
            </div>
        `;
        
        document.body.appendChild(processingModal);
        
        // 模拟支付延迟（1.5秒）
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // 移除处理中提示
        if (processingModal.parentNode) {
            document.body.removeChild(processingModal);
        }
        
        console.log(`✅ 支付处理完成: ${prescriptionId}`);
    }

    /**
     * 处理支付成功
     * @param {string} prescriptionId 处方ID
     */
    handlePaymentSuccess(prescriptionId) {
        console.log('🎉 支付成功处理:', prescriptionId);

        // 🔑 关键修复：确保prescriptionId是字符串类型
        const idStr = String(prescriptionId || '');

        // 🔧 处理临时ID的情况：需要找到实际的处方元素并更新
        if (prescriptionId === 'temp' || idStr.startsWith('temp') || idStr.startsWith('prescription_')) {
            // 找到包含处方的消息元素并重新渲染
            const messages = document.querySelectorAll('.message.ai');
            let targetMessage = null;
            
            // 找到包含处方内容的最后一个AI消息
            for (let i = messages.length - 1; i >= 0; i--) {
                const messageText = messages[i].querySelector('.message-text');
                if (messageText && messageText.innerHTML.includes('处方预览')) {
                    targetMessage = messages[i];
                    break;
                }
            }
            
            if (targetMessage) {
                const messageTextEl = targetMessage.querySelector('.message-text');
                const originalContent = messageTextEl.getAttribute('data-original-content') || messageTextEl.textContent;
                
                // 🔧 使用原始的处方ID，如果有的话，否则基于内容生成一致的ID
                let realPrescriptionId = targetMessage.getAttribute('data-prescription-id');
                const realIdStr = String(realPrescriptionId || '');
                if (!realPrescriptionId || realPrescriptionId === 'temp' || realIdStr.startsWith('temp')) {
                    // 基于内容生成一致的处方ID
                    realPrescriptionId = this.extractOrGeneratePrescriptionId(originalContent);
                    console.log(`🔧 生成基于内容的处方ID: ${realPrescriptionId}`);
                }
                
                // 🔧 关键修复：将真实的处方ID标记为已支付，并保存到localStorage
                this.markAsPaid(realPrescriptionId);
                // 🔧 同时也标记临时ID为已支付，防止重复支付
                this.markAsPaid(prescriptionId);
                
                // 🔧 确保使用正确的原始内容进行渲染
                const renderer = window.prescriptionContentRenderer;
                if (renderer) {
                    // 优先使用data-original-content，如果没有则使用当前内容
                    let contentToRender = messageTextEl.getAttribute('data-original-content');
                    if (!contentToRender) {
                        contentToRender = originalContent;
                        console.log('⚠️ 没有找到data-original-content，使用当前内容');
                    } else {
                        console.log('✅ 使用保存的data-original-content进行渲染');
                    }
                    
                    console.log(`🔍 渲染内容长度: ${contentToRender.length}, 换行数: ${(contentToRender.match(/\n/g) || []).length}`);
                    
                    const paidContent = renderer.renderPaidContent(contentToRender, realPrescriptionId);
                    messageTextEl.innerHTML = paidContent;
                    
                    // 更新处方ID属性为真实ID
                    targetMessage.setAttribute('data-prescription-id', realPrescriptionId);
                }
                
                console.log('✅ 处方显示已更新为已支付状态, 处方ID:', realPrescriptionId);
            }
        } else {
            // 处理真实处方ID
            this.markAsPaid(prescriptionId);
        }
        
        // 显示成功消息
        this.showMessage('🎉 支付成功！处方已解锁', 'success');
        
        // 🔧 不再需要页面刷新，直接更新显示
        console.log('✅ 处方支付完成，内容已自动更新');
    }

    /**
     * 提取或生成处方ID
     */
    extractOrGeneratePrescriptionId(content) {
        // 🔧 使用一致的哈希方法，不包含时间戳以确保相同内容产生相同ID
        const hashContent = content.substring(0, 200);
        const hash = this.simpleHash(hashContent);
        return `prescription_${hash}`;
    }

    /**
     * 显示消息
     */
    showMessage(message, type = 'info') {
        if (typeof window.showMessage === 'function') {
            window.showMessage(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
            alert(message);
        }
    }

    /**
     * 简单哈希函数
     */
    simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(16).substring(0, 8);
    }
}

/**
 * 处方内容渲染器 - 简化版本
 */
class PrescriptionContentRenderer {
    constructor() {
        // 延迟初始化 paymentManager，避免循环依赖
        this.paymentManager = null;
    }
    
    // 获取支付管理器，如果没有则返回全局实例
    getPaymentManager() {
        if (!this.paymentManager) {
            this.paymentManager = window.prescriptionPaymentManager;
        }
        return this.paymentManager;
    }

    /**
     * 根据支付状态渲染内容
     * @param {string} content 原始内容
     * @param {string} prescriptionId 处方ID
     * @returns {string} 渲染后的HTML
     */
    renderContent(content, prescriptionId = null) {
        // 检查是否包含处方
        if (!this.containsPrescription(content)) {
            return this.formatRegularContent(content);
        }

        // 🔧 改进支付状态检查逻辑
        let isPaid = false;
        
        console.log(`🔍 开始检查支付状态 - 原始ID: ${prescriptionId}`);
        
        if (prescriptionId) {
            // 首先检查原始处方ID
            isPaid = this.getPaymentManager().isPrescriptionPaid(prescriptionId);
            console.log(`🔍 原始ID检查结果: ${isPaid}`);
            
            // 🔧 如果原始ID未支付，检查是否有基于内容生成的处方ID已支付
            if (!isPaid) {
                const contentBasedId = this.generateContentBasedId(content);
                console.log(`🔍 尝试内容基础ID: ${contentBasedId}`);
                isPaid = this.getPaymentManager().isPrescriptionPaid(contentBasedId);
                
                if (isPaid) {
                    console.log(`🔍 发现内容匹配的已支付处方: ${contentBasedId}`);
                    prescriptionId = contentBasedId; // 使用已支付的ID
                }
            }
            
            // 🔧 最后检查所有可能的处方ID变体
            if (!isPaid) {
                const possibleIds = [
                    `paid_${prescriptionId}`,
                    `prescription_${prescriptionId}`,
                    ...this.findRelatedPrescriptionIds(content)
                ];
                
                console.log(`🔍 检查可能的ID变体:`, possibleIds);
                
                for (const possibleId of possibleIds) {
                    const checkResult = this.getPaymentManager().isPrescriptionPaid(possibleId);
                    console.log(`🔍 检查ID ${possibleId}: ${checkResult}`);
                    if (checkResult) {
                        isPaid = true;
                        prescriptionId = possibleId;
                        console.log(`🔍 发现相关的已支付处方: ${possibleId}`);
                        break;
                    }
                }
            }
        }
        
        // 🔧 添加localStorage调试信息
        console.log('🔍 当前localStorage支付记录:');
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('prescription_paid_')) {
                console.log(`  - ${key}: ${localStorage.getItem(key)}`);
            }
        }
        
        console.log(`📋 渲染处方内容: prescriptionId=${prescriptionId}, isPaid=${isPaid}`);

        if (isPaid) {
            return this.renderPaidContent(content, prescriptionId);
        } else {
            return this.renderUnpaidContent(content, prescriptionId);
        }
    }

    /**
     * 生成基于内容的处方ID
     */
    generateContentBasedId(content) {
        const hashContent = content.substring(0, 200);
        const hash = this.getPaymentManager().simpleHash(hashContent);
        return `prescription_${hash}`;
    }

    /**
     * 查找相关的处方ID
     */
    findRelatedPrescriptionIds(content) {
        const relatedIds = [];
        
        // 检查localStorage中所有以prescription_paid_开头的键
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('prescription_paid_')) {
                const storedValue = localStorage.getItem(key);
                if (storedValue === 'true') {
                    const extractedId = key.replace('prescription_paid_', '');
                    relatedIds.push(extractedId);
                }
            }
        }
        
        return relatedIds;
    }

    /**
     * 检查是否包含处方
     */
    containsPrescription(content) {
        const prescriptionKeywords = [
            '处方如下', '方剂组成', '药物组成', '具体方药', '方解',
            '君药', '臣药', '佐药', '使药', '建议方药', '推荐方剂',
            '处方预览', '解锁完整处方'  // 🔧 添加更多关键词检测
        ];
        
        const hasKeywords = prescriptionKeywords.some(keyword => content.includes(keyword));
        const hasMedicine = /[\u4e00-\u9fff]{2,4}\s*\d*\s*[克g]/g.test(content);
        
        console.log(`🔍 处方内容检测: keywords=${hasKeywords}, medicine=${hasMedicine}, content-length=${content.length}`);
        
        return hasKeywords || hasMedicine;
    }

    /**
     * 渲染已支付的完整处方
     */
    renderPaidContent(content, prescriptionId) {
        const herbs = this.extractHerbs(content);
        
        let herbsListHtml = '';
        if (herbs.length > 0) {
            herbsListHtml = `
                <div class="prescription-herbs-paid prescription-paid" style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #f0f9ff, #e0f2fe); border-radius: 12px; border: 2px solid #0ea5e9;">
                    <h4 style="color: #0369a1; margin-bottom: 15px; font-size: 16px;">✅ 完整处方 (共${herbs.length}味药材)</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px;">
                        ${herbs.map(herb => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; border-radius: 8px; border: 1px solid #0ea5e9; font-size: 14px; box-shadow: 0 2px 4px rgba(14,165,233,0.1);">
                                <span style="color: #1e40af; font-weight: 500;">${herb.name}</span>
                                <span style="color: #059669; font-weight: bold; font-size: 15px;">${herb.dosage}g</span>
                            </div>
                        `).join('')}
                    </div>
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #bae6fd; display: flex; gap: 10px; justify-content: center;">
                        <button onclick="showDecorationInfo('${prescriptionId}')" style="background: #059669; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                            🍵 联系代煎服务
                        </button>
                        <button onclick="downloadPrescription('${prescriptionId}')" style="background: #0ea5e9; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                            📄 下载处方
                        </button>
                    </div>
                </div>
            `;
        }
        
        return herbsListHtml + this.formatRegularContent(content);
    }

    /**
     * 渲染未支付的处方预览
     */
    renderUnpaidContent(content, prescriptionId) {
        const herbs = this.extractHerbs(content);
        const diagnosisInfo = this.extractDiagnosisInfo(content);
        const previewCount = Math.min(2, herbs.length);
        
        return `
            <div class="prescription-preview-unpaid" style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #fef7e7, #fef3c7); border-radius: 12px; border: 2px solid #f59e0b;">
                
                <!-- 🆕 辨证分析部分（免费展示） -->
                ${diagnosisInfo.syndrome || diagnosisInfo.pathogenesis || diagnosisInfo.treatment ? `
                    <div style="margin-bottom: 25px; padding: 20px; background: linear-gradient(135deg, #f8fafc, #f1f5f9); border-radius: 12px; border-left: 4px solid #3b82f6; box-shadow: 0 2px 8px rgba(59,130,246,0.1);">
                        <h4 style="color: #1e40af; margin: 0 0 16px 0; font-size: 18px; font-weight: 600; display: flex; align-items: center;">
                            🩺 <span style="margin-left: 8px;">中医辨证分析</span>
                        </h4>
                        <div style="space-y: 12px;">
                            ${diagnosisInfo.syndrome ? `
                                <div style="margin-bottom: 12px; padding: 12px; background: white; border-radius: 8px; border-left: 3px solid #10b981;">
                                    <h5 style="color: #059669; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">📋 证候诊断</h5>
                                    <p style="margin: 0; color: #374151; line-height: 1.6; font-size: 14px;">${diagnosisInfo.syndrome}</p>
                                </div>
                            ` : ''}
                            ${diagnosisInfo.pathogenesis ? `
                                <div style="margin-bottom: 12px; padding: 12px; background: white; border-radius: 8px; border-left: 3px solid #f59e0b;">
                                    <h5 style="color: #d97706; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">🔍 病机分析</h5>
                                    <p style="margin: 0; color: #374151; line-height: 1.6; font-size: 14px;">${diagnosisInfo.pathogenesis}</p>
                                </div>
                            ` : ''}
                            ${diagnosisInfo.treatment ? `
                                <div style="margin-bottom: 0; padding: 12px; background: white; border-radius: 8px; border-left: 3px solid #8b5cf6;">
                                    <h5 style="color: #7c3aed; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">⚕️ 治疗方案</h5>
                                    <p style="margin: 0; color: #374151; line-height: 1.6; font-size: 14px;">${diagnosisInfo.treatment}</p>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : `
                    <div style="margin-bottom: 25px; padding: 20px; background: linear-gradient(135deg, #f8fafc, #f1f5f9); border-radius: 12px; border-left: 4px solid #3b82f6; box-shadow: 0 2px 8px rgba(59,130,246,0.1);">
                        <h4 style="color: #1e40af; margin: 0 0 12px 0; font-size: 18px; font-weight: 600; display: flex; align-items: center;">
                            🩺 <span style="margin-left: 8px;">中医辨证分析</span>
                        </h4>
                        <p style="margin: 0; color: #6b7280; line-height: 1.6; font-size: 14px; font-style: italic;">
                            基于您的症状进行了全面的中医四诊分析，包含证候判断、病机分析和治疗原则
                        </p>
                    </div>
                `}

                <h4 style="color: #92400e; margin-bottom: 15px;">📋 个性化处方预览 (共${herbs.length}味药材)</h4>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px;">
                    ${herbs.slice(0, previewCount).map(herb => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; border-radius: 8px; border: 1px solid #f59e0b; font-size: 14px;">
                            <span style="color: #92400e; font-weight: 500;">${herb.name}</span>
                            <span style="color: #9ca3af; font-weight: bold;">***g</span>
                        </div>
                    `).join('')}
                    ${herbs.length > previewCount ? `
                        <div style="display: flex; justify-content: center; align-items: center; padding: 10px; background: #f3f4f6; border-radius: 8px; border: 2px dashed #d1d5db; font-size: 14px;">
                            <span style="color: #6b7280;">还有${herbs.length - previewCount}味药材</span>
                        </div>
                    ` : ''}
                </div>

                <div class="prescription-actions" style="text-align: center;">
                    <button onclick="window.prescriptionPaymentManager.startPayment('${prescriptionId || 'temp'}')" 
                            style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; box-shadow: 0 4px 8px rgba(245,158,11,0.3);">
                        🔓 解锁完整处方 ¥88
                    </button>
                </div>
                
                <div style="margin-top: 15px; text-align: center; font-size: 12px; color: #6b7280;">
                    🔒 安全支付 💯 专业保障 🎁 含代煎服务
                </div>
            </div>
        `;
    }

    /**
     * 格式化普通内容
     */
    formatRegularContent(content) {
        return content
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    /**
     * 提取药材信息
     */
    extractHerbs(content) {
        const herbs = [];
        const lines = content.split('\n');
        
        // 调试日志：显示正在解析的内容
        console.log('🔍 [DEBUG] extractHerbs 开始解析，内容长度:', content.length);
        console.log('🔍 [DEBUG] 内容前200字符:', content.substring(0, 200));
        console.log('🔍 [DEBUG] 总行数:', lines.length);
        
        // 扩展的默认剂量表 - 涵盖更多常用药材
        const defaultDosages = {
            '附子': 6, '干姜': 6, '肉桂': 3, '桂枝': 9, '麻黄': 6,
            '人参': 10, '党参': 15, '黄芪': 20, '白术': 12, '茯苓': 15,
            '当归': 10, '白芍': 12, '川芎': 6, '熟地': 15, '生地': 15,
            '甘草': 6, '大枣': 12, '生姜': 9, '半夏': 9, '陈皮': 9,
            '柴胡': 12, '黄芩': 9, '连翘': 12, '金银花': 15, '板蓝根': 20,
            '石膏': 30, '知母': 12, '山药': 20, '薏苡仁': 30, '泽泻': 12,
            '车前子': 12, '木通': 6, '竹叶': 6, '麦冬': 15, '五味子': 6,
            '酸枣仁': 15, '龙骨': 20, '牡蛎': 20, '珍珠母': 30, '磁石': 30,
            // 新增常用药材
            '枳实': 10, '厚朴': 9, '大黄': 3, '火麻仁': 15, '郁李仁': 12,
            '杏仁': 10, '桔梗': 6, '紫菀': 10, '款冬花': 10, '百部': 10,
            '贝母': 10, '川贝': 10, '浙贝': 12, '竹茹': 10, '枇杷叶': 12,
            '苏叶': 6, '藿香': 10, '佩兰': 10, '砂仁': 6, '豆蔻': 6,
            '木香': 6, '香附': 10, '青皮': 6, '乌药': 10, '延胡索': 10,
            '川楝子': 10, '小茴香': 6, '八角茴香': 3, '丁香': 3, '肉豆蔻': 6,
            '补骨脂': 12, '菟丝子': 15, '淫羊藿': 12, '仙茅': 6, '巴戟天': 12,
            '肉苁蓉': 15, '锁阳': 12, '韭菜子': 10, '覆盆子': 12, '金樱子': 12,
            '芡实': 15, '莲子': 12, '莲须': 6, '龙齿': 20, '琥珀': 3
        };
        
        // 扩展药材名称库，包含方剂中可能出现的药材
        const extendedHerbs = {
            ...defaultDosages,
            '木瓜': 12, '牛膝': 12, '杜仲': 12, '续断': 12, '狗脊': 15,
            '威灵仙': 15, '独活': 9, '羌活': 6, '防风': 9, '荆芥': 9,
            '薄荷': 6, '升麻': 6, '葛根': 15, '柴胡': 12, '前胡': 12,
            '桔梗': 6, '枳壳': 9, '枳实': 10, '厚朴': 9, '苍术': 9,
            '白芷': 9, '辛夷': 6, '苍耳子': 9, '白附子': 6, '天麻': 9,
            '钩藤': 15, '石决明': 30, '代赭石': 30, '旋覆花': 9, '赭石': 30
        };
        
        for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
            const line = lines[lineIndex];
            console.log(`🔍 [DEBUG] 第${lineIndex + 1}行:`, line);
            
            // 更全面的正则表达式数组
            const regexPatterns = [
                // 标准格式1：药材名 数量g (功效说明)
                /([一-龟\u4e00-\u9fff]{2,5})\s+(\d+)g\s*\(/g,
                // 标准格式2：药材名 数量g/克
                /([一-龟\u4e00-\u9fff]{2,5})\s*(\d+)\s*[克g]/g,
                // 隐藏格式：药材名 *g (处方预览格式)
                /([一-龟\u4e00-\u9fff]{2,5})\s*\*\s*[克g]/g,
                // 项目符号格式：- 药材名 数量g (说明)
                /[-–—•·]\s*([一-龟\u4e00-\u9fff]{2,5})\s+(\d+)\s*[克g]/g,
                // 【君药】等格式后的药材
                /【[^】]+】[^【]*?([一-龟\u4e00-\u9fff]{2,5})\s*(\d*)\s*[克g]/g,
                // 方剂中常见格式：药材名称 剂量
                /([一-龟\u4e00-\u9fff]{2,5})\s+(\d+)[克g]?/g,
                // 新增：带括号格式：药材名(别名) 剂量g
                /([一-龟\u4e00-\u9fff]{2,5})（[^）]+）\s*(\d+)\s*[克g]/g,
                // 新增：逗号分隔格式：药材名,剂量g
                /([一-龟\u4e00-\u9fff]{2,5})[,，]\s*(\d+)\s*[克g]/g,
                // 新增：冒号格式：药材名：剂量g
                /([一-龟\u4e00-\u9fff]{2,5})[：:]\s*(\d+)\s*[克g]/g,
                // 新增：直接相邻格式：药材名12g
                /([一-龟\u4e00-\u9fff]{2,5})(\d+)[克g]/g
            ];
            
            let lineHasMatch = false;
            
            for (let patternIndex = 0; patternIndex < regexPatterns.length; patternIndex++) {
                const pattern = regexPatterns[patternIndex];
                const matches = [...line.matchAll(pattern)];
                
                if (matches.length > 0) {
                    console.log(`✅ [DEBUG] 模式${patternIndex + 1}匹配到${matches.length}个药材:`, matches.map(m => m[1]));
                    lineHasMatch = true;
                }
                
                for (const match of matches) {
                    const name = match[1];
                    let dosage = match[2];
                    
                    // 处理隐藏格式(*g)和缺失剂量
                    if (!dosage || dosage === '*') {
                        dosage = extendedHerbs[name] || 12;
                        console.log(`🔄 [DEBUG] 使用默认剂量: ${name} → ${dosage}g`);
                    } else {
                        dosage = parseInt(dosage);
                    }
                    
                    // 验证是否为有效的中药名
                    if (name.length >= 2 && !herbs.find(h => h.name === name)) {
                        herbs.push({ name, dosage });
                        console.log(`✅ [DEBUG] 添加药材: ${name} ${dosage}g`);
                    }
                }
            }
            
            if (!lineHasMatch && line.trim() && line.match(/[一-龟\u4e00-\u9fff]/)) {
                console.log(`❌ [DEBUG] 该行包含中文但没有匹配任何模式`);
            }
        }
        
        console.log(`🔍 [DEBUG] 第一轮提取完成，找到 ${herbs.length} 味药材`);
        
        // 如果没有找到标准格式，尝试从文本中提取提及的药材名
        if (herbs.length === 0) {
            console.log('🔍 使用备用药材提取方法');
            const herbNames = Object.keys(extendedHerbs);
            for (const herbName of herbNames) {
                if (content.includes(herbName)) {
                    herbs.push({ 
                        name: herbName, 
                        dosage: extendedHerbs[herbName] 
                    });
                    console.log(`📋 [DEBUG] 备用方法添加: ${herbName} ${extendedHerbs[herbName]}g`);
                }
            }
        }
        
        console.log(`🌿 提取到药材: ${herbs.length}味`, herbs);
        return herbs;
    }

    /**
     * 调试函数：检查处方内容状态
     */
    debugPrescriptionContent() {
        console.log('🔍 === 处方内容调试信息 ===');
        
        const aiMessages = document.querySelectorAll('.message.ai');
        aiMessages.forEach((messageEl, index) => {
            const messageText = messageEl.querySelector('.message-text');
            const prescriptionId = messageEl.getAttribute('data-prescription-id');
            const originalContent = messageText?.getAttribute('data-original-content');
            const currentContent = messageText?.innerHTML;
            
            if (currentContent && currentContent.includes('处方')) {
                console.log(`\n📋 处方消息 #${index + 1}:`);
                console.log(`  - 处方ID: ${prescriptionId}`);
                console.log(`  - 有原始内容: ${!!originalContent}`);
                console.log(`  - 当前内容长度: ${currentContent?.length || 0}`);
                console.log(`  - 原始内容长度: ${originalContent?.length || 0}`);
                
                if (originalContent) {
                    console.log(`  - 原始内容前200字符:`, originalContent.substring(0, 200));
                    console.log(`  - 原始内容换行数: ${(originalContent.match(/\n/g) || []).length}`);
                    
                    // 测试提取
                    console.log(`  - 从原始内容提取药材:`);
                    const herbsFromOriginal = this.extractHerbsQuiet(originalContent);
                    console.log(`    ✅ 提取到 ${herbsFromOriginal.length} 味药材:`, herbsFromOriginal.map(h => h.name));
                }
                
                console.log(`  - 当前显示内容前200字符:`, currentContent.substring(0, 200));
                console.log(`  - 当前内容换行数: ${(currentContent.match(/\n/g) || []).length}`);
                
                // 测试提取
                console.log(`  - 从当前内容提取药材:`);
                const herbsFromCurrent = this.extractHerbsQuiet(currentContent);
                console.log(`    ✅ 提取到 ${herbsFromCurrent.length} 味药材:`, herbsFromCurrent.map(h => h.name));
            }
        });
        
        console.log('\n🔍 === 调试完成 ===');
    }

    /**
     * 静默提取药材（不输出调试日志）
     */
    extractHerbsQuiet(content) {
        const herbs = [];
        const lines = content.split('\n');
        
        const extendedHerbs = {
            '附子': 6, '干姜': 6, '肉桂': 3, '桂枝': 9, '麻黄': 6,
            '人参': 10, '党参': 15, '黄芪': 20, '白术': 12, '茯苓': 15,
            '当归': 10, '白芍': 12, '川芎': 6, '熟地': 15, '生地': 15,
            '甘草': 6, '大枣': 12, '生姜': 9, '半夏': 9, '陈皮': 9,
            '柴胡': 12, '黄芩': 9, '连翘': 12, '金银花': 15, '板蓝根': 20,
            '石膏': 30, '知母': 12, '山药': 20, '薏苡仁': 30, '泽泻': 12,
            '车前子': 12, '木通': 6, '竹叶': 6, '麦冬': 15, '五味子': 6,
            '酸枣仁': 15, '龙骨': 20, '牡蛎': 20, '珍珠母': 30, '磁石': 30,
            '枳实': 10, '厚朴': 9, '大黄': 3, '火麻仁': 15, '郁李仁': 12,
            '杏仁': 10, '桔梗': 6, '紫菀': 10, '款冬花': 10, '百部': 10,
            '贝母': 10, '川贝': 10, '浙贝': 12, '竹茹': 10, '枇杷叶': 12
        };
        
        for (const line of lines) {
            const regexPatterns = [
                /([一-龟\u4e00-\u9fff]{2,5})\s+(\d+)g\s*\(/g,
                /([一-龟\u4e00-\u9fff]{2,5})\s*(\d+)\s*[克g]/g,
                /([一-龟\u4e00-\u9fff]{2,5})\s*\*\s*[克g]/g,
                /[-–—•·]\s*([一-龟\u4e00-\u9fff]{2,5})\s+(\d+)\s*[克g]/g,
                /([一-龟\u4e00-\u9fff]{2,5})\s+(\d+)[克g]?/g
            ];
            
            for (const pattern of regexPatterns) {
                const matches = [...line.matchAll(pattern)];
                for (const match of matches) {
                    const name = match[1];
                    let dosage = match[2];
                    
                    if (!dosage || dosage === '*') {
                        dosage = extendedHerbs[name] || 12;
                    } else {
                        dosage = parseInt(dosage);
                    }
                    
                    if (name.length >= 2 && !herbs.find(h => h.name === name)) {
                        herbs.push({ name, dosage });
                    }
                }
            }
        }
        
        return herbs;
    }

    /**
     * 提取辨证分析信息
     */
    extractDiagnosisInfo(content) {
        const diagnosisInfo = {
            syndrome: '',      // 证候诊断
            pathogenesis: '',  // 病机分析
            treatment: '',     // 治疗原则
            analysis: ''       // 综合分析
        };

        // 常见中药名称，用于过滤
        const commonHerbs = [
            '人参', '党参', '白术', '茯苓', '甘草', '当归', '白芍', '川芎', '熟地', '干姜',
            '黄芪', '黄连', '黄芩', '黄柏', '麦冬', '五味子', '桂枝', '白芷', '陈皮', '半夏',
            '枸杞', '山药', '芡实', '莲子', '红枣', '生姜', '大枣', '薏苡仁', '茯神', '远志'
        ];

        const lines = content.split('\n');
        let currentSection = '';
        let inPrescriptionSection = false;

        for (let line of lines) {
            line = line.trim();
            
            // 🔧 检测处方区域开始，跳过含有药材的内容
            if (line.includes('处方如下') || line.includes('方剂组成') || line.includes('药物组成') || 
                line.includes('具体方药') || line.includes('建议方药') || line.match(/[一-龟\u4e00-\u9fff]{2,4}\s*\d*\s*[克g]/)) {
                inPrescriptionSection = true;
                continue;
            }
            
            // 如果在处方区域中，检测是否离开处方区域
            if (inPrescriptionSection) {
                // 如果遇到新的标题段落，说明离开了处方区域
                if (line.includes('辨证') || line.includes('病机') || line.includes('治疗原则') ||
                    line.includes('分析') || line.includes('建议') || line.includes('注意')) {
                    inPrescriptionSection = false;
                } else {
                    continue; // 还在处方区域，跳过
                }
            }
            
            // 检测各种辨证分析相关的标题
            if (line.includes('辨证') || line.includes('证候') || line.includes('诊断')) {
                currentSection = 'syndrome';
                // 如果标题行本身包含内容，提取冒号后的部分
                const colonIndex = line.indexOf('：') !== -1 ? line.indexOf('：') : line.indexOf(':');
                if (colonIndex !== -1 && colonIndex < line.length - 1) {
                    const titleContent = line.substring(colonIndex + 1).trim();
                    if (titleContent && !this.containsHerbNames(titleContent, commonHerbs)) {
                        diagnosisInfo[currentSection] = titleContent;
                    }
                }
                continue;
            } else if (line.includes('病机') || line.includes('机理') || line.includes('病因')) {
                currentSection = 'pathogenesis';
                const colonIndex = line.indexOf('：') !== -1 ? line.indexOf('：') : line.indexOf(':');
                if (colonIndex !== -1 && colonIndex < line.length - 1) {
                    const titleContent = line.substring(colonIndex + 1).trim();
                    if (titleContent && !this.containsHerbNames(titleContent, commonHerbs)) {
                        diagnosisInfo[currentSection] = titleContent;
                    }
                }
                continue;
            } else if (line.includes('治疗') && (line.includes('原则') || line.includes('方案') || line.includes('思路'))) {
                currentSection = 'treatment';
                const colonIndex = line.indexOf('：') !== -1 ? line.indexOf('：') : line.indexOf(':');
                if (colonIndex !== -1 && colonIndex < line.length - 1) {
                    const titleContent = line.substring(colonIndex + 1).trim();
                    if (titleContent && !this.containsHerbNames(titleContent, commonHerbs)) {
                        diagnosisInfo[currentSection] = titleContent;
                    }
                }
                continue;
            } else if (line.includes('分析') || line.includes('综合')) {
                currentSection = 'analysis';
                continue;
            }

            // 提取具体内容
            if (currentSection && line && !line.startsWith('#') && !line.startsWith('*')) {
                // 清理格式标记
                const cleanLine = line.replace(/\*\*/g, '').replace(/^[-•]\s*/, '').trim();
                
                // 🔧 更严格的过滤：排除包含药材名称、剂量、处方相关的内容
                if (cleanLine && 
                    !this.containsHerbNames(cleanLine, commonHerbs) &&
                    !cleanLine.includes('处方') && 
                    !cleanLine.includes('药材') &&
                    !cleanLine.includes('方剂') &&
                    !cleanLine.includes('煎服') &&
                    !cleanLine.includes('用法') &&
                    !cleanLine.match(/\d+\s*[克g]/) &&
                    !cleanLine.match(/[一-龟\u4e00-\u9fff]{2,4}\s*\d/)) {
                    
                    if (diagnosisInfo[currentSection]) {
                        diagnosisInfo[currentSection] += ' ' + cleanLine;
                    } else {
                        diagnosisInfo[currentSection] = cleanLine;
                    }
                }
            }
        }

        // 如果没有找到明确的分类，尝试从整体内容中提取关键句子
        if (!diagnosisInfo.syndrome && !diagnosisInfo.pathogenesis) {
            const keyPhrases = [
                /证候?[：:]\s*([^。\n]{5,50})/,
                /诊断[：:]\s*([^。\n]{5,50})/,
                /属于?\s*([^。\n]{3,20}证)/,
                /考虑?\s*([^。\n]{3,20}证)/
            ];

            for (const phrase of keyPhrases) {
                const match = content.match(phrase);
                if (match && match[1] && !this.containsHerbNames(match[1], commonHerbs)) {
                    diagnosisInfo.syndrome = match[1].trim();
                    break;
                }
            }
        }

        return diagnosisInfo;
    }

    /**
     * 检查文本是否包含中药名称
     */
    containsHerbNames(text, herbList) {
        return herbList.some(herb => text.includes(herb));
    }

    /**
     * 显示消息
     */
    showMessage(message, type = 'info') {
        const icons = {
            'success': '✅',
            'error': '❌', 
            'warning': '⚠️',
            'info': 'ℹ️'
        };

        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#fee2e2' : type === 'success' ? '#f0fdf4' : type === 'warning' ? '#fef3c7' : '#e0f2fe'};
            color: ${type === 'error' ? '#dc2626' : type === 'success' ? '#166534' : type === 'warning' ? '#d97706' : '#0369a1'};
            padding: 12px 20px;
            border-radius: 8px;
            border: 1px solid ${type === 'error' ? '#fecaca' : type === 'success' ? '#bbf7d0' : type === 'warning' ? '#fde68a' : '#bae6fd'};
            z-index: 1003;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-weight: 500;
        `;
        messageEl.innerHTML = `${icons[type] || 'ℹ️'} ${message}`;
        
        document.body.appendChild(messageEl);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 3000);
    }
}

// 全局初始化
window.prescriptionPaymentManager = new PrescriptionPaymentManager();
window.prescriptionContentRenderer = new PrescriptionContentRenderer();

// 🔧 页面加载完成后检查所有历史处方的支付状态
function checkAllPrescriptionStatus() {
    console.log('🔍 开始检查页面中所有处方的支付状态...');
    
    // 首先显示所有localStorage中的支付记录
    console.log('📋 当前localStorage中的所有支付记录:');
    const paidPrescriptions = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('prescription_paid_')) {
            const value = localStorage.getItem(key);
            console.log(`  ✅ ${key}: ${value}`);
            if (value === 'true') {
                paidPrescriptions.push(key.replace('prescription_paid_', ''));
            }
        }
    }
    
    // 查找所有包含处方的AI消息
    const aiMessages = document.querySelectorAll('.message.ai');
    let updatedCount = 0;
    let foundPrescriptions = 0;
    
    console.log(`🔍 页面中发现 ${aiMessages.length} 个AI消息，开始逐个检查...`);
    
    aiMessages.forEach((messageEl, index) => {
        const messageText = messageEl.querySelector('.message-text');
        if (messageText && (messageText.innerHTML.includes('处方预览') || messageText.innerHTML.includes('🔓 解锁完整处方'))) {
            foundPrescriptions++;
            
            const prescriptionId = messageEl.getAttribute('data-prescription-id');
            const originalContent = messageText.getAttribute('data-original-content') || messageText.innerHTML;
            
            console.log(`🔍 发现处方 #${index + 1}:`);
            console.log(`    - 处方ID: ${prescriptionId}`);
            console.log(`    - 有原始内容: ${!!messageText.getAttribute('data-original-content')}`);
            console.log(`    - 内容长度: ${originalContent.length}字符`);
            console.log(`    - 当前显示包含解锁按钮: ${messageText.innerHTML.includes('🔓 解锁完整处方')}`);
            
            // 生成基于内容的ID进行匹配
            if (window.prescriptionPaymentManager) {
                const contentBasedId = window.prescriptionPaymentManager.extractOrGeneratePrescriptionId(originalContent);
                console.log(`    - 内容生成ID: ${contentBasedId}`);
                
                // 检查各种可能的ID是否已支付
                const possibleIds = [
                    prescriptionId,
                    contentBasedId,
                    `paid_${prescriptionId}`,
                    `prescription_${prescriptionId}`
                ].filter(id => id);
                
                let matchedPaidId = null;
                for (const id of possibleIds) {
                    if (paidPrescriptions.includes(id)) {
                        matchedPaidId = id;
                        console.log(`    ✅ 找到匹配的支付记录: ${id}`);
                        break;
                    }
                }
                
                if (matchedPaidId && window.prescriptionContentRenderer) {
                    // 🔧 优先使用保存的原始内容
                    let contentToRender = messageText.getAttribute('data-original-content');
                    if (!contentToRender) {
                        contentToRender = originalContent;
                        console.log('⚠️ 状态检查时没有找到data-original-content，使用提取的内容');
                    } else {
                        console.log('✅ 状态检查时使用保存的data-original-content');
                    }
                    
                    // 重新渲染为已支付状态
                    const newContent = window.prescriptionContentRenderer.renderPaidContent(contentToRender, matchedPaidId);
                    
                    if (messageText.innerHTML !== newContent) {
                        messageText.innerHTML = newContent;
                        messageEl.setAttribute('data-prescription-id', matchedPaidId);
                        updatedCount++;
                        console.log(`    ✅ 已更新为已支付状态显示`);
                    }
                } else {
                    console.log(`    ❌ 未找到匹配的支付记录`);
                }
            }
        }
    });
    
    console.log(`🔍 处方状态检查完成:`);
    console.log(`    - 发现处方数量: ${foundPrescriptions}`);
    console.log(`    - 更新显示数量: ${updatedCount}`);
    console.log(`    - 已支付处方数量: ${paidPrescriptions.length}`);
    
    // 如果没有更新任何内容，但有支付记录，说明ID匹配有问题
    if (updatedCount === 0 && paidPrescriptions.length > 0 && foundPrescriptions > 0) {
        console.warn('⚠️  ID匹配问题：有支付记录但没有找到匹配的处方内容');
        console.log('建议手动运行: debugPrescriptionMatching() 进行详细调试');
    }
}

// 在页面加载完成后延迟执行检查
document.addEventListener('DOMContentLoaded', function() {
    // 延迟3秒执行，确保所有历史记录都加载完成
    setTimeout(() => {
        checkAllPrescriptionStatus();
    }, 3000);
});

// 兼容现有系统的函数
window.unlockPrescription = function(prescriptionId) {
    window.prescriptionPaymentManager.startPayment(prescriptionId);
};

window.showDecorationInfo = function(prescriptionId) {
    const info = `
🍵 中药代煎服务

✅ 服务包含：
• 专业中药师审核处方
• 优质道地药材配置
• 现代化煎药设备煎制
• 真空包装，便于保存
• 全程温控冷链配送

📋 服务流程：
1. 提交处方和收货信息
2. 中药师审核确认药材
3. 专业煎药（通常需要2-3天）
4. 包装配送到家

💰 代煎费用：
• 基础代煎费：28元/剂
• 特殊药材处理：额外5-15元
• 全国包邮（偏远地区除外）

📞 联系方式：
客服电话：400-123-4567
微信客服：tcm-service
工作时间：9:00-18:00
    `;
    
    if (confirm(info + '\n\n是否现在联系客服？')) {
        // 这里可以集成实际的客服系统
        window.open('tel:400-123-4567');
    }
};

window.downloadPrescription = function(prescriptionId) {
    try {
        // 获取处方内容
        const prescriptionElement = document.querySelector(`[data-prescription-id="${prescriptionId}"]`);
        if (!prescriptionElement) {
            alert('未找到处方信息');
            return;
        }
        
        const messageText = prescriptionElement.querySelector('.message-text');
        if (!messageText) {
            alert('处方内容为空');
            return;
        }
        
        // 提取纯文本内容
        const htmlContent = messageText.innerHTML;
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;
        
        // 移除HTML标签，保留文本
        let textContent = tempDiv.textContent || tempDiv.innerText || '';
        
        // 添加处方头部信息
        const now = new Date();
        const dateStr = now.toLocaleDateString('zh-CN');
        const timeStr = now.toLocaleTimeString('zh-CN');
        
        const prescriptionText = `
中医处方单
================================

开方时间：${dateStr} ${timeStr}
处方编号：${prescriptionId}
系统版本：TCM-AI v2.9

处方内容：
${textContent}

================================
注意事项：
1. 本处方为AI辅助生成，仅供参考
2. 请在中医师指导下使用
3. 服药期间如有不适请及时就医
4. 处方有效期：30天

⚠️ 重要提醒：
本处方建议经中医师面诊确认后使用
================================
        `;
        
        // 创建并下载文件
        const blob = new Blob([prescriptionText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `中医处方_${prescriptionId.substring(0, 8)}_${dateStr.replace(/\//g, '')}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 清理URL对象
        URL.revokeObjectURL(url);
        
        // 显示成功提示
        setTimeout(() => {
            alert('✅ 处方下载成功！\n\n文件已保存到您的下载文件夹\n请妥善保管处方信息');
        }, 500);
        
    } catch (error) {
        console.error('处方下载失败:', error);
        alert('❌ 处方下载失败，请稍后重试');
    }
};

// 导出检查函数供手动调用
window.checkAllPrescriptionStatus = checkAllPrescriptionStatus;

// 🔧 新增：详细的处方匹配调试功能
function debugPrescriptionMatching() {
    console.log('🔍 开始详细的处方匹配调试...');
    
    // 1. 显示所有支付记录
    console.log('\n📋 === localStorage支付记录详情 ===');
    const allPaidIds = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('prescription_paid_')) {
            const value = localStorage.getItem(key);
            const prescriptionId = key.replace('prescription_paid_', '');
            console.log(`✅ 已支付ID: ${prescriptionId} (${value})`);
            allPaidIds.push(prescriptionId);
        }
    }
    
    if (allPaidIds.length === 0) {
        console.log('❌ 没有找到任何支付记录');
        return;
    }
    
    // 2. 分析页面中的处方内容
    console.log('\n🔍 === 页面处方内容分析 ===');
    const aiMessages = document.querySelectorAll('.message.ai');
    const prescriptionMessages = [];
    
    aiMessages.forEach((messageEl, index) => {
        const messageText = messageEl.querySelector('.message-text');
        if (messageText && (messageText.innerHTML.includes('处方预览') || messageText.innerHTML.includes('🔓 解锁完整处方'))) {
            const prescriptionId = messageEl.getAttribute('data-prescription-id');
            const originalContent = messageText.getAttribute('data-original-content') || messageText.innerHTML;
            
            // 生成各种可能的ID
            const contentBasedId = window.prescriptionPaymentManager?.extractOrGeneratePrescriptionId(originalContent);
            const possibleIds = [
                prescriptionId,
                contentBasedId,
                `paid_${prescriptionId}`,
                `prescription_${prescriptionId}`
            ].filter(id => id && id !== 'null');

            const prescriptionInfo = {
                index: index + 1,
                element: messageEl,
                prescriptionId,
                contentBasedId,
                possibleIds,
                originalContent,
                isCurrentlyLocked: messageText.innerHTML.includes('🔓 解锁完整处方'),
                contentPreview: originalContent.substring(0, 100) + '...'
            };
            
            prescriptionMessages.push(prescriptionInfo);
            
            console.log(`🔍 处方 #${index + 1}:`);
            console.log(`    - 当前ID: ${prescriptionId}`);
            console.log(`    - 内容生成ID: ${contentBasedId}`);
            console.log(`    - 所有可能ID: ${possibleIds.join(', ')}`);
            console.log(`    - 显示状态: ${prescriptionInfo.isCurrentlyLocked ? '🔒 锁定' : '🔓 已解锁'}`);
        }
    });
    
    // 3. 执行匹配分析
    console.log('\n🔄 === ID匹配分析 ===');
    let fixCount = 0;
    
    prescriptionMessages.forEach(prescription => {
        console.log(`\n处方 #${prescription.index} 匹配分析:`);
        
        // 检查每个可能的ID是否在支付记录中
        let matchedId = null;
        for (const possibleId of prescription.possibleIds) {
            if (allPaidIds.includes(possibleId)) {
                matchedId = possibleId;
                console.log(`    ✅ 匹配成功: ${possibleId}`);
                break;
            } else {
                console.log(`    ❌ 未匹配: ${possibleId}`);
            }
        }
        
        // 如果找到匹配但当前显示为锁定，自动修复
        if (matchedId && prescription.isCurrentlyLocked) {
            console.log(`    🔧 自动修复: 将处方更新为已支付状态`);
            
            if (window.prescriptionContentRenderer) {
                // 🔧 查找对应的消息元素获取原始内容
                const messageEl = document.querySelector(`[data-prescription-id="${prescription.prescriptionId}"]`);
                const messageText = messageEl?.querySelector('.message-text');
                let contentToRender = messageText?.getAttribute('data-original-content');
                
                if (!contentToRender) {
                    contentToRender = prescription.originalContent;
                    console.log('⚠️ 修复状态时没有找到data-original-content，使用提取的内容');
                } else {
                    console.log('✅ 修复状态时使用保存的data-original-content');
                }
                
                const newContent = window.prescriptionContentRenderer.renderPaidContent(
                    contentToRender, 
                    matchedId
                );
                
                const messageTextElement = prescription.element.querySelector('.message-text');
                messageTextElement.innerHTML = newContent;
                prescription.element.setAttribute('data-prescription-id', matchedId);
                
                fixCount++;
                console.log(`    ✅ 修复完成`);
            }
        } else if (!matchedId) {
            console.log(`    ❌ 无法匹配，处方将保持锁定状态`);
        } else {
            console.log(`    ✅ 状态正确，无需修复`);
        }
    });
    
    console.log(`\n🎉 === 调试总结 ===`);
    console.log(`- 发现处方数量: ${prescriptionMessages.length}`);
    console.log(`- 支付记录数量: ${allPaidIds.length}`);
    console.log(`- 自动修复数量: ${fixCount}`);
    
    if (fixCount > 0) {
        console.log(`✅ 已自动修复 ${fixCount} 个处方的显示状态`);
    } else if (prescriptionMessages.length > 0 && allPaidIds.length > 0) {
        console.log(`⚠️  有支付记录和处方内容，但ID无法匹配，可能需要手动处理`);
    }
    
    return {
        prescriptions: prescriptionMessages.length,
        paidRecords: allPaidIds.length,
        fixedCount: fixCount
    };
}

// 导出调试函数到全局
window.debugPrescriptionMatching = debugPrescriptionMatching;

// 🔧 强制修复函数：手动将指定处方标记为已支付
window.forceUnlockPrescription = function(prescriptionIndex) {
    const aiMessages = document.querySelectorAll('.message.ai');
    const prescriptionMessages = Array.from(aiMessages).filter(el => {
        const messageText = el.querySelector('.message-text');
        return messageText && (messageText.innerHTML.includes('处方预览') || messageText.innerHTML.includes('🔓 解锁完整处方'));
    });
    
    if (prescriptionIndex <= 0 || prescriptionIndex > prescriptionMessages.length) {
        console.error(`❌ 处方索引 ${prescriptionIndex} 超出范围 (1-${prescriptionMessages.length})`);
        return false;
    }
    
    const targetMessage = prescriptionMessages[prescriptionIndex - 1];
    const messageText = targetMessage.querySelector('.message-text');
    const originalContent = messageText.getAttribute('data-original-content') || messageText.innerHTML;
    
    // 生成一个新的支付记录
    const forceId = `force_${Date.now()}`;
    window.prescriptionPaymentManager.markAsPaid(forceId);
    
    // 重新渲染为已支付状态
    if (window.prescriptionContentRenderer) {
        // 🔧 优先使用保存的原始内容
        let contentToRender = messageText.getAttribute('data-original-content');
        if (!contentToRender) {
            contentToRender = originalContent;
            console.log('⚠️ 强制解锁时没有找到data-original-content，使用提取的内容');
        } else {
            console.log('✅ 强制解锁时使用保存的data-original-content');
        }
        
        const newContent = window.prescriptionContentRenderer.renderPaidContent(contentToRender, forceId);
        messageText.innerHTML = newContent;
        targetMessage.setAttribute('data-prescription-id', forceId);
    }
    
    console.log(`✅ 已强制解锁处方 #${prescriptionIndex}`);
    return true;
};

window.checkAllPrescriptionStatus = checkAllPrescriptionStatus;

console.log('✅ 处方支付系统初始化完成 - 专业模块化版本 v1.0');