# 对话历史隔离修复方案 (Conversation History Isolation Fix)

## 问题描述

用户报告处方症状混乱问题，经深入调查发现根本原因是**前端对话历史(conversation_history)管理混乱**，导致不同问诊的对话内容相互混淆。

## 根本原因分析

### 1. 核心问题：按医生而非按对话ID存储历史

**问题代码位置**: `/opt/tcm-ai/static/js/smart_workflow_history.js` Line 866

```javascript
// ❌ 错误：按userId + doctorId存储，每个医生只有一个存储槽
const historyKey = `tcm_doctor_history_${userId}_${doctorKey}`;
```

**导致的后果**:
- 用户第一次和金大夫问诊糖尿病 → 保存到 `tcm_doctor_history_usr123_jin_daifu`
- 用户第二次和张仲景问诊咳嗽 → 保存到 `tcm_doctor_history_usr123_zhang_zhongjing`
- 用户第三次再和金大夫问诊 → 加载 `tcm_doctor_history_usr123_jin_daifu` (包含第一次的糖尿病对话)
- **结果**: AI收到混合的对话历史，编造"既往病史"

### 2. 数据结构不匹配问题

**保存时的数据结构** (Line 460-467):
```javascript
const dataToSave = {
    doctor: doctorId,
    consultations: historyByDoctor[doctorId],  // ⚠️ 数组of对话
    lastUpdated: new Date().toISOString(),
    version: '2.3',
    syncedFromDB: true
};
```

**加载时期望的结构** (Line 872):
```javascript
if (historyData.messages && historyData.messages.length > 0) {  // ❌ 期望messages字段
    messages = historyData.messages;
}
```

**问题**: 保存`consultations`数组，加载时却读取`messages`字段，导致数据无法正确恢复！

### 3. conversation_id管理缺失

**问题代码**: `/opt/tcm-ai/static/js/smart_workflow_init.js` Line 704-733

```javascript
function getCurrentConversationHistory() {
    const messages = window.messages || [];  // ⚠️ 全局共享的messages数组
    return messages.map(msg => ({
        role: msg.type === 'user' ? 'user' : 'assistant',
        content: msg.content
    }));
}
```

**问题**:
- `window.messages` 是全局共享变量
- 切换医生时，messages被覆盖而不是隔离
- 没有按`conversation_id`隔离存储和加载

## 用户需求明确化

根据用户反馈，明确以下需求：

1. ✅ **同一对话问诊**: 保留完整历史，AI要学习之前的内容
2. ✅ **不同对话问诊**: 完全隔离，互不干扰
3. ✅ **切换医生**: 加载该医生的最新对话，而非强制新建
4. ✅ **新对话按钮**: 用户主动点击才创建新对话

## 解决方案设计

### 方案架构

```
┌────────────────────────────────────────────┐
│         localStorage存储结构                │
├────────────────────────────────────────────┤
│ conversation_list_${userId}                │  对话索引表
│   ├── conv_id_1: {                         │
│   │     conversation_id: "uuid-1"          │
│   │     doctor_id: "zhang_zhongjing"       │
│   │     created_at: "2025-11-24"           │
│   │     last_message_at: "2025-11-24"      │
│   │     is_active: true                    │
│   │  }                                      │
│   └── conv_id_2: {...}                     │
│                                             │
│ conversation_messages_${conversation_id}    │  对话内容
│   ├── conversation_id: "uuid-1"            │
│   ├── doctor_id: "zhang_zhongjing"         │
│   ├── messages: [                          │
│   │     {type: "user", content: "..."},    │
│   │     {type: "ai", content: "..."}       │
│   │   ]                                     │
│   └── last_updated: "2025-11-24"           │
└────────────────────────────────────────────┘
```

### 实施步骤

#### 第一步：创建对话管理器类

**新建文件**: `/opt/tcm-ai/static/js/conversation_manager.js`

```javascript
/**
 * 对话管理器 - 负责对话历史的隔离存储和加载
 */
class ConversationManager {
    constructor() {
        this.currentConversationId = null;
        this.currentDoctor = null;
        this.currentUserId = null;
    }

    /**
     * 获取对话索引表
     */
    getConversationIndex(userId) {
        const key = `conversation_list_${userId}`;
        const stored = localStorage.getItem(key);
        return stored ? JSON.parse(stored) : {};
    }

    /**
     * 保存对话索引
     */
    saveConversationIndex(userId, index) {
        const key = `conversation_list_${userId}`;
        localStorage.setItem(key, JSON.stringify(index));
    }

    /**
     * 获取或创建对话
     * @param {string} userId - 用户ID
     * @param {string} doctorId - 医生ID
     * @param {boolean} forceNew - 是否强制创建新对话
     * @returns {string} conversation_id
     */
    getOrCreateConversation(userId, doctorId, forceNew = false) {
        const index = this.getConversationIndex(userId);

        if (!forceNew) {
            // 查找该医生的最新活跃对话
            const conversations = Object.values(index).filter(conv =>
                conv.doctor_id === doctorId && conv.is_active
            );

            if (conversations.length > 0) {
                // 按最后消息时间排序，返回最新的
                conversations.sort((a, b) =>
                    new Date(b.last_message_at) - new Date(a.last_message_at)
                );

                const latest = conversations[0];
                console.log(`✅ 加载${doctorId}的最新对话: ${latest.conversation_id}`);

                this.currentConversationId = latest.conversation_id;
                this.currentDoctor = doctorId;
                this.currentUserId = userId;

                return latest.conversation_id;
            }
        }

        // 创建新对话
        const conversationId = this.generateConversationId();

        index[conversationId] = {
            conversation_id: conversationId,
            doctor_id: doctorId,
            user_id: userId,
            created_at: new Date().toISOString(),
            last_message_at: new Date().toISOString(),
            is_active: true,
            message_count: 0
        };

        this.saveConversationIndex(userId, index);

        console.log(`✨ 创建新对话: ${conversationId} (医生: ${doctorId})`);

        this.currentConversationId = conversationId;
        this.currentDoctor = doctorId;
        this.currentUserId = userId;

        return conversationId;
    }

    /**
     * 生成对话ID
     */
    generateConversationId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 6);
        return `${timestamp}-${random}`;
    }

    /**
     * 保存对话消息
     */
    saveConversationMessages(conversationId, messages) {
        const key = `conversation_messages_${conversationId}`;
        const data = {
            conversation_id: conversationId,
            doctor_id: this.currentDoctor,
            user_id: this.currentUserId,
            messages: messages,
            last_updated: new Date().toISOString(),
            version: '3.0'
        };

        localStorage.setItem(key, JSON.stringify(data));

        // 更新索引中的最后消息时间
        const userId = this.currentUserId;
        const index = this.getConversationIndex(userId);

        if (index[conversationId]) {
            index[conversationId].last_message_at = new Date().toISOString();
            index[conversationId].message_count = messages.length;
            this.saveConversationIndex(userId, index);
        }

        console.log(`💾 保存对话 ${conversationId}: ${messages.length}条消息`);
    }

    /**
     * 加载对话消息
     */
    loadConversationMessages(conversationId) {
        const key = `conversation_messages_${conversationId}`;
        const stored = localStorage.getItem(key);

        if (stored) {
            try {
                const data = JSON.parse(stored);
                console.log(`📱 加载对话 ${conversationId}: ${data.messages?.length || 0}条消息`);
                return data.messages || [];
            } catch (error) {
                console.error(`解析对话 ${conversationId} 失败:`, error);
                return [];
            }
        }

        return [];
    }

    /**
     * 切换医生
     * @param {string} userId - 用户ID
     * @param {string} newDoctorId - 新医生ID
     * @returns {Object} {conversationId, messages}
     */
    switchDoctor(userId, newDoctorId) {
        // 获取该医生的最新对话
        const conversationId = this.getOrCreateConversation(userId, newDoctorId, false);
        const messages = this.loadConversationMessages(conversationId);

        return {
            conversationId,
            messages
        };
    }

    /**
     * 开始新对话
     * @param {string} userId - 用户ID
     * @param {string} doctorId - 医生ID
     * @returns {string} conversation_id
     */
    startNewConversation(userId, doctorId) {
        return this.getOrCreateConversation(userId, doctorId, true);
    }

    /**
     * 获取医生的所有对话列表
     */
    getDoctorConversations(userId, doctorId) {
        const index = this.getConversationIndex(userId);
        const conversations = Object.values(index).filter(conv =>
            conv.doctor_id === doctorId
        );

        // 按时间排序
        conversations.sort((a, b) =>
            new Date(b.last_message_at) - new Date(a.last_message_at)
        );

        return conversations;
    }

    /**
     * 结束对话
     */
    endConversation(conversationId) {
        const userId = this.currentUserId;
        const index = this.getConversationIndex(userId);

        if (index[conversationId]) {
            index[conversationId].is_active = false;
            index[conversationId].ended_at = new Date().toISOString();
            this.saveConversationIndex(userId, index);

            console.log(`🏁 结束对话: ${conversationId}`);
        }
    }

    /**
     * 清理旧对话数据（超过30天）
     */
    cleanupOldConversations(userId) {
        const index = this.getConversationIndex(userId);
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        let cleanedCount = 0;

        Object.keys(index).forEach(convId => {
            const conv = index[convId];
            const lastActivity = new Date(conv.last_message_at);

            if (lastActivity < thirtyDaysAgo) {
                // 删除消息数据
                localStorage.removeItem(`conversation_messages_${convId}`);
                // 从索引移除
                delete index[convId];
                cleanedCount++;
            }
        });

        if (cleanedCount > 0) {
            this.saveConversationIndex(userId, index);
            console.log(`🗑️ 清理了 ${cleanedCount} 个旧对话`);
        }

        return cleanedCount;
    }
}

// 创建全局实例
window.conversationManager = new ConversationManager();
```

#### 第二步：修改getCurrentConversationHistory函数

**修改文件**: `/opt/tcm-ai/static/js/smart_workflow_init.js` Line 704-733

**修改前**:
```javascript
function getCurrentConversationHistory() {
    const messages = window.messages || [];
    return messages.map(msg => ({
        role: msg.type === 'user' ? 'user' : 'assistant',
        content: msg.content
    }));
}
```

**修改后**:
```javascript
function getCurrentConversationHistory() {
    // 🔑 使用对话管理器获取当前对话的历史
    const conversationId = window.currentConversationId;

    if (!conversationId) {
        console.log('📝 无当前对话ID，返回空历史');
        return [];
    }

    // 从localStorage加载该对话的消息
    const messages = window.conversationManager.loadConversationMessages(conversationId);

    if (!messages || messages.length === 0) {
        console.log('📝 对话无历史记录');
        return [];
    }

    // 转换为后端期望的格式
    const conversationHistory = messages.map(msg => ({
        role: msg.type === 'user' ? 'user' : 'assistant',
        content: (function() {
            let content = msg.content || '';
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;
            return tempDiv.textContent || tempDiv.innerText || content;
        })()
    }));

    console.log(`📋 返回对话 ${conversationId} 的${conversationHistory.length}条历史`);
    return conversationHistory;
}
```

#### 第三步：修改医生切换逻辑

**修改文件**: 查找处理医生选择的函数（通常在`smart_workflow_init.js`或主HTML中）

```javascript
/**
 * 切换医生
 */
function switchDoctor(newDoctorId) {
    const userId = getCurrentUserId();

    if (!userId) {
        console.error('无法获取用户ID');
        return;
    }

    // 🔑 使用对话管理器切换医生
    const result = window.conversationManager.switchDoctor(userId, newDoctorId);

    // 更新全局变量
    window.currentConversationId = result.conversationId;
    window.selectedDoctor = newDoctorId;

    // 清空当前显示
    if (typeof clearAllMessages === 'function') {
        clearAllMessages();
    }

    // 加载该医生的最新对话历史
    if (result.messages && result.messages.length > 0) {
        console.log(`📱 加载${newDoctorId}的${result.messages.length}条历史消息`);

        result.messages.forEach(msg => {
            if (typeof addMessageWithTime === 'function') {
                addMessageWithTime(msg.type, msg.content, msg.time);
            }
        });

        // 更新window.messages用于显示
        window.messages = result.messages;
    } else {
        // 显示欢迎消息
        if (typeof addWelcomeMessage === 'function') {
            addWelcomeMessage(newDoctorId);
        }
        window.messages = [];
    }

    console.log(`✅ 切换到医生: ${newDoctorId}, 对话ID: ${result.conversationId}`);
}
```

#### 第四步：添加新对话按钮逻辑

```javascript
/**
 * 开始新对话
 */
function startNewConversation() {
    const userId = getCurrentUserId();
    const currentDoctor = window.selectedDoctor;

    if (!userId || !currentDoctor) {
        console.error('无法开始新对话：缺少用户ID或医生ID');
        return;
    }

    // 保存当前对话
    if (window.messages && window.messages.length > 0) {
        const currentConvId = window.currentConversationId;
        if (currentConvId) {
            window.conversationManager.saveConversationMessages(
                currentConvId,
                window.messages
            );
        }
    }

    // 创建新对话
    const newConversationId = window.conversationManager.startNewConversation(
        userId,
        currentDoctor
    );

    // 更新全局变量
    window.currentConversationId = newConversationId;
    window.messages = [];

    // 清空显示
    if (typeof clearAllMessages === 'function') {
        clearAllMessages();
    }

    // 显示欢迎消息
    if (typeof addWelcomeMessage === 'function') {
        addWelcomeMessage(currentDoctor);
    }

    console.log(`✨ 开始新对话: ${newConversationId}`);

    // 显示提示
    if (typeof showMessage === 'function') {
        showMessage('已开始新的对话', 'success');
    }
}

// 绑定到新对话按钮
document.addEventListener('DOMContentLoaded', function() {
    const newConvButton = document.getElementById('newConversationBtn');
    if (newConvButton) {
        newConvButton.addEventListener('click', startNewConversation);
    }
});
```

#### 第五步：修改消息保存逻辑

每次发送/接收消息后，保存到当前对话：

```javascript
/**
 * 发送消息后保存
 */
async function sendMessage(message) {
    // ... 原有发送逻辑 ...

    // 添加到messages数组
    window.messages.push({
        type: 'user',
        content: message,
        time: new Date().toLocaleTimeString(),
        timestamp: Date.now()
    });

    // 🔑 保存到localStorage
    if (window.currentConversationId) {
        window.conversationManager.saveConversationMessages(
            window.currentConversationId,
            window.messages
        );
    }

    // ... 调用API ...

    // AI回复后also保存
    window.messages.push({
        type: 'ai',
        content: aiReply,
        time: new Date().toLocaleTimeString(),
        timestamp: Date.now()
    });

    // 🔑 再次保存
    if (window.currentConversationId) {
        window.conversationManager.saveConversationMessages(
            window.currentConversationId,
            window.messages
        );
    }
}
```

### 数据迁移脚本

为了处理旧数据，需要提供迁移脚本：

```javascript
/**
 * 迁移旧数据到新格式
 */
function migrateOldConversationData(userId) {
    console.log('🔄 开始迁移旧对话数据...');

    const allKeys = Object.keys(localStorage);
    const oldHistoryKeys = allKeys.filter(key =>
        key.startsWith('tcm_doctor_history_') && key.includes(userId)
    );

    let migratedCount = 0;

    oldHistoryKeys.forEach(key => {
        try {
            const data = JSON.parse(localStorage.getItem(key));
            const doctorId = key.split('_').pop();

            // 提取messages
            let messages = [];
            if (data.messages) {
                messages = data.messages;
            } else if (data.consultations && Array.isArray(data.consultations)) {
                // consultations格式
                data.consultations.forEach(consultation => {
                    if (consultation.messages) {
                        messages = messages.concat(consultation.messages);
                    }
                });
            }

            if (messages.length > 0) {
                // 创建新对话
                const conversationId = window.conversationManager.generateConversationId();

                // 保存到新格式
                window.conversationManager.saveConversationMessages(conversationId, messages);

                // 添加到索引
                const index = window.conversationManager.getConversationIndex(userId);
                index[conversationId] = {
                    conversation_id: conversationId,
                    doctor_id: doctorId,
                    user_id: userId,
                    created_at: data.lastUpdated || new Date().toISOString(),
                    last_message_at: data.lastUpdated || new Date().toISOString(),
                    is_active: true,
                    message_count: messages.length,
                    migrated_from_old_format: true
                };
                window.conversationManager.saveConversationIndex(userId, index);

                console.log(`✅ 迁移了医生 ${doctorId} 的 ${messages.length} 条消息`);
                migratedCount++;
            }

            // 删除旧数据
            localStorage.removeItem(key);

        } catch (error) {
            console.error(`迁移 ${key} 失败:`, error);
        }
    });

    console.log(`✅ 迁移完成，共迁移 ${migratedCount} 个对话`);
    return migratedCount;
}

// 在应用初始化时运行一次
if (localStorage.getItem('conversation_data_migrated') !== 'true') {
    const userId = getCurrentUserId();
    if (userId) {
        migrateOldConversationData(userId);
        localStorage.setItem('conversation_data_migrated', 'true');
    }
}
```

## 实施计划

### Phase 1: 核心功能实现 (2-3小时)
1. ✅ 创建`conversation_manager.js`
2. ✅ 修改`getCurrentConversationHistory`
3. ✅ 测试基本的隔离功能

### Phase 2: UI集成 (1-2小时)
1. ✅ 实现医生切换逻辑
2. ✅ 添加新对话按钮
3. ✅ 修改消息保存逻辑

### Phase 3: 数据迁移 (1小时)
1. ✅ 编写迁移脚本
2. ✅ 测试迁移效果
3. ✅ 清理旧数据

### Phase 4: 测试验证 (1-2小时)
1. ✅ 测试新对话创建
2. ✅ 测试切换医生
3. ✅ 测试对话历史隔离
4. ✅ 验证AI不再混淆症状

## 测试用例

### 测试1：对话隔离
```javascript
// 1. 和张仲景问诊咳嗽
switchDoctor('zhang_zhongjing');
sendMessage('我咳嗽了');
// 期望：conversation_id = conv_1

// 2. 切换到金大夫
switchDoctor('jin_daifu');
// 期望：加载金大夫的最新对话（空或旧对话），不包含咳嗽内容

// 3. 和金大夫问诊糖尿病
sendMessage('我口干多饮');
// 期望：conversation_id = conv_2

// 4. 切换回张仲景
switchDoctor('zhang_zhongjing');
// 期望：加载conv_1，包含咳嗽对话，不包含糖尿病

// 5. 验证AI响应不混淆
sendMessage('我的症状怎么样');
// 期望：AI只提到咳嗽，不提糖尿病
```

### 测试2：新对话创建
```javascript
// 1. 当前和张仲景有对话
switchDoctor('zhang_zhongjing');
sendMessage('症状1');

// 2. 点击新对话按钮
startNewConversation();
// 期望：新的conversation_id，messages清空

// 3. 发送新症状
sendMessage('症状2');
// 期望：AI不提及症状1

// 4. 可以查看历史对话列表
const history = conversationManager.getDoctorConversations(userId, 'zhang_zhongjing');
// 期望：2个对话记录
```

### 测试3：会话恢复
```javascript
// 1. 刷新页面前
sendMessage('测试消息');
const beforeConvId = window.currentConversationId;

// 2. 刷新页面
location.reload();

// 3. 页面加载后
const afterConvId = window.currentConversationId;
// 期望：afterConvId === beforeConvId
// 期望：messages包含"测试消息"
```

## 预期效果

修复后应达到：

1. ✅ **完全隔离**: 每个conversation_id独立存储，互不干扰
2. ✅ **AI清晰**: AI只接收当前对话的历史，不会混入其他对话
3. ✅ **用户体验**: 切换医生加载最新对话，新对话按钮创建全新对话
4. ✅ **数据安全**: 旧数据正确迁移，无数据丢失
5. ✅ **症状准确**: 处方中的辨证分析只包含当前对话的症状

## 回归测试清单

- [ ] 新用户首次问诊
- [ ] 老用户继续之前的对话
- [ ] 切换医生后对话隔离
- [ ] 新对话按钮创建独立对话
- [ ] 页面刷新后对话恢复
- [ ] 多个对话历史列表显示
- [ ] 对话结束后标记为inactive
- [ ] 30天后旧对话自动清理
- [ ] AI症状不混乱
- [ ] 处方辨证分析准确

---

**文档版本**: v1.0
**创建时间**: 2025-11-25
**修复目标**: 完全解决对话历史混乱问题
**预计工时**: 6-8小时
**状态**: 待实施
