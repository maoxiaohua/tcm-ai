# 处方混乱问题修复 - 测试验证 v3.0

## 🎯 修复目标

**问题**: 切换医生后，旧处方（如216号）依然出现在新对话中
**根本原因**: 用户切换医生时加载旧对话ID，新消息被添加到旧consultation，返回旧处方

## ✅ 已实施的修复

### 修复逻辑
在用户发送新消息前，自动检测当前对话是否已有处方：
- **有处方** → 自动创建新对话ID → 新consultation → 新处方
- **无处方** → 继续使用当前对话ID → 正常问诊流程

### 代码位置
`/opt/tcm-ai/static/js/smart_workflow_chat.js` (第630-650行)

```javascript
// 🔑 v3.0 关键修复：检查是否需要创建新对话
if (window.currentConversationId && window.conversationManager) {
    const userId = window.getCurrentUserId();
    const currentDoctor = window.selectedDoctor;

    // 检查当前对话是否已完成（有处方）
    const currentMessages = window.messages || [];
    const hasPrescription = currentMessages.some(msg =>
        msg.type === 'ai' &&
        (msg.content.includes('【君药】') ||
         msg.content.includes('【处方】') ||
         msg.content.includes('解锁完整处方'))
    );

    if (hasPrescription) {
        // 已有处方，创建新对话
        const newConversationId = window.conversationManager.startNewConversation(userId, currentDoctor);
        window.currentConversationId = newConversationId;
        window.messages = [];
        console.log(`🔄 检测到旧对话已有处方，自动创建新对话: ${newConversationId}`);
    }
}
```

## 🧪 测试步骤

### 测试场景1: 切换医生后的新问诊
1. **打开智能问诊页面**
   - 地址: http://your-domain/smart
   - 强制刷新: `Ctrl+Shift+R`

2. **切换到张仲景医生**
   - 点击"张仲景"头像
   - 观察是否显示历史对话（包含处方216）

3. **提出新问题**
   - 输入: "我最近感冒了，流鼻涕咳嗽"
   - 发送消息

4. **观察控制台日志**（F12打开开发者工具）
   ```
   ✅ 期望看到:
   🔄 检测到旧对话已有处方，自动创建新对话: [新的conversation_id]
   📤 发送问诊请求 - conversationId: [新的conversation_id]

   ❌ 不应该看到:
   📤 发送问诊请求 - conversationId: e0eb-64cf-409a-9d53-e9ff (旧ID)
   ```

5. **验证处方**
   - AI给出处方后，查看处方编号
   - **必须是新的处方ID（不是216）**
   - 处方内容应该针对"感冒流鼻涕咳嗽"，不是旧症状

### 测试场景2: 正常多轮对话
1. **点击"新对话"按钮**
   - 清空当前对话

2. **开始新问诊**
   - 选择任一医生
   - 正常多轮对话
   - 最终获得处方

3. **验证**
   - 多轮对话应正常进行
   - 处方内容应完整且正确
   - 不会触发"创建新对话"逻辑（因为当前对话是新的）

### 测试场景3: 快速切换医生
1. **与李东垣医生开始问诊**
   - 问一两个问题（未完成）

2. **切换到叶天士**
   - 问几个问题，获得处方

3. **切换回李东垣**
   - 应该看到之前未完成的对话
   - 继续问诊应该正常（因为没有处方）

4. **切换回叶天士**
   - 应该看到叶天士的历史对话（有处方）
   - **提出新问题时，控制台应显示创建新对话**
   - 获得新的处方ID

## 📊 预期结果

### 正确行为
| 场景 | 旧对话有处方？ | 行为 | 结果 |
|------|---------------|------|------|
| 切换到有历史的医生 | ✅ 是 | 显示历史 + 新消息创建新对话 | 新处方ID |
| 切换到有历史的医生 | ❌ 否 | 显示历史 + 继续当前对话 | 正常问诊流程 |
| 新对话 | ❌ 否 | 全新开始 | 正常问诊流程 |
| 未完成对话切换回来 | ❌ 否 | 恢复对话 + 继续 | 正常问诊流程 |

### 关键指标
- ✅ **旧处方216不再出现在新问诊中**
- ✅ **每次新问题都获得新的处方ID**
- ✅ **控制台日志清晰显示对话切换逻辑**
- ✅ **用户体验流畅，无错误提示**

## 🔍 调试信息

### 控制台日志关键词
```
🔄 检测到旧对话已有处方，自动创建新对话
💾 已从DOM保存XXX的对话
🔄 切换到医生: XXX
📋 恢复XXX的历史对话
📤 发送问诊请求 - conversationId
✅ 收到问诊响应
```

### 数据库验证（如需深入检查）
```bash
# 查看最新consultations
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT uuid, selected_doctor_id, created_at, updated_at FROM consultations ORDER BY created_at DESC LIMIT 5;"

# 查看最新prescriptions
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT id, consultation_id, created_at FROM prescriptions ORDER BY created_at DESC LIMIT 5;"

# 检查216号处方的consultation是否被更新
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT uuid, updated_at FROM consultations WHERE uuid IN (SELECT consultation_id FROM prescriptions WHERE id = 216);"
```

## 🐛 如果问题依然存在

### 检查清单
1. **服务已重启？**
   ```bash
   sudo service tcm-ai status
   ```

2. **浏览器已强制刷新？**
   - `Ctrl+Shift+R` (清除缓存刷新)

3. **控制台无JavaScript错误？**
   - F12检查Console

4. **conversation_manager.js已加载？**
   - Console输入: `window.conversationManager`
   - 应该返回对象，不是undefined

5. **修改已生效？**
   - 检查 `/opt/tcm-ai/static/js/smart_workflow_chat.js` 第630-650行
   - 应该包含"检测到旧对话已有处方"的代码

### 收集错误信息
如果问题仍然存在，请提供：
1. 完整的控制台日志（从切换医生到收到处方）
2. 发送的消息内容
3. 返回的处方ID和内容
4. localStorage中的conversation_list内容:
   ```javascript
   console.log(localStorage.getItem('conversation_list_[your_user_id]'))
   ```

---

**修复版本**: v3.0
**修复时间**: 2025-11-27 15:33
**测试状态**: 待用户验证
**预期效果**: 完全解决处方混乱问题
