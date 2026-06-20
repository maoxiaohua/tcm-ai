# 对话管理系统重构方案 - 彻底解决处方混乱问题

## 🎯 重构目标

**核心问题**：处方混乱、数据流混乱、状态管理复杂
**重构目标**：清晰的数据流、简单的API、可靠的隔离机制

## 📊 当前架构问题分析

### 问题1：多数据源冲突
```
localStorage (前端) ←→ SQLite (后端) ←→ WebSocket (实时同步)
          ↓                ↓                    ↓
   谁是权威数据源？   同步时机？      冲突如何解决？
```

**现状**：
- ConversationManager使用localStorage
- syncHistoryFromDatabase从SQLite加载
- AutoSyncManager通过WebSocket同步
- 三者没有明确的优先级和同步策略

### 问题2：状态管理过度复杂
```
ConversationManager
ConversationStateManager
AutoSyncManager
SimplePrescriptionManager
```

**问题**：
- 职责不清晰，相互依赖
- 每个管理器都有自己的状态
- 难以追踪数据流动路径

### 问题3：检测逻辑失效
```javascript
// 当前逻辑（在switchDoctor里检测处方）
messages.some(msg => msg.content.includes('【君药】'))
```

**失效原因**（推测）：
1. messages的数据结构可能不是预期的
2. content可能是HTML或被编码
3. 异步加载导致检测时数据还未准备好

### 问题4：日志污染
```
✅ ❌ 🔑 💾 🔄 📋 📦 🔍 ... (30+种emoji日志)
```

**问题**：难以快速定位关键问题

## ✅ 重构方案：简单、清晰、可靠

### 核心原则

1. **单一数据源**：后端SQLite是唯一权威数据源
2. **简单状态管理**：只在内存保存当前会话，不依赖localStorage
3. **明确隔离规则**：一个consultation = 一次完整问诊（开始→处方）
4. **直接检测**：直接查询数据库判断是否有处方，不依赖前端状态

### 新架构设计

```
┌─────────────────────────────────────────────────────┐
│                   前端（简化）                       │
├─────────────────────────────────────────────────────┤
│  SessionManager (纯内存)                             │
│  - currentConversationId                             │
│  - currentMessages                                   │
│  - currentDoctor                                     │
└─────────────────────────────────────────────────────┘
                      ↓ API调用
┌─────────────────────────────────────────────────────┐
│                   后端（权威）                       │
├─────────────────────────────────────────────────────┤
│  ConversationService                                 │
│  - switchDoctor(userId, doctorId)                    │
│    → 检查该医生最新consultation是否有处方            │
│    → 有处方：创建新consultation_id                   │
│    → 无处方：返回现有consultation_id                 │
│  - getConversationMessages(conversationId)           │
│  - saveMessage(conversationId, message)              │
└─────────────────────────────────────────────────────┘
```

### 数据流

```
用户切换医生
    ↓
前端: SessionManager.switchDoctor(doctorId)
    ↓
调用: POST /api/conversation/switch-doctor
    ↓
后端: 查询数据库
    SELECT id FROM prescriptions
    WHERE consultation_id = (
        SELECT uuid FROM consultations
        WHERE patient_id=? AND selected_doctor_id=?
        ORDER BY created_at DESC LIMIT 1
    )
    ↓
判断: 有处方？
    YES → 创建新consultation_id
    NO  → 返回现有consultation_id
    ↓
返回: {consultation_id, messages, is_new}
    ↓
前端: 更新SessionManager状态，渲染UI
```

## 🔧 实施步骤

### Step 1: 创建后端ConversationService API

**新增路由**：`/api/conversation/switch-doctor`

**功能**：
1. 查询该医生的最新consultation
2. 检查是否有关联的prescription
3. 如果有处方→创建新consultation并返回
4. 如果无处方→返回现有consultation和消息历史

**优势**：
- 检测逻辑在后端，基于数据库查询（100%可靠）
- 前端无需复杂判断
- 一次API调用完成所有逻辑

### Step 2: 创建前端SessionManager

**职责**：
- 管理当前会话状态（纯内存）
- 提供简单的API：switchDoctor(), sendMessage(), clearSession()
- 不依赖localStorage（可选：只用于紧急恢复）

**特点**：
- 轻量级（<200行代码）
- 无复杂状态同步
- 数据来源唯一（后端API）

### Step 3: 简化医生切换逻辑

**旧代码**（复杂）：
```javascript
// 保存当前对话到DOM
// 读取localStorage
// 检查处方（失败）
// 恢复消息到UI
// 更新ConversationManager
// 同步状态...
```

**新代码**（简单）：
```javascript
async function switchDoctor(doctorId) {
    // 1. 调用后端API
    const response = await fetch('/api/conversation/switch-doctor', {
        method: 'POST',
        body: JSON.stringify({doctor_id: doctorId})
    });

    const data = await response.json();

    // 2. 更新会话状态
    sessionManager.update({
        conversationId: data.consultation_id,
        messages: data.messages,
        doctor: doctorId
    });

    // 3. 渲染UI
    renderMessages(data.messages);

    if (data.is_new) {
        console.log('已开启新对话');
    }
}
```

### Step 4: 移除冗余代码

**可以删除/简化**：
- ✅ ConversationManager的复杂localStorage逻辑
- ✅ syncHistoryFromDatabase的UI自动恢复
- ✅ AutoSyncManager（WebSocket失败率高，可选功能）
- ✅ 90%的日志语句

**保留**：
- ✅ SimplePrescriptionManager（处方展示）
- ✅ ConversationStateManager（问诊阶段管理）
- ✅ 核心聊天逻辑

## 📝 代码实现

### 后端API实现

```python
# /opt/tcm-ai/api/routes/conversation_management_routes.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import sqlite3
import json
from datetime import datetime

router = APIRouter()

class SwitchDoctorRequest(BaseModel):
    doctor_id: str

@router.post("/conversation/switch-doctor")
async def switch_doctor(
    request: SwitchDoctorRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    切换医生，智能判断是否需要创建新对话

    规则：
    - 如果该医生的最新对话已有处方 → 创建新对话
    - 如果该医生的最新对话无处方 → 返回现有对话
    """
    conn = sqlite3.connect('/opt/tcm-ai/data/user_history.sqlite')
    cursor = conn.cursor()

    try:
        # 1. 查询该医生的最新consultation
        cursor.execute("""
            SELECT uuid, conversation_log
            FROM consultations
            WHERE patient_id = ? AND selected_doctor_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, request.doctor_id))

        latest = cursor.fetchone()

        if latest:
            consultation_id = latest[0]

            # 2. 检查该consultation是否有处方
            cursor.execute("""
                SELECT id FROM prescriptions
                WHERE consultation_id = ?
                LIMIT 1
            """, (consultation_id,))

            has_prescription = cursor.fetchone() is not None

            if has_prescription:
                # 有处方：创建新consultation
                new_id = str(uuid.uuid4())[:20]
                cursor.execute("""
                    INSERT INTO consultations
                    (uuid, patient_id, selected_doctor_id, conversation_log, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_id,
                    user_id,
                    request.doctor_id,
                    json.dumps({"conversation_history": []}),
                    datetime.now().isoformat()
                ))
                conn.commit()

                return {
                    "success": True,
                    "consultation_id": new_id,
                    "messages": [],
                    "is_new": True,
                    "reason": "previous_conversation_completed"
                }
            else:
                # 无处方：返回现有consultation
                conversation_log = json.loads(latest[1]) if latest[1] else {}
                messages = conversation_log.get('conversation_history', [])

                return {
                    "success": True,
                    "consultation_id": consultation_id,
                    "messages": messages,
                    "is_new": False,
                    "reason": "continue_existing_conversation"
                }
        else:
            # 该医生无历史对话：创建新consultation
            new_id = str(uuid.uuid4())[:20]
            cursor.execute("""
                INSERT INTO consultations
                (uuid, patient_id, selected_doctor_id, conversation_log, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                new_id,
                user_id,
                request.doctor_id,
                json.dumps({"conversation_history": []}),
                datetime.now().isoformat()
            ))
            conn.commit()

            return {
                "success": True,
                "consultation_id": new_id,
                "messages": [],
                "is_new": True,
                "reason": "first_conversation_with_doctor"
            }

    finally:
        conn.close()
```

### 前端SessionManager实现

```javascript
// /opt/tcm-ai/static/js/session_manager.js

class SessionManager {
    constructor() {
        this.conversationId = null;
        this.messages = [];
        this.currentDoctor = null;
        this.userId = null;
    }

    /**
     * 切换医生
     */
    async switchDoctor(doctorId) {
        console.log(`切换到医生: ${doctorId}`);

        try {
            const response = await fetch('/api/conversation/switch-doctor', {
                method: 'POST',
                headers: window.getAuthHeaders(),
                body: JSON.stringify({ doctor_id: doctorId })
            });

            if (!response.ok) {
                throw new Error('切换医生失败');
            }

            const data = await response.json();

            // 更新会话状态
            this.conversationId = data.consultation_id;
            this.messages = data.messages || [];
            this.currentDoctor = doctorId;

            if (data.is_new) {
                console.log(`✨ 新对话: ${data.reason}`);
            } else {
                console.log(`📋 继续对话: ${this.messages.length}条历史消息`);
            }

            // 返回数据供UI渲染
            return {
                conversationId: this.conversationId,
                messages: this.messages,
                isNew: data.is_new
            };

        } catch (error) {
            console.error('切换医生失败:', error);
            throw error;
        }
    }

    /**
     * 添加消息到当前会话
     */
    addMessage(type, content) {
        const message = {
            type: type,
            content: content,
            time: new Date().toLocaleTimeString(),
            timestamp: Date.now()
        };
        this.messages.push(message);
        return message;
    }

    /**
     * 获取当前会话ID
     */
    getConversationId() {
        return this.conversationId;
    }

    /**
     * 清除会话（开始新对话）
     */
    clearSession() {
        this.conversationId = null;
        this.messages = [];
    }

    /**
     * 初始化（页面加载时调用）
     */
    init(userId) {
        this.userId = userId;
        console.log('SessionManager initialized');
    }
}

// 创建全局实例
window.sessionManager = new SessionManager();
```

### 更新医生切换逻辑

```javascript
// 修改 /opt/tcm-ai/static/js/smart_workflow_doctor.js 中的 selectDoctor 函数

async function selectDoctor(doctorKey) {
    console.log(`选择医生: ${doctorKey}`);

    // 1. 调用SessionManager切换医生
    try {
        const result = await window.sessionManager.switchDoctor(doctorKey);

        // 2. 更新全局状态
        window.selectedDoctor = doctorKey;
        window.currentConversationId = result.conversationId;
        window.messages = result.messages;

        // 3. 清空并重新渲染UI
        clearMessages();

        if (result.messages && result.messages.length > 0) {
            // 恢复历史消息
            result.messages.forEach(msg => {
                window.addMessageWithTime(msg.type, msg.content, msg.time);
            });
        }

        // 4. 更新UI状态
        updateDoctorUI(doctorKey);

        if (result.isNew) {
            console.log('✨ 已开启新对话');
        } else {
            console.log(`📋 已恢复${result.messages.length}条历史消息`);
        }

    } catch (error) {
        console.error('切换医生失败:', error);
        alert('切换医生失败，请刷新页面重试');
    }
}
```

## 🎯 预期效果

### 问题解决
- ✅ **处方混乱**：后端数据库检测，100%准确
- ✅ **状态混乱**：单一数据源，无同步冲突
- ✅ **代码复杂**：前端<200行，后端<100行
- ✅ **日志污染**：只保留关键日志

### 性能提升
- ✅ 切换医生：1次API调用完成所有逻辑
- ✅ 无localStorage读写开销
- ✅ 无WebSocket重连开销

### 可维护性
- ✅ 清晰的数据流：UI → SessionManager → Backend → Database
- ✅ 简单的API：switchDoctor(), sendMessage()
- ✅ 易于测试：每个函数职责单一

## 📋 实施计划

1. **创建新API端点** (30分钟)
2. **实现SessionManager** (30分钟)
3. **更新医生切换逻辑** (20分钟)
4. **测试验证** (20分钟)
5. **清理旧代码** (可选，后续进行)

**总耗时**：约2小时
**风险**：低（新代码与旧代码可并行运行，逐步迁移）

---

**重构版本**: v4.0
**设计理念**: Simple, Reliable, Maintainable
**核心原则**: Backend is the single source of truth
