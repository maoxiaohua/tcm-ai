# 诊疗思路文本显示缺陷分析报告

## 问题概述

**现象**：左侧"诊疗思路"文本框中，证候(syndrome)节点只显示节点名称，未显示节点的详细描述。
- 右侧Canvas: 显示完整内容"后脑疼。症状：后脑疼。"
- 左侧诊疗思路: 只显示"后脑疼"(缺少描述)

**根本原因**：数据已被正确保存到structuredData.syndromes[].description，但两个关键函数在转换/渲染时忽略了这个字段。

---

## 问题定位

### 关键发现

1. **数据流是完整的**：
   - buildStructuredData() 第5737行 ✅ 正确保存了 `syndrome.description`
   - structuredData 对象包含完整的description字段

2. **问题在两个输出函数**：
   - convertStructuredDataToText() 第6292-6347行 ❌ 未输出description到文本框
   - renderStructuredView() 第5901-6141行 ❌ 未显示description在HTML界面

3. **对比参考**：
   - disease.description 被正确处理 (第6297-6298行)
   - other_nodes.description 被正确处理 (第6337-6338行)
   - **但 syndrome.description 被遗漏** ← 不一致的处理逻辑

---

## 文件位置和行数

**文件**：`/opt/tcm-ai/static/decision_tree_v3_data_driven.html`

| 问题类别 | 函数名 | 行数范围 | 缺失内容 |
|---------|--------|---------|---------|
| 文本输出 | convertStructuredDataToText | 6292-6347 | 第6304行后缺少description输出 |
| HTML显示 | renderStructuredView | 5901-6141 | 第5987行后缺少description字段 |
| 数据源 | buildStructuredData | 5631-5895 | ✅ 已正确保存(第5737行) |

---

## 详细问题分析

### 问题1：convertStructuredDataToText() 函数

**位置**：第6303-6344行的循环中

**现状**：
```javascript
data.syndromes.forEach((syndrome, index) => {
    text += `【${syndrome.type === 'syndrome' ? '证候' : '分支'}${index + 1}】${syndrome.name}\n`;
    // ❌ 直接跳过了 syndrome.description
    
    if (syndrome.pathogenesis.length > 0) {
        text += `病机：${syndrome.pathogenesis.map(p => p.name).join('、')}\n`;
    }
    // ... 其他处理
});
```

**缺失**：第6304行后应该有类似下面的代码：
```javascript
if (syndrome.description && syndrome.description.trim()) {
    text += `${syndrome.description}\n`;
}
```

**对标**：
- disease.description 的处理方式(第6297-6298行) ✅
- other_nodes.description 的处理方式(第6337-6338行) ✅

### 问题2：renderStructuredView() 函数

**位置**：第5964-6136行的HTML生成中

**现状**：
```javascript
data.syndromes.forEach((syndrome, index) => {
    html += `<div class="syndrome-card">...`;
    
    // 证候名称字段
    html += `<div class="structured-field">...${syndrome.name}...</div>`;
    
    // ❌ 直接跳到了病机字段，没有description字段
    if (syndrome.pathogenesis.length > 0) { ... }
});
```

**缺失**：第5987行后应该添加证候描述字段的HTML

---

## 修复方案

### 方案A：简易修复（推荐首选）

#### 修复1：convertStructuredDataToText() 函数

**位置**：第6304行之后

**添加代码**（约5行）：
```javascript
text += `【${syndrome.type === 'syndrome' ? '证候' : '分支'}${index + 1}】${syndrome.name}\n`;

// 新增：输出证候描述
if (syndrome.description && syndrome.description.trim()) {
    text += `${syndrome.description}\n`;
}

if (syndrome.pathogenesis.length > 0) {
```

**优点**：
- 代码简洁（只需5行）
- 逻辑清晰
- 符合现有的disease.description处理方式

#### 修复2：renderStructuredView() 函数

**位置**：第5987行之后

**添加代码**（约12行）：
```javascript
// 证候名称字段的结束标签（第5986行）
`;

// 新增：证候描述字段
if (syndrome.description) {
    html += `
        <div class="structured-field">
            <div class="structured-field-label">证候描述</div>
            <div class="structured-field-value editable"
                 contenteditable="true"
                 onblur="handleFieldEdit(this, '${syndrome.id}', 'description')"
                 onkeydown="handleFieldKeydown(event, this)">
                ${syndrome.description}
            </div>
        </div>
    `;
}

// 病机字段（原第5989行）
if (syndrome.pathogenesis.length > 0) {
```

**优点**：
- 保持与disease.description字段的HTML结构一致
- 用户可直接在界面编辑
- 修改会自动保存

---

### 方案B：高级修复（参考备用逻辑）

**参考位置**：第6460-6481行的备用文本拼接逻辑

**特点**：
- 智能格式化多部分描述
- 按"。"分割，跳过重复部分
- 更复杂但更优雅

**适用场景**：
- 当description包含多行内容
- 需要避免显示重复的节点名称时

---

## 影响范围

### 受影响的操作
1. 用户点击"根据画布完整重新生成诊疗思路"按钮
2. 切换到文本视图/结构化视图时
3. 手动编辑诊疗思路后再次生成时

### 影响的用户
- 所有在医生工作台中使用"特色诊疗方案"功能的医生
- 使用决策树构建工具的医疗工作人员

---

## 验证清单

修复后验证步骤：
- [ ] 在canvas上创建包含description的证候节点
- [ ] 点击"根据画布完整重新生成诊疗思路"
- [ ] 验证左侧文本框中是否显示了description内容
- [ ] 如果启用HTML视图，验证是否显示"证候描述"字段
- [ ] 验证description可编辑，修改后能否保存

---

## 参考资料

### 正确处理的相似代码

**disease.description的处理**(第6295-6301行)：
```javascript
if (data.disease) {
    text += `主病：${data.disease.name}\n`;
    if (data.disease.description) {
        text += `${data.disease.description}\n`;  // ✅ 模板
    }
    text += '\n';
}
```

**other_nodes.description的处理**(第6334-6341行)：
```javascript
if (syndrome.other_nodes && syndrome.other_nodes.length > 0) {
    syndrome.other_nodes.forEach(node => {
        text += `${node.type}: ${node.name}\n`;
        if (node.description) {
            text += `  ${node.description}\n`;  // ✅ 模板
        }
    });
}
```

**disease.description的HTML显示**(第5943-5956行)：
```javascript
if (data.disease.description) {
    html += `
        <div class="structured-field">
            <div class="structured-field-label">病症描述</div>
            <div class="structured-field-value editable"
                 contenteditable="true"
                 onblur="handleFieldEdit(this, '${data.disease.id}', 'description')">
                ${data.disease.description || ''}
            </div>
        </div>
    `;  // ✅ 模板
}
```

---

## 修复优先级

1. **立即修复** ⚠️：convertStructuredDataToText() 
   - 用户看到的左侧文本框直接输出
   - 只需5行代码

2. **应同时修复**：renderStructuredView()
   - HTML界面的完整性
   - 支持用户编辑

3. **参考优化**：智能格式化逻辑
   - 可选项，优化显示效果

---

## 总结

**问题本质**：数据已正确收集和保存，但在最后的渲染/输出层被忽略了。

**修复方向**：在两个输出函数中补充缺失的description处理逻辑。

**修复复杂度**：低（只需模仿现有的disease.description处理方式）

**修复时间**：预计 15-30 分钟

---

**生成时间**：2025-11-05
**分析工具**：Claude Code Agent
**涉及文件**：/opt/tcm-ai/static/decision_tree_v3_data_driven.html (380.9KB)
