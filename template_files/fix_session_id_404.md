# 历史记录详情404错误修复

## 问题描述
患者 `maoxiaohua` 点击历史记录中金大夫的第二个问诊详情时，出现404错误：
```
Failed to load resource: api/user/conversation/:1 (404)
```

## 根本原因

### 数据库层问题
数据库中 `consultations` 表的某些记录 `uuid` 字段为空字符串：

```sql
SELECT id, uuid FROM consultations WHERE id = 195;
-- 结果: 195||  (uuid为空)
```

### 前端传递问题
当后端返回 `session_id` 为空字符串时，前端JavaScript拼接URL时：
```javascript
`/api/user/conversation/${session.session_id}`
// 如果session_id为空，变成: /api/user/conversation/
```

这导致路由匹配失败，返回404错误。

## 已实施的修复

### 1. 数据库修复 ✅
为空UUID的记录补充了有效的UUID：

```sql
-- 修复ID 195的记录
UPDATE consultations
SET uuid = '195a-b-4d7e-af0d-548eda02414b'
WHERE id = 195 AND (uuid IS NULL OR uuid = '');

-- 验证修复
SELECT id, uuid FROM consultations WHERE id = 195;
-- 结果: 195|195a-b-4d7e-af0d-548eda02414b|
```

验证结果：
```bash
sqlite3 /opt/tcm-ai/data/user_history.sqlite \
  "SELECT COUNT(*) FROM consultations WHERE uuid IS NULL OR uuid = '';"
# 结果: 0 (无空UUID记录)
```

### 2. 前端防御代码 ✅

#### 文件: `/opt/tcm-ai/static/js/modules/history_ui.js`

在渲染会话列表项时添加安全检查：

```javascript
renderSessionItem(session, dataProcessor) {
    // 🛡️ 安全检查：如果session_id为空，禁用详情和恢复按钮
    const hasValidSessionId = session.session_id && session.session_id.trim() !== '';

    const detailButton = hasValidSessionId
        ? `<button class="btn-detail" onclick="showConversationDetail('${session.session_id}')"
                   title="查看详情">📋 详情</button>`
        : `<button class="btn-detail" disabled
                   title="数据异常，无法查看"
                   style="opacity: 0.5; cursor: not-allowed;">📋 详情</button>`;

    const restoreButton = hasValidSessionId
        ? `<button class="btn-detail" onclick="viewSession('${session.session_id}')"
                   title="恢复对话" style="margin-left: 5px;">💬 恢复</button>`
        : `<button class="btn-detail" disabled
                   title="数据异常，无法恢复"
                   style="margin-left: 5px; opacity: 0.5; cursor: not-allowed;">💬 恢复</button>`;

    // ... 使用 ${detailButton} 和 ${restoreButton}
}
```

**效果**: 如果检测到空的session_id，按钮会被禁用并显示提示"数据异常，无法查看"。

#### 文件: `/opt/tcm-ai/static/js/user_history_main.js`

在函数调用时添加参数验证：

```javascript
// showConversationDetail函数
async showConversationDetail(sessionId) {
    console.log('🔍 showConversationDetail - 接收到的sessionId:', sessionId, '类型:', typeof sessionId);

    // 🛡️ 安全检查：验证sessionId有效性
    if (!sessionId || sessionId.trim() === '') {
        console.error('❌ sessionId无效:', sessionId);
        alert('数据异常：无法加载对话详情（会话ID为空）');
        return;
    }

    // ... 继续执行
}

// viewSession函数
viewSession(sessionId) {
    // 🛡️ 安全检查：验证sessionId有效性
    if (!sessionId || sessionId.trim() === '') {
        console.error('❌ sessionId无效:', sessionId);
        alert('数据异常：无法恢复对话（会话ID为空）');
        return;
    }

    // ... 继续执行
}
```

**效果**: 即使按钮没有被禁用（旧数据），函数也会在执行前验证sessionId，防止404错误。

### 3. 调试日志增强 ✅

添加了详细的调试日志，便于后续问题诊断：

```javascript
// renderSessionItem中
console.log('🔍 renderSessionItem - session数据:', {
    session_id: session.session_id,
    session_count: session.session_count,
    chief_complaint: session.chief_complaint
});

// showConversationDetail中
console.log('🔍 showConversationDetail - 接收到的sessionId:', sessionId, '类型:', typeof sessionId);
console.log('🔍 准备调用getConversationDetail，sessionId:', sessionId);
```

## 验证步骤

1. **刷新历史记录页面**
   ```bash
   访问: http://mxh0510.cn/user-history
   ```

2. **检查控制台日志**
   ```
   按F12打开控制台，应该看到：
   🔍 renderSessionItem - session数据: {
       session_id: "195a-b-4d7e-af0d-548eda02414b",
       session_count: 2,
       chief_complaint: "..."
   }
   ```

3. **点击"📋 详情"按钮**
   - 应该成功加载对话详情
   - 不再出现404错误

4. **验证数据库完整性**
   ```bash
   sqlite3 /opt/tcm-ai/data/user_history.sqlite \
     "SELECT id, uuid FROM consultations WHERE patient_id = 'usr_20250920_5741e17a78e8';"
   ```

   预期输出：
   ```
   195|195a-b-4d7e-af0d-548eda02414b
   196|ddd9-d130-4309-9bfa-5e05
   198|1ab7-b0ef-4e3c-83ff-ee79
   ```

## 预防措施

### 后端数据生成
建议在创建 `consultations` 记录时，确保UUID字段始终有值：

```python
# 在创建consultation记录时
consultation_uuid = str(uuid.uuid4())[-24:]  # 生成UUID
# 或使用完整UUID: str(uuid.uuid4())

# INSERT时明确指定uuid字段
cursor.execute("""
    INSERT INTO consultations (uuid, patient_id, selected_doctor_id, ...)
    VALUES (?, ?, ?, ...)
""", (consultation_uuid, patient_id, doctor_id, ...))
```

### 数据库约束
可以考虑添加NOT NULL约束（需要数据库迁移）：

```sql
-- 未来的数据库迁移脚本
ALTER TABLE consultations MODIFY COLUMN uuid VARCHAR(50) NOT NULL;
-- 或者在创建表时指定：
-- uuid VARCHAR(50) NOT NULL
```

### 前端验证
所有使用session_id的地方都应该进行验证：
```javascript
if (!sessionId || sessionId.trim() === '') {
    console.error('Invalid sessionId');
    return; // 或显示错误提示
}
```

## 技术细节

### URL路径问题分析
```
正常情况：
/api/user/conversation/195a-b-4d7e-af0d-548eda02414b  ✅

空字符串导致：
/api/user/conversation/                              ❌ (404)

undefined导致：
/api/user/conversation/undefined                     ❌ (可能500或404)
```

### 后端路由定义
```python
@router.get("/conversation/{session_id}")
async def get_conversation_detail(session_id: str):
    # session_id参数是路径参数，必须存在
    # 如果路径是 /conversation/，不会匹配此路由
```

## 相关文件

- **数据库**: `/opt/tcm-ai/data/user_history.sqlite`
- **前端UI**: `/opt/tcm-ai/static/js/modules/history_ui.js`
- **前端逻辑**: `/opt/tcm-ai/static/js/user_history_main.js`
- **后端API**: `/opt/tcm-ai/api/routes/user_sessions_routes.py`

## 提交记录

- 数据库修复: 手动SQL更新
- 前端防御代码: 本次提交
- 调试日志增强: 本次提交

---

**修复日期**: 2025-11-19
**影响范围**: 患者历史记录页面的详情查看和对话恢复功能
**修复状态**: ✅ 已完成
