# 画布工具栏显示问题修复

## 问题描述
用户反馈：画布中看不到工具栏（包括新添加的"🔗 连接"按钮）

## 问题原因
CSS中使用了 `display: none !important;` 强制隐藏工具栏，导致JavaScript无法通过设置 `display: flex` 来显示工具栏（`!important` 规则优先级最高）。

## 问题位置
文件：`/opt/tcm-ai/static/decision_tree_visual_builder.html`
位置：第73-85行

### 问题代码（修复前）
```css
.canvas-toolbar {
    position: absolute;
    top: 15px;
    right: 15px;
    z-index: 100;
    display: none !important;  /* ❌ 这里的 !important 阻止了JavaScript修改 */
    gap: 8px;
    background: rgba(255, 255, 255, 0.95);
    padding: 8px;
    border-radius: 10px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
}
```

### 修复代码（修复后）
```css
.canvas-toolbar {
    position: absolute;
    top: 15px;
    right: 15px;
    z-index: 100;
    display: none;  /* ✅ 移除 !important，允许JavaScript控制显示 */
    gap: 8px;
    background: rgba(255, 255, 255, 0.95);
    padding: 8px;
    border-radius: 10px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
}
```

## 工作原理
1. 页面加载时，工具栏默认隐藏（`display: none`）
2. 当有节点添加到画布时，`updateCanvas()` 函数执行
3. JavaScript设置 `canvasToolbar.style.display = 'flex'` 显示工具栏
4. 修复后，没有 `!important` 干扰，JavaScript可以正常控制显示状态

## 相关代码
### JavaScript控制逻辑
```javascript
// 更新画布状态
function updateCanvas() {
    const canvas = document.getElementById('canvas');
    const emptyHint = document.getElementById('emptyHint');
    const canvasToolbar = document.getElementById('canvasToolbar');

    if (nodes.length === 0 && !emptyHint) {
        // 无节点时显示空状态提示
        canvas.innerHTML = `...`;
    }

    // 🆕 控制画布工具栏显示：有节点时显示，无节点时隐藏
    if (canvasToolbar) {
        canvasToolbar.style.display = nodes.length > 0 ? 'flex' : 'none';
    }
}
```

### 工具栏HTML结构
```html
<div id="canvasToolbar" class="canvas-toolbar" style="display: none;">
    <button id="connectionModeBtn" class="canvas-tool-btn canvas-tool-btn-info"
            title="连接两个节点" onclick="toggleConnectionMode()">
        🔗 连接
    </button>
    <button id="arrangeBtn" class="canvas-tool-btn canvas-tool-btn-success"
            title="自动排列节点">
        📐 排列
    </button>
    <button id="clearBtn" class="canvas-tool-btn canvas-tool-btn-danger"
            title="清空画布">
        🗑️ 清空
    </button>
    <button id="exportCurrentBtn" class="canvas-tool-btn canvas-tool-btn-primary"
            title="导出当前特色诊疗方案">
        📥 导出
    </button>
</div>
```

## 工具栏位置
- **位置**: 画布右上角
- **z-index**: 100（在节点之上）
- **外观**: 半透明白色背景，毛玻璃效果
- **按钮**: 横向排列，间距8px

## 修复时间
2025-10-28

## 测试验证
1. ✅ 页面加载时，无节点，工具栏隐藏
2. ✅ 添加节点后，工具栏自动显示在右上角
3. ✅ 工具栏包含4个按钮：🔗 连接、📐 排列、🗑️ 清空、📥 导出
4. ✅ 清空画布后，工具栏自动隐藏
5. ✅ 加载已保存的方案后，工具栏正常显示

## 部署状态
- ✅ 代码已修复
- ✅ 服务已重启
- ✅ 功能已上线

请刷新页面查看效果！工具栏现在应该显示在画布右上角。
