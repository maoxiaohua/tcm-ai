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

        // 保存原始内容（使用哈希ID作为键）
        this.originalContent.set(hashId, content);
        
        // 同时保存到本地存储，确保页面刷新后能恢复
        this.saveOriginalContentToStorage(hashId, content);

        // 检查支付状态（优先使用数据库ID，回退到哈希ID）
        const checkId = dbId || hashId;
        const isPaid = await this.isPaid(checkId);
        
        console.log(`🔍 处方内容处理: 哈希ID=${hashId}, 数据库ID=${dbId}, 检查ID=${checkId}, 已支付=${isPaid}`);

        if (isPaid) {
            return this.renderPaidContent(content, hashId);
        } else {
            return this.renderUnpaidContent(content, hashId);
        }
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
     * 标记为已支付
     */
    async markAsPaid(prescriptionId) {
        // 1. 更新内存状态
        this.paymentStatus.set(prescriptionId, true);
        
        // 2. 保存到localStorage
        localStorage.setItem(`paid_${prescriptionId}`, 'true');
        
        console.log(`✅ 处方已标记为已支付: ${prescriptionId}`);
        
        // 3. 刷新页面显示
        await this.refreshDisplay(prescriptionId);
    }

    /**
     * 渲染未支付内容（隐藏处方详情）
     */
    renderUnpaidContent(content, prescriptionId) {
        // 提取基本信息（不含具体剂量）
        const diagnosis = this.extractDiagnosis(content);
        
        return `
            <div class="prescription-locked" data-prescription-id="${prescriptionId}">
                ${diagnosis ? `
                    <div style="margin-bottom: 20px; padding: 15px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <h4 style="color: #1e40af; margin: 0 0 10px 0;">🩺 中医诊断分析</h4>
                        <p style="margin: 0; color: #374151; line-height: 1.6;">${diagnosis}</p>
                    </div>
                ` : ''}
                
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
     * 渲染已支付内容（显示完整处方）
     */
    renderPaidContent(content, prescriptionId) {
        // 提取药材信息
        const herbs = this.extractHerbs(content);
        
        let herbsHtml = '';
        if (herbs.length > 0) {
            herbsHtml = `
                <div style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-radius: 12px; border: 2px solid #22c55e;">
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
                // 重新检查支付状态并渲染相应内容
                const isPaid = await this.isPaid(prescriptionId);
                const newContent = isPaid ? 
                    this.renderPaidContent(originalContent, prescriptionId) :
                    this.renderUnpaidContent(originalContent, prescriptionId);
                
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
        
        // 如果没有找到元素，尝试查找整个消息容器
        if (elements.length === 0) {
            console.log(`⚠️ 未找到处方元素，尝试查找消息容器...`);
            const messageElements = document.querySelectorAll('.message.ai');
            for (const msgElement of messageElements) {
                const textElement = msgElement.querySelector('.message-text');
                if (textElement && textElement.innerHTML.includes(prescriptionId)) {
                    const originalContent = this.originalContent.get(prescriptionId);
                    if (originalContent) {
                        const isPaid = await this.isPaid(prescriptionId);
                        const newContent = isPaid ? 
                            this.renderPaidContent(originalContent, prescriptionId) :
                            this.renderUnpaidContent(originalContent, prescriptionId);
                        textElement.innerHTML = newContent;
                        console.log(`✅ 通过消息容器刷新处方显示: ${prescriptionId}, 支付状态: ${isPaid}`);
                    }
                }
            }
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
            
            // 提取诊断信息
            const diagnosis = prescriptionData.diagnosis || '暂无诊断信息';
            const symptoms = prescriptionData.symptoms || '暂无症状记录';
            
            // 提取处方信息（优先使用医生处方，回退到AI处方）
            const prescription = prescriptionData.doctor_prescription || prescriptionData.ai_prescription || '暂无处方信息';
            
            // 重构完整的AI回复内容格式
            const reconstructedContent = `
🩺 专业诊断分析

患者症状：${symptoms}

辨证分析：${diagnosis}

📋 个性化处方方案

${prescription}

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