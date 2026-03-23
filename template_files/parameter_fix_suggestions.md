# 参数一致性修复建议

**生成时间**: 2026-03-23 20:44:31

---

## 🔴 错误修复 (共 5 个)

### 错误 1: 参数 'doctor_id' 使用了 5 种不同的命名

**类别**: 参数命名不一致

**详情**:
```
标准名称: doctor_id
描述: 医生唯一标识
当前使用情况:
  - doctor_id: 91 次使用 ✓ 标准
    文件: doctor_management.html, doctor_management.html, doctor_management.html
  - doctor_name: 56 次使用 ✗ 别名
    文件: doctor_management.html, doctor_management.html, doctor_management.html
  - doctorId: 25 次使用 ✗ 别名
    文件: decision_tree_v3_data_driven.html, decision_tree_visual_builder.html, js/conversation_state_manager.js
  - selected_doctor: 10 次使用 ✗ 别名
    文件: index_v2.html, index_v2.html, conversation_state_demo.html
  - doctor_code: 4 次使用 ✗ 别名
    文件: js/smart_workflow_doctor.js, js/modules/history_data.js

建议: 统一使用 'doctor_id'
```

**修复建议**:
```javascript
# 修复建议：统一使用 doctor_id

# 前端代码示例:
// ❌ 错误用法
{  doctorId: value  }  // 使用了别名
{  selected_doctor: value  }  // 使用了别名

// ✅ 正确用法
{  doctor_id: value  }  // 使用标准名称

// 注意: pinyin_name (不是数字！)
// 示例: zhang_zhongjing

```

---

### 错误 2: 参数 'message' 使用了 5 种不同的命名

**类别**: 参数命名不一致

**详情**:
```
标准名称: message
描述: 消息内容
当前使用情况:
  - content: 866 次使用 ✗ 别名
    文件: doctor_management.html, doctor_management.html, doctor_portal.html
  - message: 415 次使用 ✓ 标准
    文件: doctor_management.html, doctor_portal.html, phone_binding.html
  - body: 351 次使用 ✗ 别名
    文件: phone_binding.html, phone_binding.html, prescription_checker_v2.html
  - text: 162 次使用 ✗ 别名
    文件: prescription_checker_v2.html, prescription_checker_v2.html, prescription_checker_v2.html
  - msg: 12 次使用 ✗ 别名
    文件: auth_portal.html, index_v2.html, js/prescription_renderer.js

建议: 统一使用 'message'
```

**修复建议**:
```javascript
# 修复建议：统一使用 message

# 前端代码示例:
// ❌ 错误用法
{  content: value  }  // 使用了别名
{  msg: value  }  // 使用了别名

// ✅ 正确用法
{  message: value  }  // 使用标准名称

```

---

### 错误 3: 参数 'user_id' 使用了 4 种不同的命名

**类别**: 参数命名不一致

**详情**:
```
标准名称: user_id
描述: 用户/患者唯一标识
当前使用情况:
  - userId: 90 次使用 ✗ 别名
    文件: index_v2.html, js/conversation_state_manager.js, js/conversation_state_manager.js
  - user_id: 78 次使用 ✓ 标准
    文件: decision_tree_v3_data_driven.html, decision_tree_v3_data_driven.html, decision_tree_v3_data_driven.html
  - patient_id: 30 次使用 ✗ 别名
    文件: doctor_review_portal.html, decision_tree_v3_data_driven.html, decision_tree_visual_builder.html
  - patientId: 1 次使用 ✗ 别名
    文件: js/prescription_renderer.js

建议: 统一使用 'user_id'
```

**修复建议**:
```javascript
# 修复建议：统一使用 user_id

# 前端代码示例:
// ❌ 错误用法
{  userId: value  }  // 使用了别名
{  patient_id: value  }  // 使用了别名

// ✅ 正确用法
{  user_id: value  }  // 使用标准名称

```

---

### 错误 4: 参数 'prescription_id' 使用了 2 种不同的命名

**类别**: 参数命名不一致

**详情**:
```
标准名称: prescription_id
描述: 处方唯一标识
当前使用情况:
  - prescription_id: 53 次使用 ✓ 标准
    文件: patient_prescription_confirm.html, patient_prescription_confirm.html, prescription_structured_editor.html
  - prescriptionId: 50 次使用 ✗ 别名
    文件: prescription_structured_editor.html, doctor/index.html, doctor/index.html

建议: 统一使用 'prescription_id'
```

**修复建议**:
```javascript
# 修复建议：统一使用 prescription_id

# 前端代码示例:
// ❌ 错误用法
{  prescriptionId: value  }  // 使用了别名
{  rx_id: value  }  // 使用了别名

// ✅ 正确用法
{  prescription_id: value  }  // 使用标准名称

```

---

### 错误 5: 参数 'conversation_id' 使用了 4 种不同的命名

**类别**: 参数命名不一致

**详情**:
```
标准名称: conversation_id
描述: 对话会话唯一标识
当前使用情况:
  - conversation_id: 79 次使用 ✓ 标准
    文件: index_v2.html, index_v2.html, conversation_state_demo.html
  - conversationId: 42 次使用 ✗ 别名
    文件: conversation_state_demo.html, js/prescription_renderer.js, js/smart_workflow_doctor.js
  - session_id: 29 次使用 ✗ 别名
    文件: auth_portal.html, doctor/login.html, js/smart_workflow_records.js
  - sessionId: 3 次使用 ✗ 别名
    文件: js/user_history_main.js, js/user_history_main.js

建议: 统一使用 'conversation_id'
```

**修复建议**:
```javascript
# 修复建议：统一使用 conversation_id

# 前端代码示例:
// ❌ 错误用法
{  conversationId: value  }  // 使用了别名
{  session_id: value  }  // 使用了别名

// ✅ 正确用法
{  conversation_id: value  }  // 使用标准名称

```

---

## 🟡 警告修复 (共 1 个)

### 警告 1: 发现 4 个文件直接访问 .reply

**类别**: 响应数据访问不安全

**详情**:
```
文件: index_v2.html, conversation_state_demo.html, js/smart_workflow_mobile.js, js/smart_workflow_chat.js

问题: 直接访问可能因为响应格式不同而失败

推荐方案:
  ✅ 使用可选链: result?.data?.reply
  ✅ 使用兼容判断: result.data?.reply || result.reply
  ✅ 统一响应格式处理函数
```

**修复建议**:
```javascript

# 推荐方案: 创建统一的响应处理函数

// 定义统一的响应处理器
function extractReply(response) {
  // 处理新API格式 (统一问诊服务)
  if (response.success && response.data) {
    return response.data.reply || response.data.message;
  }

  // 处理旧API格式
  if (response.reply) {
    return response.reply;
  }

  // 处理直接返回
  if (typeof response === 'string') {
    return response;
  }

  // 默认值
  return '系统暂时无法响应，请稍后重试';
}

// 使用示例
const response = await fetch('/api/consultation/chat', {...});
const result = await response.json();
const reply = extractReply(result);  // 统一提取
addMessage('ai', reply);

```

---

## 📚 通用修复指南

### 参数命名标准

| 标准名称 | 类型 | 格式 | 示例 |
|---------|------|------|------|
| `user_id` | string | string | `user_12345` |
| `doctor_id` | string | pinyin_name (不是数字！) | `zhang_zhongjing` |
| `conversation_id` | string | string | `conv_12345` |
| `prescription_id` | string | string | `prescription_12345` |
| `message` | string | string | `我头痛三天了` |

### 常见错误及修复

#### 1. 医生ID格式错误

```javascript
// ❌ 错误
{ doctor_id: '1' }  // 数字格式

// ✅ 正确
{ doctor_id: 'zhang_zhongjing' }  // 名称格式
```

#### 2. 参数名称不统一

```javascript
// ❌ 错误 - 混用多种名称
{ patient_id: user.id }  // 某些地方
{ userId: user.id }      // 另一些地方

// ✅ 正确 - 统一使用
{ user_id: user.id }     // 所有地方都用 user_id
```

#### 3. 响应数据访问不安全

```javascript
// ❌ 错误
const reply = data.reply;  // 可能不存在

// ✅ 正确
const reply = data?.reply || result?.data?.reply || '默认值';
```

