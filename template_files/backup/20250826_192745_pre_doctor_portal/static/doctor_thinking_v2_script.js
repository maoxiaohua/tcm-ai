// 中医AI智能问诊系统 - 医生经验录入界面脚本 V2 (简化版)

// 全局变量
let currentStep = 1;
let clinicalSteps = [];
let stepCounter = 0;

// API配置
const API_BASE_URL = window.location.origin;

// 临床步骤模板 - 贴近实际医生思维
const clinicalTemplates = {
    initial_assessment: {
        type: 'initial_assessment',
        name: '初步评估',
        icon: '🔍',
        description: '根据患者主诉，初步判断可能的病症方向',
        example: '患者诉"头痛3天"，考虑外感风寒、肝阳上亢、血瘀阻络等可能',
        prompts: {
            symptoms: '当患者出现哪些症状时，您会考虑这个诊断方向？',
            reasoning: '您的判断依据是什么？',
            next_steps: '接下来您会重点询问哪些问题？'
        }
    },
    four_diagnosis: {
        type: 'four_diagnosis',
        name: '四诊合参',
        icon: '👁️',
        description: '望、闻、问、切四诊收集关键信息',
        example: '望：面色萎黄，舌淡苔白；问：食少便溏；切：脉缓弱',
        prompts: {
            observation: '您在望诊时重点观察什么？',
            inquiry: '您会重点询问哪些症状？',
            examination: '您在切诊时关注什么特点？'
        }
    },
    syndrome_differentiation: {
        type: 'syndrome_differentiation', 
        name: '辨证论治',
        icon: '🎯',
        description: '根据四诊信息，确定证候和治法',
        example: '证候：脾胃虚弱；治法：健脾益气，和胃止泻',
        prompts: {
            syndrome: '基于以上信息，您如何辨证？',
            principle: '治疗大法是什么？',
            contraindications: '有哪些需要注意的禁忌？'
        }
    },
    prescription: {
        type: 'prescription',
        name: '处方配伍',
        icon: '💊',
        description: '选择方剂、加减化裁、剂量调整',
        example: '基方：参苓白术散；加减：腹痛加白芍、甘草；剂量：党参15g',
        prompts: {
            base_formula: '您常用的基础方剂是什么？',
            modifications: '根据具体症状如何加减？',
            dosage: '剂量调整的原则是什么？'
        }
    },
    follow_up: {
        type: 'follow_up',
        name: '调理随访',
        icon: '📋',
        description: '用药指导、饮食调理、复诊安排',
        example: '服药7天后复诊；忌生冷油腻；配合太极拳运动',
        prompts: {
            instructions: '您给患者哪些用药指导？',
            lifestyle: '有什么生活调理建议？',
            follow_up: '复诊时间和观察要点？'
        }
    }
};

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    console.log('医生经验录入界面初始化...');
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
        if (!field.value.trim()) {
            showFieldError(field, '此字段为必填项');
            isValid = false;
        }
    });
    
    // 步骤3特殊验证
    if (currentStep === 3 && clinicalSteps.length === 0) {
        showMessage('请至少添加一个诊疗步骤', 'error');
        isValid = false;
    }
    
    return isValid;
}

function validateField(event) {
    const field = event.target;
    if (field.required && !field.value.trim()) {
        showFieldError(field, '此字段为必填项');
    } else {
        clearFieldError(field);
    }
}

function showFieldError(field, message) {
    clearFieldError(field);
    const formGroup = field.closest('.form-group');
    formGroup.classList.add('error');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    formGroup.appendChild(errorDiv);
}

function clearFieldError(field) {
    const formGroup = field.closest('.form-group');
    formGroup.classList.remove('error');
    const errorMsg = formGroup.querySelector('.error-message');
    if (errorMsg) errorMsg.remove();
}

function clearError(event) {
    clearFieldError(event.target);
}

// 添加临床步骤
function addClinicalStep(templateType) {
    if (!clinicalTemplates[templateType]) return;
    
    const template = clinicalTemplates[templateType];
    const stepData = {
        id: ++stepCounter,
        type: template.type,
        name: template.name,
        icon: template.icon,
        description: template.description,
        example: template.example,
        responses: {},
        completed: false
    };
    
    clinicalSteps.push(stepData);
    renderClinicalStep(stepData, template);
}

function addCustomClinicalStep() {
    const stepName = prompt('请输入步骤名称:', '自定义步骤');
    if (!stepName || !stepName.trim()) return;
    
    const stepData = {
        id: ++stepCounter,
        type: 'custom',
        name: stepName.trim(),
        icon: '📝',
        description: '',
        responses: {},
        completed: false
    };
    
    clinicalSteps.push(stepData);
    renderCustomStep(stepData);
}

function renderClinicalStep(stepData, template) {
    const container = document.getElementById('clinicalStepsList');
    const stepCard = document.createElement('div');
    stepCard.className = 'medical-step-card';
    stepCard.dataset.stepId = stepData.id;
    
    const promptsHtml = Object.entries(template.prompts).map(([key, prompt]) => `
        <div class="form-group">
            <label for="response_${stepData.id}_${key}">${prompt}</label>
            <textarea id="response_${stepData.id}_${key}" 
                      class="medical-textarea"
                      placeholder="请详细描述您的经验和做法..."
                      onchange="updateStepResponse(${stepData.id}, '${key}', this.value)"></textarea>
        </div>
    `).join('');
    
    stepCard.innerHTML = `
        <div class="step-type-header">
            <div>
                <span class="step-icon">${stepData.icon}</span>
                <span>${stepData.name}</span>
            </div>
            <button type="button" class="btn btn-danger btn-small" onclick="removeStep(${stepData.id})">
                🗑️ 删除
            </button>
        </div>
        
        <div class="step-content">
            <div class="clinical-example">
                <h5>💡 临床示例</h5>
                <p>${template.example}</p>
            </div>
            
            ${promptsHtml}
        </div>
    `;
    
    container.appendChild(stepCard);
}

function renderCustomStep(stepData) {
    const container = document.getElementById('clinicalStepsList');
    const stepCard = document.createElement('div');
    stepCard.className = 'medical-step-card';
    stepCard.dataset.stepId = stepData.id;
    
    stepCard.innerHTML = `
        <div class="step-type-header">
            <div>
                <span class="step-icon">${stepData.icon}</span>
                <input type="text" value="${stepData.name}" 
                       onchange="updateStepName(${stepData.id}, this.value)"
                       style="background: transparent; border: none; color: white; font-weight: bold;">
            </div>
            <button type="button" class="btn btn-danger btn-small" onclick="removeStep(${stepData.id})">
                🗑️ 删除
            </button>
        </div>
        
        <div class="step-content">
            <div class="form-group">
                <label for="custom_description_${stepData.id}">步骤描述</label>
                <textarea id="custom_description_${stepData.id}" 
                          class="medical-textarea"
                          placeholder="请描述这个步骤的具体内容和您的经验..."
                          onchange="updateStepDescription(${stepData.id}, this.value)"></textarea>
            </div>
            
            <div class="form-group">
                <label for="custom_details_${stepData.id}">详细经验</label>
                <textarea id="custom_details_${stepData.id}" 
                          class="medical-textarea"
                          placeholder="请详细描述您在这个步骤中的具体做法、注意事项等..."
                          onchange="updateStepDetails(${stepData.id}, this.value)"></textarea>
            </div>
        </div>
    `;
    
    container.appendChild(stepCard);
}

// 更新步骤数据
function updateStepResponse(stepId, responseKey, value) {
    const step = clinicalSteps.find(s => s.id === stepId);
    if (step) {
        step.responses[responseKey] = value;
    }
}

function updateStepName(stepId, name) {
    const step = clinicalSteps.find(s => s.id === stepId);
    if (step) {
        step.name = name;
    }
}

function updateStepDescription(stepId, description) {
    const step = clinicalSteps.find(s => s.id === stepId);
    if (step) {
        step.description = description;
    }
}

function updateStepDetails(stepId, details) {
    const step = clinicalSteps.find(s => s.id === stepId);
    if (step) {
        step.responses.details = details;
    }
}

function removeStep(stepId) {
    if (confirm('确定要删除这个诊疗步骤吗？')) {
        clinicalSteps = clinicalSteps.filter(s => s.id !== stepId);
        const stepCard = document.querySelector(`[data-step-id="${stepId}"]`);
        if (stepCard) {
            stepCard.remove();
        }
    }
}

// 预览更新
function updatePreview() {
    // 医生信息预览
    const doctorInfo = {
        id: document.getElementById('doctorId').value,
        name: document.getElementById('doctorName').value,
        specialty: document.getElementById('specialtyArea').value,
        experience: document.getElementById('clinicalYears').value
    };
    
    document.getElementById('doctorInfoPreview').innerHTML = `
        <p><strong>医生编号:</strong> ${doctorInfo.id}</p>
        <p><strong>医生姓名:</strong> ${doctorInfo.name}</p>
        <p><strong>专业领域:</strong> ${doctorInfo.specialty}</p>
        <p><strong>临床经验:</strong> ${doctorInfo.experience}</p>
    `;
    
    // 疾病信息预览
    const diseaseCategory = document.getElementById('diseaseCategory').value;
    const finalDisease = diseaseCategory === '其他' 
        ? document.getElementById('otherDisease').value 
        : diseaseCategory;
    
    const diseaseInfo = {
        category: finalDisease,
        accuracy: document.getElementById('patternAccuracy').value,
        description: document.getElementById('diseaseDescription').value
    };
    
    document.getElementById('diseaseInfoPreview').innerHTML = `
        <p><strong>擅长疾病:</strong> ${diseaseInfo.category}</p>
        <p><strong>临床疗效:</strong> ${(parseFloat(diseaseInfo.accuracy) * 100).toFixed(0)}%</p>
        <p><strong>特点描述:</strong> ${diseaseInfo.description || '无'}</p>
    `;
    
    // 临床步骤预览
    const stepsHtml = clinicalSteps.map((step, index) => {
        const responseCount = Object.keys(step.responses).filter(key => step.responses[key]?.trim()).length;
        return `
            <div style="margin-bottom: 15px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #4fc3f7;">
                <h5>${step.icon} 步骤 ${index + 1}: ${step.name}</h5>
                <p><strong>类型:</strong> ${getStepTypeName(step.type)}</p>
                <p><strong>已填写内容:</strong> ${responseCount} 项</p>
                ${step.description ? `<p><strong>描述:</strong> ${step.description}</p>` : ''}
            </div>
        `;
    }).join('');
    
    document.getElementById('clinicalStepsPreview').innerHTML = stepsHtml || '<p style="color: #666;">暂无诊疗步骤</p>';
}

function getStepTypeName(type) {
    const typeNames = {
        'initial_assessment': '初步评估',
        'four_diagnosis': '四诊合参', 
        'syndrome_differentiation': '辨证论治',
        'prescription': '处方配伍',
        'follow_up': '调理随访',
        'custom': '自定义步骤'
    };
    return typeNames[type] || '其他';
}

// 数据收集和提交
function collectFormData() {
    const diseaseCategory = document.getElementById('diseaseCategory').value;
    const finalDisease = diseaseCategory === '其他' 
        ? document.getElementById('otherDisease').value 
        : diseaseCategory;
    
    return {
        doctor_id: document.getElementById('doctorId').value,
        doctor_name: document.getElementById('doctorName').value,
        disease_category: finalDisease,
        specialty_area: document.getElementById('specialtyArea').value,
        clinical_experience: document.getElementById('clinicalYears').value,
        pattern_accuracy: parseFloat(document.getElementById('patternAccuracy').value),
        disease_description: document.getElementById('diseaseDescription').value,
        case_count: 0,
        decision_logic: clinicalSteps.map(step => ({
            step_order: clinicalSteps.indexOf(step) + 1,
            step_type: step.type,
            step_name: step.name,
            step_description: step.description,
            clinical_experience: step.responses,
            confidence: 0.9
        }))
    };
}

async function submitClinicalExperience() {
    try {
        const data = collectFormData();
        
        // 基本验证
        if (!data.doctor_id || !data.doctor_name || !data.disease_category) {
            throw new Error('请完善基本信息');
        }
        
        if (data.decision_logic.length === 0) {
            throw new Error('请至少添加一个诊疗步骤');
        }
        
        showMessage('正在提交到AI系统...', 'info');
        
        // 发送到API
        const response = await axios.post(`${API_BASE_URL}/import_thinking_pattern`, data, {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 30000
        });
        
        if (response.data.success) {
            showMessage('✅ 诊疗经验提交成功！AI系统已学习您的经验。', 'success');
            setTimeout(() => {
                if (confirm('是否返回医生门户？')) {
                    window.location.href = '/static/doctor_portal.html';
                }
            }, 2000);
        } else {
            throw new Error(response.data.message || '提交失败');
        }
        
    } catch (error) {
        console.error('Error submitting clinical experience:', error);
        showMessage(`提交失败: ${error.message}`, 'error');
    }
}

function downloadExperience() {
    const data = collectFormData();
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `中医诊疗经验_${data.doctor_name}_${data.disease_category}.json`;
    link.click();
}

// 消息提示
function showMessage(message, type = 'info') {
    const messageBox = document.getElementById('messageBox');
    const messageText = document.getElementById('messageText');
    
    messageText.textContent = message;
    messageBox.className = `message-box ${type}`;
    messageBox.style.display = 'block';
    
    if (type === 'success' || type === 'info') {
        setTimeout(hideMessage, 5000);
    }
}

function hideMessage() {
    document.getElementById('messageBox').style.display = 'none';
}