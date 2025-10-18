# 支付和审核流程完整修复报告

## 修复日期
2025-10-17

## 问题概述
患者支付处方后，出现两个关联问题：
1. **患者端**: 支付成功但控制台报错"NOT NULL constraint failed"
2. **医生端**: 无法看到待审核处方，显示"支付未完成"

## 完整问题链
```
患者问诊 → AI生成处方 → 患者支付
    ↓
❌ 支付确认失败（consultation_id NULL约束）
    ↓
❌ 未进入医生审核队列
    ↓
❌ 医生端看不到待审核处方
```

## 根本原因分析

### 数据库设计问题
```sql
-- prescriptions表
consultation_id VARCHAR(50) NULL  -- 可以为空

-- doctor_review_queue表
consultation_id TEXT NOT NULL  -- 不能为空 ❌

-- 实际数据
prescriptions.consultation_id = NULL
prescriptions.conversation_id = "a8c5-6270-4b0f-89b0-eff0"
```

### 代码问题
```python
# prescription_status_manager.py
cursor.execute("""
    INSERT OR REPLACE INTO doctor_review_queue (...)
    SELECT ?, doctor_id, consultation_id, ...  -- ❌ 直接使用NULL值
    FROM prescriptions WHERE id = ?
""", (prescription_id, prescription_id))
```

### 错误信息
```javascript
// 前端控制台
⚠️ 支付确认失败: 更新失败: NOT NULL constraint failed: doctor_review_queue.consultation_id
```

## 完整解决方案

### 1. 修复consultation_id NULL处理

**修改文件**: `/opt/tcm-ai/core/prescription/prescription_status_manager.py`

**修复代码**:
```python
# 🔑 修复：使用COALESCE处理consultation_id为NULL的情况
cursor.execute("""
    INSERT OR REPLACE INTO doctor_review_queue (
        prescription_id, doctor_id, consultation_id,
        submitted_at, status, priority
    )
    SELECT ?,
           doctor_id,
           COALESCE(consultation_id, conversation_id, 'unknown_' || CAST(id AS TEXT)),
           datetime('now', 'localtime'), 'pending', 'normal'
    FROM prescriptions WHERE id = ?
""", (prescription_id, prescription_id))
```

**COALESCE逻辑**:
1. 优先使用 `consultation_id`
2. 如果为NULL，使用 `conversation_id`
3. 如果都为NULL，生成 `unknown_162` 格式

### 2. 修复处方详情显示

**修改文件**: `/opt/tcm-ai/api/routes/prescription_routes.py`

**新增API端点**:
```python
@router.get("/detail/{session_id}")
async def get_prescription_detail_by_session(session_id: str):
    """通过session_id获取处方详情（患者端历史记录查看）"""
    # ... 详见前一个修复报告
```

## 测试验证

### 1. 支付确认流程
```bash
# 测试API
curl -X POST "http://localhost:8000/api/prescription-review/payment-confirm" \
  -d '{"prescription_id": 162, "payment_amount": 88.0, "payment_method": "alipay"}'
```

**结果**: ✅ 成功
```json
{
    "success": true,
    "message": "支付确认成功，处方已提交医生审核",
    "data": {
        "prescription_id": 162,
        "status": "pending_review",
        "note": "处方正在等待医生审核，审核完成后即可配药"
    }
}
```

### 2. 处方状态验证
```sql
SELECT id, status, review_status, payment_status
FROM prescriptions WHERE id = 162;

-- 结果
162|pending_review|pending_review|paid  ✅
```

### 3. 审核队列验证
```sql
SELECT * FROM doctor_review_queue WHERE prescription_id = 162;

-- 结果
id|prescription_id|doctor_id|consultation_id|status
96|162|1|a8c5-6270-4b0f-89b0-eff0|pending  ✅
```

### 4. 医生端查看待审核处方
```bash
curl http://localhost:8000/api/prescription-review/doctor-queue/1
```

**结果**: ✅ 成功
```json
{
    "success": true,
    "data": {
        "doctor_id": "1",
        "pending_count": 2,
        "pending_reviews": [
            {
                "prescription_id": 162,
                "patient_id": "usr_20250920_5741e17a78e8",
                "status": "pending_review",
                ...
            }
        ]
    }
}
```

## 完整流程验证

### 患者端
1. ✅ 问诊完成后支付处方
2. ✅ 支付成功，显示"处方已提交医生审核"
3. ✅ 控制台无错误信息
4. ✅ 可以在历史记录中查看处方详情

### 医生端
1. ✅ 可以看到待审核处方列表
2. ✅ 处方信息完整显示
3. ✅ 可以进行审核操作

## 修复的关键模块

### 核心代码文件
1. `/opt/tcm-ai/core/prescription/prescription_status_manager.py`
   - 修复consultation_id NULL处理
   - 确保审核队列插入成功

2. `/opt/tcm-ai/api/routes/prescription_routes.py`
   - 新增处方详情查询端点
   - 支持session_id查询

3. `/opt/tcm-ai/api/routes/prescription_review_routes.py`
   - 支付确认API
   - 医生审核队列API

### 数据库表
1. `prescriptions` - 处方主表
2. `doctor_review_queue` - 医生审核队列
3. `prescription_payment_logs` - 支付日志
4. `consultations` - 问诊记录

## 影响范围

### 修复的功能
- ✅ 患者支付处方功能
- ✅ 处方提交到审核队列
- ✅ 医生查看待审核处方
- ✅ 患者查看处方详情
- ✅ 支付状态同步

### 涉及的用户界面
- ✅ 患者端问诊页面
- ✅ 患者端历史记录页面
- ✅ 医生端审核工作台
- ✅ 医生端处方管理

## 技术总结

### 1. 数据库约束处理
使用`COALESCE`函数优雅地处理NULL值，避免直接修改表结构。

### 2. 向后兼容性
修复代码完全兼容现有数据，自动处理历史遗留记录。

### 3. 状态流转完整性
```
ai_generated → 支付 → pending_review → 审核 → approved
     ↓                      ↓                    ↓
  pending_payment      进入审核队列        配药完成
```

### 4. 多表协同
确保prescriptions、doctor_review_queue、consultations三表数据一致性。

## 部署检查清单

- [x] 修改状态管理器代码
- [x] 修改处方路由代码
- [x] 重启服务
- [x] 测试支付确认API
- [x] 验证处方状态更新
- [x] 检查审核队列数据
- [x] 测试医生端查询
- [x] 验证患者端显示
- [x] 提交代码到Git

## 相关文档
- `PRESCRIPTION_DETAIL_FIX_20251017.md` - 处方详情显示修复
- `PAYMENT_CONSULTATION_ID_FIX_20251017.md` - consultation_id NULL修复

## 修复时间线
1. 09:00 - 发现问题（患者端支付失败）
2. 09:20 - 定位根本原因（consultation_id NULL约束）
3. 09:35 - 实施修复（COALESCE处理）
4. 09:45 - 测试验证（支付成功）
5. 09:50 - 验证完整流程（医生端也正常）
6. 10:00 - 完成修复并提交

## 结论
支付和审核流程已完全恢复正常，患者可以正常支付处方，医生可以正常查看和审核处方。修复代码具有良好的向后兼容性和可维护性。
