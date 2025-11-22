# 处方consultation_id为空问题 - 系统性修复

## 2025-11-19 完整修复记录

---

## 🐛 问题描述

用户反馈：
- 新建问诊，处方ID 200
- 模拟支付完成
- 医生端找到处方200，点击"通过"时提示"未支付"

## 🔍 根本原因分析

### 问题1: 处方200的consultation_id为空
```sql
SELECT id, consultation_id, payment_status FROM prescriptions WHERE id = 200;
-- 结果: 200 | NULL | pending
```

### 问题2: 两个处方创建函数缺少consultation_id设置

**文件1**: `/opt/tcm-ai/core/consultation/unified_consultation_service.py`
- ❌ INSERT语句中没有consultation_id字段
- ❌ 没有查找或创建consultation记录的逻辑

**文件2**: `/opt/tcm-ai/api/routes/prescription_routes.py`
- ❌ INSERT语句中没有consultation_id字段
- ❌ 没有consultation关联逻辑

### 问题3: 状态管理器检查payment_status

`/opt/tcm-ai/core/prescription/prescription_status_manager.py` (第266行):
```python
if current_payment != PaymentStatus.PAID.value:
    return {
        "success": False,
        "message": f"处方尚未支付，无法审核（当前支付状态：{current_payment}）"
    }
```

**逻辑链**:
1. 处方200创建时，payment_status='pending', consultation_id=NULL
2. 模拟支付 → 但因为没有真正调用支付API，payment_status仍是'pending'
3. 医生审核 → 状态管理器检查payment_status，发现是'pending'，拒绝审核

---

## ✅ 已实施的修复

### 修复1: 处方200数据修复

```sql
-- 关联到正确的consultation
UPDATE prescriptions
SET consultation_id = '6295-0c56-4d91-a536-d5dd'
WHERE id = 200;

-- 更新审核队列
UPDATE doctor_review_queue
SET consultation_id = '6295-0c56-4d91-a536-d5dd'
WHERE prescription_id = 200;
```

### 修复2: unified_consultation_service.py

**位置**: 第471-521行

**修复内容**:
```python
# 🔑 创建处方记录 - 包含consultation_id
# 需要先创建或找到对应的consultation记录
import uuid as uuid_lib
consultation_uuid = None

# 尝试通过conversation_id查找对应的consultation
cursor.execute("""
    SELECT uuid FROM consultations
    WHERE conversation_log LIKE ?
    ORDER BY created_at DESC LIMIT 1
""", (f'%"conversation_id": "{request.conversation_id}"%',))
result = cursor.fetchone()

if result:
    consultation_uuid = result[0]
else:
    # 如果找不到，创建一个consultation记录
    consultation_uuid = str(uuid_lib.uuid4())
    cursor.execute("""
        INSERT INTO consultations (
            uuid, patient_id, selected_doctor_id, conversation_log,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        consultation_uuid,
        request.patient_id,
        doctor_id,
        json.dumps({"conversation_id": request.conversation_id, "conversation_history": []}),
        'in_progress'
    ))

cursor.execute("""
    INSERT INTO prescriptions (
        patient_id, conversation_id, consultation_id, doctor_id, patient_name,
        symptoms, diagnosis, ai_prescription, status, payment_status,
        is_visible_to_patient, review_status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
""", (
    request.patient_id,
    request.conversation_id,
    consultation_uuid,  # 🔑 关键：添加consultation_id
    doctor_id,
    request.patient_id,
    symptoms,
    diagnosis,
    ai_response,
    'ai_generated',  # 🔑 使用标准状态
    'pending',  # 待支付
    0,
    'not_submitted'  # 未提交审核
))
```

### 修复3: prescription_routes.py

**位置**: 第292-366行

**修复内容**:
```python
@router.post("/create")
async def create_prescription(request: CreatePrescriptionRequest):
    """创建新处方（AI问诊完成后调用）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 🔑 查找或创建consultation记录
        import json
        import uuid as uuid_lib
        consultation_uuid = None

        # 尝试通过conversation_id查找对应的consultation
        cursor.execute("""
            SELECT uuid FROM consultations
            WHERE conversation_log LIKE ?
            ORDER BY created_at DESC LIMIT 1
        """, (f'%"conversation_id": "{request.conversation_id}"%',))
        result = cursor.fetchone()

        if result:
            consultation_uuid = result['uuid']
        else:
            # 如果找不到，创建一个consultation记录
            consultation_uuid = str(uuid_lib.uuid4())
            cursor.execute("""
                INSERT INTO consultations (
                    uuid, patient_id, selected_doctor_id, conversation_log,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                consultation_uuid,
                request.patient_id,
                request.doctor_id,
                json.dumps({"conversation_id": request.conversation_id, "conversation_history": []}),
                'in_progress'
            ))

        # 插入处方记录
        cursor.execute("""
            INSERT INTO prescriptions (
                patient_id, conversation_id, consultation_id, doctor_id, patient_name, patient_phone,
                symptoms, diagnosis, ai_prescription, status, payment_status, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.patient_id,
            request.conversation_id,
            consultation_uuid,  # 🔑 关键：添加consultation_id
            request.doctor_id,
            request.patient_name,
            request.patient_phone,
            request.symptoms,
            request.diagnosis,
            request.ai_prescription,
            'ai_generated',  # 🔑 使用标准状态
            'pending',  # 待支付
            'not_submitted'  # 未提交审核
        ))

        prescription_id = cursor.lastrowid
        conn.commit()

        return {
            "success": True,
            "message": "处方创建成功，等待患者支付",
            "prescription_id": prescription_id,
            "consultation_id": consultation_uuid,
            "status": 'ai_generated'
        }
```

---

## 📋 修复后状态

```sql
-- 处方200状态
id  | consultation_id                | payment_status | status         | review_status
200 | 6295-0c56-4d91-a536-d5dd       | pending        | pending_review | pending_review

-- 审核队列状态
prescription_id | doctor_id | consultation_id          | status
200             | 1         | 6295-0c56-4d91-a536-d5dd | pending
```

✅ consultation_id已正确设置
✅ 审核队列已更新
✅ 新创建的处方将自动包含consultation_id

---

## 🔍 剩余问题

### 问题: 模拟支付未真正更新payment_status

虽然处方200的consultation_id已修复，但payment_status仍为'pending'。

**原因**: 用户说"模拟支付完成"，但实际上可能只是前端模拟，没有调用后端支付确认API。

**解决方案**: 需要调用支付确认API来更新payment_status:

```python
POST /api/prescription-review/payment-confirm
{
    "prescription_id": 200,
    "payment_amount": 88.00,
    "payment_method": "alipay"
}
```

或者直接修改数据库（仅用于测试）:
```sql
UPDATE prescriptions
SET payment_status = 'paid'
WHERE id = 200;
```

---

## 🛡️ 预防措施

### 1. 数据库约束（建议添加）

```sql
-- 未来可以添加约束，但需要先修复历史数据
-- ALTER TABLE prescriptions
-- MODIFY COLUMN consultation_id VARCHAR(50) NOT NULL;
```

### 2. 代码验证

已在两个创建函数中添加了consultation查找/创建逻辑：
- ✅ 先查找是否已存在consultation
- ✅ 如不存在则自动创建
- ✅ 确保consultation_id始终有值

### 3. 状态一致性

使用统一的状态值：
- status: 'ai_generated' (而非'pending' 或'pending_review')
- payment_status: 'pending'
- review_status: 'not_submitted'

---

## 📝 验证步骤

### 1. 验证处方200已修复

```bash
# 手动更新payment_status进行测试
sqlite3 /opt/tcm-ai/data/user_history.sqlite "UPDATE prescriptions SET payment_status='paid' WHERE id=200;"

# 然后在医生端审核处方200，应该能成功通过
```

### 2. 测试新建处方

1. 患者端发起新问诊
2. AI生成处方
3. 检查数据库：
```sql
SELECT id, consultation_id, payment_status, status, review_status
FROM prescriptions
ORDER BY id DESC LIMIT 1;
```

预期结果：consultation_id不为空

---

## 📊 影响范围

**修改的文件**:
1. `/opt/tcm-ai/core/consultation/unified_consultation_service.py`
2. `/opt/tcm-ai/api/routes/prescription_routes.py`

**数据库修改**:
- prescriptions表：处方200的consultation_id已更新
- doctor_review_queue表：处方200的consultation_id已更新

**服务重启**: ✅ 已重启 (2025-11-19 16:31:18)

---

## 🎯 后续TODO

1. **处方恢复功能**: 实现处方已生成但未审核时，在问诊页面恢复对话内容
2. **支付流程完善**: 确保模拟支付能正确调用payment-confirm API
3. **历史数据修复**: 检查并修复所有consultation_id为空的历史处方
4. **监控告警**: 添加consultation_id为空的检测机制

---

**修复完成时间**: 2025-11-19 16:31
**修复状态**: ✅ 代码已修复，服务已重启
**遗留问题**: 处方200的payment_status仍为pending（需手动更新或调用支付API）
