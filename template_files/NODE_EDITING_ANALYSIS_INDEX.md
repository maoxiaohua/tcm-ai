# Node Editing Analysis Documentation - Complete Index

## Overview
This documentation set provides a complete analysis of the node editing functionality and "诊疗思路" (thinking process) auto-update mechanism in the decision tree visual builder.

**File Being Analyzed**: `/opt/tcm-ai/static/decision_tree_visual_builder.html`

**Context**: User reported that when editing a prescription node name (e.g., "处方1" → "桂枝汤"), the left sidebar "诊疗思路" text doesn't automatically update.

---

## Documentation Files

### 1. NODE_EDITING_QUICK_SUMMARY.md
**Start here for quick answers**
- Direct answer to the question
- What actually happens (canvas vs textarea vs separate display)
- Step-by-step flow with code snippets
- Limitations and edge cases
- How to verify it works
- Debugging checklist

**Best for**: Getting quick answers, understanding basic flow, troubleshooting

---

### 2. NODE_EDITING_SIDEBAR_SYNC_ANALYSIS.md
**Deep dive into mechanisms**
- Comprehensive summary of auto-update status
- Complete implementation of each function
- What gets updated vs. what doesn't
- Sidebar HTML structure
- Issue analysis (user expectation vs. reality)
- Auto-update trigger chain diagram
- Related functions overview

**Best for**: Understanding the architecture, detailed implementation review, identifying missing pieces

---

### 3. NODE_EDITING_CODE_LOCATIONS.md
**Code reference with full snippets**
- Quick reference table of all functions and their line numbers
- Complete code snippets for each function
- Function explanations and key points
- Key data structures (Node object, textarea element)
- Function call chain diagram
- Important notes and debugging tips

**Best for**: Reading actual code, finding specific functions, understanding implementation details

---

## Key Findings Summary

### Auto-Update Status
✅ **AUTO-UPDATE EXISTS** - But with clarifications:

1. **Canvas Node Display**: Updates immediately ✅
   - Function: `updateNodeDisplay(node)` ~line 3490
   - When: After user saves node edit
   - Method: DOM innerHTML updates with new name

2. **Sidebar Textarea (`#doctorThought`)**: Updates automatically ✅
   - Function: `syncNodeToThinking()` ~line 3800
   - When: Right after `updateNodeDisplay()`
   - Method: Regex-based replacement of old name with new name
   - Feedback: Green border highlight for 1 second

3. **Separate Display Element**: NO auto-update ❌
   - If sidebar has read-only preview element, it won't update
   - Only the editable textarea gets synced
   - Would need additional `updateThinkingProcessDisplay()` call

---

## Critical Code Path

```
User Double-Clicks Canvas Node
    ↓
ensureNodeEditability() listener fires (line 3667)
    ↓
editNode(node) dialog opens (line 3550)
    ↓
User edits name/type/description and clicks Save
    ↓
Save Button Handler (line 3670-3690):
  1. Captures: oldName, oldDescription
  2. Updates: node.name, node.type, node.description
  3. Calls: updateNodeDisplay(node)
  4. Calls: syncNodeToThinking(oldName, oldDesc, newName, newDesc)
    ↓
updateNodeDisplay(node) (line 3490):
  - Updates .node-title innerHTML with icon + new name
  - Updates .node-content with description
  - Updates related symptoms
    ↓
syncNodeToThinking() (line 3800):
  - Gets textarea #doctorThought
  - Replaces all oldName occurrences with newName (regex)
  - Handles 3 description change scenarios
  - Updates textarea.value
  - Shows green border feedback for 1 second
    ↓
Done - Both canvas and textarea updated
```

---

## The Three Sync Scenarios

When node description changes, `syncNodeToThinking()` handles three cases:

### Scenario 1: Name Change
```javascript
oldName !== newName → Replace all oldName with newName in textarea
Example: "处方1" → "桂枝汤"
```

### Scenario 2A: Description Format "方剂：XXX"
```javascript
newDescription matches /^方剂[：:]\s*(.+)$/ 
→ Extract prescription name and update "处方：X" line
```

### Scenario 2B: Generic Description Content
```javascript
newDescription is regular content
→ Insert/update description next to "处方：XXX" line
Pattern: "处方：名\n  描述\n"
```

### Scenario 2C: Delete Description
```javascript
oldDescription exists but newDescription is empty
→ Remove "处方：名\n  描述\n" line
```

---

## Important Limitations

1. **Textarea must have content**
   - If empty, sync returns early
   - No existing text = nothing to replace

2. **Old name must exist in textarea**
   - Regex looks for exact match
   - If "处方1" wasn't in textarea initially, won't be found

3. **Case-sensitive matching**
   - "处方1" ≠ "处方"
   - Must match exactly

4. **Special characters need escaping**
   - Names with ? * + $ etc. are escaped via `escapeRegExp()`
   - Prevents regex syntax errors

5. **Only updates textarea, not separate elements**
   - If sidebar has multiple display locations, only textarea syncs
   - Other elements would need separate update calls

---

## How to Verify It Works

### Browser Console Method
1. Open DevTools → Console
2. Double-click a node
3. Change the name
4. Click Save
5. Look for console logs:
   - "🔄 开始增量同步节点内容"
   - "✅ 节点名称已同步"
   - "✅ 诊疗思路已同步更新"

### Visual Method
1. Double-click node
2. Change name (e.g., "处方1" → "桂枝汤")
3. Click Save
4. Check left sidebar textarea
5. Should see: Green border highlight + updated content

---

## Functions Reference

| Function | Line | Purpose |
|----------|------|---------|
| `ensureNodeEditability()` | ~3667 | Attach double-click handler to nodes |
| `editNode()` | ~3550 | Open edit dialog with form |
| `updateNodeDisplay()` | ~3490 | Update canvas node display |
| `syncNodeToThinking()` | ~3800 | Auto-sync textarea with edited node |
| `syncConnectionToThinking()` | ~4100 | Sync connection relationships |
| `escapeRegExp()` | ~3950 | Helper: escape regex special chars |
| `manualUpdateThinking()` | ~4200 | Manual regeneration option |

---

## Sidebar HTML Structure

```html
<div class="sidebar">
    <div class="section-title">🏥 基本信息</div>
    
    <div class="form-group">
        <label class="form-label">疾病名称</label>
        <input type="text" id="diseaseName">
    </div>
    
    <div class="form-group">
        <label class="form-label">诊疗思路</label>
        <textarea id="doctorThought" class="form-textarea"></textarea>
    </div>
</div>
```

**Key Element**: `#doctorThought` textarea
- This is what gets auto-updated via `syncNodeToThinking()`
- Only element that receives sync updates

---

## Related Functionality

### Connection Sync
`syncConnectionToThinking(fromNode, toNode, action)`
- Called when user creates/deletes node connections
- Manages syndrome → prescription relationships
- Appends/removes prescriptions in syndrome entries

### Manual Regeneration
`manualUpdateThinking()`
- User-triggered full regeneration
- Asks for confirmation (existing content will be overwritten)
- Useful if automatic sync insufficient

---

## Possible Issues & Solutions

### Problem: Textarea doesn't update after editing node

**Checklist**:
1. Is textarea `#doctorThought` visible? If not, that's the issue
2. Does textarea have content before editing? (Empty textarea = early return)
3. Is the old node name actually in the textarea? (Must exist for regex replacement)
4. Check browser console for errors
5. Check if `syncNodeToThinking()` logs appear
6. Verify regex replacement found matches

### Problem: Separate display element doesn't update

**Solution**:
1. Create new function:
```javascript
function updateThinkingProcessDisplay() {
    const displayElement = document.getElementById('thinkingDisplay');
    if (!displayElement) return;
    
    const thinkingTextarea = document.getElementById('doctorThought');
    if (thinkingTextarea) {
        displayElement.textContent = thinkingTextarea.value;
    }
}
```

2. Call after `syncNodeToThinking()`:
```javascript
syncNodeToThinking(oldName, oldDescription, newName, newDescription);
updateThinkingProcessDisplay();  // Add this
```

---

## Visual Feedback Mechanism

When sync completes successfully:

```javascript
// Green border appears
thinkingTextarea.style.borderColor = '#10b981';
thinkingTextarea.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';

// Reverts after 1 second
setTimeout(() => {
    thinkingTextarea.style.borderColor = '';
    thinkingTextarea.style.boxShadow = '';
}, 1000);
```

User sees: **Green border around textarea for 1 second** → Indicates successful sync

---

## Testing Scenarios

### Test 1: Simple Name Change
1. Create a prescription node named "处方1"
2. Generate thinking process with "处方1" mentioned
3. Edit node name to "桂枝汤"
4. Verify: Textarea should show "桂枝汤" instead of "处方1"

### Test 2: Name with Special Characters
1. Create node "处方?"
2. Edit to "处方A"
3. Verify: Regex escape works, replacement succeeds

### Test 3: Empty Textarea
1. Create node
2. Don't generate thinking process (textarea empty)
3. Edit node name
4. Verify: No sync occurs (expected - nothing to sync into)

### Test 4: Multiple Occurrences
1. Thinking process mentions "处方1" multiple times
2. Edit to "桂枝汤"
3. Verify: ALL occurrences get replaced

---

## Performance Characteristics

- **Regex replacement**: O(n) where n = textarea character count
- **Visual feedback**: Appears within ~100ms
- **No database calls**: All client-side JavaScript
- **Console overhead**: Extensive logging for debugging (can be disabled)

---

## Console Debug Output

When node editing occurs, these messages appear:

```
🔄 开始增量同步节点内容
  旧名称: 处方1
  新名称: 桂枝汤
  旧描述: (empty)
  新描述: (empty)
  当前诊疗思路文本（前200字符）: ...

📝 尝试同步名称...
  查找: 处方1
  替换为: 桂枝汤

✅ 节点名称已同步
  更新后文本（前200字符）: ...

✅ 诊疗思路已同步更新
```

---

## Quick Decision Tree

**Does textarea `#doctorThought` get updated when I edit a node?**
- YES ✅ (via `syncNodeToThinking()` function)

**Does it work immediately?**
- YES ✅ (happens right after Save button click)

**Do I need to do anything special?**
- NO ❌ (automatic, no user action needed)

**What if it doesn't work?**
- Check: Is textarea empty? (sync won't work on empty textarea)
- Check: Is old name in textarea? (must exist for regex to find it)
- Check: Browser console logs (look for sync messages)

**What if I have a separate display element?**
- That won't update automatically ❌
- Need to add separate update function call

---

## References

**File**: `/opt/tcm-ai/static/decision_tree_visual_builder.html`

**Key Functions**:
- `ensureNodeEditability()` - Line 3667
- `editNode()` - Line 3550
- `updateNodeDisplay()` - Line 3490
- `syncNodeToThinking()` - Line 3800
- `escapeRegExp()` - Line 3950
- `syncConnectionToThinking()` - Line 4100
- `manualUpdateThinking()` - Line 4200

**Related Files**: None (self-contained HTML file)

---

## Document Version
- Created: 2025-10-30
- Analysis Scope: Complete node editing and auto-update mechanism
- Accuracy: High (based on actual code review)
- Completeness: Comprehensive

