/**
 * TCM-AI 处方内容智能渲染器 v2.6.2
 * 实现分级展示：免费诊断 → 预览模式 → 付费解锁
 * 修复临时建议检测误判问题 - 2025-09-16
 */

class PrescriptionRenderer {
    constructor() {
        this.paymentStatus = null;
        this.prescriptionId = null;
        
        // 🔍 调试信息：版本验证
        console.log('🔧 PrescriptionRenderer v2.6.3 初始化 - 沙盒支付测试版');
        
        // 🔒 正式支付模式
        console.log('🔒 正式支付模式 - 使用真实支付流程');
        
        // 处方关键词检测（强化版）
        this.prescriptionKeywords = [
            '处方如下', '方剂组成', '药物组成', '具体方药',
            '方解', '君药', '臣药', '佐药', '使药',
            '【君药】', '【臣药】', '【佐药】', '【使药】',
            '三、处方建议', '处方方案', '治疗方案', '用药方案',
            '建议方药', '推荐方剂', '可考虑', '方剂:', '处方:',
            '药材组成', '中药配伍', '组方', '方用'
        ];

        // 常见中药材名称（用于更严格的检测）
        this.commonHerbs = [
            '当归', '白芍', '川芎', '熟地', '党参', '白术', '茯苓', '甘草',
            '黄芪', '人参', '生地', '麦冬', '五味子', '山药', '泽泻', '牡丹皮',
            '山茱萸', '附子', '肉桂', '干姜', '半夏', '陈皮', '茯神', '远志',
            '酸枣仁', '龙骨', '牡蛎', '柴胡', '黄芩', '连翘', '金银花', '板蓝根',
            '桔梗', '杏仁', '枇杷叶', '川贝母', '百合', '知母', '石膏', '栀子'
        ];

        // 临时建议关键词（修复版 - 移除误判词汇）
        this.temporaryKeywords = [
            '初步处方建议', '待确认处方', '若您能提供更多信息', '请补充具体症状', 
            '需要了解更多病史', '完善信息后开方', '详细描述症状后',
            '暂拟方药', '待详诊后开方', '待补充信息后',
            '补充舌象后开方', '舌象信息后确认', '脉象信息后处方', '上传舌象后',
            '提供舌象后', '后确认处方', '暂拟处方方案',
            '初步建议处方', '建议面诊确认', 
            '如需准确诊断请', '更详细的症状描述', '需要更多信息才能',
            '暂时建议处方', '请您补充症状', '需要您提供更多',
            '临时处方方案', '初步处方方案', '可先试用此方'
        ];
        
        // 🔍 调试信息：关键词列表验证
        console.log('🔧 临时建议关键词已加载，总数:', this.temporaryKeywords.length);
        const problematicCheck = ['建议进一步', '若症状持续'].filter(k => this.temporaryKeywords.includes(k));
        if (problematicCheck.length > 0) {
            console.error('❌ 发现问题关键词:', problematicCheck);
        } else {
            console.log('✅ 问题关键词已清除');
        }
    }

    /**
     * 生成对话ID
     */
    generateConversationId() {
        return 'conv-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * 获取当前用户ID
     */
    getCurrentUserId() {
        // 尝试多种方式获取用户ID
        if (window.getCurrentUserId && typeof window.getCurrentUserId === 'function') {
            return window.getCurrentUserId();
        }
        
        // 从localStorage获取
        try {
            const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
            return currentUser.user_id || null;
        } catch (error) {
            console.warn('获取用户ID失败:', error);
            return null;
        }
    }

    /**
     * 检测内容是否包含处方（强化版检测）
     * 
     * 🔑 关键区别：
     * - 完整处方：明确的处方关键词 + 具体剂量 + 非临时建议
     * - 临时建议：包含"待确认"、"建议补充"等临时性表述
     */
    containsPrescription(content) {
        if (!content || typeof content !== 'string') return false;

        // 🚨 首先检查是否为临时建议
        if (this.isTemporaryAdvice(content)) {
            console.log('🔍 检测到临时建议，不算完整处方:', content.substring(0, 100));
            return false;
        }

        // 1. 检测明确的处方关键词
        const hasExplicitKeywords = this.prescriptionKeywords.some(keyword => content.includes(keyword));
        
        // 2. 检测药材+剂量的模式（更严格）
        const hasDosagePattern = /\d+[克g]\s*[，,，。]/gi.test(content);
        
        // 3. 检测常见中药材名称
        const herbCount = this.commonHerbs.filter(herb => content.includes(herb)).length;
        
        // 4. 检测典型的方剂描述模式
        const hasFormulaPattern = /[：:]\s*\w+\s*\d+[克g]/.test(content); // 如"党参: 15克"
        const hasHerbList = /\d+\s*[味个]\s*药/.test(content); // 如"6味药"
        
        // 5. 🔑 检测完整处方的特征（区别于临时建议）
        const hasCompleteStructure = content.includes('【君药】') || 
                                   content.includes('【臣药】') || 
                                   content.includes('方剂组成') ||
                                   content.includes('处方如下') ||
                                   /方[名用][：:]/.test(content);
        
        // 6. 检测药材数量（完整处方通常有更多药材）
        const hasMultipleHerbs = herbCount >= 4; // 提高阈值
        
        // 🔑 修复：进一步降低检测阈值，确保更多处方被识别
        const isCompletePrescription = (
            // 基本条件：有处方关键词 OR (有剂量 + 有中药材) OR 有完整结构
            hasExplicitKeywords || 
            (hasDosagePattern && herbCount >= 2) ||  // 只要有2种药材+剂量即可
            hasFormulaPattern ||
            hasCompleteStructure ||
            // 增加额外检测：多种药材（即使没有明确剂量）
            (herbCount >= 5) ||  // 5种以上药材很可能是处方
            // 检测典型处方句式
            /[配伍|治疗|方用|方取]/.test(content) && herbCount >= 3
        );
        
        if (isCompletePrescription) {
            console.log('✅ 检测到完整处方:', {
                hasExplicitKeywords,
                hasDosagePattern,
                hasCompleteStructure,
                herbCount,
                content: content.substring(0, 100)
            });
        }
        
        return isCompletePrescription;
    }

    /**
     * 检测是否为临时建议 - 使用精确匹配避免误判
     */
    isTemporaryAdvice(content) {
        // 🔑 修复：优先检查完整处方特征，降低误判率
        
        // 1. 先检查是否有明确的完整处方特征
        const hasCompleteStructure = content.includes('【君药】') || 
                                   content.includes('【臣药】') || 
                                   content.includes('【佐药】') || 
                                   content.includes('【使药】') ||
                                   content.includes('方剂组成') ||
                                   content.includes('处方如下');
        
        // 2. 检查药材数量和剂量
        const herbCount = this.commonHerbs.filter(herb => content.includes(herb)).length;
        const hasDosagePattern = /\d+[克g]\s*[，,，。]/gi.test(content);
        
        // 3. 如果有完整结构特征 + 多种药材 + 剂量，优先认为是完整处方
        if (hasCompleteStructure && herbCount >= 3 && hasDosagePattern) {
            console.log('✅ 检测到完整处方特征，不视为临时建议');
            return false;
        }
        
        // 4. 检查临时建议关键词（提高阈值）
        let matchedKeywords = [];
        const strongTemporaryKeywords = [
            '初步处方建议', '待确认处方', '若您能提供更多信息', 
            '请补充具体症状', '需要了解更多病史', '完善信息后开方',
            '暂拟方药', '待详诊后开方', '补充舌象后开方',
            '建议面诊确认', '需要更多信息才能'
        ];
        
        for (const keyword of strongTemporaryKeywords) {
            if (content.includes(keyword)) {
                matchedKeywords.push(keyword);
            }
        }
        
        // 5. 🔑 关键修复：只有匹配到强临时关键词且没有完整结构时才认为是临时建议
        const isTemporary = matchedKeywords.length > 0 && !hasCompleteStructure;
        
        if (isTemporary) {
            console.log('🔍 检测到临时建议关键词:', matchedKeywords, '内容预览:', content.substring(0, 150));
        } else if (matchedKeywords.length > 0) {
            console.log('⚠️ 虽有临时关键词但有完整结构，视为完整处方:', matchedKeywords);
        }
        
        return isTemporary;
    }

    /**
     * 主渲染函数
     */
    renderContent(content, isPaid = false, prescriptionId = null) {
        console.log('📋 renderContent 被调用:', {
            contentLength: content.length,
            isPaid,
            prescription_id: prescriptionId,
            contentPreview: content.substring(0, 100)
        });
        
        this.paymentStatus = isPaid;
        this.prescriptionId = prescriptionId;

        // 🔒 信任后端的处方检测结果，同时进行前端验证
        const backendDetectedPrescription = prescriptionId !== null && prescriptionId !== undefined;
        const frontendDetectedPrescription = this.containsPrescription(content);
        
        console.log('🔍 处方检测结果对比:', {
            backendDetected: backendDetectedPrescription,
            frontendDetected: frontendDetectedPrescription,
            prescription_id: prescriptionId
        });
        
        // 优先信任后端检测结果
        const containsActualPrescription = backendDetectedPrescription || frontendDetectedPrescription;
        
        if (!containsActualPrescription) {
            // 普通对话内容，进行基础格式化
            return this.renderDiagnosisAnalysis(content);
        }

        // 🔒 正式模式：仅依赖API返回的支付状态
        console.log(`📋 处方支付状态检查 - isPaid: ${isPaid}, prescriptionId: ${prescriptionId}`);

        // 🚨 检测到处方内容 - 根据支付状态决定显示方式
        console.log('🔒 检测到处方内容，支付状态:', isPaid, '处方ID:', prescriptionId);

        if (this.isTemporaryAdvice(content)) {
            // 临时建议，显示完整内容但加特殊标识
            return this.renderTemporaryAdvice(content);
        }

        if (isPaid) {
            // 已付费用户，显示完整处方
            console.log('✅ 用户已付费，显示完整处方');
            return this.renderFullPrescription(content);
        } else {
            // 未付费用户，强制显示预览模式（隐藏具体处方内容）
            console.log('🔒 用户未付费，显示预览模式');
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
        
        console.log('🔍 renderFullPrescription 解析结果:', {
            herbsCount: parsedPrescription.herbs.length,
            herbs: parsedPrescription.herbs.map(h => `${h.name} ${h.dosage}g`)
        });
        
        // 如果成功解析到药材，生成结构化的药材列表
        let herbsListHtml = '';
        if (parsedPrescription.herbs.length > 0) {
            herbsListHtml = `
                <div class="prescription-herbs-list" style="margin: 20px 0; padding: 20px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;">
                    <h4 style="color: #2d3748; margin-bottom: 15px; font-size: 16px;">📋 方剂组成 (共${parsedPrescription.herbs.length}味药材)</h4>
                    <div class="herbs-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                        ${parsedPrescription.herbs.map(herb => `
                            <div class="herb-item" style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: white; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 14px;">
                                <span class="herb-name" style="color: #2d3748; font-weight: 500;">${herb.name}</span>
                                <span class="herb-dosage" style="color: #059669; font-weight: bold;">${herb.dosage}g</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="prescription-full">
                <div class="prescription-header">
                    <span class="prescription-badge">✅ 完整处方</span>
                    <span class="paid-status">已解锁查看</span>
                </div>
                <div class="prescription-content">
                    ${herbsListHtml}
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
                        ${diagnosisInfo.syndrome ? `<p><strong>辨证分析：</strong>${diagnosisInfo.syndrome}</p>` : ''}
                        ${diagnosisInfo.pathogenesis ? `<p><strong>病机分析：</strong>${diagnosisInfo.pathogenesis}</p>` : ''}
                        ${diagnosisInfo.treatment ? `<p><strong>治疗原则：</strong>${diagnosisInfo.treatment}</p>` : ''}
                        ${diagnosisInfo.analysis ? `<p><strong>综合分析：</strong>${diagnosisInfo.analysis}</p>` : ''}
                        ${!diagnosisInfo.syndrome && !diagnosisInfo.pathogenesis && !diagnosisInfo.treatment && !diagnosisInfo.analysis ? 
                            '<p><strong>专业辨证：</strong>完整的中医四诊合参分析，包含证候判断、病机分析、治疗方案等</p>' : ''}
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
        
        console.log('🔍 解析处方内容，总行数:', lines.length);
        
        for (let line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;
            
            // 匹配药材和剂量的多种模式
            const patterns = [
                // 1. "党参 15克" "白术 12g"
                /([^0-9\-\*]+)\s*(\d+)\s*[克g]/,
                // 2. "党参：15克" "白术: 12g" 
                /([^0-9\-\*：:]+)[：:]\s*(\d+)\s*[克g]/,
                // 3. "- 党参 15克" "* 白术 12g"
                /[\-\*•]\s*([^0-9\-\*]+)\s*(\d+)\s*[克g]/,
                // 4. "人参 g" 这种没有具体剂量的格式（使用默认剂量）
                /([^0-9\-\*]+)\s*[克g](?!\d)/,
                // 5. 纯药材名称，后面跟着空格或其他字符
                /^\s*[\-\*•]?\s*([一-龟\u4e00-\u9fff]{2,6})(?:\s|$|[，,。.])/
            ];
            
            let matched = false;
            for (let i = 0; i < patterns.length; i++) {
                const herbMatch = trimmedLine.match(patterns[i]);
                if (herbMatch) {
                    const herbName = herbMatch[1].trim();
                    let dosage = herbMatch[2] ? parseInt(herbMatch[2]) : null;
                    
                    // 如果没有找到剂量，根据常见药材设置默认剂量
                    if (!dosage) {
                        dosage = this.getDefaultDosage(herbName);
                    }
                    
                    // 验证药材名称（排除非药材词汇）
                    if (this.isValidHerbName(herbName)) {
                        herbs.push({
                            name: herbName,
                            dosage: dosage,
                            unit: 'g',
                            line: trimmedLine,
                            pattern_matched: i + 1
                        });
                        matched = true;
                        console.log(`✅ 解析到药材: ${herbName} ${dosage}g (模式${i + 1})`);
                    }
                    break;
                }
            }
            
            if (!matched && trimmedLine.length > 1) {
                console.log(`⚠️ 未能解析行: "${trimmedLine}"`);
            }
        }

        console.log(`🔍 解析完成，共找到 ${herbs.length} 味药材:`, herbs.map(h => `${h.name} ${h.dosage}g`));

        return {
            herbs: herbs,
            originalContent: content,
            summary: this.extractPrescriptionSummary(content)
        };
    }

    /**
     * 获取药材默认剂量
     */
    getDefaultDosage(herbName) {
        const defaultDosages = {
            '人参': 10, '党参': 15, '白术': 12, '茯苓': 15, '甘草': 6,
            '当归': 10, '白芍': 12, '川芎': 6, '熟地': 15, '生地': 15,
            '黄芪': 20, '白芥子': 10, '陈皮': 9, '半夏': 9, '干姜': 6,
            '附子': 6, '肉桂': 3, '山药': 15, '泽泻': 12, '牡丹皮': 10,
            '山茱萸': 12, '五味子': 6, '麦冬': 12, '知母': 10, '石膏': 30,
            '黄芩': 10, '黄连': 6, '栀子': 10, '连翘': 12, '金银花': 15,
            '板蓝根': 15, '桔梗': 6, '杏仁': 10, '枇杷叶': 10, '川贝母': 10,
            '百合': 20, '远志': 6, '酸枣仁': 15, '龙骨': 20, '牡蛎': 20
        };
        return defaultDosages[herbName] || 12; // 默认12g
    }

    /**
     * 验证是否为有效的药材名称
     */
    isValidHerbName(name) {
        // 排除明显不是药材的词汇
        const invalidWords = [
            '处方', '方剂', '组成', '君药', '臣药', '佐药', '使药', '功效', '主治',
            '用法', '用量', '禁忌', '注意', '方解', '按语', '加减', '如下', '建议',
            '症状', '治疗', '疾病', '患者', '先生', '女士', '医生', '中医', '方法',
            '效果', '作用', '配伍', '药材', '中药', '汤剂', '丸剂', '散剂'
        ];
        
        if (invalidWords.includes(name)) {
            return false;
        }
        
        // 检查长度和字符
        if (name.length < 2 || name.length > 6) {
            return false;
        }
        
        // 检查是否全部为中文字符
        return /^[\u4e00-\u9fff]+$/.test(name);
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
     * 提取诊断信息（强化版）
     */
    extractDiagnosisInfo(content) {
        const info = {
            syndrome: null,
            pathogenesis: null,
            treatment: null,
            analysis: null
        };

        // 匹配辨证分析（多种模式）- 修复：允许逗号，提取更完整的内容
        const analysisPatterns = [
            /辨证分析[：:]?\s*([^。\n]+)/,
            /辨证为[：:]?\s*([^。\n]+)/,
            /初步辨证[：:]?\s*([^。\n]+)/,
            /证候[：:]\s*([^。\n]+)/,
            /【([^】]*病机[^】]*)】/,
            /\*\*([^*]*病机[^*]*)\*\*/
        ];
        
        for (const pattern of analysisPatterns) {
            const match = content.match(pattern);
            if (match) {
                info.syndrome = match[1].replace(/[*】【]/g, '').trim();
                break;
            }
        }

        // 匹配病机分析
        const pathogenesisPatterns = [
            /病机[：:]\s*([^。\n]+)/,
            /病因病机[：:]\s*([^。\n]+)/,
            /发病机理[：:]\s*([^。\n]+)/
        ];
        
        for (const pattern of pathogenesisPatterns) {
            const match = content.match(pattern);
            if (match) {
                info.pathogenesis = match[1];
                break;
            }
        }

        // 匹配治法原则 - 修复：提取更完整的治疗原则
        const treatmentPatterns = [
            /治疗原则[：:]\s*([^。\n]+)/,
            /治法[：:]\s*([^。\n]+)/,
            /治宜[：:]?\s*([^。\n]+)/,
            /方法[：:]\s*([^。\n]+)/
        ];
        
        for (const pattern of treatmentPatterns) {
            const match = content.match(pattern);
            if (match) {
                info.treatment = match[1].replace(/[*】【]/g, '').trim();
                break;
            }
        }

        // 提取整体分析摘要（取前面的分析部分，避免处方内容）
        const beforePrescription = content.split(/【处方|【君药|处方如下|方剂组成/)[0];
        if (beforePrescription && beforePrescription.length > 50) {
            // 取最后一个完整段落作为分析摘要
            const paragraphs = beforePrescription.split('\n\n').filter(p => p.trim());
            if (paragraphs.length > 0) {
                const lastParagraph = paragraphs[paragraphs.length - 1].trim();
                if (lastParagraph.length > 30 && lastParagraph.length < 200) {
                    info.analysis = lastParagraph.replace(/[*#【】]/g, '').trim();
                }
            }
        }

        return info;
    }

    /**
     * 获取当前医生名称
     */
    getDoctorName() {
        const doctors = {
            'zhang_zhongjing': '张仲景',
            'jin_daifu': '金大夫'
        };

        return doctors[window.selectedDoctor] || '名医';
    }

    /**
     * 格式化内容（增强版）
     */
    formatContent(content) {
        if (!content || typeof content !== 'string') return '';
        
        return content
            // 处理【处方】标签 - 特殊高亮样式
            .replace(/\*\*【处方】\*\*/g, '<div style="background: linear-gradient(135deg, #2d5aa0, #4a7bc8); color: white; padding: 10px 15px; border-radius: 8px; margin: 15px 0; font-weight: bold; font-size: 16px; text-align: center;">📋 中药处方</div>')
            // 处理【用法】【注意】等标签
            .replace(/\*\*【(用法|注意|禁忌|功效)】\*\*/g, '<div style="background: #f3f4f6; color: #374151; padding: 8px 12px; border-radius: 6px; margin: 10px 0; font-weight: bold; border-left: 4px solid #6b7280;">$1</div>')
            // 处理其他粗体标签【xxx】
            .replace(/\*\*【(.*?)】\*\*/g, '<strong style="color: #2d5aa0; font-size: 15px; background: #e0f2fe; padding: 2px 6px; border-radius: 4px;">【$1】</strong>')
            // 处理其他粗体文本
            .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #1f2937; font-weight: bold;">$1</strong>')
            .replace(/\*(.*?)\*/g, '<em style="color: #6b7280;">$1</em>')
            // 处理#####标记 - 转换为分割线
            .replace(/#{5,}/g, '<hr style="margin: 20px 0; border: none; border-top: 2px solid #e5e7eb; background: linear-gradient(to right, #e5e7eb, transparent);">')
            // 处理###标记 - 转换为明显的小标题
            .replace(/###\s*(.*?)(?=\n|$)/g, '<h4 style="margin: 20px 0 12px 0; color: #2d5aa0; font-size: 17px; font-weight: bold; padding-left: 8px; border-left: 4px solid #2d5aa0; background: #f8fafc;">$1</h4>')
            // 处理##标记 - 转换为更大的中标题  
            .replace(/##\s*(.*?)(?=\n|$)/g, '<h3 style="margin: 25px 0 15px 0; color: #1f2937; font-size: 19px; font-weight: bold; padding: 8px 12px; background: linear-gradient(135deg, #f3f4f6, #e5e7eb); border-radius: 6px;">$1</h3>')
            // 处理#标记 - 转换为大标题
            .replace(/^#\s*(.*?)(?=\n|$)/gm, '<h2 style="margin: 30px 0 20px 0; color: #111827; font-size: 22px; font-weight: bold; text-align: center; padding: 12px; background: linear-gradient(135deg, #dbeafe, #bfdbfe); border-radius: 8px;">$1</h2>')
            // 处理药材列表 - 特殊样式
            .replace(/([一-龟\u4e00-\u9fff]+)\s+(\d+)g/g, '<span style="display: inline-block; background: #ecfdf5; color: #065f46; padding: 2px 6px; margin: 1px 3px; border-radius: 4px; font-weight: 500; border: 1px solid #d1fae5;">$1 <strong>$2g</strong></span>')
            .replace(/\n\n/g, '<br><br>')  // 段落间距
            .replace(/\n/g, '<br>')        // 普通换行
            .replace(/(\d+\.\s)/g, '<br><span style="color: #2d5aa0; font-weight: bold;">$1</span>') // 数字列表样式
            .replace(/^<br>/, '');         // 移除开头的换行
    }

    /**
     * 格式化处方内容
     */
    formatPrescriptionContent(parsedPrescription) {
        let formatted = this.formatContent(parsedPrescription.originalContent);
        
        // 高亮药材名称
        parsedPrescription.herbs.forEach(herb => {
            // 🔧 转义药材名称中的正则表达式特殊字符
            const escapedHerbName = herb.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escapedHerbName})\\s*(\\d+[克g])`, 'g');
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

    /**
     * 按药物分类分组
     */
    groupHerbsByCategory(content, herbs) {
        const categories = {
            君药: [],
            臣药: [],
            佐药: [],
            使药: [],
            其他: []
        };
        
        let hasCategories = false;
        
        // 检查是否有明确的分类标识
        const categoryPatterns = {
            君药: /【君药】([\s\S]*?)(?=【[臣佐使]药】|$)/,
            臣药: /【臣药】([\s\S]*?)(?=【[佐使]药】|$)/,
            佐药: /【佐药】([\s\S]*?)(?=【使药】|$)/,
            使药: /【使药】([\s\S]*?)$/
        };
        
        Object.keys(categoryPatterns).forEach(category => {
            const match = content.match(categoryPatterns[category]);
            if (match) {
                hasCategories = true;
                const categoryHerbs = herbs.filter(herb => 
                    match[1].includes(herb.name)
                );
                categories[category] = categoryHerbs;
            }
        });
        
        // 如果没有明确分类，将所有药材放入"其他"
        if (!hasCategories) {
            categories.其他 = herbs;
        }
        
        return { ...categories, hasCategories };
    }

    /**
     * 渲染分类药材
     */
    renderCategorizedHerbs(herbsGrouped) {
        let html = '<div class="categorized-herbs">';
        
        const categoryLabels = {
            君药: '👑 君药（主药）',
            臣药: '🤝 臣药（辅助）', 
            佐药: '⚖️ 佐药（调和）',
            使药: '🎯 使药（引经）'
        };
        
        Object.keys(categoryLabels).forEach(category => {
            if (herbsGrouped[category] && herbsGrouped[category].length > 0) {
                html += `
                    <div class="herb-category">
                        <h5 class="category-title">${categoryLabels[category]}</h5>
                        <div class="herbs-grid">
                            ${herbsGrouped[category].map(herb => `
                                <div class="herb-item">
                                    <span class="herb-name">${herb.name}</span>
                                    <span class="herb-dosage">${herb.dosage}${herb.unit}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
        });
        
        html += '</div>';
        return html;
    }

    /**
     * 渲染简单药材列表
     */
    renderSimpleHerbsList(herbs) {
        return `
            <div class="simple-herbs-list">
                <div class="herbs-grid">
                    ${herbs.map(herb => `
                        <div class="herb-item">
                            <span class="herb-name">${herb.name}</span>
                            <span class="herb-dosage">${herb.dosage}${herb.unit}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * 格式化支付弹窗中的处方内容（问诊汇总信息）- 增强版
     */
    formatForPaymentModal(content) {
        if (!content || typeof content !== 'string') {
            return '<p class="no-content">暂无处方内容</p>';
        }

        console.log('🔍 开始格式化支付模态框内容:', content.substring(0, 200));

        // 🔑 简化处理：直接格式化内容，保持结构清晰
        const formattedContent = this.formatContent(content);
        
        return `
            <div class="payment-modal-content">
                <div class="modal-section">
                    <h4 class="section-title">📋 ${this.getDoctorName()}专业问诊汇总</h4>
                    <div class="section-content" style="max-height: 400px; overflow-y: auto; line-height: 1.6;">
                        ${formattedContent}
                    </div>
                </div>
                <div class="modal-footer">
                    <p class="consultation-summary-note">
                        <span class="note-icon">💰</span>
                        <span>支付后可获得完整处方详情及用药指导</span>
                    </p>
                </div>
            </div>
        `;
    }

    /**
     * 检测是否为章节标题
     */
    isSectionTitle(line) {
        const sectionPatterns = [
            /^[一二三四五六七八九十]+[、．。]/,  // 中文序号
            /^\d+[、．。]/,                      // 阿拉伯数字序号
            /^[证病机治方药煎服注意][候机法剂物服意][：:]/,  // 中医术语开头
            /^【[^】]+】/,                        // 【标题】格式
            /^[▪•·]/,                          // 项目符号
            /^处方[如下建议方案]/,                   // 处方相关
        ];
        
        return sectionPatterns.some(pattern => pattern.test(line));
    }

    /**
     * 格式化章节标题
     */
    formatSectionTitle(title) {
        // 移除序号和符号，保留核心内容
        let cleanTitle = title
            .replace(/^[一二三四五六七八九十]+[、．。]\s*/, '')
            .replace(/^\d+[、．。]\s*/, '')
            .replace(/^【([^】]+)】/, '$1')
            .replace(/[：:]$/, '');

        // 添加适当的emoji图标
        const iconMap = {
            '证候': '🩺',
            '诊断': '🩺',
            '病机': '🧬',
            '治法': '⚕️',
            '方药': '📋',
            '处方': '📋',
            '煎服': '🍵',
            '用法': '🍵',
            '注意': '⚠️',
            '禁忌': '⚠️'
        };

        for (const [key, icon] of Object.entries(iconMap)) {
            if (cleanTitle.includes(key)) {
                return `${icon} ${cleanTitle}`;
            }
        }

        return cleanTitle;
    }

    /**
     * 格式化行内容
     */
    formatLineContent(line) {
        return line
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // 粗体
            .replace(/([^0-9]+)(\d+[克g])/g, '<span class="herb-highlight">$1</span> <strong>$2</strong>');  // 药材高亮
    }

    /**
     * 提取煎服方法
     */
    extractDecoctionMethod(content) {
        const patterns = [
            /煎服[方法]*[：:]([^。\n]+)/,
            /用法用量[：:]([^。\n]+)/,
            /每日[一二三1-3]剂[，,]?([^。\n]+)/
        ];

        for (const pattern of patterns) {
            const match = content.match(pattern);
            if (match) return match[1];
        }

        return null;
    }

    /**
     * 提取注意事项
     */
    extractPrecautions(content) {
        const patterns = [
            /注意事项[：:]([^。\n]+)/,
            /禁忌[：:]([^。\n]+)/,
            /忌[食用]([^。\n]+)/
        ];

        for (const pattern of patterns) {
            const match = content.match(pattern);
            if (match) return match[1];
        }

        return null;
    }

    /**
     * 渲染支付弹窗章节内容
     */
    renderPaymentModalSections(sections) {
        if (sections.length === 0) {
            return '<p class="no-content">处方内容解析中...</p>';
        }

        const sectionsHtml = sections.map(section => `
            <div class="modal-section">
                <h4 class="section-title">${section.title}</h4>
                <div class="section-content">
                    ${section.content}
                </div>
            </div>
        `).join('');

        return `
            <div class="payment-modal-content">
                ${sectionsHtml}
                <div class="modal-footer">
                    <p class="consultation-summary-note">
                        <span class="note-icon">📋</span>
                        <span>以上为${this.getDoctorName()}专业问诊汇总，支付后可获得完整处方详情</span>
                    </p>
                </div>
            </div>
        `;
    }

    /**
     * 渲染普通诊断分析内容（结构化显示）
     */
    renderDiagnosisAnalysis(content) {
        if (!content || typeof content !== 'string') {
            return content;
        }

        const sections = [];
        const lines = content.split('\n').filter(line => line.trim());

        // 解析内容结构
        let currentSection = null;
        let currentContent = [];

        for (const line of lines) {
            const trimmedLine = line.trim();
            
            // 检测章节标题
            if (this.isDiagnosisSection(trimmedLine)) {
                // 保存上一个章节
                if (currentSection && currentContent.length > 0) {
                    sections.push({
                        title: currentSection,
                        content: currentContent.join('<br>')
                    });
                }
                
                // 开始新章节
                currentSection = this.formatDiagnosisSectionTitle(trimmedLine);
                currentContent = [];
            } else if (trimmedLine) {
                // 添加到当前章节内容
                currentContent.push(this.formatLineContent(trimmedLine));
            }
        }

        // 保存最后一个章节
        if (currentSection && currentContent.length > 0) {
            sections.push({
                title: currentSection,
                content: currentContent.join('<br>')
            });
        }

        // 如果没有找到章节结构，按段落分组
        if (sections.length === 0) {
            const paragraphs = content.split('\n\n').filter(p => p.trim());
            
            if (paragraphs.length > 1) {
                paragraphs.forEach((paragraph, index) => {
                    const lines = paragraph.trim().split('\n').filter(line => line.trim());
                    if (lines.length > 0) {
                        const firstLine = lines[0].trim();
                        let title = '📋 诊断分析';
                        
                        // 根据内容特征生成标题
                        if (firstLine.includes('症状') || firstLine.includes('主诉')) {
                            title = '📝 症状分析';
                        } else if (firstLine.includes('证候') || firstLine.includes('辨证')) {
                            title = '🩺 辨证分析';
                        } else if (firstLine.includes('病机') || firstLine.includes('机理')) {
                            title = '🧬 病机分析';
                        } else if (firstLine.includes('治法') || firstLine.includes('治疗')) {
                            title = '⚕️ 治疗原则';
                        } else if (firstLine.includes('建议') || firstLine.includes('需要')) {
                            title = '💡 医嘱建议';
                        } else if (index === 0) {
                            title = '🩺 初步分析';
                        } else {
                            title = `📋 分析要点 ${index + 1}`;
                        }
                        
                        sections.push({
                            title: title,
                            content: lines.map(line => this.formatLineContent(line)).join('<br>')
                        });
                    }
                });
            } else {
                // 单段内容，默认格式化
                return `
                    <div class="diagnosis-analysis">
                        <div class="analysis-content">
                            ${this.formatLineContent(content)}
                        </div>
                    </div>
                `;
            }
        }

        // 生成最终HTML
        return this.renderDiagnosisSections(sections);
    }

    /**
     * 检测是否为诊断章节标题
     */
    isDiagnosisSection(line) {
        const diagnosisPatterns = [
            /^[一二三四五六七八九十]+[、．。]/,  // 中文序号
            /^\d+[）)、．。]/,                   // 阿拉伯数字序号
            /^[证病机治建议需要][候机法疗议要][：:]/,  // 中医术语开头
            /^【[^】]+】/,                        // 【标题】格式
            /^[▪•·]/,                           // 项目符号
            /^(症状分析|辨证论治|病机|治法|建议|诊断)/     // 常见诊断术语
        ];
        
        return diagnosisPatterns.some(pattern => pattern.test(line));
    }

    /**
     * 格式化诊断章节标题
     */
    formatDiagnosisSectionTitle(title) {
        // 移除序号和符号，保留核心内容
        let cleanTitle = title
            .replace(/^[一二三四五六七八九十]+[、．。]\s*/, '')
            .replace(/^\d+[）)、．。]\s*/, '')
            .replace(/^【([^】]+)】/, '$1')
            .replace(/[：:]$/, '');

        // 添加适当的emoji图标
        const diagnosisIconMap = {
            '症状': '📝',
            '主诉': '📝',
            '证候': '🩺',
            '辨证': '🩺',
            '诊断': '🩺',
            '病机': '🧬',
            '机理': '🧬',
            '治法': '⚕️',
            '治疗': '⚕️',
            '方药': '💊',
            '用药': '💊',
            '建议': '💡',
            '医嘱': '💡',
            '需要': '💡',
            '注意': '⚠️',
            '禁忌': '⚠️'
        };

        for (const [key, icon] of Object.entries(diagnosisIconMap)) {
            if (cleanTitle.includes(key)) {
                return `${icon} ${cleanTitle}`;
            }
        }

        return `📋 ${cleanTitle}`;
    }

    /**
     * 渲染诊断分析章节内容
     */
    renderDiagnosisSections(sections) {
        if (sections.length === 0) {
            return '';
        }

        const sectionsHtml = sections.map(section => `
            <div class="diagnosis-section">
                <h4 class="diagnosis-section-title">${section.title}</h4>
                <div class="diagnosis-section-content">
                    ${section.content}
                </div>
            </div>
        `).join('');

        return `
            <div class="diagnosis-analysis">
                ${sectionsHtml}
            </div>
        `;
    }
}

// 全局处方解锁函数
function unlockPrescription(prescriptionId) {
    console.log('🔓 开始处方解锁流程:', prescriptionId);
    
    // 🔑 增强的登录状态检查逻辑
    const isLoggedIn = checkUserLoginStatus();
    
    if (!isLoggedIn) {
        console.log('❌ 用户未登录，显示登录模态框');
        showCompatibleMessage('请先登录后解锁处方', 'error');
        if (typeof window.showLoginModal === 'function') {
            window.showLoginModal();
        } else if (typeof showLoginModal === 'function') {
            showLoginModal();
        } else {
            // 备用方案：跳转到登录页面
            window.location.href = '/login';
        }
        return;
    }

    console.log('✅ 用户已登录，继续处方解锁流程');

    // 如果是临时ID，先创建处方记录
    if (prescriptionId === 'temp') {
        createPrescriptionRecord();
    } else {
        // 直接进入支付流程
        initiatePrescriptionPayment(prescriptionId);
    }
}

/**
 * 检查用户登录状态 - 兼容多种登录状态存储方式
 */
function checkUserLoginStatus() {
    console.log('🔍 开始登录状态检查，当前环境:');
    console.log('  - window.currentUser:', window.currentUser);
    console.log('  - window.userToken:', window.userToken);
    
    // 方法1: 检查全局变量
    if (window.currentUser && window.userToken) {
        console.log('🔑 通过全局变量验证登录状态');
        return true;
    }

    // 方法2: 检查localStorage中的currentUser
    try {
        const currentUserStr = localStorage.getItem('currentUser');
        console.log('  - localStorage.currentUser:', currentUserStr);
        
        if (currentUserStr && currentUserStr !== 'null' && currentUserStr !== 'undefined') {
            const currentUser = JSON.parse(currentUserStr);
            console.log('  - 解析后的currentUser:', currentUser);
            
            if (currentUser && (currentUser.id || currentUser.user_id)) {
                console.log('🔑 通过localStorage currentUser验证登录状态:', currentUser);
                // 同步更新全局变量
                window.currentUser = currentUser;
                return true;
            }
        }
    } catch (error) {
        console.warn('currentUser数据解析失败:', error);
    }

    // 方法3: 检查userData
    try {
        const userData = localStorage.getItem('userData');
        console.log('  - localStorage.userData:', userData);
        
        if (userData && userData !== 'null' && userData !== 'undefined') {
            const user = JSON.parse(userData);
            console.log('  - 解析后的userData:', user);
            
            if (user && (user.id || user.user_id)) {
                console.log('🔑 通过localStorage userData验证登录状态:', user);
                // 同步更新全局变量
                window.currentUser = user;
                return true;
            }
        }
    } catch (error) {
        console.warn('userData数据解析失败:', error);
    }

    // 方法4: 检查各种token
    const tokens = [
        localStorage.getItem('userToken'),
        localStorage.getItem('patientToken'),
        localStorage.getItem('doctorToken'),
        localStorage.getItem('adminToken')
    ];
    
    console.log('  - 检查tokens:', tokens);
    
    const validToken = tokens.find(token => token && token !== 'null' && token !== 'undefined');
    if (validToken) {
        console.log('🔑 通过token验证登录状态:', validToken);
        window.userToken = validToken;
        // 即使只有token也认为是登录状态
        return true;
    }

    // 方法5: 检查页面特定的用户ID（智能问诊页面的临时用户）
    const smartUserId = localStorage.getItem('currentUserId');
    console.log('  - localStorage.currentUserId:', smartUserId);
    
    if (smartUserId && smartUserId !== 'null' && smartUserId !== 'undefined') {
        // 检查是否是真实用户ID还是临时访客ID
        if (smartUserId.startsWith('real_user_') || 
            (!smartUserId.startsWith('smart_user_') && !smartUserId.startsWith('temp_user_'))) {
            console.log('🔑 通过currentUserId验证登录状态（真实用户）:', smartUserId);
            return true;
        } else {
            console.log('⚠️ 检测到访客模式ID，不算登录状态:', smartUserId);
        }
    }

    console.log('❌ 所有登录状态检查都失败');
    console.log('📊 完整的localStorage内容:');
    Object.keys(localStorage).forEach(key => {
        if (key.includes('user') || key.includes('token') || key.includes('auth')) {
            console.log(`  ${key}:`, localStorage.getItem(key));
        }
    });
    
    return false;
}

/**
 * 获取兼容的认证头 - 兼容主页面的getAuthHeaders函数
 */
function getCompatibleAuthHeaders() {
    // 优先使用主页面的getAuthHeaders函数
    if (typeof window.getAuthHeaders === 'function') {
        return window.getAuthHeaders();
    } else if (typeof getAuthHeaders === 'function') {
        return getAuthHeaders();
    }
    
    // 备用方案：自己构建认证头
    const headers = {
        'Content-Type': 'application/json',
    };

    // 查找可用的token
    const tokens = [
        localStorage.getItem('userToken'),
        localStorage.getItem('patientToken'),
        localStorage.getItem('doctorToken'),
        localStorage.getItem('adminToken')
    ];
    
    const validToken = tokens.find(token => token && token !== 'null' && token !== 'undefined');
    if (validToken) {
        headers['Authorization'] = `Bearer ${validToken}`;
    }

    return headers;
}

/**
 * 兼容的消息显示函数
 */
function showCompatibleMessage(message, type = 'info') {
    // 优先使用主页面的showMessage函数
    if (typeof window.showMessage === 'function') {
        window.showMessage(message, type);
    } else if (typeof showMessage === 'function') {
        showMessage(message, type);
    } else {
        // 备用方案：使用alert
        console.log(`[${type.toUpperCase()}] ${message}`);
        if (type === 'error') {
            alert(`错误: ${message}`);
        } else if (type === 'warning') {
            alert(`警告: ${message}`);
        } else {
            alert(message);
        }
    }
}

// 创建处方记录
async function createPrescriptionRecord() {
    try {
        // 获取最后一条包含处方的AI消息
        const prescriptionContent = getPrescriptionContent();
        if (!prescriptionContent) {
            showCompatibleMessage('未找到处方内容', 'error');
            return;
        }

        const headers = getCompatibleAuthHeaders();
        
        // 获取当前用户ID作为patient_id
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        const patientId = currentUser.user_id || window.currentUser?.user_id || localStorage.getItem('currentUserId');
        
        if (!patientId) {
            showCompatibleMessage('用户信息缺失，无法创建处方记录', 'error');
            return;
        }
        
        // 🔍 获取对话ID的多种方式
        let conversationId = null;
        
        // 1. 尝试从 window 对象获取
        if (window.currentConversationId && window.currentConversationId !== 'undefined' && window.currentConversationId !== 'null') {
            conversationId = window.currentConversationId;
            console.log('🔧 从window获取到对话ID:', conversationId);
        }
        // 2. 尝试从全局作用域获取 (尝试访问页面级变量)
        else if (typeof currentConversationId !== 'undefined' && currentConversationId && currentConversationId !== 'null') {
            conversationId = currentConversationId;
            console.log('🔧 从全局变量获取到对话ID:', conversationId);
        }
        // 3. 尝试从父窗口获取 (iframe情况)
        else if (window.parent && window.parent.currentConversationId && window.parent.currentConversationId !== 'undefined') {
            conversationId = window.parent.currentConversationId;
            console.log('🔧 从父窗口获取到对话ID:', conversationId);
        }
        // 4. 尝试从localStorage获取
        else if (localStorage.getItem(`conversationId_${patientId}`)) {
            conversationId = localStorage.getItem(`conversationId_${patientId}`);
            console.log('🔧 从localStorage获取到对话ID:', conversationId);
        }
        // 5. 生成新的对话ID
        else {
            conversationId = this.generateConversationId();
            console.log('🔧 生成新的对话ID:', conversationId);
            // 保存到localStorage以便后续使用
            localStorage.setItem(`conversationId_${patientId}`, conversationId);
        }
        
        console.log('🔍 准备创建处方记录:', {
            patient_id: patientId,
            conversation_id: conversationId,
            prescription_length: prescriptionContent.length,
            source: window.currentConversationId ? 'window' : 'generated'
        });
        
        const response = await fetch('/api/prescription/create', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                patient_id: patientId,
                conversation_id: conversationId,
                ai_prescription: prescriptionContent,
                symptoms: getCurrentSymptoms()
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ API请求失败:', response.status, errorText);
            showCompatibleMessage(`创建处方记录失败: ${response.status} ${errorText}`, 'error');
            return;
        }
        
        const result = await response.json();
        console.log('✅ 处方创建API响应:', result);
        
        if (result.success && result.prescription_id) {
            console.log('✅ 处方记录创建成功, ID:', result.prescription_id);
            initiatePrescriptionPayment(result.prescription_id);
        } else {
            console.error('❌ 处方创建失败:', result);
            showCompatibleMessage('创建处方记录失败: ' + (result.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('创建处方记录失败:', error);
        showCompatibleMessage('创建处方记录失败', 'error');
    }
}

// 启动处方支付流程
function initiatePrescriptionPayment(prescriptionId) {
    console.log('💰 启动支付流程:', prescriptionId);
    
    // 🧪 沙盒测试模式：检查是否启用测试支付
    console.log('🔒 正式支付模式：启动真实支付流程');
    
    // 🔍 调试：检查支付函数是否存在
    console.log('🔍 检查支付函数:', {
        'window.showPaymentModal': typeof window.showPaymentModal,
        'showPaymentModal': typeof showPaymentModal
    });
    
    // 🔒 启动真实支付流程
    console.log('🔒 启动真实支付流程');
    useRealPayment(prescriptionId);
}

/**
 * 🧪 模拟支付成功 - 沙盒测试模式
 */
function simulatePaymentSuccess(prescriptionId) {
    console.log('🧪 开始模拟支付流程...');
    
    // 显示支付进度
    showCompatibleMessage('正在处理支付...', 'info');
    
    setTimeout(() => {
        showCompatibleMessage('支付成功！处方已解锁', 'success');
        
        // 模拟支付成功，更新处方状态
        handlePaymentSuccess(prescriptionId);
        
        // 刷新页面显示已支付状态
        setTimeout(() => {
            location.reload();
        }, 2000);
    }, 2000);
}

/**
 * 🧪 显示测试支付选项
 */
function showTestPaymentOptions(prescriptionId) {
    const testHtml = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; align-items: center; justify-content: center;" onclick="this.remove()">
            <div style="background: white; padding: 30px; border-radius: 15px; max-width: 400px; text-align: center;" onclick="event.stopPropagation()">
                <h3 style="color: #333; margin-bottom: 20px;">💳 支付方式选择</h3>
                <p style="color: #666; margin-bottom: 20px;">请选择支付方式</p>
                
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <button onclick="useRealPayment('${prescriptionId}'); this.closest('div').remove();" 
                            style="background: #3b82f6; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-size: 14px;">
                        💳 确认处方并支付
                    </button>
                    
                    <button onclick="this.closest('div').remove();" 
                            style="background: #6b7280; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        取消
                    </button>
                </div>
                
                <p style="font-size: 11px; color: #9ca3af; margin-top: 15px;">
                    测试模式可以模拟支付成功，查看完整处方效果
                </p>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', testHtml);
}

/**
 * 🔒 处理真实支付流程
 */
function processRealPayment() {
    console.log('🔒 启动真实支付流程');
    showCompatibleMessage('正在启动支付流程...', 'info');
}

/**
 * 💰 使用真实支付系统
 */
function useRealPayment(prescriptionId) {
    console.log('💰 使用真实支付系统:', prescriptionId);
    
    // 调用现有的支付模态框
    if (typeof window.showPaymentModal === 'function') {
        console.log('📞 调用真实支付 window.showPaymentModal');
        window.showPaymentModal(prescriptionId, 88.00);
    } else if (typeof showPaymentModal === 'function') {
        console.log('📞 调用真实支付 showPaymentModal');
        showPaymentModal(prescriptionId, 88.00);
    } else {
        console.warn('⚠️ 真实支付系统不可用');
        showCompatibleMessage('支付系统暂时不可用，请稍后再试', 'warning');
    }
}

// 🔍 将函数绑定到全局作用域，确保HTML中的onclick能访问到
window.enableSandboxMode = enableSandboxMode;
window.simulatePaymentSuccess = simulatePaymentSuccess;
window.useRealPayment = useRealPayment;

/**
 * 处理支付成功后的逻辑
 */
function handlePaymentSuccess(prescriptionId) {
    console.log('✅ 支付成功，处方ID:', prescriptionId);

    // 更新本地存储的支付状态
    const userId = getCurrentUserId();
    const paymentKey = `prescription_paid_${prescriptionId}`;

    console.log('💾 保存支付状态:', {
        prescriptionId,
        userId,
        paymentKey
    });
    
    localStorage.setItem(paymentKey, 'true');
    
    // 验证保存结果
    const savedStatus = localStorage.getItem(paymentKey);
    console.log('💾 支付状态保存结果:', savedStatus);
    
    if (savedStatus === 'true') {
        console.log('✅ 支付状态保存成功');
    } else {
        console.error('❌ 支付状态保存失败');
    }
}

// 获取处方内容
function getPrescriptionContent() {
    console.log('🔍 开始获取处方内容...');
    
    // 方法1: 尝试从最近的对话历史中获取原始内容
    if (window.currentConversationId) {
        const conversationKey = `conversation_${window.selectedDoctor}_${window.currentConversationId}`;
        const conversationData = localStorage.getItem(conversationKey);
        if (conversationData) {
            try {
                const history = JSON.parse(conversationData);
                // 从最后的AI消息中查找处方
                for (let i = history.length - 1; i >= 0; i--) {
                    const message = history[i];
                    if (message.type === 'ai' && message.content) {
                        const renderer = new PrescriptionRenderer();
                        if (renderer.containsPrescription(message.content) && !renderer.isTemporaryAdvice(message.content)) {
                            console.log('✅ 从对话历史获取到处方内容，长度:', message.content.length);
                            return message.content;
                        }
                    }
                }
            } catch (e) {
                console.warn('解析对话历史失败:', e);
            }
        }
    }
    
    // 方法2: 备用方案，从DOM获取
    const messages = document.querySelectorAll('.message.ai .message-text');
    for (let i = messages.length - 1; i >= 0; i--) {
        const content = messages[i].textContent;
        const renderer = new PrescriptionRenderer();
        if (renderer.containsPrescription(content) && !renderer.isTemporaryAdvice(content)) {
            console.log('✅ 从DOM获取到处方内容，长度:', content.length);
            return content;
        }
    }
    
    console.warn('❌ 未找到有效的处方内容');
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
    showCompatibleMessage('处方下载功能开发中', 'info');
}

// 显示代煎服务信息
function showDecorationInfo(prescriptionId) {
    console.log('🍵 显示代煎服务信息:', prescriptionId);
    showCompatibleMessage('代煎服务功能开发中', 'info');
}

// 创建全局实例
window.prescriptionRenderer = new PrescriptionRenderer();

// 🔑 修复：将关键函数绑定到全局作用域
window.getPrescriptionContent = getPrescriptionContent;
window.getCurrentSymptoms = getCurrentSymptoms;
window.unlockPrescription = unlockPrescription;
window.downloadPrescription = downloadPrescription;
window.showDecorationInfo = showDecorationInfo;

console.log('✅ 处方渲染器已加载 - 版本 v2.6.4 (修复API数据格式+改进内容获取)');
