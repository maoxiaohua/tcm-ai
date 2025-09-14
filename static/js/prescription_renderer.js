/**
 * TCM-AI 处方内容智能渲染器
 * 实现分级展示：免费诊断 → 预览模式 → 付费解锁
 */

class PrescriptionRenderer {
    constructor() {
        this.paymentStatus = null;
        this.prescriptionId = null;
        
        // 处方关键词检测
        this.prescriptionKeywords = [
            '处方如下', '方剂组成', '药物组成', '具体方药',
            '方解', '君药', '臣药', '佐药', '使药',
            '【君药】', '【臣药】', '【佐药】', '【使药】',
            '三、处方建议', '处方方案', '治疗方案', '用药方案'
        ];

        // 临时建议关键词
        this.temporaryKeywords = [
            '初步处方建议', '待确认', '若您能提供', '请补充', 
            '需要了解', '建议进一步', '完善信息后', '详细描述',
            '暂拟方药', '初步考虑', '待详诊后', '待补充',
            '补充舌象', '舌象信息后', '脉象信息后', '上传舌象'
        ];
    }

    /**
     * 检测内容是否包含处方
     */
    containsPrescription(content) {
        if (!content || typeof content !== 'string') return false;

        const hasKeywords = this.prescriptionKeywords.some(keyword => content.includes(keyword));
        const hasDosage = /\d+[克g]\s*[，,，]/.test(content);
        
        return hasKeywords && hasDosage;
    }

    /**
     * 检测是否为临时建议
     */
    isTemporaryAdvice(content) {
        return this.temporaryKeywords.some(keyword => content.includes(keyword));
    }

    /**
     * 主渲染函数
     */
    renderContent(content, isPaid = false, prescriptionId = null) {
        this.paymentStatus = isPaid;
        this.prescriptionId = prescriptionId;

        if (!this.containsPrescription(content)) {
            // 普通对话内容，直接返回
            return content;
        }

        if (this.isTemporaryAdvice(content)) {
            // 临时建议，显示完整内容但加特殊标识
            return this.renderTemporaryAdvice(content);
        }

        if (isPaid) {
            // 已付费用户，显示完整处方
            return this.renderFullPrescription(content);
        } else {
            // 未付费用户，显示预览模式
            return this.renderPrescriptionPreview(content);
        }
    }

    /**
     * 渲染临时建议（完整显示但加标识）
     */
    renderTemporaryAdvice(content) {
        return `
            <div class="temporary-advice-wrapper">
                <div class="advice-header">
                    <span class="advice-badge">💡 初步建议</span>
                    <span class="advice-status">待完善信息后确认</span>
                </div>
                <div class="advice-content">
                    ${this.formatContent(content)}
                </div>
                <div class="advice-footer">
                    <small>⚠️ 此为初步建议，完善症状描述后将提供准确处方</small>
                </div>
            </div>
        `;
    }

    /**
     * 渲染完整处方（付费用户）
     */
    renderFullPrescription(content) {
        const parsedPrescription = this.parsePrescriptionContent(content);
        
        return `
            <div class="prescription-full">
                <div class="prescription-header">
                    <span class="prescription-badge">✅ 完整处方</span>
                    <span class="paid-status">已解锁查看</span>
                </div>
                <div class="prescription-content">
                    ${this.formatPrescriptionContent(parsedPrescription)}
                </div>
                <div class="prescription-actions">
                    <button class="action-btn decoction-btn" onclick="showDecorationInfo('${this.prescriptionId}')">
                        🍵 联系代煎服务
                    </button>
                    <button class="action-btn download-btn" onclick="downloadPrescription('${this.prescriptionId}')">
                        📄 下载处方
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * 渲染处方预览（未付费用户）
     */
    renderPrescriptionPreview(content) {
        const parsedPrescription = this.parsePrescriptionContent(content);
        const diagnosisInfo = this.extractDiagnosisInfo(content);
        const herbsPreview = this.generateHerbsPreview(parsedPrescription.herbs);

        return `
            <div class="prescription-preview-wrapper">
                <!-- 免费部分：专业诊断 -->
                <div class="diagnosis-section">
                    <h4 class="section-title">🩺 专业诊断分析</h4>
                    <div class="diagnosis-content">
                        ${diagnosisInfo.syndrome ? `<p><strong>证候诊断：</strong>${diagnosisInfo.syndrome}</p>` : ''}
                        ${diagnosisInfo.pathogenesis ? `<p><strong>病机分析：</strong>${diagnosisInfo.pathogenesis}</p>` : ''}
                        ${diagnosisInfo.treatment ? `<p><strong>治疗原则：</strong>${diagnosisInfo.treatment}</p>` : ''}
                    </div>
                </div>

                <!-- 处方预览部分 -->
                <div class="prescription-preview">
                    <div class="preview-header">
                        <h4 class="section-title">📋 个性化处方方案</h4>
                        <span class="doctor-badge">${this.getDoctorName()}专方</span>
                    </div>

                    <div class="herbs-preview">
                        <h5>方剂组成预览 <span class="total-count">(共${herbsPreview.total}味药材)</span></h5>
                        <div class="herbs-grid">
                            ${herbsPreview.visible.map(herb => `
                                <div class="herb-card visible">
                                    <span class="herb-name">${herb.name}</span>
                                    <span class="herb-dosage">***g</span>
                                </div>
                            `).join('')}
                            ${herbsPreview.hidden > 0 ? `
                                <div class="herb-card hidden">
                                    <span class="more-herbs">+ ${herbsPreview.hidden} 味药材</span>
                                    <span class="unlock-hint">解锁查看</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    <div class="value-highlights">
                        <h5>完整处方包含</h5>
                        <div class="highlights-grid">
                            <div class="highlight-item">
                                <span class="icon">⚖️</span>
                                <span class="text">精确剂量配比</span>
                            </div>
                            <div class="highlight-item">
                                <span class="icon">🎯</span>
                                <span class="text">个人体质调整</span>
                            </div>
                            <div class="highlight-item">
                                <span class="icon">📖</span>
                                <span class="text">详细煎服指导</span>
                            </div>
                            <div class="highlight-item">
                                <span class="icon">⚠️</span>
                                <span class="text">用药注意事项</span>
                            </div>
                        </div>
                    </div>

                    <!-- 价值对比 -->
                    <div class="value-comparison">
                        <div class="comparison-item traditional">
                            <div class="item-header">
                                <span class="label">传统中医院</span>
                                <span class="price">¥200-400</span>
                            </div>
                            <div class="item-details">
                                <small>挂号费 + 诊疗费 + 交通时间成本</small>
                            </div>
                        </div>
                        <div class="comparison-item tcm-ai highlighted">
                            <div class="item-header">
                                <span class="label">TCM-AI智能诊疗</span>
                                <span class="price">¥88</span>
                            </div>
                            <div class="item-details">
                                <small>5位名医智慧 + AI精准分析 + 24小时服务</small>
                            </div>
                            <div class="savings">节省 ¥112-312</div>
                        </div>
                    </div>

                    <!-- 解锁按钮 -->
                    <div class="unlock-section">
                        <button class="unlock-prescription-btn" onclick="unlockPrescription('${this.prescriptionId || 'temp'}')">
                            <span class="btn-icon">🔓</span>
                            <span class="btn-text">解锁完整处方</span>
                            <span class="btn-price">¥88</span>
                        </button>
                        <div class="trust-indicators">
                            <span class="trust-item">🔒 安全支付</span>
                            <span class="trust-item">💯 专业保障</span>
                            <span class="trust-item">🎁 含代煎服务</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 解析处方内容
     */
    parsePrescriptionContent(content) {
        const herbs = [];
        const lines = content.split('\n');
        
        for (let line of lines) {
            // 匹配药材和剂量：如"党参 15克"、"白术 12g"等
            const herbMatch = line.match(/([^0-9]+)\s*(\d+)\s*[克g]/);
            if (herbMatch) {
                herbs.push({
                    name: herbMatch[1].trim(),
                    dosage: parseInt(herbMatch[2]),
                    unit: 'g',
                    line: line.trim()
                });
            }
        }

        return {
            herbs: herbs,
            originalContent: content,
            summary: this.extractPrescriptionSummary(content)
        };
    }

    /**
     * 生成药材预览
     */
    generateHerbsPreview(herbs) {
        const total = herbs.length;
        const visibleCount = Math.min(2, total); // 显示前2味药材
        const hiddenCount = total - visibleCount;

        return {
            total: total,
            visible: herbs.slice(0, visibleCount),
            hidden: hiddenCount
        };
    }

    /**
     * 提取诊断信息
     */
    extractDiagnosisInfo(content) {
        const info = {
            syndrome: null,
            pathogenesis: null,
            treatment: null
        };

        // 匹配证候
        const syndromeMatch = content.match(/证候[：:]\s*([^。\n]+)/);
        if (syndromeMatch) info.syndrome = syndromeMatch[1];

        // 匹配病机
        const pathogenesisMatch = content.match(/病机[：:]\s*([^。\n]+)/);
        if (pathogenesisMatch) info.pathogenesis = pathogenesisMatch[1];

        // 匹配治法
        const treatmentMatch = content.match(/治法[：:]\s*([^。\n]+)/);
        if (treatmentMatch) info.treatment = treatmentMatch[1];

        return info;
    }

    /**
     * 获取当前医生名称
     */
    getDoctorName() {
        const doctors = {
            'zhang_zhongjing': '张仲景',
            'ye_tianshi': '叶天士',
            'li_dongyuan': '李东垣',
            'zheng_qinan': '郑钦安',
            'liu_duzhou': '刘渡舟'
        };
        
        return doctors[window.selectedDoctor] || '名医';
    }

    /**
     * 格式化内容
     */
    formatContent(content) {
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    /**
     * 格式化处方内容
     */
    formatPrescriptionContent(parsedPrescription) {
        let formatted = this.formatContent(parsedPrescription.originalContent);
        
        // 高亮药材名称
        parsedPrescription.herbs.forEach(herb => {
            const regex = new RegExp(`(${herb.name})\\s*(\\d+[克g])`, 'g');
            formatted = formatted.replace(regex, '<span class="herb-highlight">$1 $2</span>');
        });

        return formatted;
    }

    /**
     * 提取处方摘要
     */
    extractPrescriptionSummary(content) {
        // 提取方剂名称
        const formulaMatch = content.match(/方[名用][：:]?\s*([^。\n,，]+)/);
        return formulaMatch ? formulaMatch[1] : '个性化方剂';
    }
}

// 全局处方解锁函数
function unlockPrescription(prescriptionId) {
    console.log('🔓 开始处方解锁流程:', prescriptionId);
    
    // 检查登录状态
    if (!window.currentUser || !window.userToken) {
        showMessage('请先登录后解锁处方', 'error');
        showLoginModal();
        return;
    }

    // 如果是临时ID，先创建处方记录
    if (prescriptionId === 'temp') {
        createPrescriptionRecord();
    } else {
        // 直接进入支付流程
        initiatePrescriptionPayment(prescriptionId);
    }
}

// 创建处方记录
async function createPrescriptionRecord() {
    try {
        // 获取最后一条包含处方的AI消息
        const prescriptionContent = getPrescriptionContent();
        if (!prescriptionContent) {
            showMessage('未找到处方内容', 'error');
            return;
        }

        const response = await fetch('/api/prescriptions/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                conversation_id: window.currentConversationId,
                doctor_name: window.selectedDoctor,
                prescription_content: prescriptionContent,
                patient_symptoms: getCurrentSymptoms()
            })
        });

        const result = await response.json();
        if (result.success && result.prescription_id) {
            initiatePrescriptionPayment(result.prescription_id);
        } else {
            showMessage('创建处方记录失败', 'error');
        }
    } catch (error) {
        console.error('创建处方记录失败:', error);
        showMessage('创建处方记录失败', 'error');
    }
}

// 启动处方支付流程
function initiatePrescriptionPayment(prescriptionId) {
    console.log('💰 启动支付流程:', prescriptionId);
    
    // 调用现有的支付模态框
    if (typeof showPaymentModal === 'function') {
        showPaymentModal(prescriptionId, 88.00);
    } else {
        showMessage('支付系统暂时不可用', 'error');
    }
}

// 获取处方内容
function getPrescriptionContent() {
    const messages = document.querySelectorAll('.message.ai .message-text');
    for (let i = messages.length - 1; i >= 0; i--) {
        const content = messages[i].textContent;
        const renderer = new PrescriptionRenderer();
        if (renderer.containsPrescription(content) && !renderer.isTemporaryAdvice(content)) {
            return content;
        }
    }
    return null;
}

// 获取当前症状描述
function getCurrentSymptoms() {
    const userMessages = document.querySelectorAll('.message.user .message-text');
    const symptoms = [];
    userMessages.forEach(msg => {
        symptoms.push(msg.textContent.trim());
    });
    return symptoms.join(' | ');
}

// 下载处方
function downloadPrescription(prescriptionId) {
    console.log('📄 下载处方:', prescriptionId);
    showMessage('处方下载功能开发中', 'info');
}

// 创建全局实例
window.prescriptionRenderer = new PrescriptionRenderer();

console.log('✅ 处方渲染器已加载');