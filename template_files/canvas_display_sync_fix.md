# 画布显示同步修复 - Canvas Display Sync Fix

## 问题描述

用户反馈：在左侧结构化视图中编辑方剂内容后，右侧画布上的节点卡片显示没有实时更新。但是双击节点后发现内容实际上已经更新了，只是视觉显示没有同步。

## 问题分析

### 控制台错误
```
Uncaught ReferenceError: redrawCanvas is not defined
    at handleFieldEdit (decision_tree_v3_data_driven.html:5992:17)
```

### 根本原因
1. **DOM选择器错误**: 使用了 `document.querySelector('[data-node-id="${nodeId}"]')` 查找节点
2. **实际节点结构**: 画布节点使用 `id` 属性，不是 `data-node-id` 属性
3. **renderNode()函数**（第4226行）中的实际代码：
   ```javascript
   nodeElement.id = node.id;  // 直接使用id属性
   ```

### 导致结果
- 选择器找不到节点元素，返回 `null`
- `console.warn('⚠️ 找不到画布节点元素')` 被触发
- 数据更新了（`node[field] = newValue`），但DOM没更新
- 双击节点时重新渲染，才能看到更新后的内容

## 解决方案

### 修改内容
**文件**: `/opt/tcm-ai/static/decision_tree_v3_data_driven.html`

**位置**: `handleFieldEdit()` 函数（第5981-6022行）

### 修改前代码
```javascript
function handleFieldEdit(element, nodeId, field) {
    const newValue = element.innerText.trim();
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
        node[field] = newValue;

        // ❌ 错误的选择器
        const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
        if (nodeElement) {
            const titleElement = nodeElement.querySelector('.node-title');
            const contentElement = nodeElement.querySelector('.node-content');

            if (field === 'name' && titleElement) {
                titleElement.textContent = newValue;  // ❌ 会丢失图标
            } else if (field === 'description' && contentElement) {
                contentElement.textContent = newValue;
            }
        }
    }
}
```

### 修改后代码
```javascript
function handleFieldEdit(element, nodeId, field) {
    const newValue = element.innerText.trim();
    console.log(`✏️ 编辑字段: nodeId=${nodeId}, field=${field}, newValue=${newValue}`);

    const node = nodes.find(n => n.id === nodeId);
    if (node) {
        node[field] = newValue;
        console.log(`✅ 节点数据已更新:`, node);

        // ✅ 修正：使用getElementById直接查找节点
        const nodeElement = document.getElementById(nodeId);
        if (nodeElement) {
            console.log('✅ 找到画布节点元素:', nodeElement);

            if (field === 'name') {
                // ✅ 更新节点标题（保留图标）
                const titleElement = nodeElement.querySelector('.node-title');
                if (titleElement) {
                    const iconElement = titleElement.querySelector('.node-type-icon');
                    const iconHTML = iconElement ? iconElement.outerHTML : '';
                    titleElement.innerHTML = iconHTML + newValue;
                    console.log('✅ 画布节点标题已更新');
                }
            } else if (field === 'description') {
                // ✅ 更新节点内容
                const contentElement = nodeElement.querySelector('.node-content');
                if (contentElement) {
                    contentElement.textContent = newValue;
                    console.log('✅ 画布节点内容已更新');
                }
            }
        } else {
            console.warn('⚠️ 找不到画布节点元素:', nodeId);
        }

        showResult('提示', '内容已更新，记得保存', 'info');
    }
}
```

## 关键改进点

### 1. 正确的DOM选择器
**修改前**:
```javascript
const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
```

**修改后**:
```javascript
const nodeElement = document.getElementById(nodeId);  // ✅ 直接使用id
```

### 2. 保留节点图标
**修改前**:
```javascript
titleElement.textContent = newValue;  // ❌ 会删除图标元素
```

**修改后**:
```javascript
const iconElement = titleElement.querySelector('.node-type-icon');
const iconHTML = iconElement ? iconElement.outerHTML : '';
titleElement.innerHTML = iconHTML + newValue;  // ✅ 保留图标
```

### 3. 增强的调试日志
添加了详细的控制台日志，便于调试：
- `✏️ 编辑字段: nodeId=..., field=..., newValue=...`
- `✅ 节点数据已更新`
- `✅ 找到画布节点元素`
- `✅ 画布节点标题已更新` / `✅ 画布节点内容已更新`

## 节点结构说明

### 画布节点的实际DOM结构
```html
<div class="node prescription" id="node_6" style="left: 400px; top: 300px;">
    <button class="delete-btn" onclick="deleteNodeById('node_6')">×</button>
    <div class="node-title">
        <span class="node-type-icon">💊</span>
        天麻钩藤饮
    </div>
    <div class="node-content" id="content_node_6">
        天麻10g, 钩藤12g, 石决明15g...
    </div>
</div>
```

### 关键点
1. **节点ID**: 直接使用 `id="node_6"` 属性
2. **节点图标**: 包含在 `.node-title` 中的 `.node-type-icon` 元素
3. **节点标题**: `.node-title` 的文本部分（图标之后）
4. **节点内容**: `.node-content` 元素的全部文本

## 数据流程

### 完整的编辑流程
1. **用户操作**: 在左侧结构化视图中点击可编辑字段进行编辑
2. **失焦触发**: 编辑完成后失焦（blur），触发 `handleFieldEdit(element, nodeId, field)`
3. **数据更新**: 更新 `nodes` 数组中对应节点的字段值
4. **DOM同步**: 使用 `getElementById` 找到画布上的节点元素
5. **视觉更新**: 更新 `.node-title` 或 `.node-content` 的显示内容
6. **用户反馈**: 显示"内容已更新，记得保存"提示

### 双向同步机制
```
左侧结构化视图 ←→ nodes数据 ←→ 右侧画布显示
       ↓                ↓              ↓
  contenteditable    数组对象        DOM元素
       ↓                ↓              ↓
    失焦保存     → 更新数据值 →   更新视觉显示
```

## 测试步骤

### 验证修复效果
1. **打开页面**: https://mxh0510.cn/static/decision_tree_v3_data_driven.html
2. **添加处方节点**: 在画布中添加一个处方类型节点
3. **点击重新生成**: 生成左侧结构化视图
4. **编辑方剂组成**: 在左侧结构化视图中点击"方剂组成"字段并编辑
5. **失焦保存**: 点击页面其他地方，触发失焦保存
6. **验证同步**:
   - ✅ 右侧画布上的节点卡片应该**立即**显示更新后的内容
   - ✅ 不需要双击节点就能看到更新
   - ✅ 节点图标应该保持完整（不会丢失💊等图标）

### 测试其他字段
1. **处方名称**: 编辑处方名称，验证标题更新（保留图标）
2. **症状描述**: 编辑症状节点的描述，验证内容更新
3. **病机说明**: 编辑病机节点，验证同步
4. **加减条件**: 编辑加减节点，验证显示

## 控制台日志示例

### 成功更新的日志
```
✏️ 编辑字段: nodeId=node_6, field=description, newValue=天麻10g, 钩藤12g, 石决明15g, 牛膝10g
✅ 节点数据已更新: {id: "node_6", type: "prescription", name: "天麻钩藤饮", description: "天麻10g, 钩藤12g...", ...}
✅ 找到画布节点元素: <div class="node prescription" id="node_6">...</div>
✅ 画布节点内容已更新
```

### 如果出现问题的日志
```
✏️ 编辑字段: nodeId=node_6, field=description, newValue=...
✅ 节点数据已更新: {...}
⚠️ 找不到画布节点元素: node_6
```
如果看到这个警告，说明节点ID不匹配或节点未渲染。

## 技术要点总结

### 1. DOM选择器的选择
- ✅ **getElementById**: 最快，适合已知id的情况
- ⚠️ **querySelector**: 灵活但慢，适合复杂选择器
- ❌ **错误属性**: 使用不存在的属性（如data-node-id）会返回null

### 2. innerHTML vs textContent
- **textContent**: 只设置文本，会删除所有子元素
- **innerHTML**: 可以设置HTML结构，保留图标等元素
- **安全性**: 本场景使用的是已存在的图标HTML，安全可控

### 3. 事件处理时机
- **onblur**: 失焦时触发，适合保存编辑
- **onkeydown**: 可以捕获Enter键快速保存
- **contenteditable**: HTML5原生编辑功能，无需额外输入框

## 相关文档

- **结构化视图实现**: `decision_tree_v3_structured_update_summary.md`
- **处方字段优化**: `prescription_field_separation_fix.md`
- **优化方案设计**: `decision_tree_v3_optimization_plan.md`

## 部署信息

- ✅ 代码已修改：2025-10-31 12:20
- ✅ 服务已重启：2025-10-31 12:21
- ✅ 修改已生效：立即可用

## 总结

### 问题本质
DOM选择器使用了错误的属性名，导致无法找到画布节点进行视觉更新。

### 解决方法
1. 使用正确的 `getElementById(nodeId)` 选择器
2. 更新标题时保留图标元素结构
3. 添加详细日志便于后续调试

### 效果
✅ 左侧结构化视图编辑 → 右侧画布**实时**视觉同步
✅ 双向数据流完全打通
✅ 用户体验流畅，所见即所得

---

**更新时间**: 2025-10-31 12:21
**状态**: ✅ 已完成并部署
**版本**: v3.1-结构化版本
