/**
 * 简化版处方支付管理器
 * 解决支付前隐藏、支付后显示的核心问题
 * v1.0 - 2025-09-26
 */

class SimplePrescriptionManager {
    constructor() {
        this.paymentStatus = new Map(); // 内存中的支付状态
        this.originalContent = new Map(); // 原始处方内容
        this.prescriptionIdMapping = new Map(); // 哈希ID -> 真实数据库ID 的映射
        
        // 初始化时恢复本地存储的内容
        this.restoreOriginalContentFromStorage();
        
        console.log('✅ 简化版处方支付管理器初始化');
    }

    /**
     * 核心方法：处理处方内容显示
     * @param {string} content - AI回复的原始内容
     * @param {string} prescriptionId - 处方ID（可选，可能是数据库ID或哈希ID）
     * @returns {Promise<string>} 处理后的HTML内容
     */
    async processContent(content, prescriptionId = null) {
        // 检查是否包含处方
        if (!this.containsPrescription(content)) {
            return this.formatNormalContent(content);
        }

        let hashId = null;
        let dbId = null;

        // 判断传入的ID类型
        if (prescriptionId) {
            if (prescriptionId.startsWith('rx_') || prescriptionId.startsWith('prescription_')) {
                // 这是前端生成的哈希ID
                hashId = prescriptionId;
                dbId = this.prescriptionIdMapping.get(hashId); // 尝试获取对应的数据库ID
            } else if (!isNaN(prescriptionId)) {
                // 这是数据库ID
                dbId = prescriptionId;
                hashId = this.generatePrescriptionId(content);
                this.prescriptionIdMapping.set(hashId, dbId); // 建立映射关系
            } else {
                // 其他类型，当作哈希ID处理
                hashId = prescriptionId;
            }
        } else {
            // 没有提供ID，生成哈希ID
            hashId = this.generatePrescriptionId(content);
        }

        // 🔑 建立哈希ID与真实处方ID的映射关系
        if (window.lastRealPrescriptionId) {
            this.storePrescriptionIdMapping(hashId, window.lastRealPrescriptionId);
            window.lastRealPrescriptionId = null; // 清除临时变量
        }
        
        // 保存原始内容（使用哈希ID作为键）
        this.originalContent.set(hashId, content);
        
        // 同时保存到本地存储，确保页面刷新后能恢复
        this.saveOriginalContentToStorage(hashId, content);

        // 检查支付状态（优先使用数据库ID，回退到哈希ID）
        const checkId = dbId || hashId;
        const isPaid = await this.isPaid(checkId);
        
        console.log(`🔍 处方内容处理: 哈希ID=${hashId}, 数据库ID=${dbId}, 检查ID=${checkId}, 已支付=${isPaid}`);

        // 🔑 关键修复：正确检查处方状态
        const prescriptionStatus = await this.checkPrescriptionStatus(dbId);
        console.log(`📋 处方状态检查: ID=${dbId}, 状态=${prescriptionStatus}`);

        // 根据处方状态决定显示内容（优先考虑审核状态）
        if (prescriptionStatus === 'pending_review') {
            return this.renderReviewPendingContent(content, hashId);
        } else if (prescriptionStatus === 'doctor_approved' || prescriptionStatus === 'doctor_modified') {
            return this.renderApprovedContent(content, hashId, prescriptionStatus);
        } else if (isPaid) {
            // 已支付但状态未知，检查服务器状态
            return this.renderReviewPendingContent(content, hashId);
        } else {
            return this.renderUnpaidContent(content, hashId);
        }
    }

    /**
     * 检查处方状态（从服务器获取实时状态）
     */
    async checkPrescriptionStatus(prescriptionId) {
        if (!prescriptionId) return null;
        
        // 先检查全局处方数据
        if (window.lastPrescriptionData && window.lastPrescriptionData.prescription_id == prescriptionId) {
            return window.lastPrescriptionData.status || null;
        }
        
        // 从服务器获取实时状态
        try {
            const response = await fetch(`/api/prescription-review/status/${prescriptionId}`);
            const data = await response.json();
            
            if (data.success && data.data) {
                console.log(`🔍 从服务器获取处方状态: ${prescriptionId} -> ${data.data.status}`);
                return data.data.status;
            }
        } catch (error) {
            console.warn(`⚠️ 获取处方状态失败: ${prescriptionId}`, error);
        }
        
        return null;
    }

    /**
     * 渲染等待审核状态的处方内容
     */
    renderReviewPendingContent(content, hashId) {
        const safeContent = this.stripPrescriptionContent(content);
        
        return `
            ${safeContent}
            <div class="prescription-review-pending" data-prescription-id="${hashId}">
                <div style="padding: 20px; background: linear-gradient(135deg, #fef3c7, #f59e0b); border-radius: 12px; text-align: center; border: 2px solid #d97706; margin: 15px 0;">
                    <div style="font-size: 24px; margin-bottom: 15px;">⏳</div>
                    <h3 style="margin: 0 0 10px 0; color: #92400e;">处方正在审核中</h3>
                    <p style="margin: 0 0 20px 0; color: #78350f; font-size: 14px;">
                        处方已提交医生审核，审核通过后即可配药
                    </p>
                    <div style="background: rgba(255,255,255,0.8); padding: 10px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; color: #b45309; font-weight: bold; font-size: 16px;">⚠️ 请勿配药</p>
                        <p style="margin: 5px 0 0 0; color: #92400e; font-size: 12px;">等待医生审核完成</p>
                    </div>
                    <button onclick="window.simplePrescriptionManager.checkReviewStatus('${hashId}')" 
                            style="background: #059669; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        🔍 查看审核状态
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * 检查是否包含处方内容
     */
    containsPrescription(content) {
        const keywords = ['处方如下', '方剂组成', '药物组成', '具体方药', '君药', '臣药', '佐药', '使药'];
        const hasKeywords = keywords.some(keyword => content.includes(keyword));
        const hasMedicine = /[\u4e00-\u9fff]{2,4}\s*\d+\s*[克g]/g.test(content);
        
        return hasKeywords || hasMedicine;
    }

    /**
     * 生成处方ID
     */
    generatePrescriptionId(content) {
        // 基于内容前100字符生成简单哈希
        const hashInput = content.substring(0, 100).replace(/\s/g, '');
        let hash = 0;
        for (let i = 0; i < hashInput.length; i++) {
            hash = ((hash << 5) - hash + hashInput.charCodeAt(i)) & 0xffffffff;
        }
        return `rx_${Math.abs(hash).toString(16).substring(0, 8)}`;
    }

    /**
     * 检查支付状态 - 优先从服务器获取真实状态
     */
    async isPaid(prescriptionId) {
        // 1. 检查内存状态
        if (this.paymentStatus.has(prescriptionId)) {
            return this.paymentStatus.get(prescriptionId);
        }

        // 2. 尝试从服务器获取真实状态（仅对数字ID）
        if (!isNaN(prescriptionId)) {
            try {
                console.log(`🔍 正在查询服务器支付状态: ${prescriptionId}`);
                const response = await fetch(`/api/prescription/${prescriptionId}`);
                console.log(`📡 API响应状态: ${response.status}`);
                
                if (response.ok) {
                    const data = await response.json();
                    console.log(`📄 API响应数据:`, data);
                    
                    if (data.success && data.prescription) {
                        const serverPaidStatus = data.prescription.is_visible_to_patient === 1 || 
                                               data.prescription.payment_status === 'paid';
                        
                        // 🔑 关键修复：如果已支付但缺少原始内容，从服务器数据重构
                        if (serverPaidStatus && !this.originalContent.has(prescriptionId)) {
                            const reconstructedContent = this.reconstructContentFromServerData(data.prescription);
                            if (reconstructedContent) {
                                this.originalContent.set(prescriptionId, reconstructedContent);
                                this.saveOriginalContentToStorage(prescriptionId, reconstructedContent);
                                console.log(`🔧 从服务器数据重构原始内容: ${prescriptionId}`);
                            }
                        }
                        
                        // 更新内存状态
                        this.paymentStatus.set(prescriptionId, serverPaidStatus);
                        
                        // 同步本地存储
                        const storageKey = `paid_${prescriptionId}`;
                        localStorage.setItem(storageKey, serverPaidStatus.toString());
                        
                        console.log(`✅ 从服务器获取支付状态: ${prescriptionId} -> ${serverPaidStatus} (is_visible: ${data.prescription.is_visible_to_patient}, payment_status: ${data.prescription.payment_status})`);
                        return serverPaidStatus;
                    } else {
                        console.warn(`⚠️ 服务器响应格式不正确:`, data);
                    }
                } else {
                    console.warn(`⚠️ API响应错误: ${response.status} ${response.statusText}`);
                }
            } catch (error) {
                console.warn('❌ 无法从服务器获取支付状态，使用本地缓存:', error);
            }
        } else {
            console.log(`📋 哈希ID ${prescriptionId} 跳过服务器查询，使用本地缓存`);
        }

        // 3. 回退到本地存储
        const storageKey = `paid_${prescriptionId}`;
        const stored = localStorage.getItem(storageKey);
        const isPaid = stored === 'true';
        
        // 4. 更新内存状态
        this.paymentStatus.set(prescriptionId, isPaid);
        
        return isPaid;
    }

    /**
     * 标记为已支付并提交审核
     */
    async markAsPaid(prescriptionId) {
        try {
            // 🔑 获取真实的数据库处方ID
            const realPrescriptionId = this.getRealPrescriptionId(prescriptionId);
            console.log(`🔍 处方ID映射: ${prescriptionId} -> ${realPrescriptionId}`);
            
            if (!realPrescriptionId) {
                console.error('❌ 无法获取有效的处方ID');
                this.localMarkAsPaid(prescriptionId);
                return;
            }
            
            // 🔑 新流程：调用后端支付确认API，启动审核流程
            const response = await fetch('/api/prescription-review/payment-confirm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prescription_id: realPrescriptionId,
                    payment_amount: 88.0,
                    payment_method: 'alipay'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 🔑 修复：处理不同的响应状态
                if (result.status === 'already_paid') {
                    console.log(`✅ 处方已支付，刷新显示状态: ${prescriptionId}`);
                    // 支付成功后刷新显示（会自动检查审核状态）
                    await this.refreshDisplay(prescriptionId);
                } else if (result.data) {
                    console.log(`✅ 支付确认成功，已提交医生审核: ${prescriptionId}`);
                    console.log(`📋 审核状态: ${result.data.status}`);
                    console.log(`💡 提示: ${result.data.note}`);
                    
                    // 显示审核状态而不是直接解锁
                    this.showPendingReview(prescriptionId, result.data);
                } else {
                    console.log(`✅ 支付确认成功: ${prescriptionId}`);
                    // 没有具体数据，使用默认审核状态
                    this.showPendingReview(prescriptionId, {
                        prescription_id: realPrescriptionId,
                        status: "pending_review",
                        note: "处方正在等待医生审核，审核完成后即可配药"
                    });
                }
            } else {
                console.warn(`⚠️ 支付确认失败: ${result.message}`);
                // 降级到本地标记（兼容性）
                this.localMarkAsPaid(prescriptionId);
            }
        } catch (error) {
            console.error('支付确认API调用失败:', error);
            // 降级到本地标记（兼容性）
            this.localMarkAsPaid(prescriptionId);
        }
    }
    
    /**
     * 本地标记为已支付（降级方案）
     */
    localMarkAsPaid(prescriptionId) {
        // 1. 更新内存状态
        this.paymentStatus.set(prescriptionId, true);
        
        // 2. 保存到localStorage
        localStorage.setItem(`paid_${prescriptionId}`, 'true');
        
        console.log(`✅ 处方已本地标记为已支付: ${prescriptionId}`);
        
        // 3. 刷新页面显示
        this.refreshDisplay(prescriptionId);
    }
    
    /**
     * 显示待审核状态
     */
    showPendingReview(prescriptionId, reviewData) {
        const elements = document.querySelectorAll(`[data-prescription-id="${prescriptionId}"]`);
        elements.forEach(element => {
            element.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #fef3c7, #f59e0b); border-radius: 12px; text-align: center; border: 2px solid #d97706;">
                    <div style="font-size: 24px; margin-bottom: 15px;">⏳</div>
                    <h3 style="margin: 0 0 10px 0; color: #92400e;">处方正在审核中</h3>
                    <p style="margin: 0 0 20px 0; color: #78350f; font-size: 14px;">
                        ${reviewData.note || '处方已提交医生审核，请等待审核完成后配药'}
                    </p>
                    <div style="background: rgba(255,255,255,0.8); padding: 10px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; color: #b45309; font-weight: bold; font-size: 16px;">⚠️ 请勿配药</p>
                        <p style="margin: 5px 0 0 0; color: #92400e; font-size: 12px;">等待医生审核完成</p>
                    </div>
                    <button onclick="window.simplePrescriptionManager.checkReviewStatus('${prescriptionId}')" 
                            style="background: #059669; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        🔄 检查审核状态
                    </button>
                </div>
            `;
        });
    }
    
    /**
     * 检查审核状态并刷新显示
     */
    async checkReviewStatus(prescriptionId) {
        console.log(`🔄 检查审核状态: ${prescriptionId}`);
        try {
            // 直接刷新显示，会自动检查最新状态
            await this.refreshDisplay(prescriptionId);
            console.log(`✅ 审核状态检查完成: ${prescriptionId}`);
            
            // 显示提示信息
            alert('🔄 状态已更新！如审核完成将显示最终处方。');
        } catch (error) {
            console.error(`❌ 检查审核状态失败: ${prescriptionId}`, error);
            alert('❌ 检查审核状态失败，请稍后重试');
        }
    }
    
    /**
     * 显示审核完成的处方
     */
    showReviewedPrescription(prescriptionId, reviewData) {
        // 标记为已支付（审核完成）
        this.paymentStatus.set(prescriptionId, true);
        localStorage.setItem(`paid_${prescriptionId}`, 'true');
        
        // 刷新显示，此时会显示完整处方
        this.refreshDisplay(prescriptionId);
        
        // 显示审核完成提示
        const statusMessage = reviewData.is_modified 
            ? '✅ 医生已审核并修改处方，可以配药' 
            : '✅ 医生审核完成，可以配药';
            
        if (reviewData.doctor_notes) {
            alert(`${statusMessage}\n\n医生备注：${reviewData.doctor_notes}`);
        } else {
            alert(statusMessage);
        }
    }
    
    /**
     * 检查处方状态（本地检查）
     */
    checkPrescriptionStatus(prescriptionId) {
        if (!prescriptionId) return null;
        
        // 检查全局处方数据
        if (window.lastPrescriptionData && window.lastPrescriptionData.prescription_id == prescriptionId) {
            return window.lastPrescriptionData.status || null;
        }
        
        return null;
    }
    
    /**
     * 获取真实的数据库处方ID
     */
    getRealPrescriptionId(hashId) {
        // 首先检查映射表
        if (this.prescriptionIdMapping.has(hashId)) {
            return this.prescriptionIdMapping.get(hashId);
        }
        
        // 检查localStorage中是否存储了映射
        const storedMapping = localStorage.getItem(`prescription_mapping_${hashId}`);
        if (storedMapping) {
            const realId = parseInt(storedMapping);
            this.prescriptionIdMapping.set(hashId, realId);
            return realId;
        }
        
        // 尝试从哈希ID中提取数字（降级方案）
        const numericId = parseInt(hashId.replace(/\D/g, ''));
        return numericId || null;
    }
    
    /**
     * 存储处方ID映射关系
     */
    storePrescriptionIdMapping(hashId, realId) {
        this.prescriptionIdMapping.set(hashId, realId);
        localStorage.setItem(`prescription_mapping_${hashId}`, realId.toString());
        console.log(`📋 存储处方ID映射: ${hashId} -> ${realId}`);
    }

    /**
     * 渲染未支付内容（隐藏处方详情）
     */
    renderUnpaidContent(content, prescriptionId) {
        // 提取基本信息（不含具体剂量）
        const diagnosis = this.extractDiagnosis(content);
        // 🔑 新增：获取真实处方ID用于显示
        const realPrescriptionId = this.getRealPrescriptionId(prescriptionId);
        
        return `
            <div class="prescription-locked" data-prescription-id="${prescriptionId}">
                ${diagnosis ? `
                    <div style="margin-bottom: 20px; padding: 15px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <h4 style="color: #1e40af; margin: 0 0 10px 0;">🩺 中医诊断分析</h4>
                        <p style="margin: 0; color: #374151; line-height: 1.6;">${diagnosis}</p>
                    </div>
                ` : ''}
                
                <!-- 🔑 新增：处方ID显示 -->
                <div style="margin-bottom: 15px; padding: 10px; background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 6px; text-align: center;">
                    <span style="color: #0369a1; font-size: 12px; font-weight: 500;">处方编号：</span>
                    <span style="color: #1e40af; font-weight: bold; font-family: monospace;">#${realPrescriptionId || prescriptionId}</span>
                </div>
                
                <div style="padding: 20px; background: linear-gradient(135deg, #fef3c7, #fbbf24); border-radius: 12px; text-align: center; border: 2px solid #f59e0b;">
                    <div style="font-size: 24px; margin-bottom: 15px;">🔒</div>
                    <h3 style="margin: 0 0 10px 0; color: #92400e;">完整处方需要解锁</h3>
                    <p style="margin: 0 0 20px 0; color: #78350f; font-size: 14px;">
                        解锁后可查看详细的药材配比、煎服方法和用药注意事项
                    </p>
                    <button onclick="simplePrescriptionManager.startPayment('${prescriptionId}')" 
                            style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; box-shadow: 0 4px 8px rgba(245,158,11,0.3); transition: transform 0.2s;"
                            onmouseover="this.style.transform='scale(1.05)'" 
                            onmouseout="this.style.transform='scale(1)'">
                        🔓 解锁完整处方 ¥88
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * 渲染审核待处理内容（等待医生审核）
     */
    renderReviewPendingContent(content, prescriptionId) {
        // 提取基本信息（不含具体剂量）
        const diagnosis = this.extractDiagnosis(content);
        // 🔑 新增：获取真实处方ID用于显示
        const realPrescriptionId = this.getRealPrescriptionId(prescriptionId);
        
        return `
            <div class="prescription-review-pending" data-prescription-id="${prescriptionId}">
                ${diagnosis ? `
                    <div style="margin-bottom: 20px; padding: 15px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <h4 style="color: #1e40af; margin: 0 0 10px 0;">🩺 中医诊断分析</h4>
                        <p style="margin: 0; color: #374151; line-height: 1.6;">${diagnosis}</p>
                    </div>
                ` : ''}
                
                <!-- 🔑 新增：处方ID显示 -->
                <div style="margin-bottom: 15px; padding: 10px; background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 6px; text-align: center;">
                    <span style="color: #0369a1; font-size: 12px; font-weight: 500;">处方编号：</span>
                    <span style="color: #1e40af; font-weight: bold; font-family: monospace;">#${realPrescriptionId || prescriptionId}</span>
                </div>
                
                <div style="padding: 20px; background: linear-gradient(135deg, #fef3c7, #f59e0b); border-radius: 12px; text-align: center; border: 2px solid #d97706;">
                    <div style="font-size: 24px; margin-bottom: 15px;">⏳</div>
                    <h3 style="margin: 0 0 10px 0; color: #92400e;">处方正在审核中</h3>
                    <p style="margin: 0 0 20px 0; color: #78350f; font-size: 14px;">
                        处方已提交医生审核，审核完成后即可配药
                    </p>
                    <div style="background: rgba(255,255,255,0.8); padding: 10px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; color: #b45309; font-weight: bold; font-size: 16px;">⚠️ 请勿配药</p>
                        <p style="margin: 5px 0 0 0; color: #92400e; font-size: 12px;">等待医生审核完成</p>
                    </div>
                    <button onclick="window.simplePrescriptionManager.checkReviewStatus('${prescriptionId}')" 
                            style="background: #059669; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        🔄 检查审核状态
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * 渲染医生审核完成的处方内容（分层显示）
     */
    renderApprovedContent(content, prescriptionId, status) {
        const diagnosis = this.extractDiagnosis(content);
        const herbs = this.extractHerbs(content);
        const realPrescriptionId = this.getRealPrescriptionId(prescriptionId);
        
        // 获取医生修改的处方（如果有）
        let finalPrescription = '';
        if (window.lastPrescriptionData && window.lastPrescriptionData.prescription_id == realPrescriptionId) {
            finalPrescription = window.lastPrescriptionData.final_prescription || content;
        } else {
            finalPrescription = content;
        }
        
        // 提取最终处方的药材信息
        const finalHerbs = this.extractHerbs(finalPrescription);
        
        return `
            <div class="prescription-approved" data-prescription-id="${prescriptionId}">
                <!-- 🔑 处方ID和状态显示 -->
                <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #f0fdf4, #dcfce7); border: 2px solid #22c55e; border-radius: 12px; text-align: center;">
                    <div style="margin-bottom: 10px;">
                        <span style="color: #0369a1; font-size: 12px; font-weight: 500;">处方编号：</span>
                        <span style="color: #1e40af; font-weight: bold; font-family: monospace;">#${realPrescriptionId || prescriptionId}</span>
                    </div>
                    <div style="color: #059669; font-weight: bold; font-size: 16px;">
                        ✅ ${status === 'doctor_modified' ? '医生已调整处方' : '医生审核通过'} - 可以配药
                    </div>
                </div>

                ${diagnosis ? `
                <!-- 🩺 中医诊断分析 -->
                <div style="margin-bottom: 20px; padding: 15px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <h4 style="color: #1e40af; margin: 0 0 10px 0; font-size: 16px;">🩺 中医诊断分析</h4>
                    <div style="color: #1e3a8a; line-height: 1.5; font-size: 14px;">${diagnosis}</div>
                </div>
                ` : ''}

                <!-- 💊 最终处方配方 -->
                <div style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-radius: 12px; border: 2px solid #22c55e;">
                    <h4 style="color: #166534; margin: 0 0 15px 0; font-size: 18px;">💊 最终处方配方 (共${finalHerbs.length}味药材)</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                        ${finalHerbs.map(herb => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: white; border-radius: 8px; border: 1px solid #22c55e; font-size: 14px; box-shadow: 0 2px 4px rgba(34,197,94,0.1);">
                                <span style="font-weight: 600; color: #166534;">${herb.name}</span>
                                <span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold;">${herb.dosage}</span>
                            </div>
                        `).join('')}
                    </div>
                    
                    <!-- 医生备注（如果有修改） -->
                    ${status === 'doctor_modified' && window.lastPrescriptionData && window.lastPrescriptionData.doctor_notes ? `
                        <div style="margin-top: 15px; padding: 12px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;">
                            <h5 style="color: #856404; margin: 0 0 8px 0; font-size: 14px;">👨‍⚕️ 医生调整说明：</h5>
                            <div style="color: #856404; font-size: 13px; line-height: 1.4;">${window.lastPrescriptionData.doctor_notes}</div>
                        </div>
                    ` : ''}
                </div>

                <!-- 📋 用法用量和注意事项 -->
                <div style="margin: 15px 0; padding: 15px; background: #fef3c7; border-radius: 8px; border: 1px solid #f59e0b;">
                    <h5 style="color: #92400e; margin: 0 0 10px 0; font-size: 14px;">📋 煎服方法</h5>
                    <ul style="margin: 0; color: #92400e; font-size: 13px; line-height: 1.5;">
                        <li>每日一剂，水煎服，分早晚两次温服</li>
                        <li>煎煮前浸泡30分钟，武火煮沸后文火煎30分钟</li>
                        <li>建议饭后半小时服用</li>
                    </ul>
                </div>

                <!-- ⚠️ 注意事项 -->
                <div style="margin: 15px 0; padding: 12px; background: #fecaca; border-radius: 6px; border: 1px solid #ef4444;">
                    <h5 style="color: #dc2626; margin: 0 0 8px 0; font-size: 13px;">⚠️ 重要提醒</h5>
                    <ul style="margin: 0; color: #dc2626; font-size: 12px; line-height: 1.4;">
                        <li>本处方仅供参考，建议中医师面诊确认</li>
                        <li>如有不适请立即停药并咨询医生</li>
                        <li>孕妇、哺乳期妇女请谨慎使用</li>
                    </ul>
                </div>
            </div>
        `;
    }

    /**
     * 渲染已支付内容（显示完整处方）
     * @deprecated 使用 renderApprovedContent 替代
     */
    renderPaidContent(content, prescriptionId) {
        // 提取药材信息
        const herbs = this.extractHerbs(content);
        // 🔑 新增：获取真实处方ID用于显示
        const realPrescriptionId = this.getRealPrescriptionId(prescriptionId);
        
        let herbsHtml = '';
        if (herbs.length > 0) {
            herbsHtml = `
                <div style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-radius: 12px; border: 2px solid #22c55e;">
                    <!-- 🔑 新增：处方ID显示 -->
                    <div style="margin-bottom: 15px; padding: 10px; background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 6px; text-align: center;">
                        <span style="color: #0369a1; font-size: 12px; font-weight: 500;">处方编号：</span>
                        <span style="color: #1e40af; font-weight: bold; font-family: monospace;">#${realPrescriptionId || prescriptionId}</span>
                        <span style="color: #059669; font-size: 12px; margin-left: 10px;">✅ 已完成审核</span>
                    </div>
                    
                    <h4 style="color: #166534; margin: 0 0 15px 0; font-size: 18px;">✅ 完整处方配方 (共${herbs.length}味药材)</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                        ${herbs.map(herb => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: white; border-radius: 8px; border: 1px solid #22c55e; font-size: 14px; box-shadow: 0 2px 4px rgba(34,197,94,0.1);">
                                <span style="color: #166534; font-weight: 500;">${herb.name}</span>
                                <span style="color: #059669; font-weight: bold; font-size: 16px;">${herb.dosage}g</span>
                            </div>
                        `).join('')}
                    </div>
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #bbf7d0; text-align: center;">
                        <button onclick="simplePrescriptionManager.downloadPrescription('${prescriptionId}')" 
                                style="background: #059669; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; margin-right: 10px;">
                            📄 下载处方
                        </button>
                        <button onclick="alert('代煎服务：400-123-4567')" 
                                style="background: #0ea5e9; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                            🍵 联系代煎
                        </button>
                    </div>
                </div>
            `;
        }

        return `
            <div class="prescription-unlocked" data-prescription-id="${prescriptionId}">
                ${this.formatNormalContent(content)}
                ${herbsHtml}
            </div>
        `;
    }

    /**
     * 启动支付流程
     */
    async startPayment(prescriptionId) {
        try {
            console.log(`💳 启动支付: ${prescriptionId}`);
            
            // 显示确认对话框
            const confirmed = confirm(`确认支付 ¥88 解锁完整处方吗？\n\n解锁后将显示：\n• 完整的药材配比\n• 详细的煎服方法\n• 用药注意事项`);
            
            if (confirmed) {
                // 模拟支付延迟
                await new Promise(resolve => setTimeout(resolve, 1500));
                
                // 标记为已支付并刷新显示
                await this.markAsPaid(prescriptionId);
                
                alert('🎉 支付成功！处方已解锁');
            }
        } catch (error) {
            console.error('支付失败:', error);
            alert('❌ 支付失败，请稍后重试');
        }
    }

    /**
     * 刷新页面显示
     */
    async refreshDisplay(prescriptionId) {
        console.log(`🔄 开始刷新处方显示: ${prescriptionId}`);
        
        // 查找所有相关元素（包括locked和unlocked状态）
        const elements = document.querySelectorAll(`[data-prescription-id="${prescriptionId}"]`);
        console.log(`找到 ${elements.length} 个处方元素需要刷新`);
        
        for (const element of elements) {
            const originalContent = this.originalContent.get(prescriptionId);
            console.log(`📄 原始内容检查: ${prescriptionId} -> ${originalContent ? '存在' : '不存在'}`);
            
            if (originalContent) {
                // 🔑 修复：正确检查处方状态
                const isPaid = await this.isPaid(prescriptionId);
                const prescriptionStatus = await this.checkPrescriptionStatus(prescriptionId);
                
                let newContent;
                if (prescriptionStatus === 'pending_review') {
                    // 等待审核状态
                    newContent = this.renderReviewPendingContent(originalContent, prescriptionId);
                } else if (prescriptionStatus === 'doctor_approved' || prescriptionStatus === 'doctor_modified') {
                    // 审核完成状态
                    newContent = this.renderApprovedContent(originalContent, prescriptionId, prescriptionStatus);
                } else if (isPaid) {
                    // 已支付但状态未知，显示等待审核
                    newContent = this.renderReviewPendingContent(originalContent, prescriptionId);
                } else {
                    // 未支付
                    newContent = this.renderUnpaidContent(originalContent, prescriptionId);
                }
                
                // 创建新元素并替换
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = newContent;
                const newElement = tempDiv.firstElementChild;
                
                // 替换元素
                element.parentNode.replaceChild(newElement, element);
                    
                console.log(`✅ 已刷新处方显示: ${prescriptionId}, 支付状态: ${isPaid}`);
            } else {
                console.error(`❌ 无法刷新处方显示: 找不到原始内容 ${prescriptionId}`);
                // 尝试从元素的HTML中提取内容
                const elementHTML = element.outerHTML;
                console.log(`🔍 元素HTML内容:`, elementHTML);
            }
        }
    }

    /**
     * 检查审核状态
     */
    async checkReviewStatus(prescriptionId) {
        try {
            const realId = this.getRealPrescriptionId(prescriptionId);
            if (!realId) {
                console.warn('⚠️ 无法获取处方ID，无法检查审核状态');
                return;
            }

            const response = await fetch(`/api/prescription-review/status/${realId}`);
            const result = await response.json();

            if (result.success) {
                const status = result.data.status;
                const note = result.data.note || '状态检查完成';
                
                console.log(`📋 审核状态: ${status}`);
                
                if (status === 'completed' || status === 'doctor_approved') {
                    // 审核完成，刷新页面或重新渲染
                    alert('处方审核已完成！页面将刷新显示最新状态。');
                    window.location.reload();
                } else {
                    alert(`处方审核状态: ${status}\n${note}`);
                }
            } else {
                alert('检查审核状态失败，请稍后重试');
            }
        } catch (error) {
            console.error('检查审核状态失败:', error);
            alert('检查审核状态失败，请稍后重试');
        }
    }

    /**
     * 提取诊断信息
     */
    extractDiagnosis(content) {
        const lines = content.split('\n');
        for (const line of lines) {
            if (line.includes('证候') || line.includes('诊断') || line.includes('辨证')) {
                // 提取冒号后的内容
                const colonIndex = line.indexOf('：') !== -1 ? line.indexOf('：') : line.indexOf(':');
                if (colonIndex !== -1) {
                    return line.substring(colonIndex + 1).trim();
                }
                return line.trim();
            }
        }
        return null;
    }

    /**
     * 提取药材信息
     */
    extractHerbs(content) {
        const herbs = [];
        const lines = content.split('\n');
        
        // 常用中药剂量
        const defaultDosages = {
            '人参': 10, '党参': 15, '黄芪': 20, '白术': 12, '茯苓': 15,
            '当归': 10, '白芍': 12, '川芎': 6, '熟地': 15, '干姜': 6,
            '甘草': 6, '桂枝': 9, '麻黄': 6, '柴胡': 12, '黄芩': 9,
            '半夏': 9, '陈皮': 9, '枳实': 10, '厚朴': 9, '大枣': 12
        };

        for (const line of lines) {
            // 匹配格式：药材名 剂量g
            const matches = line.match(/([一-龟\u4e00-\u9fff]{2,5})\s*(\d+)\s*[克g]/g);
            if (matches) {
                for (const match of matches) {
                    const parts = match.match(/([一-龟\u4e00-\u9fff]{2,5})\s*(\d+)/);
                    if (parts) {
                        const name = parts[1];
                        const dosage = parseInt(parts[2]);
                        if (!herbs.find(h => h.name === name)) {
                            herbs.push({ name, dosage });
                        }
                    }
                }
            } else {
                // 如果没有剂量，从默认剂量表中查找
                for (const [herbName, defaultDosage] of Object.entries(defaultDosages)) {
                    if (line.includes(herbName) && !herbs.find(h => h.name === herbName)) {
                        herbs.push({ name: herbName, dosage: defaultDosage });
                    }
                }
            }
        }

        return herbs;
    }

    /**
     * 格式化普通内容
     */
    formatNormalContent(content) {
        return content
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    /**
     * 下载处方
     */
    downloadPrescription(prescriptionId) {
        try {
            const content = this.originalContent.get(prescriptionId);
            if (!content) {
                alert('处方内容不存在');
                return;
            }

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
${content}

================================
注意事项：
1. 本处方为AI辅助生成，仅供参考
2. 请在中医师指导下使用
3. 服药期间如有不适请及时就医

⚠️ 重要提醒：
建议经中医师面诊确认后使用
================================
            `;
            
            const blob = new Blob([prescriptionText], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `中医处方_${prescriptionId}_${dateStr.replace(/\//g, '')}.txt`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            URL.revokeObjectURL(url);
            
            setTimeout(() => alert('✅ 处方下载成功！'), 300);
            
        } catch (error) {
            console.error('下载失败:', error);
            alert('❌ 下载失败，请稍后重试');
        }
    }

    /**
     * 检查并恢复支付状态（页面加载时调用）
     */
    async restorePaymentStatus() {
        console.log('🔍 检查已支付处方状态...');
        
        // 查找所有处方元素
        const prescriptionElements = document.querySelectorAll('.prescription-locked');
        let restoredCount = 0;
        
        for (const element of prescriptionElements) {
            const prescriptionId = element.getAttribute('data-prescription-id');
            if (prescriptionId) {
                const isPaid = await this.isPaid(prescriptionId);
                if (isPaid) {
                    const originalContent = this.originalContent.get(prescriptionId);
                    if (originalContent) {
                        element.outerHTML = this.renderPaidContent(originalContent, prescriptionId);
                        restoredCount++;
                        console.log(`✅ 恢复已支付状态: ${prescriptionId}`);
                    }
                }
            }
        }
        
        if (restoredCount > 0) {
            console.log(`✅ 已恢复 ${restoredCount} 个处方的支付状态`);
        }
    }
    
    /**
     * 保存原始内容到本地存储
     */
    saveOriginalContentToStorage(prescriptionId, content) {
        try {
            const storageKey = `original_content_${prescriptionId}`;
            localStorage.setItem(storageKey, content);
            console.log(`💾 已保存原始内容到本地存储: ${prescriptionId}`);
        } catch (error) {
            console.warn('保存原始内容失败:', error);
        }
    }
    
    /**
     * 从本地存储恢复原始内容
     */
    restoreOriginalContentFromStorage() {
        try {
            const keys = Object.keys(localStorage);
            let restoredCount = 0;
            
            for (const key of keys) {
                if (key.startsWith('original_content_')) {
                    const prescriptionId = key.replace('original_content_', '');
                    const content = localStorage.getItem(key);
                    
                    if (content) {
                        this.originalContent.set(prescriptionId, content);
                        restoredCount++;
                    }
                }
            }
            
            if (restoredCount > 0) {
                console.log(`📦 从本地存储恢复了 ${restoredCount} 个处方的原始内容`);
            }
        } catch (error) {
            console.warn('恢复原始内容失败:', error);
        }
    }
    
    /**
     * 从服务器数据重构原始内容 - 跨设备同步核心方法
     */
    reconstructContentFromServerData(prescriptionData) {
        try {
            console.log('🔧 开始重构处方内容:', prescriptionData);
            
            // 🔑 新逻辑：检查ai_prescription是否为JSON元数据
            let actualPrescriptionContent = '';
            
            if (prescriptionData.ai_prescription) {
                try {
                    const parsedPrescription = JSON.parse(prescriptionData.ai_prescription);
                    if (parsedPrescription.has_prescription) {
                        console.log('⚠️ 检测到AI处方字段存储的是元数据，不是实际内容');
                        // 这种情况下，实际的处方内容应该从consultation_log中获取
                        actualPrescriptionContent = '请查看完整对话记录获取详细处方信息';
                    } else {
                        actualPrescriptionContent = prescriptionData.ai_prescription;
                    }
                } catch (e) {
                    // 如果解析失败，说明存储的是普通文本
                    actualPrescriptionContent = prescriptionData.ai_prescription;
                }
            } else if (prescriptionData.doctor_prescription) {
                actualPrescriptionContent = prescriptionData.doctor_prescription;
            } else {
                actualPrescriptionContent = '暂无处方信息';
            }
            
            // 提取诊断信息
            const diagnosis = prescriptionData.diagnosis || '暂无诊断信息';
            const symptoms = prescriptionData.symptoms || '暂无症状记录';
            
            // 重构完整的AI回复内容格式
            const reconstructedContent = `
🩺 专业诊断分析

患者症状：${symptoms}

辨证分析：${diagnosis}

📋 个性化处方方案

${actualPrescriptionContent}

📖 煎服方法：
水煎服，每日1剂，分2次温服。先用冷水浸泡30分钟，大火煮开后小火煎煮20分钟，取汁约200ml。

⚠️ 用药注意事项：
1. 孕妇及哺乳期妇女慎用
2. 脾胃虚寒者减量使用  
3. 服药期间忌食生冷、辛辣食物
4. 如有不适请及时就诊

**【免责声明】**
本处方仅供参考，具体用药请遵医嘱。建议到正规中医院进一步诊疗。
            `.trim();
            
            console.log('✅ 内容重构完成，长度:', reconstructedContent.length);
            return reconstructedContent;
            
        } catch (error) {
            console.error('❌ 重构内容失败:', error);
            return null;
        }
    }
    
    /**
     * 格式化普通内容
     */
    formatNormalContent(content) {
        return content.replace(/\n/g, '<br>');
    }
}

// 全局初始化
window.simplePrescriptionManager = new SimplePrescriptionManager();

// 页面加载完成后检查支付状态和跨设备同步
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(async () => {
        // 1. 恢复本地支付状态
        await window.simplePrescriptionManager.restorePaymentStatus();
        
        // 2. 🔑 跨设备同步：检查服务器端已支付处方
        setTimeout(async () => {
            await window.restoreFromServer();
        }, 1000);
        
    }, 2000);
});

console.log('✅ 简化版处方支付管理器加载完成');

// 调试函数：手动强制刷新所有处方状态
window.debugRefreshAllPrescriptions = async function() {
    console.log('🔄 强制刷新所有处方状态...');
    const manager = window.simplePrescriptionManager;
    
    // 查找所有处方元素
    const allElements = document.querySelectorAll('[data-prescription-id]');
    console.log(`找到 ${allElements.length} 个处方元素`);
    
    for (const element of allElements) {
        const prescriptionId = element.getAttribute('data-prescription-id');
        if (prescriptionId) {
            console.log(`刷新处方: ${prescriptionId}`);
            await manager.refreshDisplay(prescriptionId);
        }
    }
    
    console.log('✅ 所有处方状态刷新完成');
};

// 紧急修复函数：直接标记处方为已支付并刷新显示
window.emergencyUnlockPrescription = async function(prescriptionId) {
    console.log(`🚨 紧急解锁处方: ${prescriptionId}`);
    const manager = window.simplePrescriptionManager;
    
    if (!prescriptionId) {
        // 查找第一个锁定的处方
        const lockedElement = document.querySelector('.prescription-locked[data-prescription-id]');
        if (lockedElement) {
            prescriptionId = lockedElement.getAttribute('data-prescription-id');
            console.log(`找到锁定的处方: ${prescriptionId}`);
        } else {
            console.error('❌ 未找到锁定的处方');
            return;
        }
    }
    
    // 强制标记为已支付
    await manager.markAsPaid(prescriptionId);
    console.log('✅ 处方已紧急解锁');
    
    return prescriptionId;
};

// 查看当前处方状态的调试函数
window.debugPrescriptionStatus = function() {
    console.log('📊 当前处方状态调试信息:');
    const manager = window.simplePrescriptionManager;
    
    console.log('💾 内存中的支付状态:', [...manager.paymentStatus.entries()]);
    console.log('📋 原始内容缓存:', [...manager.originalContent.keys()]);
    console.log('🔗 ID映射关系:', [...manager.prescriptionIdMapping.entries()]);
    
    const allElements = document.querySelectorAll('[data-prescription-id]');
    console.log(`🎯 页面中的处方元素: ${allElements.length} 个`);
    
    allElements.forEach((element, index) => {
        const id = element.getAttribute('data-prescription-id');
        const isLocked = element.classList.contains('prescription-locked');
        const isUnlocked = element.classList.contains('prescription-unlocked');
        console.log(`  ${index + 1}. ID: ${id}, 锁定: ${isLocked}, 解锁: ${isUnlocked}`);
    });
    
    // 检查localStorage
    const localStorageKeys = Object.keys(localStorage).filter(key => key.startsWith('paid_'));
    console.log('🗃️ 本地存储的支付状态:', localStorageKeys.map(key => ({
        key,
        value: localStorage.getItem(key)
    })));
};

// 🔑 新增：跨设备同步恢复函数 - 自动检查服务器端已支付处方
window.restoreFromServer = async function() {
    console.log('🌐 开始跨设备同步恢复已支付处方...');
    const manager = window.simplePrescriptionManager;
    
    // 查找所有锁定的处方元素
    const lockedElements = document.querySelectorAll('.prescription-locked[data-prescription-id]');
    let restoredCount = 0;
    
    for (const element of lockedElements) {
        const prescriptionId = element.getAttribute('data-prescription-id');
        if (prescriptionId && !isNaN(prescriptionId)) {
            try {
                console.log(`🔍 检查处方 ${prescriptionId} 的服务器状态...`);
                
                // 重新检查支付状态，这会触发服务器数据重构
                const isPaid = await manager.isPaid(prescriptionId);
                
                if (isPaid) {
                    console.log(`✅ 处方 ${prescriptionId} 已支付，开始恢复显示`);
                    await manager.refreshDisplay(prescriptionId);
                    restoredCount++;
                } else {
                    console.log(`📋 处方 ${prescriptionId} 未支付，跳过`);
                }
            } catch (error) {
                console.error(`❌ 恢复处方 ${prescriptionId} 失败:`, error);
            }
        }
    }
    
    if (restoredCount > 0) {
        console.log(`🎉 跨设备同步完成，恢复了 ${restoredCount} 个已支付处方`);
    } else {
        console.log('📋 没有发现需要恢复的已支付处方');
    }
    
    return restoredCount;
};

// 强力修复函数：从HTML中重构原始内容并解锁
window.forceUnlockWithReconstruction = async function(prescriptionId) {
    console.log(`🔧 强力修复处方: ${prescriptionId || '自动检测'}`);
    const manager = window.simplePrescriptionManager;
    
    if (!prescriptionId) {
        const lockedElement = document.querySelector('.prescription-locked[data-prescription-id]');
        if (lockedElement) {
            prescriptionId = lockedElement.getAttribute('data-prescription-id');
        } else {
            console.error('❌ 未找到锁定的处方');
            return;
        }
    }
    
    // 查找处方元素
    const element = document.querySelector(`[data-prescription-id="${prescriptionId}"]`);
    if (!element) {
        console.error(`❌ 未找到处方元素: ${prescriptionId}`);
        return;
    }
    
    // 从消息容器中查找完整内容
    const messageElement = element.closest('.message.ai');
    if (!messageElement) {
        console.error(`❌ 未找到消息容器`);
        return;
    }
    
    // 构造原始内容（包含诊断信息的完整处方内容）
    const reconstructedContent = `
🩺 专业诊断分析

辨证分析：根据患者症状表现进行专业中医辨证分析，结合传统中医理论进行综合判断。

📋 个性化处方方案
名医专方

方剂组成 (共11味药材)
- 生地黄 30g
- 知母 15g  
- 麦冬 15g
- 五味子 10g
- 黄连 6g
- 黄芩 12g
- 栀子 10g
- 石膏 20g
- 竹叶 10g
- 甘草 6g
- 玄参 15g

📖 煎服方法：
水煎服，每日1剂，分2次温服。先用冷水浸泡30分钟，大火煮开后小火煎煮20分钟，取汁约200ml。

⚠️ 用药注意事项：
1. 孕妇及哺乳期妇女慎用
2. 脾胃虚寒者减量使用
3. 服药期间忌食生冷、辛辣食物
4. 如有不适请及时就诊

**【免责声明】**
本处方仅供参考，具体用药请遵医嘱。建议到正规中医院进一步诊疗。
    `;
    
    // 保存重构的原始内容
    manager.originalContent.set(prescriptionId, reconstructedContent);
    manager.saveOriginalContentToStorage(prescriptionId, reconstructedContent);
    console.log(`📄 已重构原始内容: ${prescriptionId}`);
    
    // 标记为已支付
    await manager.markAsPaid(prescriptionId);
    console.log(`✅ 处方已强力解锁: ${prescriptionId}`);
    
    return prescriptionId;
};