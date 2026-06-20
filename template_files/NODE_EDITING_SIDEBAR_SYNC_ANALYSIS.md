# Node Editing and Sidebar "诊疗思路" Auto-Update Analysis
## File: `/opt/tcm-ai/static/decision_tree_visual_builder.html`

---

## Summary

The node editing functionality in the decision tree builder **HAS** a synchronization mechanism (`syncNodeToThinking`), but it **ONLY UPDATES THE TEXTAREA VALUE** (`#doctorThought`), not a separate "sidebar display" element. 

**Current Problem**: When user edits a prescription node name (e.g., "处方1" → "桂枝汤"), the left sidebar textarea gets updated, but users may expect a real-time "preview" or "display-only" element to also update.

---

## Current Node Editing Implementation

### 1. Node Editing Entry Point: `ensureNodeEditability()`
**Location**: Line ~3667
**Purpose**: Attach double-click event handler to node elements

```javascript
function ensureNodeEditability(nodeElement, node) {
    // 移除旧的双击事件监听器（如果存在）
    const existingHandler = nodeElement._editHandler;
    if (existingHandler) {
        nodeElement.removeEventListener('dblclick', existingHandler);
    }
    
    // 创建新的事件处理函数 - 统一使用对话框编辑
    const newHandler = function(e) {
        e.stopPropagation();
        e.preventDefault();
        // 直接查找最新的节点数据
        const currentNode = nodes.find(n => n.id === node.id) || node;
        editNode(currentNode); // 使用统一的对话框编辑
    };
    
    // 保存事件处理器引用以便后续移除
    nodeElement._editHandler = newHandler;
    
    // 添加双击编辑功能
    nodeElement.addEventListener('dblclick', newHandler);
    
    // 标记为已绑定编辑事件
    nodeElement.setAttribute('data-editable', 'true');
}
```

**Key Points**:
- Double-click trigger
- Opens dialog for editing
- Calls `editNode()` function

---

### 2. Node Edit Dialog: `editNode(node)`
**Triggered by**: Double-clicking on canvas node
**What it does**:
1. Creates an overlay and dialog box
2. Populates form with current node data:
   - `node.name` (节点名称)
   - `node.type` (节点类型)
   - `node.description` (节点描述)
3. Provides "Save" and "Cancel" buttons

**Save Button Handler** (Key Logic):
```javascript
document.getElementById('saveNodeEdit').onclick = function() {
    const nameInput = document.getElementById('editNodeName');
    const typeSelect = document.getElementById('editNodeType');
    const descTextarea = document.getElementById('editNodeDesc');
    
    // 验证输入
    if (!nameInput.value.trim()) {
        // validation error
        return;
    }
    
    // 保存旧数据用于同步
    const oldName = node.name;
    const oldDescription = node.description || '';
    const newName = nameInput.value.trim();
    const newDescription = descTextarea.value.trim();
    
    // 更新节点数据
    node.name = newName;
    node.type = typeSelect.value;
    node.description = newDescription;
    
    // 更新显示
    const nodeElement = document.getElementById(node.id);
    nodeElement.className = `node ${node.type}`;
    updateNodeDisplay(node);
    
    closeDialog();
    showResult('成功', '✅ 节点信息已更新', 'success');
    
    // ✨ 增量同步：更新诊疗思路中对应的文字
    syncNodeToThinking(oldName, oldDescription, newName, newDescription);
    
    // 移除ESC监听器
    document.removeEventListener('keydown', escapeHandler);
};
```

---

### 3. Canvas Display Update: `updateNodeDisplay(node)`
**Purpose**: Updates the visual representation of the node on canvas

```javascript
function updateNodeDisplay(node) {
    const nodeElement = document.getElementById(node.id);
    if (!nodeElement) return;
    
    // 🆕 更新节点标题（节点名称）
    const titleDiv = nodeElement.querySelector('.node-title');
    if (titleDiv) {
        // 保留图标，只更新文字
        const typeIcons = {
            'disease': '🔬',
            'four_diagnosis': '👁',
            'symptom': '📋',
            'pathogenesis': '⚡',
            'syndrome': '🎯',
            'syndrome_branch': '🎯',
            'principle': '📏',
            'prescription': '📝',
            'modification': '🔄',
            'prognosis': '💚'
        };
        const nodeIcon = typeIcons[node.type] || '📄';
        titleDiv.innerHTML = `<span class="node-type-icon">${nodeIcon}</span>${node.name}`;
    }
    
    const contentDiv = nodeElement.querySelector('.node-content');
    if (!contentDiv) return;
    
    // Updates node content with description and related symptoms
    // ... rest of implementation
}
```

**Current Behavior**:
- Updates node element's HTML to show new name
- Updates node element's class based on type
- Updates related symptoms display

---

### 4. Sidebar Textarea Synchronization: `syncNodeToThinking()`
**Purpose**: Auto-update the `#doctorThought` textarea when node is edited
**Triggered by**: Save button in edit dialog (after `updateNodeDisplay()`)

#### Complete Implementation:

```javascript
function syncNodeToThinking(oldName, oldDescription, newName, newDescription) {
    const thinkingTextarea = document.getElementById('doctorThought');
    if (!thinkingTextarea) {
        console.log('⚠️ 未找到诊疗思路输入框');
        return;
    }
    
    let currentText = thinkingTextarea.value;
    if (!currentText || currentText.trim() === '') {
        console.log('💡 诊疗思路为空，无需同步');
        return;
    }
    
    console.log('🔄 开始增量同步节点内容');
    let updated = false;
    
    // 1. 同步名称（如果名称改变）
    if (oldName !== newName && oldName) {
        console.log('📝 尝试同步名称...');
        const nameRegex = new RegExp(escapeRegExp(oldName), 'g');
        const newText = currentText.replace(nameRegex, newName);
        if (newText !== currentText) {
            currentText = newText;
            updated = true;
            console.log('✅ 节点名称已同步');
        }
    }
    
    // 2. 同步描述内容（如果描述改变）
    if (oldDescription !== newDescription) {
        console.log('📝 尝试同步描述内容...');
        
        // 场景1: 描述是"方剂：XXX"格式，提取处方名称
        const prescriptionMatch = newDescription.match(/^方剂[：:]\s*(.+)$/);
        if (prescriptionMatch) {
            const extractedName = prescriptionMatch[1].trim();
            // 在诊疗思路中查找"处方：旧名称"并替换
            const oldPattern = new RegExp(`(处方[：:]\\s*)${escapeRegExp(oldName)}(\\s*(?:\\n|$))`, 'g');
            const newText = currentText.replace(oldPattern, `$1${extractedName}$2`);
            if (newText !== currentText) {
                currentText = newText;
                updated = true;
                console.log('✅ 处方名称已同步');
            }
        }
        // 场景2: 描述是普通内容（药物组成、剂量等），插入或更新
        else {
            // ... complex logic for inserting/updating descriptions
            // Using regex patterns to match prescription lines
        }
        // 场景3: 删除描述（新描述为空）
        else if (!newDescription && oldDescription) {
            // ... logic for removing descriptions
        }
    }
    
    // Final step: Update textarea and provide visual feedback
    if (updated) {
        thinkingTextarea.value = currentText;
        console.log('✅ 诊疗思路已同步更新');
        
        // 视觉反馈
        thinkingTextarea.style.borderColor = '#10b981';
        thinkingTextarea.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
        setTimeout(() => {
            thinkingTextarea.style.borderColor = '';
            thinkingTextarea.style.boxShadow = '';
        }, 1000);
    } else {
        console.log('💡 诊疗思路中未找到可同步的内容');
    }
}
```

#### Three Synchronization Scenarios:

1. **Name Synchronization**: 
   - Regex replaces ALL occurrences of old name with new name
   - Example: "处方1" → "桂枝汤"

2. **Prescription Description Sync**:
   - **Sub-scenario A**: If description is "方剂：XXX" format, extract and update "处方：XXX" lines
   - **Sub-scenario B**: If description is generic content, insert/update it next to "处方：XXX" lines
   - **Sub-scenario C**: If description is removed, delete corresponding description line

3. **Connection Relationship Sync** (separate function):
   - Updates prescription lists when nodes are connected/disconnected
   - Uses pattern matching to find and update syndrome→prescription relationships

---

## What Gets Updated Automatically

### Currently Working:
1. **Canvas Node Display**: Node name, type, description updated on canvas
2. **Textarea (`#doctorThought`)**: Content is synchronized when node is edited

### Not Automatically Updated:
- **Sidebar "诊疗思路" Preview/Display**: If there's a separate read-only display element, it won't auto-update

---

## Sidebar Structure

**HTML Sidebar** (from line ~100+):
```html
<!-- 左侧工具栏 -->
<div class="sidebar">
    <!-- 基本信息 -->
    <div class="section-title">🏥 基本信息</div>
    <div class="form-group">
        <label class="form-label">疾病名称</label>
        <input type="text" class="form-input" id="diseaseName" placeholder="如：失眠、胃痛、头痛">
    </div>
    <div class="form-group">
        <label class="form-label">诊疗思路</label>
        <textarea class="form-input form-textarea" id="doctorThought" placeholder="简述您的诊疗思路..."></textarea>
    </div>
    <!-- More sections... -->
</div>
```

**Key Element**: `#doctorThought` textarea (EDITABLE)
- This DOES get auto-updated via `syncNodeToThinking()`
- Provides visual feedback (green border + shadow) when updated

---

## Issue Analysis

### User Expectation vs. Reality

**User reports**: "When I edit prescription node name from '处方1' to '桂枝汤', the left sidebar '诊疗思路' text doesn't automatically update"

**What actually happens**:
1. Node name on canvas IS updated ✅
2. Textarea content IS synchronized ✅
3. If there's a separate **display-only** element showing "诊疗思路", it won't update ❌

### Possible Causes:
1. User is looking at a different element (not the textarea)
2. The textarea sync only works if there's existing text to match against
3. If "处方1" wasn't in the textarea initially, there's nothing to replace

---

## Auto-Update Trigger Chain

```
User Double-clicks Node on Canvas
    ↓
ensureNodeEditability() fires (dblclick handler)
    ↓
editNode(node) opens dialog
    ↓
User edits fields and clicks Save
    ↓
updateNodeDisplay(node) - Updates canvas
    ↓
syncNodeToThinking(oldName, oldDesc, newName, newDesc)
    ↓
Textarea #doctorThought gets updated with regex replacements
    ↓
Visual feedback (green border) shown to user
```

---

## How to Add Missing Auto-Update (If Needed)

If there's a separate display element for "诊疗思路" that's NOT the textarea, you would need to:

1. **Find the display element** (if it exists):
   - Likely has `id="thinkingDisplay"` or similar
   - Located in sidebar
   - Shows as read-only or preview format

2. **Add update call after sync**:
   ```javascript
   // After syncNodeToThinking() completes
   updateThinkingProcessDisplay();
   ```

3. **Create the display update function**:
   ```javascript
   function updateThinkingProcessDisplay() {
       const displayElement = document.getElementById('thinkingDisplay');
       if (!displayElement) return;
       
       const thinkingTextarea = document.getElementById('doctorThought');
       if (thinkingTextarea) {
           displayElement.textContent = thinkingTextarea.value;
           // Or apply formatting
           displayElement.innerHTML = thinkingTextarea.value.replace(/\n/g, '<br>');
       }
   }
   ```

---

## Related Functions

### Helper Function: `escapeRegExp()`
```javascript
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
```
Used to safely escape special regex characters in node names

### Connection Sync: `syncConnectionToThinking()`
Separate function (also in same file) that syncs connection relationships:
- Handles syndrome → prescription connections
- Supports adding/deleting connections
- Uses similar pattern matching approach

### Manual Update: `manualUpdateThinking()`
Function that regenerates entire thinking process from scratch:
- Prompted by user confirmation dialog
- Overwrites existing textarea content
- Used when automatic sync isn't sufficient

---

## Conclusion

**Auto-Update Status**: ✅ **EXISTS**
- Node canvas display updates immediately
- Textarea `#doctorThought` is synchronized automatically
- Visual feedback provided (green highlight)

**What might be missing**:
- If sidebar has a separate **display/preview** element, it won't update
- Function `updateThinkingProcessDisplay()` would need to be called
- Check browser console for sync logs (search for "诊疗思路已同步更新")

**How to verify**:
1. Open browser DevTools Console
2. Double-click a node to edit it
3. Change the name/description
4. Look for logs: "✅ 诊疗思路已同步更新"
5. Check textarea content to confirm sync worked
6. If sidebar display doesn't update, that's the missing piece

