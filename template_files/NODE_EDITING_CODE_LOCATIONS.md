# Node Editing Functions - Code Locations & Snippets
## File: `/opt/tcm-ai/static/decision_tree_visual_builder.html`

---

## Quick Reference: Function Locations

| Function | Approx Line | Purpose |
|----------|------------|---------|
| `ensureNodeEditability()` | 3667 | Attach double-click handler to nodes |
| `editNode()` | 3550+ | Open edit dialog |
| `updateNodeDisplay()` | 3490+ | Update canvas node display |
| `syncNodeToThinking()` | 3800+ | Auto-sync textarea with edited node |
| `syncConnectionToThinking()` | 4100+ | Sync connection relationships |
| `escapeRegExp()` | 3950+ | Helper for regex escaping |
| `manualUpdateThinking()` | 4200+ | Manual full regeneration |

---

## Complete Code Snippets

### Function 1: ensureNodeEditability() - Lines ~3667-3690

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
- Triggered: When node is created/recreated
- Event: Double-click on node element
- Action: Calls `editNode(currentNode)`
- Data tracking: Stores handler reference to allow cleanup

---

### Function 2: editNode() - Lines ~3550-3760 (Partial)

```javascript
function editNode(node) {
    // 创建遮罩层
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        z-index: 9999;
        backdrop-filter: blur(2px);
        animation: fadeIn 0.2s ease-out;
    `;
    
    // 创建编辑对话框
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 0;
        border-radius: 12px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        z-index: 10000;
        width: 480px;
        max-width: 90vw;
        max-height: 80vh;
        overflow: hidden;
        animation: slideIn 0.3s ease-out;
    `;
    
    // ... Dialog HTML with form fields ...
    
    // KEY: Save button handler (around line 3670-3690)
    document.getElementById('saveNodeEdit').onclick = function() {
        const nameInput = document.getElementById('editNodeName');
        const typeSelect = document.getElementById('editNodeType');
        const descTextarea = document.getElementById('editNodeDesc');
        
        // 验证输入
        if (!nameInput.value.trim()) {
            nameInput.focus();
            nameInput.style.borderColor = '#ef4444';
            setTimeout(() => nameInput.style.borderColor = '#e5e7eb', 2000);
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
    
    // ... Cancel button, ESC key handler, etc ...
}
```

**Critical Section**: Save button handler
- Line: Gets old values (oldName, oldDescription)
- Updates: node.name, node.type, node.description
- Display: Calls `updateNodeDisplay(node)`
- Sync: Calls `syncNodeToThinking(oldName, oldDescription, newName, newDescription)`

---

### Function 3: updateNodeDisplay() - Lines ~3490-3540

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
    
    // 清理描述内容，移除已有的相关症状HTML
    let cleanDescription = node.description || '';
    // 移除之前添加的相关症状HTML，防止重复
    cleanDescription = cleanDescription.replace(/<div class="related-symptoms">[\s\S]*?<\/div>/g, '');
    
    // 重新构建内容
    let nodeContent = cleanDescription;
    if (node.relatedSymptoms && node.relatedSymptoms.length > 0) {
        nodeContent = `${nodeContent}
            <div class="related-symptoms">
                <div class="symptoms-label">相关症状:</div>
                <div class="symptoms-list">${node.relatedSymptoms.join(', ')}</div>
            </div>`;
    }
    
    // ... More content updates ...
}
```

**Canvas Update Chain**:
1. Updates node-title innerHTML with icon + new name
2. Updates node-content with description
3. Updates related symptoms
4. Happens BEFORE syncNodeToThinking()

---

### Function 4: syncNodeToThinking() - Lines ~3800-3950 (Complete)

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
    console.log('  旧名称:', oldName);
    console.log('  新名称:', newName);
    console.log('  旧描述:', oldDescription);
    console.log('  新描述:', newDescription);
    console.log('  当前诊疗思路文本（前200字符）:', currentText.substring(0, 200));
    
    let updated = false;
    
    // ========== SCENARIO 1: Sync Name Change ==========
    if (oldName !== newName && oldName) {
        console.log('📝 尝试同步名称...');
        console.log('  查找:', oldName);
        console.log('  替换为:', newName);
        const nameRegex = new RegExp(escapeRegExp(oldName), 'g');
        const newText = currentText.replace(nameRegex, newName);
        if (newText !== currentText) {
            currentText = newText;
            updated = true;
            console.log('✅ 节点名称已同步');
            console.log('  更新后文本（前200字符）:', currentText.substring(0, 200));
        } else {
            console.log('⚠️ 在诊疗思路中未找到"' + oldName + '"');
        }
    } else {
        console.log('ℹ️ 名称未改变，跳过名称同步');
    }
    
    // ========== SCENARIO 2: Sync Description Change ==========
    if (oldDescription !== newDescription) {
        console.log('📝 尝试同步描述内容...');
        console.log('  当前节点名称:', newName);
        
        // 🔍 智能处理描述内容
        if (newDescription && newDescription.trim()) {
            // SCENARIO 2A: Description is "方剂：XXX" format - extract prescription name
            const prescriptionMatch = newDescription.match(/^方剂[：:]\s*(.+)$/);
            if (prescriptionMatch) {
                const extractedName = prescriptionMatch[1].trim();
                console.log('  场景1: 提取到处方名称:', extractedName);
                
                // Find "处方：oldName" and replace with extracted name
                const oldPattern = new RegExp(`(处方[：:]\\s*)${escapeRegExp(oldName)}(\\s*(?:\\n|$))`, 'g');
                const newText = currentText.replace(oldPattern, `$1${extractedName}$2`);
                if (newText !== currentText) {
                    currentText = newText;
                    updated = true;
                    console.log('✅ 处方名称已同步');
                }
            }
            // SCENARIO 2B: Generic description content - insert/update next to prescription line
            else {
                console.log('  场景2: 处理描述内容，准备插入/更新');
                
                // Pattern: "处方：处方名\n(  旧描述内容\n)?"
                const prescriptionLineRegex = new RegExp(
                    `(处方[：:]\\s*${escapeRegExp(newName)})\\n(?:  [^\\n]+\\n)?`,
                    'g'
                );
                
                // Replace with: "处方：处方名\n  新描述内容\n"
                const newText = currentText.replace(
                    prescriptionLineRegex,
                    `$1\n  ${newDescription}\n`
                );
                
                if (newText !== currentText) {
                    currentText = newText;
                    updated = true;
                    console.log('✅ 处方描述已更新/插入');
                } else {
                    // Fallback: Try simple insert pattern if not found
                    const simpleInsertRegex = new RegExp(
                        `(处方[：:]\\s*${escapeRegExp(newName)})(\\s*\\n)`,
                        'g'
                    );
                    const newText2 = currentText.replace(
                        simpleInsertRegex,
                        `$1\n  ${newDescription}$2`
                    );
                    if (newText2 !== currentText) {
                        currentText = newText2;
                        updated = true;
                        console.log('✅ 处方描述已插入（简单模式）');
                    }
                }
            }
        }
        // SCENARIO 2C: Description removed (new description is empty)
        else if (!newDescription && oldDescription) {
            console.log('  场景3: 删除描述内容');
            
            // Find and remove "处方：XXX\n  description\n"
            const removeDescRegex = new RegExp(
                `(处方[：:]\\s*${escapeRegExp(newName)})\\n  [^\\n]+\\n`,
                'g'
            );
            const newText = currentText.replace(removeDescRegex, '$1\n');
            if (newText !== currentText) {
                currentText = newText;
                updated = true;
                console.log('✅ 处方描述已删除');
            }
        }
    }
    
    // ========== FINAL STEP: Update Textarea ==========
    if (updated) {
        thinkingTextarea.value = currentText;
        console.log('✅ 诊疗思路已同步更新');
        
        // Visual feedback
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

**Execution Flow**:
1. Gets textarea element
2. Gets current text from textarea
3. If empty → early return
4. Compares oldName vs newName → replace all occurrences
5. Compares oldDescription vs newDescription → handle 3 scenarios
6. Updates textarea.value if changes made
7. Shows visual feedback (green border)

**Visual Feedback Code**:
```javascript
thinkingTextarea.style.borderColor = '#10b981';        // Green
thinkingTextarea.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';  // Green shadow
setTimeout(() => {
    thinkingTextarea.style.borderColor = '';
    thinkingTextarea.style.boxShadow = '';
}, 1000);  // Resets after 1 second
```

---

### Function 5: escapeRegExp() Helper - Lines ~3950

```javascript
// 辅助函数：转义正则表达式特殊字符
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
```

**Purpose**: Safely escapes special regex characters
- Example: "处方?" → "处方\\?"
- Used in all regex patterns in sync functions
- Prevents regex syntax errors when node names contain special chars

---

### Function 6: syncConnectionToThinking() - Lines ~4100-4280 (Partial)

```javascript
// 连接关系同步：智能更新证候对应的处方
function syncConnectionToThinking(fromNode, toNode, action) {
    const thinkingTextarea = document.getElementById('doctorThought');
    if (!thinkingTextarea || !fromNode || !toNode) {
        return;
    }
    
    let currentText = thinkingTextarea.value;
    if (!currentText || currentText.trim() === '') {
        console.log('💡 诊疗思路为空，无需同步连接关系');
        return;
    }
    
    console.log('🔗 开始同步连接关系');
    console.log('  从:', fromNode.name, `(${fromNode.type})`);
    console.log('  到:', toNode.name, `(${toNode.type})`);
    console.log('  操作:', action === 'add' ? '创建连接' : '删除连接');
    
    let updated = false;
    
    // Scenario: syndrome/syndrome_branch → prescription
    if ((fromNode.type === 'syndrome' || fromNode.type === 'syndrome_branch') && toNode.type === 'prescription') {
        console.log('📝 检测到证候-处方连接，尝试更新...');
        
        const syndromePattern = new RegExp(
            `(【证候\\d+】${escapeRegExp(fromNode.name)}[\\s\\S]*?处方[：:]\\s*)([^\\n]*)(\\n)`,
            'g'
        );
        
        if (action === 'add') {
            // Add: Append prescription (with 、 separator)
            const newText = currentText.replace(syndromePattern, (match, prefix, currentPrescriptions, newline) => {
                const trimmed = currentPrescriptions.trim();
                if (!trimmed) {
                    return `${prefix}${toNode.name}${newline}`;
                } else if (!trimmed.includes(toNode.name)) {
                    return `${prefix}${trimmed}、${toNode.name}${newline}`;
                } else {
                    return match;
                }
            });
            
            if (newText !== currentText) {
                currentText = newText;
                updated = true;
            }
        } else if (action === 'delete') {
            // Delete: Remove prescription from list
            const newText = currentText.replace(syndromePattern, (match, prefix, currentPrescriptions, newline) => {
                const prescriptionList = currentPrescriptions.trim().split(/[、，,\s]+/).filter(p => p.trim());
                const updatedList = prescriptionList.filter(p => p.trim() !== toNode.name);
                const newPrescriptions = updatedList.join('、');
                return `${prefix}${newPrescriptions}${newline}`;
            });
            
            if (newText !== currentText) {
                currentText = newText;
                updated = true;
            }
        }
    }
    
    // ... More scenarios ...
    
    if (updated) {
        thinkingTextarea.value = currentText;
        console.log('✅ 连接关系已同步到诊疗思路');
        // Visual feedback
        thinkingTextarea.style.borderColor = '#10b981';
        thinkingTextarea.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
        setTimeout(() => {
            thinkingTextarea.style.borderColor = '';
            thinkingTextarea.style.boxShadow = '';
        }, 1000);
    }
}
```

**Called When**: User creates/deletes connection between nodes
**Handles**: Adding/removing prescriptions from syndrome entries
**Uses**: Same textarea sync pattern as `syncNodeToThinking()`

---

## Function Call Chain for Node Editing

```
User Double-Clicks Node
    ↓
ensureNodeEditability() listener fires
    ↓
editNode(node) dialog opens
    ↓
User fills form and clicks Save
    ↓
Save button onclick handler:
    - Gets oldName, oldDescription
    - Updates node.name/type/description
    - Calls updateNodeDisplay(node)
    - Calls closeDialog()
    - Shows success toast
    - Calls syncNodeToThinking(oldName, oldDesc, newName, newDesc)
    ↓
syncNodeToThinking():
    - Gets textarea
    - Replaces old name with new name (scenario 1)
    - Handles description changes (scenarios 2A/2B/2C)
    - Updates textarea.value
    - Shows green highlight feedback
    ↓
Edit complete - both canvas and textarea updated
```

---

## Key Data Structures

### Node Object
```javascript
{
    id: "node_1234567890",
    type: "prescription",      // disease, four_diagnosis, symptom, syndrome, etc.
    name: "桂枝汤",            // Updated by editNode()
    description: "组成：桂枝...",
    x: 450,                    // Position on canvas
    y: 200,
    relatedSymptoms: ["发热", "恶寒"],
    createdTime: 1234567890
}
```

### Textarea Element
```html
<textarea 
    class="form-input form-textarea" 
    id="doctorThought" 
    placeholder="简述您的诊疗思路..."
></textarea>
```

Content format (after AI generation):
```
【疾病】失眠
  病因：心脾两虚

【四诊】
  问诊：患者入睡困难，易醒，心烦

【证候1】心脾气虚
  处方：酸枣仁汤

【证候2】...
```

---

## Important Notes

1. **Sync only works if textarea has content**: If `#doctorThought` is empty, `syncNodeToThinking()` returns early
2. **Regex-based replacement**: Old name must appear in textarea for sync to work
3. **Case-sensitive**: "处方1" ≠ "处方" (exact match required)
4. **Special characters**: Are escaped via `escapeRegExp()` before regex use
5. **Visual feedback**: 1-second green highlight to indicate sync success
6. **No separate display**: System only updates the textarea, not a separate display element

---

## Debugging Tips

1. **Check console logs**: Look for "诊疗思路已同步更新" message
2. **Check textarea**: See if content actually updated
3. **Verify old name exists**: If "处方1" not in textarea, won't sync
4. **Check escapeRegExp()**: If name has special chars, they should be escaped
5. **Use DevTools**: Set breakpoint in syncNodeToThinking() to trace execution

