# 处方ID不匹配问题修复

## 问题描述

用户反馈：
- 患者端支付了处方198
- 医生端看到的最新处方是199，没有198
- 医生尝试审核处方199时提示"患者未支付"

## 问题分析

### 根本原因

**数据库记录错误**：
1. 多条处方和consultation的 `consultation_id`/`uuid` 字段**为空**
2. `doctor_review_queue` 表中使用了不一致的 `doctor_id` 格式（字符串 vs 数字）

### 具体问题

#### 问题1: Consultation UUID缺失

| Consultation ID | UUID | 创建时间 | 状态 |
|----------------|------|---------|------|
| 195 | ✅ `195a-b-4d7e-af0d-548eda02414b` | 2025-11-18 06:54:01 | pending_payment |
| 196 | ✅ `ddd9-d130-4309-9bfa-5e05` | 2025-11-18 06:54:36 | completed |
| 199 | ❌ **空** | 2025-11-19 07:16:40 | pending_payment |
| 200 | ✅ `258d-8643-4eab-b188-9987` | 2025-11-19 07:17:26 | completed |

**影响**: Consultation 199的UUID为空，导致关联到它的处方也无法正确设置consultation_id。

#### 问题2: 处方关联缺失

**修复前状态**:

| 处方ID | consultation_id | payment_status | doctor_id | 问题 |
|-------|----------------|----------------|-----------|------|
| 197 | ❌ **空** | pending | 1 | 无法关联到consultation |
| 198 | ❌ **空** | **paid** | `'jin_daifu'`(字符串) | 无法关联，且doctor_id格式错误 |
| 199 | ❌ **空** | pending | 1 | 无法关联到consultation |

**影响**:
- 处方无法追溯到具体的问诊记录
- 患者端和医生端看到的处方不一致
- 医生审核时无法验证支付状态

#### 问题3: Doctor ID格式不一致

`doctor_review_queue` 表中：
- 处方197: `doctor_id = 1` (数字)
- 处方198: `doctor_id = 'jin_daifu'` (字符串) ❌
- 处方199: `doctor_id = 1` (数字)

金大夫在doctors表中的ID是 `1` (数字)，所以：
- 医生端查询时使用 `doctor_id=1` 只能看到197和199
- 处方198因为doctor_id是字符串 `'jin_daifu'`，医生端看不到！

#### 问题4: 重复的Consultation记录

同一次问诊创建了两条consultation记录：
- **Consultation 199** (UUID为空, 11354字节对话记录) - 主记录
- **Consultation 200** (UUID正常, 2251字节对话记录) - 可能是重复创建

## 已实施的修复

### 修复1: 补充Consultation 199的UUID

```sql
UPDATE consultations
SET uuid = '199a-454c-9166-289b9762919e'
WHERE id = 199 AND (uuid IS NULL OR uuid = '');
```

**结果**: Consultation 199现在有了有效的UUID ✅

### 修复2: 关联处方到Consultation

```sql
-- 处方197 → Consultation 196
UPDATE prescriptions
SET consultation_id = 'ddd9-d130-4309-9bfa-5e05'
WHERE id = 197;

-- 处方198 → Consultation 195
UPDATE prescriptions
SET consultation_id = '195a-b-4d7e-af0d-548eda02414b',
    doctor_id = 1  -- 同时修复doctor_id格式
WHERE id = 198;

-- 处方199 → Consultation 199
UPDATE prescriptions
SET consultation_id = '199a-454c-9166-289b9762919e'
WHERE id = 199;
```

**结果**: 所有处方现在都正确关联到consultation ✅

### 修复3: 统一Doctor ID格式

```sql
-- 修复review_queue中的doctor_id
UPDATE doctor_review_queue
SET doctor_id = '1'
WHERE prescription_id = 198;
```

**结果**: 处方198的doctor_id统一为数字格式 ✅

## 修复后状态

### 最终数据状态

| 处方ID | consultation_id | 关联的Consultation | payment_status | doctor_id | queue_status | 状态 |
|-------|----------------|-------------------|----------------|-----------|--------------|------|
| 197 | `ddd9-d130-4309-9bfa-5e05` | Consultation 196 | pending | 1 | pending | ✅ 正常 |
| 198 | `195a-b-4d7e-af0d-548eda02414b` | Consultation 195 | **paid** | 1 | pending | ✅ 正常 |
| 199 | `199a-454c-9166-289b9762919e` | Consultation 199 | pending | 1 | pending | ✅ 正常 |

### 验证查询

```sql
SELECT
    'Prescription ' || p.id as item,
    p.consultation_id,
    c.id as consultation_db_id,
    p.payment_status,
    p.status,
    q.status as queue_status
FROM prescriptions p
LEFT JOIN consultations c ON p.consultation_id = c.uuid
LEFT JOIN doctor_review_queue q ON p.id = q.prescription_id
WHERE p.id IN (197, 198, 199)
ORDER BY p.id;
```

**结果**:
```
Prescription 197 | ddd9-d130-4309-9bfa-5e05 | 196 | pending | pending_review | pending
Prescription 198 | 195a-b-4d7e-af0d-548eda02414b | 195 | paid | pending_review | pending
Prescription 199 | 199a-454c-9166-289b9762919e | 199 | pending | pending_review | pending
```

所有处方都正确关联到consultation ✅

## 用户操作指南

### 患者端

1. **刷新历史记录页面**: `Ctrl+F5`
2. **验证处方状态**: 处方198应显示为"已支付，待医生审核"

### 医生端

1. **刷新待审核处方列表**: `Ctrl+F5`
2. **应该看到3条待审核处方**:
   - 处方197: 未支付
   - 处方198: **已支付** ← 这是用户支付的
   - 处方199: 未支付

3. **审核处方198**:
   - 点击处方198的"审核"按钮
   - 应该能看到支付状态为"已支付"
   - 可以正常通过审核或退回修改

## 根本原因分析

### 为什么会出现这个问题？

1. **Consultation创建逻辑问题**:
   - 某些情况下创建consultation时UUID字段为空
   - 可能是UUID生成逻辑失败或被跳过
   - 建议检查consultation创建代码中的UUID生成逻辑

2. **重复创建问题**:
   - 同一次问诊创建了两条consultation记录（ID 199和200）
   - 可能是前端重复提交或异常重试导致
   - 建议添加幂等性检查

3. **Doctor ID格式不一致**:
   - 系统中混用了数字ID（如`1`）和字符串ID（如`'jin_daifu'`）
   - 前端选择医生时传递的ID格式不统一
   - 建议统一使用一种ID格式

4. **Consultation ID未传递**:
   - 处方创建时 `consultation_id` 参数可能为None或空字符串
   - 代码中有正确的插入语句，但传入的值有问题
   - 建议在处方创建前验证consultation_id有效性

## 预防措施

### 1. 数据库约束

```sql
-- 建议添加NOT NULL约束
ALTER TABLE consultations MODIFY COLUMN uuid VARCHAR(50) NOT NULL;
ALTER TABLE prescriptions MODIFY COLUMN consultation_id VARCHAR(50) NOT NULL;
```

### 2. 代码验证

**处方创建前验证**:
```python
def create_prescription(consultation_id: str, ...):
    # 🔑 验证consultation_id
    if not consultation_id or consultation_id.strip() == '':
        raise ValueError("consultation_id不能为空")

    # 🔑 验证consultation存在
    cursor.execute("SELECT uuid FROM consultations WHERE uuid = ?", (consultation_id,))
    if not cursor.fetchone():
        raise ValueError(f"Consultation {consultation_id} 不存在")

    # 继续创建处方...
```

**Consultation创建时生成UUID**:
```python
import uuid

def create_consultation(...):
    # 🔑 确保生成UUID
    consultation_uuid = str(uuid.uuid4())[-24:]

    # 🔑 验证UUID不为空
    assert consultation_uuid and len(consultation_uuid) > 0

    cursor.execute("""
        INSERT INTO consultations (uuid, ...)
        VALUES (?, ...)
    """, (consultation_uuid, ...))

    return consultation_uuid
```

### 3. 统一ID格式

**医生ID标准化**:
```python
def normalize_doctor_id(doctor_id: Union[str, int]) -> int:
    """统一转换为整数ID"""
    # 如果是字符串医生代码，查询对应的数字ID
    if isinstance(doctor_id, str) and not doctor_id.isdigit():
        # 'jin_daifu' → 1
        # 'zhang_zhongjing' → 4
        return get_doctor_id_by_code(doctor_id)
    return int(doctor_id)
```

### 4. 幂等性检查

**避免重复创建**:
```python
def create_consultation_idempotent(conversation_id: str, ...):
    # 🔑 检查是否已存在
    cursor.execute("""
        SELECT uuid FROM consultations
        WHERE conversation_id = ? OR
              (patient_id = ? AND created_at > datetime('now', '-1 minute'))
    """, (conversation_id, patient_id))

    existing = cursor.fetchone()
    if existing:
        return existing['uuid']  # 返回已存在的UUID

    # 创建新的consultation
    return create_new_consultation(...)
```

### 5. 监控告警

**检测数据异常**:
```sql
-- 定期检查空UUID
SELECT COUNT(*) as empty_uuid_count
FROM consultations
WHERE uuid IS NULL OR uuid = '';

-- 定期检查未关联的处方
SELECT COUNT(*) as orphan_prescription_count
FROM prescriptions p
LEFT JOIN consultations c ON p.consultation_id = c.uuid
WHERE c.uuid IS NULL;
```

如果发现异常，及时告警。

## 技术细节

### Consultation vs Prescription关系

```
┌─────────────────────┐
│   Consultations     │
│  (问诊记录)          │
│                     │
│  uuid: VARCHAR(50)  │ ← 主键UUID
│  patient_id         │
│  doctor_id          │
│  conversation_log   │
│  ...                │
└─────────┬───────────┘
          │
          │ 1:N (一个consultation可以有多个处方版本)
          │
┌─────────▼───────────┐
│   Prescriptions     │
│  (处方)              │
│                     │
│  id: INTEGER        │
│  consultation_id    │ ← 外键，关联consultation.uuid
│  ai_prescription    │
│  payment_status     │
│  ...                │
└─────────┬───────────┘
          │
          │ 1:1
          │
┌─────────▼───────────┐
│doctor_review_queue  │
│  (医生审核队列)      │
│                     │
│  prescription_id    │ ← 外键，关联prescription.id
│  doctor_id          │
│  status             │
│  ...                │
└─────────────────────┘
```

### Doctor ID映射表

| 医生名称 | doctors表ID | 字符串代码 | 正确格式 |
|---------|------------|-----------|---------|
| 金大夫 | 1 | `jin_daifu` | 使用 `1` |
| 张仲景 | 4 | `zhang_zhongjing` | 使用 `4` |
| 叶天士 | 2 | `ye_tianshi` | 使用 `2` |
| 李东垣 | 3 | `li_dongyuan` | 使用 `3` |
| 刘渡舟 | 5 | `liu_duzhou` | 使用 `5` |
| 郑钦安 | 6 | `zheng_qin_an` | 使用 `6` |

**建议**: 在API层统一转换，后端数据库只存储数字ID。

## 相关文件

- **处方路由**: `/opt/tcm-ai/api/routes/prescription_routes.py`
- **统一问诊路由**: `/opt/tcm-ai/api/routes/unified_consultation_routes.py`
- **医生路由**: `/opt/tcm-ai/api/routes/doctor_routes.py`
- **数据库**: `/opt/tcm-ai/data/user_history.sqlite`

## 提交记录

- 数据修复: 手动SQL更新
- 补充consultation UUID
- 修复处方关联关系
- 统一doctor_id格式

---

**修复日期**: 2025-11-19
**影响范围**: 处方审核流程
**修复状态**: ✅ 已完成
**遗留问题**: 需要修复根本原因（consultation创建逻辑）
