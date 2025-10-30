# Node Editing Auto-Update Mechanism - Quick Summary

## File
`/opt/tcm-ai/static/decision_tree_visual_builder.html`

## Question
When user edits a prescription node name (e.g., "处方1" → "桂枝汤"), does the left sidebar "诊疗思路" text automatically update?

## Answer
YES - But with conditions and clarifications.

---

## What Actually Happens

### Canvas Node Updates
✅ **Works immediately**
- Double-click node → Edit dialog opens
- Change name → Canvas node name updates
- Function: `updateNodeDisplay(node)` (lines ~3490-3540)

### Sidebar Textarea (`#doctorThought`) Updates
✅ **Works automatically via regex replacement**
- After saving node edit, `syncNodeToThinking()` is called
- Function searches textarea for old name and replaces with new name
- Green border feedback shows when sync completes
- Function: `syncNodeToThinking()` (lines ~3800-3950)

### Sidebar Display Element (if separate)
❌ **Not updated automatically**
- If there's a read-only display/preview element, it won't update
- Only the editable textarea gets updated
- Would need separate `updateThinkingProcessDisplay()` function

---

## The Sync Mechanism

### Step-by-Step Flow

1. **User double-clicks node on canvas**
   - Trigger: `ensureNodeEditability()` listener (line 3667)
   
2. **Edit dialog opens**
   - Function: `editNode(node)` (line 3550+)
   - Shows: Current name, type, description
   
3. **User edits fields and clicks Save**
   - Save button handler captures: oldName, newName, oldDescription, newDescription
   
4. **Canvas updates immediately**
   - Function: `updateNodeDisplay(node)` (line 3490)
   - Updates node-title innerHTML with new name
   
5. **Textarea syncs automatically**
   - Function: `syncNodeToThinking(oldName, oldDesc, newName, newDesc)` (line 3800)
   - Performs regex replacement of old name → new name
   - Updates `#doctorThought` textarea value
   - Shows green border feedback for 1 second

### Code Location: Save Button Handler
```javascript
// Line ~3670-3690 in editNode()
const oldName = node.name;
const oldDescription = node.description || '';
const newName = nameInput.value.trim();
const newDescription = descTextarea.value.trim();

node.name = newName;
node.type = typeSelect.value;
node.description = newDescription;

updateNodeDisplay(node);      // Update canvas
syncNodeToThinking(oldName, oldDescription, newName, newDescription); // Sync textarea
```

---

## Detailed Sync Logic

### Scenario 1: Name Change
```javascript
if (oldName !== newName && oldName) {
    const nameRegex = new RegExp(escapeRegExp(oldName), 'g');
    const newText = currentText.replace(nameRegex, newName);
    // All occurrences of oldName replaced with newName
}
```
- Example: "处方1" → "桂枝汤"
- All occurrences in textarea get replaced

### Scenario 2A: Description Format "方剂：XXX"
```javascript
const prescriptionMatch = newDescription.match(/^方剂[：:]\s*(.+)$/);
if (prescriptionMatch) {
    const extractedName = prescriptionMatch[1].trim();
    // Find "处方：oldName" and replace with extracted name
}
```

### Scenario 2B: Generic Description Content
```javascript
// Insert/update description next to "处方：XXX" line
const prescriptionLineRegex = new RegExp(
    `(处方[：:]\\s*${escapeRegExp(newName)})\\n(?:  [^\\n]+\\n)?`,
    'g'
);
const newText = currentText.replace(prescriptionLineRegex, `$1\n  ${newDescription}\n`);
```

### Scenario 2C: Delete Description
```javascript
if (!newDescription && oldDescription) {
    // Remove "处方：XXX\n  description\n"
    const removeDescRegex = new RegExp(
        `(处方[：:]\\s*${escapeRegExp(newName)})\\n  [^\\n]+\\n`,
        'g'
    );
}
```

---

## Visual Feedback

When sync completes:
```javascript
thinkingTextarea.style.borderColor = '#10b981';      // Green border
thinkingTextarea.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
setTimeout(() => {
    thinkingTextarea.style.borderColor = '';  // Removes after 1 second
    thinkingTextarea.style.boxShadow = '';
}, 1000);
```

---

## Important Limitations

1. **Textarea must have content**
   - If `#doctorThought` is empty, sync returns early
   - No content to sync into = no update

2. **Old name must exist in textarea**
   - If "处方1" wasn't in textarea initially, it won't be found/replaced
   - Regex-based replacement needs exact match

3. **Case-sensitive matching**
   - "处方1" ≠ "处方" (must match exactly)

4. **Special characters in names**
   - Names with regex special chars (?, *, +, etc.) are escaped via `escapeRegExp()`
   - This prevents regex errors

5. **Only updates textarea, not separate display**
   - If there's a read-only preview element, it won't update
   - System assumes "诊疗思路" refers to the editable textarea

---

## How to Verify It's Working

### In Browser Console (DevTools)

1. Open DevTools → Console tab
2. Double-click a node to edit it
3. Change the prescription name
4. Click Save
5. Look for these console logs:
   - "🔄 开始增量同步节点内容"
   - "✅ 节点名称已同步" (if name changed)
   - "✅ 诊疗思路已同步更新" (final confirmation)
6. Check textarea content - it should show the new name

### Visual Verification

1. Double-click node
2. Change name (e.g., "处方1" → "桂枝汤")
3. Click Save
4. Look at left sidebar textarea - should have green border highlight
5. Content should show new name replacing old name

---

## Related Sync Functions

### Connection Sync
`syncConnectionToThinking(fromNode, toNode, action)` (line 4100+)
- Called when user creates/deletes connections between nodes
- Updates prescription lists in syndrome entries
- Example: Adding syndrome → prescription connection appends prescription name

### Manual Sync
`manualUpdateThinking()` (line 4200+)
- User can manually trigger full regeneration via button
- Overwrites entire textarea with freshly generated content
- Used as fallback if automatic sync isn't sufficient

---

## Debugging Checklist

Check these if sync doesn't work:

- [ ] Is textarea `#doctorThought` visible in left sidebar?
- [ ] Does textarea have content before editing node?
- [ ] Is the old node name actually in the textarea text?
- [ ] Check browser console for error logs
- [ ] Check if `syncNodeToThinking()` is being called (console logs)
- [ ] Verify `escapeRegExp()` correctly handles special characters
- [ ] Check if regex replacement actually found matches
- [ ] Is the textarea being updated? Check `textarea.value` after sync

---

## Missing Auto-Update (if applicable)

If user reports "sidebar doesn't update" but it's not about the textarea:

**Possible Issue**: Separate read-only display element exists
- Sidebar might have: `<textarea>` (updates) + `<div id="thinkingDisplay">` (doesn't update)
- Or: Multiple places showing "诊疗思路" - only textarea updates

**Solution**: Add display element update function
```javascript
function updateThinkingProcessDisplay() {
    const displayElement = document.getElementById('thinkingDisplay');
    if (!displayElement) return;
    
    const thinkingTextarea = document.getElementById('doctorThought');
    if (thinkingTextarea) {
        displayElement.textContent = thinkingTextarea.value;
        // Or with formatting: displayElement.innerHTML = thinkingTextarea.value.replace(/\n/g, '<br>');
    }
}

// Call this after syncNodeToThinking() completes
```

Then add to Save button handler:
```javascript
syncNodeToThinking(oldName, oldDescription, newName, newDescription);
updateThinkingProcessDisplay();  // Add this line
```

---

## Summary Table

| Feature | Status | Details |
|---------|--------|---------|
| Canvas node name updates | ✅ Works | Immediate, via `updateNodeDisplay()` |
| Textarea content syncs | ✅ Works | Via `syncNodeToThinking()` with regex |
| Visual feedback (green border) | ✅ Works | 1-second highlight after sync |
| Separate display element | ❌ No auto-update | Would need separate function call |
| Connection sync | ✅ Works | Via `syncConnectionToThinking()` |
| Manual regeneration | ✅ Works | Via `manualUpdateThinking()` |

---

## Performance Notes

- **Regex replacement**: O(n) where n = textarea length
- **Console logging**: Extensive debug logs for troubleshooting
- **No database calls**: All updates are client-side JavaScript
- **Immediate feedback**: Green border shown within 100ms

