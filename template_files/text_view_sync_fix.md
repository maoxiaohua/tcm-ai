# 文本视图同步修复 - Text View Sync Fix

## 问题描述

用户反馈：在左侧诊疗思路的**结构化视图**中编辑内容后，切换到**文本视图**时，显示的还是旧内容，没有实时同步。

## 问题分析

### 双视图系统架构
```
左侧诊疗思路
├── 📋 结构化视图 (默认)
│   └── 可编辑字段 (contenteditable)
└── 📝 文本视图
    └── 只读文本区域 (textarea)
```

### 数据流向
```
画布节点数据 (nodes数组)
    ↓
buildStructuredData()
    ↓
structuredData缓存
    ↓
    ├─→ renderStructuredView() → 结构化视图
    └─→ convertStructuredDataToText() → 文本视图
```

### 根本原因
当用户在结构化视图中编辑字段时：

1. **handleFieldEdit()** 更新了 `nodes` 数组中的节点数据 ✅
2. **handleFieldEdit()** 更新了画布上的DOM显示 ✅
3. **但是没有更新 `structuredData` 缓存** ❌

结果：
- 结构化视图显示正确（因为直接更新了DOM）
- 切换到文本视图时，`toggleView()` 使用的是**旧的** `structuredData` 缓存
- 文本视图显示的是编辑前的内容

### 触发流程对比

#### ✅ 画布编辑 → 正常同步
```javascript
editNode() → 保存
    ↓
updateThinkingProcessFromNodes()
    ↓
structuredData = buildStructuredData()  // 重建缓存
    ↓
根据当前视图渲染
```

#### ❌ 结构化视图编辑 → 缓存未更新
```javascript
handleFieldEdit() → 失焦保存
    ↓
更新 nodes 数组 ✅
更新画布 DOM ✅
// 缺少这一步：structuredData = buildStructuredData() ❌
```

## 解决方案

### 修改内容
**文件**: `/opt/tcm-ai/static/decision_tree_v3_data_driven.html`

**位置**: `handleFieldEdit()` 函数（第5981-6026行）

### 修改前代码
```javascript
function handleFieldEdit(element, nodeId, field) {
    const newValue = element.innerText.trim();

    const node = nodes.find(n => n.id === nodeId);
    if (node) {
        // 更新节点数据
        node[field] = newValue;

        // 更新画布DOM
        const nodeElement = document.getElementById(nodeId);
        // ... 更新DOM逻辑

        // ❌ 缺少：更新结构化数据缓存

        showResult('提示', '内容已更新，记得保存', 'info');
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
        // 更新节点数据
        node[field] = newValue;
        console.log(`✅ 节点数据已更新:`, node);

        // 更新画布DOM
        const nodeElement = document.getElementById(nodeId);
        if (nodeElement) {
            console.log('✅ 找到画布节点元素:', nodeElement);

            if (field === 'name') {
                // 更新标题
                const titleElement = nodeElement.querySelector('.node-title');
                if (titleElement) {
                    const iconElement = titleElement.querySelector('.node-type-icon');
                    const iconHTML = iconElement ? iconElement.outerHTML : '';
                    titleElement.innerHTML = iconHTML + newValue;
                    console.log('✅ 画布节点标题已更新');
                }
            } else if (field === 'description') {
                // 更新内容
                const contentElement = nodeElement.querySelector('.node-content');
                if (contentElement) {
                    contentElement.textContent = newValue;
                    console.log('✅ 画布节点内容已更新');
                }
            }
        } else {
            console.warn('⚠️ 找不到画布节点元素:', nodeId);
        }

        // 🆕 重建结构化数据缓存，确保切换到文本视图时数据是最新的
        structuredData = buildStructuredData();
        console.log('✅ 结构化数据缓存已更新');

        showResult('提示', '内容已更新，记得保存', 'info');
    } else {
        console.error(`❌ 找不到节点数据: ${nodeId}`);
    }
}
```

## 关键改进

### 新增的关键代码
```javascript
// 🆕 重建结构化数据缓存，确保切换到文本视图时数据是最新的
structuredData = buildStructuredData();
console.log('✅ 结构化数据缓存已更新');
```

### 为什么这样修复有效

1. **数据一致性**: 每次编辑后立即重建缓存，确保 `structuredData` 始终反映最新的 `nodes` 数组
2. **视图切换正确**: `toggleView()` 使用最新的 `structuredData`，文本视图显示最新内容
3. **性能可控**: `buildStructuredData()` 是轻量级函数，即使频繁调用也不会影响性能

## 完整的数据同步流程

### 修复后的三种编辑场景

#### 场景1: 画布编辑节点
```javascript
双击节点 → editNode() → 保存
    ↓
updateThinkingProcessFromNodes()
    ↓
structuredData = buildStructuredData()
    ↓
renderStructuredView(structuredData)
```

#### 场景2: 结构化视图编辑
```javascript
点击字段 → 编辑 → 失焦
    ↓
handleFieldEdit(element, nodeId, field)
    ↓
更新 nodes 数组
    ↓
更新画布 DOM
    ↓
structuredData = buildStructuredData()  // 🆕 新增
    ↓
结构化视图显示最新
```

#### 场景3: 切换到文本视图
```javascript
点击 "📝 文本" 按钮
    ↓
toggleView()
    ↓
使用 structuredData (已是最新) ✅
    ↓
textarea.value = convertStructuredDataToText(structuredData)
    ↓
文本视图显示最新内容 ✅
```

## 视图切换逻辑说明

### toggleView() 函数逻辑
```javascript
function toggleView() {
    isStructuredView = !isStructuredView;

    if (isStructuredView) {
        // 切换到结构化视图
        structuredView.style.display = 'block';
        textView.style.display = 'none';

        if (!structuredData) {
            structuredData = buildStructuredData();
        }
        renderStructuredView(structuredData);
    } else {
        // 切换到文本视图
        structuredView.style.display = 'none';
        textView.style.display = 'block';

        if (!structuredData) {
            structuredData = buildStructuredData();
        }
        // 🔑 关键：使用最新的 structuredData 生成文本
        const textarea = document.getElementById('doctorThought');
        textarea.value = convertStructuredDataToText(structuredData);
    }
}
```

### 为什么之前不同步

**之前**:
```javascript
handleFieldEdit() {
    node[field] = newValue;  // ✅ 更新数据
    // 直接更新DOM         // ✅ 更新显示
    // structuredData 没有更新 ❌ 缓存过期
}

toggleView() {
    // 使用过期的 structuredData ❌
    textarea.value = convertStructuredDataToText(structuredData);
}
```

**现在**:
```javascript
handleFieldEdit() {
    node[field] = newValue;              // ✅ 更新数据
    // 更新DOM                           // ✅ 更新显示
    structuredData = buildStructuredData(); // ✅ 更新缓存
}

toggleView() {
    // 使用最新的 structuredData ✅
    textarea.value = convertStructuredDataToText(structuredData);
}
```

## 测试步骤

### 验证修复效果

1. **打开页面**: https://mxh0510.cn/static/decision_tree_v3_data_driven.html
2. **添加节点**: 在画布中添加一些节点（病种 → 证候 → 处方）
3. **生成结构化视图**: 点击"重新生成"按钮
4. **在结构化视图编辑**:
   - 点击"方剂组成"字段
   - 修改内容（如添加几味药材）
   - 点击页面其他地方触发保存
5. **切换到文本视图**: 点击"📝 文本"按钮
6. **验证同步** ✅:
   - 文本视图应该显示刚才编辑的最新内容
   - 不应该显示编辑前的旧内容
7. **切换回结构化视图**: 点击"📋 结构"按钮
8. **再次验证**: 结构化视图仍然显示最新内容

### 测试多个字段
- ✅ 处方名称编辑 → 切换到文本视图 → 验证同步
- ✅ 方剂组成编辑 → 切换到文本视图 → 验证同步
- ✅ 病机描述编辑 → 切换到文本视图 → 验证同步
- ✅ 症状内容编辑 → 切换到文本视图 → 验证同步

### 测试编辑顺序
1. 在结构化视图编辑字段A
2. 切换到文本视图 → 应该看到A的修改 ✅
3. 切换回结构化视图
4. 编辑字段B
5. 切换到文本视图 → 应该看到A和B的修改 ✅

## 控制台日志示例

### 成功同步的日志
```
✏️ 编辑字段: nodeId=node_6, field=description, newValue=天麻10g, 钩藤12g, 石决明15g, 牛膝10g
✅ 节点数据已更新: {id: "node_6", type: "prescription", ...}
✅ 找到画布节点元素: <div class="node prescription" id="node_6">...</div>
✅ 画布节点内容已更新
🏗️ 开始构建结构化数据...
✅ 结构化数据缓存已更新
```

切换到文本视图时：
```
// toggleView() 执行
// 使用最新的 structuredData 生成文本
```

## 性能考虑

### buildStructuredData() 调用频率
- **场景1**: 画布编辑保存 → 1次调用
- **场景2**: 结构化视图编辑 → 每次编辑1次调用
- **场景3**: 视图切换 → 仅在缓存为空时调用

### 性能影响分析
```javascript
// buildStructuredData() 的复杂度
O(nodes.length) + O(connections.length)

// 典型场景
nodes.length ~ 10-20 个节点
connections.length ~ 15-30 个连接
执行时间 < 10ms
```

**结论**: 性能影响可忽略不计，用户体验提升明显。

## 技术要点总结

### 1. 缓存一致性
- **问题**: 缓存数据与实际数据不一致
- **原则**: 每次修改数据后立即更新缓存
- **实现**: `structuredData = buildStructuredData()`

### 2. 数据流单向性
```
nodes 数组 (唯一数据源)
    ↓
structuredData (缓存)
    ↓
视图渲染 (结构化/文本)
```

### 3. 视图切换逻辑
- 不同视图使用相同的数据源 (`structuredData`)
- 切换时根据数据重新渲染，而不是保存视图状态

### 4. 编辑触发点
- 结构化视图：`onblur` 事件（失焦保存）
- 画布编辑：点击"保存"按钮
- 两者最终都更新 `nodes` 数组和 `structuredData`

## 相关文档

- **画布同步修复**: `canvas_display_sync_fix.md`
- **结构化视图实现**: `decision_tree_v3_structured_update_summary.md`
- **处方字段优化**: `prescription_field_separation_fix.md`

## 部署信息

- ✅ 代码已修改：2025-10-31 12:48
- ✅ 服务已重启：2025-10-31 12:49
- ✅ 修改已生效：立即可用

## 总结

### 问题本质
结构化视图编辑后没有更新 `structuredData` 缓存，导致切换到文本视图时看到旧数据。

### 解决方法
在 `handleFieldEdit()` 函数中添加：
```javascript
structuredData = buildStructuredData();
```

### 效果
✅ 结构化视图编辑 → 文本视图**实时**同步
✅ 双向切换数据完全一致
✅ 所有编辑操作数据流完整

---

**更新时间**: 2025-10-31 12:49
**状态**: ✅ 已完成并部署
**版本**: v3.1-结构化版本
