/**
 * 简化版处方支付管理器
 * 解决支付前隐藏、支付后显示的核心问题
 * v1.0 - 2025-09-26
 */

class SimplePrescriptionManager {
    constructor() {
        this.paymentStatus = new Map(); // 内存中的支付状态
        this.originalContent = new Map(); // 原始处方内容
        console.log('✅ 简化版处方支付管理器初始化');
    }

    /**
     * 核心方法：处理处方内容显示
     * @param {string} content - AI回复的原始内容
     * @param {string} prescriptionId - 处方ID（可选）
     * @returns {string} 处理后的HTML内容
     */
    processContent(content, prescriptionId = null) {
        // 检查是否包含处方
        if (!this.containsPrescription(content)) {
            return this.formatNormalContent(content);
        }

        // 生成处方ID（如果没有提供）
        if (!prescriptionId) {
            prescriptionId = this.generatePrescriptionId(content);
        }

        // 保存原始内容
        this.originalContent.set(prescriptionId, content);

        // 检查支付状态
        const isPaid = this.isPaid(prescriptionId);
        
        console.log(`🔍 处方内容处理: ID=${prescriptionId}, 已支付=${isPaid}`);

        if (isPaid) {
            return this.renderPaidContent(content, prescriptionId);
        } else {
            return this.renderUnpaidContent(content, prescriptionId);
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
     * 检查支付状态
     */
    isPaid(prescriptionId) {
        // 1. 检查内存状态
        if (this.paymentStatus.has(prescriptionId)) {
            return this.paymentStatus.get(prescriptionId);
        }

        // 2. 检查localStorage
        const storageKey = `paid_${prescriptionId}`;
        const stored = localStorage.getItem(storageKey);
        const isPaid = stored === 'true';
        
        // 3. 更新内存状态
        this.paymentStatus.set(prescriptionId, isPaid);
        
        return isPaid;
    }

    /**
     * 标记为已支付
     */
    markAsPaid(prescriptionId) {
        // 1. 更新内存状态
        this.paymentStatus.set(prescriptionId, true);
        
        // 2. 保存到localStorage
        localStorage.setItem(`paid_${prescriptionId}`, 'true');
        
        console.log(`✅ 处方已标记为已支付: ${prescriptionId}`);
        
        // 3. 刷新页面显示
        this.refreshDisplay(prescriptionId);
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
                this.markAsPaid(prescriptionId);
                
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
    refreshDisplay(prescriptionId) {
        const elements = document.querySelectorAll(`[data-prescription-id="${prescriptionId}"]`);
        
        elements.forEach(element => {
            const originalContent = this.originalContent.get(prescriptionId);
            if (originalContent) {
                element.outerHTML = this.renderPaidContent(originalContent, prescriptionId);
                console.log(`✅ 已刷新处方显示: ${prescriptionId}`);
            }
        });
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
    restorePaymentStatus() {
        console.log('🔍 检查已支付处方状态...');
        
        // 查找所有处方元素
        const prescriptionElements = document.querySelectorAll('.prescription-locked');
        let restoredCount = 0;
        
        prescriptionElements.forEach(element => {
            const prescriptionId = element.getAttribute('data-prescription-id');
            if (prescriptionId && this.isPaid(prescriptionId)) {
                const originalContent = this.originalContent.get(prescriptionId);
                if (originalContent) {
                    element.outerHTML = this.renderPaidContent(originalContent, prescriptionId);
                    restoredCount++;
                    console.log(`✅ 恢复已支付状态: ${prescriptionId}`);
                }
            }
        });
        
        if (restoredCount > 0) {
            console.log(`✅ 已恢复 ${restoredCount} 个处方的支付状态`);
        }
    }
}

// 全局初始化
window.simplePrescriptionManager = new SimplePrescriptionManager();

// 页面加载完成后检查支付状态
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        window.simplePrescriptionManager.restorePaymentStatus();
    }, 2000);
});

console.log('✅ 简化版处方支付管理器加载完成');