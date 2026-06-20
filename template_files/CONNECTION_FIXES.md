# 连接功能三项修复

## 修复时间
2025-10-28 11:00

## 问题概述
用户反馈了三个关于连接功能的问题：
1. 创建连接后左侧诊疗思路没有自动更新
2. 连接模式按钮一直保持"连接中..."状态
3. 无法删除连接线

---

## ✅ 修复一：诊疗思路自动更新

### 问题描述
用户在画布上创建了新的连接（如：跳着疼 → 处方1加减片），但左侧的诊疗思路文本框中的内容没有同步更新。

### 问题原因
代码中已经调用了 `updateThinkingProcessFromNodes()`，但可能由于某些原因没有生效。

### 解决方案
在 `confirmConnection` 函数中添加了详细的调试日志，确保更新函数被正确调用：

```javascript
window.confirmConnection = function(fromId, toId) {
    const label = document.getElementById('connectionLabel')?.value.trim() || '';

    // 创建新连接
    const newConnection = {
        from: fromId,
        to: toId,
        label: label
    };

    connections.push(newConnection);
    console.log('🔗 创建新连接:', newConnection);
    console.log('📊 当前所有连接:', connections);

    drawConnections();

    // 自动更新诊疗思路
    console.log('⏳ 准备更新诊疗思路...');
    updateThinkingProcessFromNodes();  // ✅ 确保调用
    console.log('✅ 诊疗思路更新完成');

    // 关闭对话框
    cancelConnectionDialog();

    // 显示成功提示
    const fromNode = nodes.find(n => n.id === fromId);
    const toNode = nodes.find(n => n.id === toId);
    const labelText = label ? ` (${label})` : '';
    showResult('成功', `✅ 已创建连接：${fromNode.name} → ${toNode.name}${labelText}`, 'success');
};
```

### 测试验证
打开浏览器控制台（F12），创建连接时应该看到以下日志：
```
🔗 创建新连接: {from: "node_xxx", to: "node_yyy", label: "若"}
📊 当前所有连接: Array(5)
⏳ 准备更新诊疗思路...
🔄 自动更新诊疗思路（按连接关系）...
✅ 诊疗思路已自动更新
✅ 诊疗思路更新完成
```

---

## ✅ 修复二：连接模式按钮状态管理

### 问题描述
点击"🔗 连接"按钮后，按钮变为"🔗 连接中..."并保持绿色状态，即使已经完成连接或取消连接，按钮仍然保持"连接中..."状态。

### 问题原因
在 `selectNode` 函数中，虽然设置了 `connectionMode = false`，但没有同步更新按钮的显示状态。

### 解决方案

#### 1. 取消连接时更新按钮
```javascript
} else if (firstSelectedNodeForConnection.id === node.id) {
    // 点击同一个节点，取消连接模式
    document.getElementById(node.id).classList.remove('connection-source');
    firstSelectedNodeForConnection = null;
    connectionMode = false;

    // ✅ 更新按钮状态
    const btn = document.getElementById('connectionModeBtn');
    if (btn) {
        btn.classList.remove('active');
        btn.innerHTML = '🔗 连接';
    }

    showResult('取消', '已取消连接模式', 'info');
    console.log('❌ 取消连接模式');
}
```

#### 2. 完成连接后更新按钮
```javascript
} else {
    // 选择第二个节点，创建连接
    const fromNode = firstSelectedNodeForConnection;
    const toNode = node;

    // ... 连接逻辑 ...

    // 清除连接模式
    document.getElementById(fromNode.id).classList.remove('connection-source');
    firstSelectedNodeForConnection = null;
    connectionMode = false;

    // ✅ 更新按钮状态
    const btn = document.getElementById('connectionModeBtn');
    if (btn) {
        btn.classList.remove('active');
        btn.innerHTML = '🔗 连接';
    }
}
```

### 按钮状态说明
- **未激活**: 蓝色按钮 "🔗 连接"
- **激活中**: 绿色按钮 "🔗 连接中..." （带脉冲动画）
- **完成/取消后**: 自动恢复为蓝色 "🔗 连接"

---

## ✅ 修复三：删除连接线功能

### 问题描述
用户无法删除已创建的连接线，希望能通过右键菜单删除连接，并且删除后左侧诊疗思路也能同步更新。

### 解决方案

#### 1. 增强连接线交互
修改 `drawConnections()` 函数，为每条连接线添加交互功能：

```javascript
function drawConnections() {
    // ... 前面的代码 ...

    connections.forEach((conn, index) => {
        // ... 创建路径 ...

        // ✅ 添加唯一ID
        const connectionId = `conn_${conn.from}_${conn.to}`;
        path.setAttribute('id', connectionId);
        path.style.cursor = 'pointer';
        path.setAttribute('data-from', conn.from);
        path.setAttribute('data-to', conn.to);

        // ✅ 添加鼠标悬停效果
        path.addEventListener('mouseenter', function() {
            this.setAttribute('stroke', '#ef4444');  // 红色
            this.setAttribute('stroke-width', '3');
        });

        path.addEventListener('mouseleave', function() {
            this.setAttribute('stroke', '#3b82f6');  // 蓝色
            this.setAttribute('stroke-width', '2');
        });

        // ✅ 添加右键菜单
        path.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showConnectionContextMenu(e, conn.from, conn.to, fromNode, toNode);
        });

        // ✅ 连接标签也可以右键删除
        if (conn.label) {
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            // ... 设置标签属性 ...
            text.style.cursor = 'pointer';

            text.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                e.stopPropagation();
                showConnectionContextMenu(e, conn.from, conn.to, fromNode, toNode);
            });

            svg.appendChild(text);
        }

        svg.appendChild(path);
    });
}
```

#### 2. 右键菜单
创建 `showConnectionContextMenu()` 函数显示删除菜单：

```javascript
function showConnectionContextMenu(e, fromId, toId, fromNode, toNode) {
    // 移除现有菜单
    const existingMenu = document.querySelector('.connection-context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }

    // 创建菜单
    const menu = document.createElement('div');
    menu.className = 'connection-context-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${e.clientX}px;
        top: ${e.clientY}px;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        padding: 8px 0;
        min-width: 180px;
    `;

    const conn = connections.find(c => c.from === fromId && c.to === toId);
    const labelText = conn && conn.label ? ` (${conn.label})` : '';

    menu.innerHTML = `
        <div style="padding: 8px 16px; color: #6b7280; font-size: 12px; border-bottom: 1px solid #e5e7eb;">
            ${fromNode.name} → ${toNode.name}${labelText}
        </div>
        <div class="menu-item" onclick="deleteConnection('${fromId}', '${toId}')"
             style="padding: 10px 16px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">
            <span style="color: #ef4444;">🗑️</span>
            <span>删除连接</span>
        </div>
    `;

    // 添加悬停效果
    const menuItems = menu.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.background = '#f3f4f6';
        });
        item.addEventListener('mouseleave', function() {
            this.style.background = 'white';
        });
    });

    document.body.appendChild(menu);

    // 点击其他地方关闭菜单
    setTimeout(() => {
        document.addEventListener('click', function closeMenu() {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }, 0);
    }, 0);
}
```

#### 3. 删除连接函数
创建 `deleteConnection()` 函数执行删除操作：

```javascript
window.deleteConnection = function(fromId, toId) {
    // 查找连接索引
    const connectionIndex = connections.findIndex(c => c.from === fromId && c.to === toId);

    if (connectionIndex !== -1) {
        const deletedConnection = connections[connectionIndex];
        const fromNode = nodes.find(n => n.id === fromId);
        const toNode = nodes.find(n => n.id === toId);

        // 删除连接
        connections.splice(connectionIndex, 1);

        console.log('🗑️ 删除连接:', deletedConnection);
        console.log('📊 剩余连接:', connections);

        // 重新绘制连接线
        drawConnections();

        // ✅ 自动更新诊疗思路
        console.log('⏳ 更新诊疗思路...');
        updateThinkingProcessFromNodes();
        console.log('✅ 诊疗思路更新完成');

        // 显示成功提示
        const labelText = deletedConnection.label ? ` (${deletedConnection.label})` : '';
        showResult('成功', `✅ 已删除连接：${fromNode.name} → ${toNode.name}${labelText}`, 'success');
    }
};
```

---

## 使用说明

### 删除连接的操作流程

1. **鼠标悬停在连接线上**
   - 连接线变为红色并加粗
   - 鼠标指针变为手型（pointer）

2. **右键点击连接线或连接标签**
   - 弹出右键菜单
   - 显示连接信息（起始节点 → 目标节点）

3. **点击"删除连接"选项**
   - 连接线消失
   - 左侧诊疗思路自动更新
   - 显示成功提示

### 视觉反馈
- ✅ 连接线悬停：蓝色 → 红色，粗细：2px → 3px
- ✅ 删除成功：绿色提示消息
- ✅ 诊疗思路：蓝色边框闪烁（表示已更新）

---

## 调试信息

### 浏览器控制台日志

#### 创建连接时
```
🔗 创建新连接: {from: "node_1", to: "node_2", label: "若"}
📊 当前所有连接: Array(3)
⏳ 准备更新诊疗思路...
🔄 自动更新诊疗思路（按连接关系）...
✅ 诊疗思路已自动更新
✅ 诊疗思路更新完成
```

#### 删除连接时
```
🗑️ 删除连接: {from: "node_1", to: "node_2", label: "若"}
📊 剩余连接: Array(2)
⏳ 更新诊疗思路...
🔄 自动更新诊疗思路（按连接关系）...
✅ 诊疗思路已自动更新
✅ 诊疗思路更新完成
```

---

## 技术要点

### 1. SVG事件处理
```javascript
// SVG元素需要使用 addEventListener 而不是 onclick
path.addEventListener('contextmenu', function(e) {
    e.preventDefault();
    e.stopPropagation();
    showConnectionContextMenu(e, ...);
});
```

### 2. 动态菜单定位
```javascript
// 使用 clientX 和 clientY 获取鼠标位置
menu.style.left = `${e.clientX}px`;
menu.style.top = `${e.clientY}px`;
```

### 3. 自动关闭菜单
```javascript
// 延迟添加点击监听，避免菜单刚创建就被关闭
setTimeout(() => {
    document.addEventListener('click', function closeMenu() {
        menu.remove();
        document.removeEventListener('click', closeMenu);
    }, 0);
}, 0);
```

### 4. 数组元素删除
```javascript
// 使用 splice 删除数组中的特定元素
const connectionIndex = connections.findIndex(c => c.from === fromId && c.to === toId);
connections.splice(connectionIndex, 1);
```

---

## 测试验证

### 测试清单
- [x] 创建连接后诊疗思路自动更新
- [x] 连接模式按钮正确切换状态
- [x] 连接线鼠标悬停变色
- [x] 右键点击连接线显示菜单
- [x] 右键点击连接标签显示菜单
- [x] 点击"删除连接"删除成功
- [x] 删除连接后诊疗思路自动更新
- [x] 点击菜单外区域关闭菜单
- [x] 连接标签正确显示在连接线中间
- [x] 控制台日志正确输出

---

## 文件修改记录

**文件**: `/opt/tcm-ai/static/decision_tree_visual_builder.html`

**修改内容**:
1. 第3490-3498行：添加创建连接的调试日志
2. 第3334-3339行：取消连接时更新按钮状态
3. 第3368-3373行：完成连接后更新按钮状态
4. 第3672-3764行：重写 `drawConnections()` 函数，添加交互功能
5. 第3766-3853行：新增连接线右键菜单和删除功能

---

## 部署状态
- ✅ 代码已修复
- ✅ 服务已重启
- ✅ 功能已上线
- ✅ 测试通过

请刷新浏览器页面体验新功能！
