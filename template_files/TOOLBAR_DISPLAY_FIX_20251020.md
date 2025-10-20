# 画布工具栏显示统一修复

## 📋 问题描述

用户发现从不同入口加载决策树时，工具栏显示不一致：

### 问题1：从"我的决策树"加载 ❌

**操作路径**: 左侧 → 点击"历史"按钮 → 展开"我的决策树"列表 → 点击某个决策树

**现象**:
- 决策树正常加载到画布
- **右上角没有显示工具栏**（缺少排列、清空、导出按钮）

---

### 问题2：从"历史对话框"加载 ✅

**操作路径**: 点击某个位置打开历史对话框 → 点击某个决策树

**现象**:
- 决策树正常加载到画布
- **右上角正确显示工具栏**（包含排列、清空、导出按钮）

---

### 用户需求

> "我希望这个最好可以都统一下，都有这些功能按钮。"

无论从哪个入口加载决策树，工具栏都应该显示。

---

## 🔍 问题分析

### 相关函数

1. **loadTreeFromHistory** (Line 5513)
   - 从"我的决策树"列表加载
   - 调用路径：`onclick="loadTreeFromHistory('${pattern.pattern_id}')"`

2. **loadHistoryTree** (Line 5341)
   - 从"历史对话框"加载
   - 调用路径：`onclick="loadHistoryTree('${pattern.pattern_id}')"`

---

### 根本原因

**对比两个函数**:

**loadHistoryTree**（工作正常）:
```javascript
async function loadHistoryTree(patternId) {
    // ... 加载节点逻辑 ...

    if (pattern.tree_structure && pattern.tree_structure.nodes) {
        clearCanvas();
        nodes = pattern.tree_structure.nodes;
        connections = pattern.tree_structure.connections || [];

        nodes.forEach(node => renderNode(node));
        drawConnections();
        updateCanvas();  // ✅ 有这行！
    }
}
```

**loadTreeFromHistory**（有问题）:
```javascript
async function loadTreeFromHistory(patternId) {
    // ... 加载节点逻辑 ...

    if (pattern.tree_structure.nodes && pattern.tree_structure.nodes.length > 0) {
        nodes = pattern.tree_structure.nodes;
        connections = pattern.tree_structure.connections || [];

        nodes.forEach(node => {
            renderNode(node);
        });

        setTimeout(() => {
            drawConnections();
            // ❌ 缺少 updateCanvas() 调用！
            hideLoading();
            showResult('成功', `✅ 已加载决策树：${pattern.disease_name}`, 'success');
        }, 100);
    }
}
```

**问题核心**:
- `loadTreeFromHistory` 函数加载节点后，**没有调用 `updateCanvas()`**
- `updateCanvas()` 函数负责控制工具栏的显示/隐藏
- 缺少这个调用导致工具栏不显示

---

## ✅ 修复方案

### 修改文件

**文件**: `/opt/tcm-ai/static/decision_tree_visual_builder.html`

**修改位置**: Line 5553-5559

**修改前**:
```javascript
// 绘制连接线
setTimeout(() => {
    drawConnections();
    hideLoading();
    showResult('成功', `✅ 已加载决策树：${pattern.disease_name}`, 'success');
}, 100);
```

**修改后**:
```javascript
// 绘制连接线
setTimeout(() => {
    drawConnections();
    updateCanvas();  // 🔧 修复：添加updateCanvas调用，确保工具栏显示
    hideLoading();
    showResult('成功', `✅ 已加载决策树：${pattern.disease_name}`, 'success');
}, 100);
```

---

## 📊 修复效果

### 修复前 ❌

| 加载路径 | 节点显示 | 工具栏显示 |
|---------|---------|-----------|
| 我的决策树 | ✅ 正常 | ❌ 不显示 |
| 历史对话框 | ✅ 正常 | ✅ 显示 |

**问题**: 不一致，让用户困惑

---

### 修复后 ✅

| 加载路径 | 节点显示 | 工具栏显示 |
|---------|---------|-----------|
| 我的决策树 | ✅ 正常 | ✅ 显示 |
| 历史对话框 | ✅ 正常 | ✅ 显示 |

**效果**: 统一一致，符合用户期望

---

## 🧪 测试验证

### 测试步骤

**访问**: https://mxh0510.cn/static/decision_tree_visual_builder.html

---

#### **测试1：从"我的决策树"加载**

1. 登录医生账号
2. 点击左侧"📋 历史"按钮
3. 在展开的"📚 我的决策树"列表中，点击任意一个决策树

**预期结果**:
- ✅ 决策树节点正常加载到画布
- ✅ 右上角显示工具栏（排列、清空、导出三个按钮）
- ✅ 工具栏按钮可正常点击使用

---

#### **测试2：从"历史对话框"加载**

1. 点击打开历史对话框（如果有的话）
2. 点击任意一个决策树

**预期结果**:
- ✅ 决策树节点正常加载到画布
- ✅ 右上角显示工具栏（排列、清空、导出三个按钮）
- ✅ 工具栏按钮可正常点击使用

---

#### **测试3：对比一致性**

1. 分别从两个入口加载同一个决策树
2. 观察工具栏显示

**预期结果**:
- ✅ 两个入口加载后，工具栏显示完全一致
- ✅ 工具栏都包含3个按钮，颜色和样式相同
- ✅ 功能完全相同

---

#### **测试4：工具栏功能验证**

从"我的决策树"加载后，测试工具栏功能：

**测试排列**:
1. 点击"📐 排列"按钮
2. 观察节点是否自动排列

**测试清空**:
1. 点击"🗑️ 清空"按钮
2. 确认清空操作
3. 观察画布是否清空，工具栏是否隐藏

**测试导出**:
1. 重新加载决策树
2. 点击"📥 导出"按钮
3. 验证是否下载文本文件

---

## 📝 技术细节

### updateCanvas() 函数的作用

```javascript
function updateCanvas() {
    const canvas = document.getElementById('canvas');
    const emptyHint = document.getElementById('emptyHint');
    const canvasToolbar = document.getElementById('canvasToolbar');

    if (nodes.length === 0 && !emptyHint) {
        // 显示空画布提示
        canvas.innerHTML = `...`;
    }

    // 🔑 关键：控制工具栏显示
    if (canvasToolbar) {
        canvasToolbar.style.display = nodes.length > 0 ? 'flex' : 'none';
    }
}
```

**核心逻辑**:
- 检查 `nodes.length`（当前画布的节点数量）
- 如果有节点 → 显示工具栏（`display: flex`）
- 如果无节点 → 隐藏工具栏（`display: none`）

**为什么需要调用**:
- 加载决策树后，`nodes` 数组已经有数据
- 但工具栏的显示状态没有更新
- 必须调用 `updateCanvas()` 来触发显示逻辑

---

### 为什么 loadHistoryTree 正常

`loadHistoryTree` 函数在加载节点后直接调用了 `updateCanvas()`：

```javascript
async function loadHistoryTree(patternId) {
    // ...
    if (pattern.tree_structure && pattern.tree_structure.nodes) {
        clearCanvas();
        nodes = pattern.tree_structure.nodes;
        connections = pattern.tree_structure.connections || [];

        nodes.forEach(node => renderNode(node));
        drawConnections();
        updateCanvas();  // ✅ 这里调用了！
    }
    // ...
}
```

---

### 为什么 loadTreeFromHistory 有问题

原代码中缺少 `updateCanvas()` 调用：

```javascript
async function loadTreeFromHistory(patternId) {
    // ...
    if (pattern.tree_structure.nodes && pattern.tree_structure.nodes.length > 0) {
        nodes = pattern.tree_structure.nodes;
        connections = pattern.tree_structure.connections || [];

        nodes.forEach(node => {
            renderNode(node);
        });

        setTimeout(() => {
            drawConnections();
            // ❌ 这里缺少 updateCanvas() 调用
            hideLoading();
            showResult('成功', `✅ 已加载决策树：${pattern.disease_name}`, 'success');
        }, 100);
    }
    // ...
}
```

**修复**: 在 `drawConnections()` 后添加 `updateCanvas()`

---

## 📋 修改清单

| 文件 | 修改内容 | 行号 |
|------|---------|------|
| `/opt/tcm-ai/static/decision_tree_visual_builder.html` | 在loadTreeFromHistory函数中添加updateCanvas()调用 | 5556 |

**修改统计**:
- JavaScript修改: 1处（添加1行代码）
- 影响范围: loadTreeFromHistory函数

---

## 🎉 修复总结

### 核心问题

从"我的决策树"加载时，工具栏不显示

### 根本原因

`loadTreeFromHistory` 函数缺少 `updateCanvas()` 调用

### 修复方案

在 `loadTreeFromHistory` 函数的 `setTimeout` 中添加 `updateCanvas()` 调用

### 修复效果

- ✅ 两个加载入口的工具栏显示统一
- ✅ 用户体验一致
- ✅ 所有功能按钮都可用

---

## ✅ 完成清单

- [x] 诊断问题根本原因
- [x] 修改loadTreeFromHistory函数
- [x] 添加updateCanvas()调用
- [x] 服务重启部署
- [x] 创建修复文档

---

**修复时间**: 2025-10-20 01:28
**修复文件**: `/opt/tcm-ai/static/decision_tree_visual_builder.html`
**服务状态**: ✅ 已重启运行
**测试状态**: 等待用户验证

---

**现在从任何入口加载决策树都能看到工具栏了！** 🎊

访问: https://mxh0510.cn/static/decision_tree_visual_builder.html
