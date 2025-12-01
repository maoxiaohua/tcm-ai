# TCM-AI v3.0 对话隔离功能测试指南

## 修复内容总结

本次更新实现了完整的对话历史隔离系统，解决了处方症状混乱的根本问题。

### 核心修改

1. ✅ **创建ConversationManager类** (`/static/js/conversation_manager.js`)
   - 按conversation_id隔离存储对话
   - 支持医生切换时加载最新对话
   - 支持新对话按钮创建独立对话
   - 自动迁移旧数据到新格式

2. ✅ **修改getCurrentConversationHistory函数** (`/static/js/smart_workflow_init.js`)
   - 使用ConversationManager加载当前对话历史
   - 确保AI只接收当前对话的症状

3. ✅ **实现医生切换逻辑** (`/static/js/smart_workflow_doctor.js`)
   - 切换医生时自动保存当前对话
   - 加载目标医生的最新对话（而非创建新对话）
   - 如果医生无历史记录，显示欢迎消息

4. ✅ **更新新对话按钮** (`/static/js/smart_workflow_history.js`)
   - 保存当前对话并标记为结束
   - 创建全新对话ID
   - 清空界面并显示欢迎消息

5. ✅ **修改消息保存逻辑** (`/static/js/smart_workflow_history.js`)
   - 每次发送/接收消息自动保存到当前conversation_id
   - 同步更新window.messages数组

## 测试场景

### 测试1：对话隔离验证 ⭐ 最重要

**目的**: 验证不同对话的症状完全隔离

**步骤**:
1. 访问 https://mxh0510.cn
2. 选择**张仲景医生**
3. 输入症状：`我咳嗽了一周，干咳，嗓子痒`
4. 与AI进行2-3轮对话
5. 切换到**金大夫**
6. 输入症状：`我口干多饮，夜尿频多`
7. 与AI进行2-3轮对话
8. 让AI开具处方

**预期结果**:
- ✅ 金大夫的处方【辨证分析】中**不应包含**"咳嗽"、"嗓子痒"等症状
- ✅ 金大夫的处方【辨证分析】中**只应包含**"口干多饮、夜尿频多"相关症状
- ✅ 检查浏览器Console，应看到不同的conversation_id

**验证命令**:
```javascript
// 在浏览器Console中运行
console.log('当前对话ID:', window.currentConversationId);
console.log('当前医生:', window.selectedDoctor);
window.showConversationDebug(); // 查看详细状态
```

### 测试2：医生切换功能验证

**目的**: 验证切换医生时加载最新对话

**步骤**:
1. 继续测试1，当前在金大夫界面
2. 切换回**张仲景医生**
3. 观察聊天界面

**预期结果**:
- ✅ 应该自动加载之前和张仲景的对话（关于咳嗽）
- ✅ 界面显示之前的2-3轮对话记录
- ✅ 不应该显示金大夫的对话内容
- ✅ Console应显示：`📱 恢复zhang_zhongjing的最新对话: X条消息`

### 测试3：新对话按钮功能

**目的**: 验证新对话按钮创建独立对话

**步骤**:
1. 继续测试2，当前在张仲景界面，显示咳嗽对话
2. 点击右上角**✨新对话**按钮
3. 观察界面变化
4. 输入新症状：`我头痛头晕`
5. 进行对话并获取处方

**预期结果**:
- ✅ 点击新对话后，界面清空
- ✅ 显示张仲景的欢迎消息
- ✅ conversation_id变更（可在Console查看）
- ✅ 新处方【辨证分析】只包含"头痛头晕"，不包含"咳嗽"
- ✅ Console显示：`✨ 创建新对话: [新ID]`

### 测试4：对话持久化验证

**目的**: 验证刷新页面后对话恢复

**步骤**:
1. 继续测试3，当前在张仲景的头痛对话
2. 按F5刷新页面
3. 观察界面

**预期结果**:
- ✅ 页面刷新后，自动恢复张仲景的最新对话（头痛对话）
- ✅ 之前的消息全部显示
- ✅ conversation_id保持不变

### 测试5：多次切换医生验证

**目的**: 验证复杂切换场景

**步骤**:
1. 张仲景 - 咳嗽对话（测试1创建）
2. 切换到金大夫 - 糖尿病对话（测试1创建）
3. 切换到叶天士 - 新对话 - 发热对话
4. 切换回张仲景 - 应显示咳嗽对话
5. 切换到金大夫 - 应显示糖尿病对话
6. 切换到叶天士 - 应显示发热对话

**预期结果**:
- ✅ 每个医生都能正确恢复其最新对话
- ✅ 对话内容互不混淆
- ✅ Console显示正确的conversation_id切换

### 测试6：数据迁移验证（老用户）

**目的**: 验证旧数据自动迁移

**步骤**:
1. 清除浏览器localStorage：
   ```javascript
   // 在Console运行
   localStorage.clear();
   ```
2. 手动创建旧格式数据：
   ```javascript
   localStorage.setItem('tcm_doctor_history_test_user_zhang_zhongjing', JSON.stringify({
       messages: [
           {type: 'user', content: '旧数据测试', time: '10:00'},
           {type: 'ai', content: 'AI回复', time: '10:01'}
       ],
       lastUpdated: new Date().toISOString(),
       version: '2.1'
   }));
   ```
3. 刷新页面
4. 选择张仲景医生

**预期结果**:
- ✅ 控制台显示：`🔄 开始迁移旧对话数据...`
- ✅ 控制台显示：`✅ 迁移了医生 zhang_zhongjing 的 2 条消息`
- ✅ 界面显示迁移后的对话
- ✅ localStorage中创建了新格式的数据

## 调试工具

### 查看当前状态

在浏览器Console运行：
```javascript
// 查看conversation_id
console.log('当前对话ID:', window.currentConversationId);
console.log('当前医生:', window.selectedDoctor);
console.log('当前消息数:', window.messages?.length);

// 查看详细状态
window.showConversationDebug();

// 查看对话索引
const userId = window.getCurrentUserId();
const index = window.conversationManager.getConversationIndex(userId);
console.table(Object.values(index));
```

### 查看localStorage数据

```javascript
// 列出所有对话
Object.keys(localStorage).filter(k => k.startsWith('conversation_')).forEach(k => {
    console.log(k, localStorage.getItem(k).length, 'bytes');
});

// 查看specific对话
const convId = window.currentConversationId;
const key = `conversation_messages_${convId}`;
console.log(JSON.parse(localStorage.getItem(key)));
```

### 清理测试数据

```javascript
// 清除所有对话数据
Object.keys(localStorage).filter(k => k.startsWith('conversation_')).forEach(k => {
    localStorage.removeItem(k);
});
console.log('✅ 已清除所有对话数据');

// 清除迁移标记（重新触发迁移）
localStorage.removeItem('conversation_data_migrated_v3');
```

## 问题排查

### 问题1：切换医生后显示空白

**症状**: 切换医生后没有显示历史记录，也没有欢迎消息

**排查**:
1. 检查Console是否有错误
2. 检查`window.conversationManager`是否存在：
   ```javascript
   console.log('ConversationManager:', !!window.conversationManager);
   ```
3. 检查是否有conversation_id：
   ```javascript
   console.log('Conversation ID:', window.currentConversationId);
   ```

**解决**: 如果ConversationManager不存在，检查`conversation_manager.js`是否正确加载

### 问题2：AI仍然混淆症状

**症状**: AI生成的处方包含其他对话的症状

**排查**:
1. 检查发送给AI的conversation_history：
   ```javascript
   const history = window.getCurrentConversationHistory();
   console.log('发送给AI的历史:', history);
   ```
2. 确认history中只包含当前对话
3. 检查conversation_id是否正确

**解决**: 如果history包含其他对话，检查`getCurrentConversationHistory`函数是否正确使用ConversationManager

### 问题3：页面刷新后对话丢失

**症状**: 刷新页面后之前的对话不见了

**排查**:
1. 检查localStorage是否有数据：
   ```javascript
   const keys = Object.keys(localStorage).filter(k => k.startsWith('conversation_'));
   console.log('存储的对话数:', keys.length);
   ```
2. 检查conversation_id是否保存：
   ```javascript
   console.log('当前ID:', window.currentConversationId);
   ```

**解决**: 如果没有数据，检查`saveCurrentDoctorHistory`是否正常调用

## 成功标准

✅ **核心功能验证通过**:
- [ ] 不同对话的症状完全隔离
- [ ] AI生成的处方不包含其他对话症状
- [ ] 切换医生时正确加载最新对话
- [ ] 新对话按钮创建独立对话
- [ ] 页面刷新后对话正确恢复

✅ **用户体验良好**:
- [ ] 切换医生响应快速（<1秒）
- [ ] 历史记录加载正常
- [ ] 无Console错误
- [ ] 移动端和PC端都正常工作

✅ **医疗安全保障**:
- [ ] 处方【辨证分析】症状准确
- [ ] 无"既往病史"编造问题
- [ ] 患者数据隔离正确

## 回归测试清单

在完成以上功能测试后，还需验证以下功能未被破坏：

- [ ] 用户登录/注册功能正常
- [ ] 处方支付解锁功能正常
- [ ] 医生审查处方功能正常
- [ ] 历史记录查看功能正常
- [ ] 图片上传（舌象）功能正常
- [ ] 移动端适配正常
- [ ] 退出登录功能正常

## 测试完成报告

测试完成后，请填写：

**测试人员**: ___________
**测试日期**: ___________
**测试结果**: [ ] 通过 [ ] 失败

**发现的问题**:
1. ___________
2. ___________
3. ___________

**备注**: ___________

---

**版本**: v3.0
**创建时间**: 2025-11-25
**最后更新**: 2025-11-25
