// 中医AI智能问诊系统 - 医生思维录入界面脚本

// 全局变量
let currentStep = 1;
let thinkingSteps = [];
let stepCounter = 0;

// API配置
const API_BASE_URL = window.location.origin;

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    console.log('医生思维录入界面初始化...');
    initializeForm();
    bindEvents();
});

// 初始化表单
function initializeForm() {
    // 疾病类型选择事件
    const diseaseSelect = document.getElementById('diseaseCategory');
    const otherGroup = document.getElementById('otherDiseaseGroup');
    
    diseaseSelect.addEventListener('change', function() {
        if (this.value === '其他') {
            otherGroup.style.display = 'block';
            document.getElementById('otherDisease').required = true;
        } else {
            otherGroup.style.display = 'none';
            document.getElementById('otherDisease').required = false;
        }
    });
}

// 绑定事件
function bindEvents() {
    // 表单验证事件
    const inputs = document.querySelectorAll('input[required], select[required]');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearError);
    });
}

// 步骤导航
function nextStep() {
    if (validateCurrentStep()) {
        if (currentStep < 4) {
            currentStep++;
            updateStepDisplay();
        }
    }
}

function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateStepDisplay();
    }
}

function updateStepDisplay() {
    // 更新进度条
    document.querySelectorAll('.step').forEach((step, index) => {
        const stepNum = index + 1;
        step.classList.remove('active', 'completed');
        
        if (stepNum === currentStep) {
            step.classList.add('active');
        } else if (stepNum < currentStep) {
            step.classList.add('completed');
        }
    });
    
    // 更新表单区域
    document.querySelectorAll('.form-section').forEach((section, index) => {
        section.classList.remove('active');
        if (index + 1 === currentStep) {
            section.classList.add('active');
        }
    });
    
    // 更新导航按钮
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    prevBtn.style.display = currentStep > 1 ? 'block' : 'none';
    
    if (currentStep === 4) {
        nextBtn.style.display = 'none';
        updatePreview();
    } else {
        nextBtn.style.display = 'block';
        nextBtn.textContent = currentStep === 3 ? '预览确认 👁️' : '下一步 ➡️';
    }
}

// 表单验证
function validateCurrentStep() {
    let isValid = true;
    const currentSection = document.querySelector(`#step${currentStep}`);
    const requiredFields = currentSection.querySelectorAll('input[required], select[required]');
    
    requiredFields.forEach(field => {
        if (!validateField({ target: field })) {
            isValid = false;
        }
    });
    
    // 步骤3特殊验证
    if (currentStep === 3 && thinkingSteps.length === 0) {
        showMessage('请至少添加一个思维步骤', 'error');
        isValid = false;
    }
    
    return isValid;
}

function validateField(event) {
    const field = event.target;
    const formGroup = field.closest('.form-group');
    const errorMsg = formGroup.querySelector('.error-message');
    
    // 清除之前的错误状态
    formGroup.classList.remove('error');
    if (errorMsg) errorMsg.remove();
    
    let isValid = true;
    let message = '';
    
    // 必填字段验证
    if (field.required && !field.value.trim()) {
        isValid = false;
        message = '此字段为必填项';
    }
    
    // 特殊字段验证
    if (field.id === 'doctorId' && field.value) {
        if (!/^[a-zA-Z0-9_]+$/.test(field.value)) {
            isValid = false;
            message = '医生ID只能包含字母、数字和下划线';
        }
    }
    
    // 显示错误
    if (!isValid) {
        formGroup.classList.add('error');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        formGroup.appendChild(errorDiv);
    }
    
    return isValid;
}

function clearError(event) {
    const field = event.target;
    const formGroup = field.closest('.form-group');
    formGroup.classList.remove('error');
    const errorMsg = formGroup.querySelector('.error-message');
    if (errorMsg) errorMsg.remove();
}

// 添加思维步骤
function addThinkingStep() {
    const stepData = {
        id: ++stepCounter,
        type: 'analysis',
        name: `思维步骤 ${stepCounter}`,
        description: '',
        conditions: [],
        actions: []
    };
    
    thinkingSteps.push(stepData);
    renderThinkingStep(stepData);
}

function addTemplateStep(type) {
    const templates = {
        symptom: {
            type: 'symptom_analysis',
            name: '症状评估',
            description: '评估患者主要症状表现',
            conditions: [
                { attribute: '主要症状', operator: 'has', value: 'True', weight: 1.0 }
            ],
            actions: [
                {
                    type: 'record_symptom',
                    content: { symptom_group: '主要症状', importance: 'high' },
                    confidence: 0.9,
                    reasoning: '症状记录和分析'
                }
            ]
        },
        syndrome: {
            type: 'syndrome_analysis',
            name: '证候分析',
            description: '根据症状进行中医辨证',
            conditions: [
                { attribute: '证候特征', operator: 'has', value: 'True', weight: 1.5 }
            ],
            actions: [
                {
                    type: 'analyze_syndrome',
                    content: { syndrome: '具体证型', characteristics: '证候特征描述' },
                    confidence: 0.85,
                    reasoning: '中医辨证分析'
                }
            ]
        },
        formula: {
            type: 'formula_selection',
            name: '方剂选择',
            description: '根据证型选择合适方剂',
            conditions: [
                { attribute: '证型', operator: 'has', value: '具体证型', weight: 2.0 }
            ],
            actions: [
                {
                    type: 'select_formula',
                    content: { 
                        formula_name: '方剂名称',
                        main_herbs: {},
                        formula_function: '方剂功效'
                    },
                    confidence: 0.9,
                    reasoning: '经典方剂选择'
                }
            ]
        },
        dosage: {
            type: 'dosage_adjustment',
            name: '剂量调整',
            description: '根据患者情况调整用药剂量',
            conditions: [
                { attribute: '患者特征', operator: 'has', value: 'True', weight: 1.0 }
            ],
            actions: [
                {
                    type: 'adjust_dosage',
                    content: { adjustments: '剂量调整说明' },
                    confidence: 0.8,
                    reasoning: '个体化用药调整'
                }
            ]
        }
    };
    
    const template = templates[type];
    if (template) {
        const stepData = {
            id: ++stepCounter,
            ...template
        };
        
        thinkingSteps.push(stepData);
        renderThinkingStep(stepData);
    }
}

function renderThinkingStep(stepData) {
    const container = document.getElementById('thinkingStepsList');
    const stepCard = document.createElement('div');
    stepCard.className = 'thinking-step-card';
    stepCard.dataset.stepId = stepData.id;
    
    stepCard.innerHTML = `
        <div class="thinking-step-header">
            <div>
                <span class="step-type-badge ${stepData.type.split('_')[0]}">${getStepTypeName(stepData.type)}</span>
                <strong style="margin-left: 10px;">${stepData.name}</strong>
            </div>
            <div class="step-actions">
                <button type="button" class="btn btn-small btn-secondary" onclick="editStep(${stepData.id})">编辑</button>
                <button type="button" class="btn btn-small" style="background: #dc3545; color: white;" onclick="removeStep(${stepData.id})">删除</button>
            </div>
        </div>
        
        <div class="form-group">
            <label>步骤描述</label>
            <input type="text" value="${stepData.description}" onchange="updateStepData(${stepData.id}, 'description', this.value)" placeholder="请描述这个思维步骤...">
        </div>
        
        <div class="conditions-section">
            <h5>诊断条件 <button type="button" class="btn btn-small btn-template" onclick="addCondition(${stepData.id})">添加条件</button></h5>
            <div class="conditions-list" id="conditions-${stepData.id}">
                ${renderConditions(stepData.conditions, stepData.id)}
            </div>
        </div>
        
        <div class="actions-section">
            <h5>诊疗行动 <button type="button" class="btn btn-small btn-template" onclick="addAction(${stepData.id})">添加行动</button></h5>
            <div class="actions-list" id="actions-${stepData.id}">
                ${renderActions(stepData.actions, stepData.id)}
            </div>
        </div>
    `;
    
    container.appendChild(stepCard);
}

function renderConditions(conditions, stepId) {
    return conditions.map((condition, index) => `
        <div class="condition-item">
            <button class="remove-btn" onclick="removeCondition(${stepId}, ${index})">×</button>
            <div style="display: grid; grid-template-columns: 1fr 120px 1fr 100px; gap: 10px; align-items: center;">
                <input type="text" placeholder="症状/特征" value="${condition.attribute}" 
                       onchange="updateConditionData(${stepId}, ${index}, 'attribute', this.value)">
                <select onchange="updateConditionData(${stepId}, ${index}, 'operator', this.value)">
                    <option value="has" ${condition.operator === 'has' ? 'selected' : ''}>具有</option>
                    <option value="not_has" ${condition.operator === 'not_has' ? 'selected' : ''}>不具有</option>
                    <option value="severity" ${condition.operator === 'severity' ? 'selected' : ''}>严重程度</option>
                </select>
                <input type="text" placeholder="期望值" value="${condition.value}" 
                       onchange="updateConditionData(${stepId}, ${index}, 'value', this.value)">
                <input type="number" placeholder="权重" step="0.1" min="0.1" max="3.0" value="${condition.weight}" 
                       onchange="updateConditionData(${stepId}, ${index}, 'weight', parseFloat(this.value))">
            </div>
        </div>
    `).join('');
}

function renderActions(actions, stepId) {
    return actions.map((action, index) => `
        <div class="action-item">
            <button class="remove-btn" onclick="removeAction(${stepId}, ${index})">×</button>
            <div style="margin-bottom: 10px;">
                <label style="display: inline-block; width: 80px;">行动类型:</label>
                <select style="width: 200px;" onchange="updateActionData(${stepId}, ${index}, 'type', this.value)">
                    <option value="record_symptom" ${action.type === 'record_symptom' ? 'selected' : ''}>记录症状</option>
                    <option value="analyze_syndrome" ${action.type === 'analyze_syndrome' ? 'selected' : ''}>分析证候</option>
                    <option value="select_formula" ${action.type === 'select_formula' ? 'selected' : ''}>选择方剂</option>
                    <option value="adjust_dosage" ${action.type === 'adjust_dosage' ? 'selected' : ''}>调整剂量</option>
                    <option value="give_advice" ${action.type === 'give_advice' ? 'selected' : ''}>给出建议</option>
                </select>
                <label style="display: inline-block; width: 60px; margin-left: 20px;">信心度:</label>
                <input type="number" step="0.01" min="0.1" max="1.0" value="${action.confidence}" style="width: 80px;"
                       onchange="updateActionData(${stepId}, ${index}, 'confidence', parseFloat(this.value))">
            </div>
            <div style="margin-bottom: 10px;">
                <label>内容 (JSON格式):</label>
                <textarea rows="2" placeholder='{"key": "value"}' 
                          onchange="updateActionContent(${stepId}, ${index}, this.value)">${JSON.stringify(action.content, null, 2)}</textarea>
            </div>
            <div>
                <label>推理过程:</label>
                <input type="text" placeholder="请描述推理逻辑..." value="${action.reasoning}" 
                       onchange="updateActionData(${stepId}, ${index}, 'reasoning', this.value)">
            </div>
        </div>
    `).join('');
}

// 工具函数
function getStepTypeName(type) {
    const typeNames = {
        'symptom_analysis': '症状',
        'syndrome_analysis': '证候',
        'formula_selection': '方剂',
        'dosage_adjustment': '剂量',
        'analysis': '分析'
    };
    return typeNames[type] || '分析';
}

function updateStepData(stepId, field, value) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (step) {
        step[field] = value;
    }
}

function addCondition(stepId) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (step) {
        step.conditions.push({
            attribute: '',
            operator: 'has',
            value: '',
            weight: 1.0
        });
        
        const container = document.getElementById(`conditions-${stepId}`);
        container.innerHTML = renderConditions(step.conditions, stepId);
    }
}

function addAction(stepId) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (step) {
        step.actions.push({
            type: 'record_symptom',
            content: {},
            confidence: 0.8,
            reasoning: ''
        });
        
        const container = document.getElementById(`actions-${stepId}`);
        container.innerHTML = renderActions(step.actions, stepId);
    }
}

function removeStep(stepId) {
    if (confirm('确定要删除这个思维步骤吗？')) {
        thinkingSteps = thinkingSteps.filter(s => s.id !== stepId);
        const stepCard = document.querySelector(`[data-step-id="${stepId}"]`);
        if (stepCard) {
            stepCard.remove();
        }
    }
}

function removeCondition(stepId, conditionIndex) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (step) {
        step.conditions.splice(conditionIndex, 1);
        const container = document.getElementById(`conditions-${stepId}`);
        container.innerHTML = renderConditions(step.conditions, stepId);
    }
}

function removeAction(stepId, actionIndex) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (step) {
        step.actions.splice(actionIndex, 1);
        const container = document.getElementById(`actions-${stepId}`);
        container.innerHTML = renderActions(step.actions, stepId);
    }
}

function updateConditionData(stepId, conditionIndex, field, value) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (step && step.conditions[conditionIndex]) {
        step.conditions[conditionIndex][field] = value;
    }
}

function updateActionData(stepId, actionIndex, field, value) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (step && step.actions[actionIndex]) {
        step.actions[actionIndex][field] = value;
    }
}

function updateActionContent(stepId, actionIndex, jsonString) {
    try {
        const content = JSON.parse(jsonString);
        const step = thinkingSteps.find(s => s.id === stepId);
        if (step && step.actions[actionIndex]) {
            step.actions[actionIndex].content = content;
        }
    } catch (e) {
        showMessage('JSON格式错误，请检查内容格式', 'error');
    }
}

// 预览功能
function updatePreview() {
    // 医生信息预览
    const doctorInfo = {
        name: document.getElementById('doctorName').value,
        id: document.getElementById('doctorId').value,
        specialty: document.getElementById('specialtyArea').value,
        experience: document.getElementById('experience').value
    };
    
    document.getElementById('doctorInfoPreview').innerHTML = `
        <p><strong>医生姓名:</strong> ${doctorInfo.name}</p>
        <p><strong>医生ID:</strong> ${doctorInfo.id}</p>
        <p><strong>专业领域:</strong> ${doctorInfo.specialty}</p>
        <p><strong>从业经验:</strong> ${doctorInfo.experience}</p>
    `;
    
    // 专科信息预览
    const diseaseCategory = document.getElementById('diseaseCategory').value;
    const otherDisease = document.getElementById('otherDisease').value;
    const finalDisease = diseaseCategory === '其他' ? otherDisease : diseaseCategory;
    
    const diseaseInfo = {
        category: finalDisease,
        accuracy: document.getElementById('patternAccuracy').value,
        description: document.getElementById('diseaseDescription').value
    };
    
    document.getElementById('diseaseInfoPreview').innerHTML = `
        <p><strong>擅长疾病:</strong> ${diseaseInfo.category}</p>
        <p><strong>诊疗准确率:</strong> ${(parseFloat(diseaseInfo.accuracy) * 100).toFixed(0)}%</p>
        <p><strong>疾病描述:</strong> ${diseaseInfo.description || '无'}</p>
    `;
    
    // 思维步骤预览
    const stepsHtml = thinkingSteps.map((step, index) => `
        <div style="margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #667eea;">
            <h5>步骤 ${index + 1}: ${step.name}</h5>
            <p><strong>类型:</strong> ${getStepTypeName(step.type)}</p>
            <p><strong>描述:</strong> ${step.description}</p>
            <p><strong>条件数量:</strong> ${step.conditions.length} 个</p>
            <p><strong>行动数量:</strong> ${step.actions.length} 个</p>
        </div>
    `).join('');
    
    document.getElementById('thinkingStepsPreview').innerHTML = stepsHtml || '<p style="color: #666;">暂无思维步骤</p>';
}

// 数据导出
function downloadData() {
    const data = collectFormData();
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `${data.doctor_name}_thinking_pattern_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    showMessage('思维模式数据已下载到本地', 'success');
}

// 收集表单数据
function collectFormData() {
    const diseaseCategory = document.getElementById('diseaseCategory').value;
    const otherDisease = document.getElementById('otherDisease').value;
    const finalDisease = diseaseCategory === '其他' ? otherDisease : diseaseCategory;
    
    return {
        doctor_id: document.getElementById('doctorId').value,
        doctor_name: document.getElementById('doctorName').value,
        disease_category: finalDisease,
        specialty_area: document.getElementById('specialtyArea').value,
        pattern_accuracy: parseFloat(document.getElementById('patternAccuracy').value),
        case_count: 0,
        decision_logic: thinkingSteps.map(step => ({
            type: step.type,
            name: step.name,
            description: step.description,
            conditions: step.conditions.filter(c => c.attribute.trim()),
            actions: step.actions.filter(a => a.reasoning.trim())
        }))
    };
}

// 提交到系统
async function submitThinkingPattern() {
    const submitBtn = event.target;
    const originalText = submitBtn.innerHTML;
    
    try {
        submitBtn.innerHTML = '<span class="loading"></span>提交中...';
        submitBtn.disabled = true;
        
        const data = collectFormData();
        
        // 验证数据
        if (!data.doctor_id || !data.doctor_name || !data.disease_category) {
            throw new Error('请完善基本信息');
        }
        
        if (data.decision_logic.length === 0) {
            throw new Error('请至少添加一个思维步骤');
        }
        
        // 发送到API
        const response = await axios.post(`${API_BASE_URL}/import_thinking_pattern`, data, {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 30000
        });
        
        if (response.data.success) {
            showMessage('思维模式提交成功！系统已开始学习您的诊疗思维。', 'success');
            
            // 3秒后刷新页面
            setTimeout(() => {
                if (confirm('提交成功！是否重新开始录入新的思维模式？')) {
                    location.reload();
                }
            }, 3000);
        } else {
            throw new Error(response.data.message || '提交失败');
        }
        
    } catch (error) {
        console.error('提交错误:', error);
        let errorMessage = '提交失败：';
        
        if (error.response) {
            errorMessage += error.response.data.message || error.response.statusText;
        } else if (error.request) {
            errorMessage += '无法连接到服务器，请检查网络连接';
        } else {
            errorMessage += error.message;
        }
        
        showMessage(errorMessage, 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// 消息提示
function showMessage(text, type = 'success') {
    const messageBox = document.getElementById('messageBox');
    const messageContent = messageBox.querySelector('.message-content');
    const messageText = messageBox.querySelector('.message-text');
    
    messageText.textContent = text;
    messageContent.className = `message-content ${type}`;
    messageBox.style.display = 'block';
    
    // 自动隐藏成功消息
    if (type === 'success') {
        setTimeout(hideMessage, 5000);
    }
}

function hideMessage() {
    document.getElementById('messageBox').style.display = 'none';
}

// 编辑步骤（简化版）
function editStep(stepId) {
    const step = thinkingSteps.find(s => s.id === stepId);
    if (!step) return;
    
    const newName = prompt('请输入步骤名称:', step.name);
    if (newName && newName.trim()) {
        step.name = newName.trim();
        // 重新渲染步骤
        const stepCard = document.querySelector(`[data-step-id="${stepId}"]`);
        stepCard.remove();
        renderThinkingStep(step);
    }
}