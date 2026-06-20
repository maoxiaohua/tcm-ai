# TCM-AI 前端API调用完整清单与后端对比分析

**文档版本**: v1.0  
**更新时间**: 2025-10-29  
**扫描范围**: 所有HTML和JS文件的fetch调用  
**彻底度**: Medium (全面搜索 + 详细分析)

---

## 目录
1. [认证相关API](#认证相关api)
2. [问诊相关API](#问诊相关api)
3. [医生API](#医生api)
4. [处方相关API](#处方相关api)
5. [数据同步API](#数据同步api)
6. [支付API](#支付api)
7. [管理员API](#管理员api)
8. [核心发现与建议](#核心发现与建议)

---

## 认证相关API

### 1. POST /api/v2/auth/login

**文件位置**: `auth_portal.html` (第1072行), `index_smart_workflow.html`

**发送数据结构**:
```json
{
  "username": "string",
  "password": "string",
  "remember_me": true
}
```

**期望响应结构**:
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "string",
      "username": "string",
      "primary_role": "patient|doctor|admin",
      "display_name": "string"
    },
    "session": {
      "session_id": "string"
    }
  },
  "redirect_url": "string"
}
```

**响应数据访问方式**:
```javascript
data.user              // 用户信息
data.session.session_id  // 会话令牌
data.redirect_url      // 重定向地址
```

**错误处理方式**:
```javascript
try {
  const response = await fetch('/api/v2/auth/login', {...});
  const data = await response.json();
  if (response.ok && data.success) {
    // 成功
  } else {
    showError(data.detail || data.message || '登录失败');
  }
} catch (error) {
  showError('网络错误，请稍后重试');
}
```

**状态存储**:
- localStorage: `session_token`, `currentUser` (JSON字符串)
- localStorage: `${role}Token` (向后兼容)
- Cookie: `session_token` (secure, samesite=strict)

---

### 2. GET /api/v2/auth/profile

**文件位置**: `js/auth_manager.js` (第140行)

**发送数据**: HTTP头 `Authorization: Bearer {token}`

**期望响应结构**:
```json
{
  "success": true,
  "user": {
    "id": "string",
    "username": "string",
    "display_name": "string",
    "primary_role": "string",
    "permissions": ["string"]
  }
}
```

**响应数据访问方式**:
```javascript
data.user  // 完整用户对象
```

**错误处理方式**:
```javascript
try {
  const response = await fetch('/api/v2/auth/profile', {
    headers: {'Authorization': `Bearer ${token}`}
  });
  if (response.ok) {
    const data = await response.json();
    if (data.success && data.user) return data.user;
  }
  return null;
} catch (error) {
  console.error('Token验证失败:', error);
  return null;
}
```

---

### 3. POST /api/v2/auth/register

**文件位置**: `auth_portal.html` (第1835行)

**发送数据**:
```json
{
  "username": "string",
  "password": "string",
  "display_name": "string"
}
```

**期望响应**: `{success: true, error?: string}`

---

### 4-10. 其他认证API

| API端点 | 发送数据 | 响应格式 | 文件 |
|--------|--------|--------|------|
| POST /api/auth/register/email | {email, password, nickname} | {success, error} | auth_portal.html |
| POST /api/auth/send-verification-code | {phone} | {success, error} | auth_portal.html |
| POST /api/auth/verify-phone-code | {phone, code} | {success, error} | auth_portal.html |
| POST /api/auth/bind-phone | {phone, nickname} | {success, error} | auth_portal.html |

---

## 问诊相关API

### 1. POST /api/consultation/chat (核心API)

**文件位置**: `index_smart_workflow.html` (第4317行) 【最重要的问诊API】

**发送数据结构**:
```json
{
  "message": "用户输入的症状描述",
  "conversation_id": "对话ID(可能为null)",
  "selected_doctor": "doctor_code",
  "patient_id": "用户ID",
  "conversation_history": [
    {
      "role": "user|ai",
      "content": "消息内容"
    }
  ]
}
```

**期望响应结构**:
```json
{
  "success": true,
  "data": {
    "reply": "AI的诊疗建议文本",
    "contains_prescription": true,
    "stage": "diagnosis|prescription",
    "conversation_id": "string"
  }
}
```

**重要: 兼容多种响应格式**:
```javascript
let aiReply;
if (responseData.success && responseData.data && responseData.data.reply) {
  aiReply = responseData.data.reply;  // 新格式
} else if (responseData.reply) {
  aiReply = responseData.reply;       // 旧格式
} else {
  throw new Error('API响应格式错误');
}
```

**错误处理**:
```javascript
try {
  const response = await fetch('/api/consultation/chat', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({...})
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const responseData = await response.json();
  // 处理不同的响应格式...
  
} catch (error) {
  console.error('问诊错误:', error);
  showError('问诊服务暂时不可用');
}
```

---

### 2. POST /api/consultation/save

**文件位置**: `index_smart_workflow.html` (第3285行)

**功能**: 保存完整的问诊记录

**发送数据**: consultation对象，包含症状、诊断等

**期望响应**: `{success: true}`

---

### 3. POST /api/consultation/update-status

**文件位置**: `index_smart_workflow.html` (第9009行)

**发送数据**: `{consultation_id, new_status}`

**期望响应**: `{success: true}`

---

## 医生API

### 1. GET /api/doctors/list (医生列表 - 关键API)

**文件位置**: `index_smart_workflow.html` (第2689行), `user_history.html`

**发送数据**: 无请求体

**期望响应结构**:
```json
{
  "success": true,
  "doctors": [
    {
      "id": "string",
      "doctor_code": "zhang_zhongjing",
      "name": "张仲景",
      "specialties": "["经方", "伤寒论"]或"经方、伤寒论"",
      "introduction": "诊疗特长介绍",
      "avatar": "👨‍⚕️"
    }
  ]
}
```

**关键处理**:
```javascript
// 从API获取医生数据
if (result.success && result.doctors && result.doctors.length > 0) {
  const newDoctors = {};
  result.doctors.forEach(doctor => {
    const doctorCode = doctor.doctor_code;
    
    // 处理specialties字段(可能是JSON字符串或直接字符串)
    let specialty = "中医全科";
    if (doctor.specialties) {
      try {
        const specs = JSON.parse(doctor.specialties);
        specialty = Array.isArray(specs) ? specs.join('、') : doctor.specialties;
      } catch {
        specialty = doctor.specialties;
      }
    }
    
    newDoctors[doctorCode] = {
      name: doctor.name,
      school: specialty.split('、')[0] || "中医",
      specialty: specialty,
      introduction: doctor.introduction
    };
  });
  // 使用newDoctors覆盖前端默认医生数据
}
```

**常见问题**:
- specialty字段可能是JSON字符串，需要解析
- 需要转换为前端医生对象格式

---

### 2. GET /api/doctor/profile

**文件位置**: `doctor/index.html` (第1160行)

**发送数据**: Authorization header

**期望响应**: `{success: true, data: {doctor信息}}`

---

### 3. GET /api/doctor/statistics

**文件位置**: `doctor/index.html` (第1938行)

**功能**: 获取医生工作统计

**期望响应**: `{success: true, data: {统计数据}}`

---

### 4. GET /api/doctor/pending-prescriptions

**文件位置**: `doctor/index.html` (第2544行)

**功能**: 获取待审核处方列表

**期望响应**: `{success: true, data: [处方数组]}`

---

## 处方相关API

### 1. POST /api/prescription/create (处方创建)

**文件位置**: `index_smart_workflow.html` (第4420行)

**发送数据**:
```json
{
  "doctor": "doctor_code",
  "patient_id": "用户ID",
  "symptoms": ["症状1", "症状2"],
  "diagnosis": "证候名称",
  "prescription": "处方文本",
  "remarks": "备注信息"
}
```

**期望响应**:
```json
{
  "success": true,
  "prescription_id": "string",
  "message": "处方创建成功"
}
```

**访问方式**:
```javascript
const createResult = await createResponse.json();
if (createResult.success) {
  prescriptionId = createResult.prescription_id;
}
```

---

### 2. POST /api/prescription-review/payment-confirm

**文件位置**: `index_smart_workflow.html` (第6490行)

**功能**: 确认处方支付

**发送数据**: `{prescription_id, ...}`

**期望响应**: `{success: true, ...}`

---

### 3. POST /api/prescription-review/doctor-review

**文件位置**: `doctor/index.html` (第3034行)

**功能**: 医生审核处方

**发送数据**: `{prescription_id, review_content, status}`

**期望响应**: `{success: true, data: {...}}`

---

## 数据同步API

### 1. POST /api/conversation/sync (关键同步API)

**文件位置**: `index_smart_workflow.html` (第9564行), `js/conversation_state_manager.js` (第696行)

**发送数据**:
```json
{
  "user_id": "用户固定ID",
  "doctor_id": "医生代码",
  "state_data": {
    "currentState": "对话阶段",
    "stateHistory": [状态变更历史],
    "conversationData": {症状等数据},
    "startTime": 时间戳,
    "lastUpdated": 时间戳
  },
  "device_info": {
    "fingerprint": "设备指纹",
    "timestamp": 时间戳
  }
}
```

**期望响应**: `{success: true, message: "同步成功"}`

**错误处理**:
```javascript
try {
  const response = await fetch('/api/conversation/sync', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...})
  });
  
  if (response.ok) {
    const result = await response.json();
    if (result.success) {
      console.log('✅ 状态同步成功');
    }
  } else {
    throw new Error(`同步失败: ${response.status}`);
  }
} catch (error) {
  console.warn('同步状态失败:', error);
}
```

---

### 2. POST /api/user-sync/full-sync (完整用户数据同步)

**文件位置**: `js/conversation_state_manager.js` (第967行)

**功能**: 完整的用户数据同步，包含跨设备恢复

**发送数据**:
```json
{
  "user_id": "用户ID",
  "device_info": {
    "fingerprint": "设备指纹",
    "user_agent": "浏览器信息",
    "timestamp": 时间戳
  },
  "sync_data": {
    "conversations": [对话数据],
    "device_id": "设备ID",
    "last_updated": "ISO时间"
  },
  "sync_type": "full",
  "client_timestamp": 时间戳
}
```

**期望响应**:
```json
{
  "success": true,
  "data": {
    "conversations": [恢复的对话数据]
  },
  "conflicts": []
}
```

---

### 3. POST /api/conversation/clear

**文件位置**: `index_smart_workflow.html` (第4943行)

**功能**: 清空对话记录

**发送数据**: `{conversation_id}`

**期望响应**: `{success: true}`

---

## 支付API

### 1. POST /api/payment/alipay/create

**文件位置**: `index_smart_workflow.html` (第7771行)

**发送数据**: `{prescription_id, ...}`

**期望响应**: `{success: true, payment_url: "支付链接"}`

---

### 2. POST /api/payment/wechat/create

**文件位置**: `index_smart_workflow.html` (第7904行)

**发送数据**: `{prescription_id, ...}`

**期望响应**: `{success: true, payment_data: {...}}`

---

## 医疗记录API

### POST /api/medical-records/list

**文件位置**: `index_smart_workflow.html` (第4537行, 4674行)

**请求变体**:
```
GET /api/medical-records/list                      // 全部记录
GET /api/medical-records/list?type=consultation   // 问诊记录
GET /api/medical-records/list?type=prescription   // 处方记录
```

**期望响应**: `{success: true, data: [记录数组]}`

---

## 管理员API

| API | 发送数据 | 响应格式 |
|-----|--------|--------|
| GET /api/admin/dashboard | - | {success, data: {...}} |
| GET /api/admin/users | - | {success, data: [...]} |
| GET /api/admin/doctors?page=1&per_page=20 | - | {success, data: [...]} |
| GET /api/admin/prescriptions?page=1&per_page=20 | - | {success, data: [...]} |
| GET /api/admin/prescriptions/stats | - | {success, data: {...}} |
| GET /api/admin/orders?page=1&per_page=20 | - | {success, data: [...]} |
| GET /api/admin/system | - | {success, data: {...}} |
| GET /api/admin/logs?page=1&per_page=50 | - | {success, data: [...]} |

---

## 核心发现与建议

### 发现1: API响应格式不统一

**问题**: 某些旧API返回 `{reply: "...", success: bool}` 而新API返回 `{success: true, data: {reply: "..."}}`

**前端处理**:
```javascript
// 必须同时处理两种格式
let aiReply;
if (responseData.success && responseData.data && responseData.data.reply) {
  aiReply = responseData.data.reply;
} else if (responseData.reply) {
  aiReply = responseData.reply;
} else {
  throw new Error('格式错误');
}
```

**建议**:
- 后端统一响应格式为 `{success: bool, data: {...}, message?: string}`
- 所有API在2025年底前迁移到统一格式
- 为旧API创建适配层

---

### 发现2: 医生ID的参数名不统一

**问题**:
- 前端使用: `selected_doctor` (字符串)
- 后端API参数: `doctor_id`
- 数据库存储: `doctor_code`

**前端转换示例**:
```javascript
// 从API获取
result.doctors[].doctor_code   // 返回值
// 发送给API时
{selected_doctor: doctorCode}  // 发送值
{doctor_id: doctorCode}        // 某些API的参数名
```

**建议**: 统一参数名为 `doctor_id` 或 `selected_doctor`

---

### 发现3: 用户ID的多种形式

**前端使用**:
- `currentUser.id` - 登录用户ID (固定)
- `getCurrentUserId()` - 函数获取用户ID
- `patient_id` - API参数名
- `user_id` - API参数名
- 设备指纹: `temp_user_*`, `device_*` 前缀表示临时用户

**建议**: 统一参数名为 `user_id` 或 `patient_id`

---

### 发现4: 认证方式混乱

**使用方式**:
- localStorage: `session_token`
- localStorage: `patientToken` / `doctorToken` / `adminToken`
- Cookie: `session_token`
- HTTP头: `Authorization: Bearer {token}`

**建议**:
- 仅使用 `session_token`
- 删除角色专用token (`patientToken` 等)
- HTTP头统一使用 `Authorization: Bearer`

---

### 发现5: 处方状态管理复杂

**前端判断处方是否完整**:
```javascript
const containsActualPrescription = containsPrescription(aiReply);  // 文本解析
const isTemporaryAdvice = 检查关键词("暂拟", "待确认"等);         // 启发式判断
const needsPayment = containsActualPrescription && !isTemporaryAdvice && !isPaid;
```

**后端返回**:
```json
{
  "data": {
    "contains_prescription": true,  // API级别的标记
    "stage": "prescription"         // 诊疗阶段
  }
}
```

**建议**: 后端应在 `/api/consultation/chat` 响应中返回明确的处方标记，避免前端文本解析

---

### 发现6: 对话状态同步机制

**同步优先级**:
1. 优先从服务器恢复: `/api/user-sync/full-sync`
2. 回退到单独API: `/api/conversation/sync`
3. 再回退到本地localStorage

**问题**: 临时用户 (`temp_user_*`) 的数据不会同步到服务器，存在数据丢失风险

**建议**: 
- 为临时用户提供升级注册流程
- 在升级时自动迁移临时对话数据
- 提供导出/导入机制用于用户迁移

---

### 发现7: 医疗安全检查实现

**前端进行的安全检查**:
```javascript
// 检查AI是否编造症状
detectSymptomFabrication(message, aiReply)

// 检查是否泄露西药
checkMedicalSafety(aiReply)  // 返回warnings数组

// 记录安全事件
logSecurityEvent('ai_symptom_fabrication', aiReply, details)
```

**发送到后端**: `/api/security/log-event` 记录

**建议**: 
- 后端也应进行相同的安全检查
- 前后端检查结果应该一致
- 应该有审计日志存储所有安全事件

---

### 建议汇总

#### 立即行动 (优先级高)

1. **统一API响应格式** - 所有API返回 `{success, data, message}`
2. **统一参数名** - `doctor_id`, `user_id`, 避免混用
3. **认证简化** - 仅用 `session_token`，删除角色专用token
4. **处方标记明确化** - 后端在 `/api/consultation/chat` 中清楚标记处方

#### 短期改进 (1-2周)

5. **增强数据同步** - 为临时用户提供注册升级流程
6. **后端安全检查** - 重复前端的安全检查逻辑
7. **API文档生成** - 自动生成标准格式的API文档

#### 长期优化 (1个月+)

8. **API版本控制** - 为API添加版本号，支持渐进式迁移
9. **监控和告警** - 添加API调用监控和错误告警
10. **SDK提供** - 为前端提供规范化的API调用SDK

---

## 附录: 测试清单

### 登录流程测试
- [ ] 使用正确的用户名密码登录
- [ ] 验证 `session_token` 保存到localStorage
- [ ] 验证 `currentUser` 保存到localStorage
- [ ] 验证重定向到正确的页面

### 问诊流程测试
- [ ] 选择医生并开始问诊
- [ ] 验证 `/api/consultation/chat` 调用
- [ ] 验证新旧响应格式都能正确解析
- [ ] 验证 `/api/conversation/sync` 定期同步
- [ ] 验证临时用户数据不会丢失

### 处方流程测试
- [ ] AI生成完整处方
- [ ] 验证 `/api/prescription/create` 创建处方
- [ ] 验证处方未支付时的提示
- [ ] 验证支付API调用 (支付宝/微信)

### 数据同步测试
- [ ] 刷新页面，验证对话状态恢复
- [ ] 跨浏览器，验证数据同步
- [ ] 离线工作，验证本地缓存
- [ ] 临时用户升级注册，验证数据迁移

---

**文档结束**

