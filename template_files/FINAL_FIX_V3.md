# 对话隔离系统最终修复 - v3.0

## 🔍 发现的核心问题

通过分析Console日志和代码，找到了两个严重的问题：

### 问题1：前端自动恢复UI导致混乱

**位置**: `smart_workflow_history.js` 第413-453行

**问题描述**:
- `syncHistoryFromDatabase`函数在页面加载时自动恢复最近的对话到UI
- 并且会自动切换医生：`selectDoctor(latestConsultation.doctor_id)`
- 这导致用户手动切换医生时，UI显示混乱

**实际影响**:
```
页面加载 → syncHistoryFromDatabase执行
→ 自动恢复金大夫的对话（4条消息）到UI
→ 自动切换到金大夫

用户手动切换到张仲景
→ ConversationManager加载张仲景历史（2条消息）
→ 但UI上已经有金大夫的4条消息
→ 结果：页面显示混乱，消息混杂
```

**修复方案**:
删除自动恢复UI的逻辑，改为：
- 数据库历史记录只保存到ConversationManager
- UI恢复由用户主动切换医生时触发
- 避免自动切换医生造成混乱

### 问题2：后端consultation查重逻辑错误 ⭐ **最严重**

**位置**: `unified_consultation_routes.py` 第580-588行

**错误代码**:
```python
SELECT uuid, conversation_log FROM consultations
WHERE patient_id = ? AND (
    uuid = ? OR
    conversation_log LIKE ? OR
    (selected_doctor_id = ? AND ABS(strftime('%s', 'now') - strftime('%s', created_at)) < 3600)
    # ↑ 这个条件导致1小时内同一医生的所有问诊都复用同一个consultation！
)
```

**问题后果**:
```
场景：
1. 11:00 - 用户问张仲景"偏头痛"，创建consultation A，生成处方216
2. 11:30 - 用户切换到金大夫，创建新对话
3. 11:40 - 用户切换回张仲景，问"偏头痛又犯了"

后端逻辑：
- 检查：张仲景 + 1小时内 → 找到consultation A（11:00创建）
- 复用consultation A
- 返回consultation A关联的处方216（旧处方！）
→ 用户看到的是11:00的旧处方，而不是11:40新问诊的处方
```

**实际日志证据**:
```
用户提问："最近偏头痛又犯了。"（新对话）
后端返回：处方216（前天测试的旧处方）
处方内容：阳虚症状（与当前偏头痛无关）
```

**修复方案**:
只根据conversation_id精确匹配，移除基于时间和医生的模糊匹配：
```python
SELECT uuid, conversation_log FROM consultations
WHERE patient_id = ? AND uuid = ?
ORDER BY created_at DESC LIMIT 1
```

## ✅ 已完成的修复

### 1. 前端修复

**文件**: `/opt/tcm-ai/static/js/smart_workflow_history.js`

**修改**:
```javascript
// 修复前：自动恢复UI
const latestConsultation = consultations[0];
if (latestConsultation && latestConsultation.conversation_history) {
    // 清空UI
    chatMessages.innerHTML = '';
    // 设置当前对话ID
    window.currentConversationId = latestConsultation.consultation_id;
    // 自动切换医生！
    selectDoctor(latestConsultation.doctor_id);
    // 恢复消息到UI
    latestConsultation.conversation_history.forEach(turn => {
        addMessage('user', turn.patient_query);
        addMessage('ai', turn.ai_response);
    });
}

// 修复后：只保存数据，不自动恢复UI
console.log('📋 数据库历史记录仅保存到ConversationManager，不自动恢复UI');
```

### 2. 后端修复

**文件**: `/opt/tcm-ai/api/routes/unified_consultation_routes.py`

**修改**:
```python
# 修复前：模糊匹配导致错误复用
cursor.execute("""
    SELECT uuid, conversation_log FROM consultations
    WHERE patient_id = ? AND (
        uuid = ? OR
        conversation_log LIKE ? OR
        (selected_doctor_id = ? AND ABS(...) < 3600)  # ❌ 错误！
    )
""", (user_id, conversation_id, pattern, doctor_id))

# 修复后：只根据conversation_id精确匹配
cursor.execute("""
    SELECT uuid, conversation_log FROM consultations
    WHERE patient_id = ? AND uuid = ?
""", (user_id, request.conversation_id))
```

### 3. 服务重启

✅ TCM-AI服务已重启，修改已生效

## 🧪 完整测试步骤

### 准备工作：清除浏览器数据

在浏览器Console运行：
```javascript
// 清除所有对话数据，重新开始测试
Object.keys(localStorage)
    .filter(k => k.startsWith('conversation_') || k.startsWith('tcm_doctor_history_'))
    .forEach(k => localStorage.removeItem(k));
console.log('✅ 已清除所有对话数据');

// 强制刷新
location.reload(true);
```

### 测试1：基本对话隔离

1. **选择张仲景医生**
2. **输入症状A**："我咳嗽了一周，干咳，嗓子痒"
3. **与AI对话2-3轮**，获取处方
4. **记录处方ID**（例如：处方217）

**期望**:
- Console显示：`✨ 创建新对话: [conversation_id_1]`
- 处方包含：咳嗽、干咳、嗓子痒相关症状

5. **切换到金大夫**
6. **输入症状B**："我口干多饮，夜尿频多"
7. **与AI对话2-3轮**，获取处方
8. **记录处方ID**（例如：处方218）

**期望**:
- Console显示：`✨ 创建新对话: [conversation_id_2]`
- 处方只包含：口干多饮、夜尿频多相关症状
- 处方**不包含**：咳嗽、干咳、嗓子痒等症状A

### 测试2：医生切换恢复历史

9. **切换回张仲景**

**期望Console输出**:
```
🔄 切换医生: zhang_zhongjing
✅ 加载zhang_zhongjing的最新对话: [conversation_id_1]
📱 加载对话 [conversation_id_1]: X条消息
📱 恢复zhang_zhongjing的最新对话: X条消息
```

**期望UI显示**:
- 聊天界面显示之前和张仲景的完整对话（症状A相关）
- 不应该显示金大夫的对话内容

10. **切换回金大夫**

**期望**:
- 聊天界面显示之前和金大夫的完整对话（症状B相关）
- 不应该显示张仲景的对话内容

### 测试3：同一医生新对话不复用旧consultation

11. **保持在金大夫界面**
12. **点击右上角"✨新对话"按钮**
13. **输入症状C**："我最近头晕乏力"
14. **与AI对话2-3轮**，获取处方
15. **记录处方ID**（例如：处方219）

**期望**:
- Console显示：`✨ 创建新对话: [conversation_id_3]`（新的conversation_id）
- 处方只包含：头晕乏力相关症状
- 处方**不包含**：症状A（咳嗽）或症状B（口干多饮）
- 处方ID应该是新的（219），而不是复用旧的（217或218）

### 测试4：页面刷新后状态恢复

16. **按F5刷新页面**

**期望**:
- 页面加载后不会自动切换医生
- 不会自动恢复任何对话到UI（UI应该是空白的欢迎状态）
- Console显示数据已保存到ConversationManager
- 手动选择医生后，能正确恢复该医生的最新对话

### 测试5：验证对话索引数据

在Console运行：
```javascript
const userId = window.getCurrentUserId();
const index = window.conversationManager.getConversationIndex(userId);
console.table(Object.values(index));
```

**期望输出**:
```
conversation_id          | doctor_id        | message_count | is_active
------------------------|------------------|---------------|----------
[conversation_id_1]     | zhang_zhongjing  | X             | true/false
[conversation_id_2]     | jin_daifu        | Y             | false
[conversation_id_3]     | jin_daifu        | Z             | true
```

- 每个conversation_id对应唯一的医生
- 医生ID是完整ID（`zhang_zhongjing`，不是`zhongjing`）
- 每个医生可以有多个对话（如测试3中金大夫有两个对话）

## 🎯 成功标准

所有以下标准必须满足：

1. ✅ **对话完全隔离**: 不同conversation_id的症状完全独立
2. ✅ **处方内容准确**: AI生成的处方只包含当前对话的症状
3. ✅ **医生切换正确**: 切换医生时加载该医生的最新对话
4. ✅ **新对话独立**: 点击"新对话"创建独立的conversation_id
5. ✅ **不复用consultation**: 同一医生的新对话创建新的consultation记录
6. ✅ **页面加载无干扰**: 刷新页面不会自动切换医生或恢复UI
7. ✅ **数据持久化**: 所有对话数据正确保存和恢复

## ⚠️ 关键验证点

### 验证点1：处方是否包含其他对话的症状

在医生工作台查看处方详情时，检查【辨证分析】和【症状描述】部分：
- 应该**只包含**当前对话中患者明确描述的症状
- **不应该包含**其他对话、其他医生的症状
- **不应该包含**患者未提及的症状

### 验证点2：Console日志关键信息

```javascript
// ✅ 正确的日志
✅ 加载zhang_zhongjing的最新对话: [conversation_id]
📱 恢复zhang_zhongjing的最新对话: X条消息
✨ 创建新对话: [new_conversation_id]

// ❌ 不应该出现的日志
✨ 创建新对话（当切换到有历史记录的医生时）
📝 对话无历史记录（当切换到有历史记录的医生时）
```

### 验证点3：数据库consultation记录

可选：在服务器端验证
```bash
sqlite3 /opt/tcm-ai/data/user_history.sqlite
SELECT uuid, selected_doctor_id, created_at FROM consultations
WHERE patient_id = 'usr_20250920_5741e17a78e8'
ORDER BY created_at DESC LIMIT 5;
```

应该看到：
- 每个对话有独立的uuid（对应conversation_id）
- 时间戳准确反映创建时间
- 同一医生的不同对话有不同的uuid

## 🐛 如果仍有问题

### 问题A：切换医生后还是创建新对话

**检查**:
1. Console是否显示：`✅ 加载[doctor]的最新对话`
2. 如果显示`✨ 创建新对话`，说明索引中没有该医生的对话
3. 运行调试命令查看索引：
```javascript
const index = window.conversationManager.getConversationIndex(window.getCurrentUserId());
console.table(Object.values(index));
```

### 问题B：新对话还是返回旧处方

**检查**:
1. Console中conversation_id是否变化
2. 后端日志查看是否复用了旧consultation：
```bash
sudo journalctl -u tcm-ai -n 50 | grep consultation
```

### 问题C：页面加载后自动切换医生

**检查**:
1. 确认修复后的代码是否生效（查看`smart_workflow_history.js`）
2. 强制清除浏览器缓存：`Ctrl+Shift+Delete`
3. 检查是否有其他初始化代码调用了`selectDoctor`

---

**修复时间**: 2025-11-27 10:14
**修复版本**: v3.0 Final
**修复文件**:
1. `/opt/tcm-ai/static/js/smart_workflow_history.js` - 移除自动恢复UI逻辑
2. `/opt/tcm-ai/api/routes/unified_consultation_routes.py` - 修复consultation查重逻辑

**状态**: ✅ 代码已修复，服务已重启，待用户清除数据后完整测试
