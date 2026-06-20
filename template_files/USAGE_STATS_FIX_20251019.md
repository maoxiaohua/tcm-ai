# 使用统计功能修复 - 2025-10-19

## 问题描述

用户点击"数据分析 → 查看使用统计"时，选择任何时间范围（今日、本周、本月）都会报错：

```
/api/doctor-decision-tree/usage-stats/1?time_range=today:1
Failed to load resource: the server responded with a status of 500 ()

加载使用统计失败: Error: 获取统计数据失败
```

---

## 根本原因

### 问题1: SQL别名错误 ❌

**文件**: `/opt/tcm-ai/api/routes/doctor_decision_tree_routes.py:2053-2057`

**错误代码**:
```sql
SELECT COUNT(*) as total_consultations
FROM consultations
WHERE 1=1 {time_filter}
```

当`time_filter`为 `"AND DATE(c.created_at) = DATE('now')"` 时，SQL变成：

```sql
SELECT COUNT(*) as total_consultations
FROM consultations
WHERE 1=1 AND DATE(c.created_at) = DATE('now')
```

**问题**:
- `time_filter`使用了别名 `c.created_at`
- 但FROM子句中没有给`consultations`表起别名`c`
- 导致SQL错误：`no such column: c.created_at`

---

### 问题2: 前端医生ID错误 ❌

**文件**: `/opt/tcm-ai/static/decision_tree_visual_builder.html:4853`

**错误代码**:
```javascript
const doctorId = currentUser.id || currentUser.user_id;
```

**问题**:
- `currentUser.id` 返回的是 `1`（数字ID）
- 但数据库中使用的是 `anonymous_doctor`（字符串ID）
- 导致查询不到任何数据

---

## 修复方案

### 修复1: 添加SQL表别名

**文件**: `/opt/tcm-ai/api/routes/doctor_decision_tree_routes.py:2055`

```sql
-- 修改前
FROM consultations

-- 修改后
FROM consultations c
```

**完整SQL**:
```sql
SELECT COUNT(*) as total_consultations
FROM consultations c  -- ✅ 添加别名c
WHERE 1=1 AND DATE(c.created_at) = DATE('now')
```

---

### 修复2: 使用统一的医生ID获取函数

**文件**: `/opt/tcm-ai/static/decision_tree_visual_builder.html:4847-4852`

```javascript
// 修改前 ❌
const token = localStorage.getItem('token');
if (!token) {
    throw new Error('未登录');
}
const doctorId = currentUser.id || currentUser.user_id;

// 修改后 ✅
const doctorId = getCurrentDoctorId();  // 使用统一函数，返回anonymous_doctor
console.log('🔍 获取使用统计 - 医生ID:', doctorId);

const response = await fetch(`/api/doctor-decision-tree/usage-stats/${doctorId}?time_range=${currentTimeRange}`, {
    headers: getAuthHeaders()  // 使用统一的headers函数
});
```

**改进**:
- ✅ 使用 `getCurrentDoctorId()` 函数
- ✅ 自动返回 `anonymous_doctor` 作为备用
- ✅ 与历史记录功能保持一致
- ✅ 使用 `getAuthHeaders()` 统一处理认证

---

## API测试验证

### 测试命令
```bash
curl -X GET "http://127.0.0.1:8000/api/doctor-decision-tree/usage-stats/anonymous_doctor?time_range=today"
```

### 成功响应
```json
{
    "success": true,
    "data": {
        "overall": {
            "total_patterns": 1,
            "total_calls": 0,
            "success_calls": 0,
            "coverage_rate": null,
            "total_consultations": 1,
            "time_range": "today"
        },
        "patterns": [
            {
                "pattern_id": "f20c3d0a-265d-4aba-b17e-79dc54339a1b",
                "disease_name": "脾胃虚寒型胃痛",
                "thinking_process": "",
                "pattern_created_at": "2025-10-19T10:51:31.315402",
                "call_count": 0,
                "success_count": 0,
                "success_rate": null,
                "last_used_at": null,
                "avg_match_score": null,
                "usage_rate": 0.0
            }
        ]
    }
}
```

**说明**:
- `total_patterns`: 1（有1个决策树）
- `total_calls`: 0（还没有在问诊中使用过）
- `total_consultations`: 1（今天有1次问诊）
- `usage_rate`: 0.0（使用率0%）

这些数据是正常的，因为决策树刚保存，还没有在实际问诊中使用。

---

## 前端测试步骤

### 第1步：清除浏览器缓存

**⚠️ 必须清除缓存！**

- **Windows/Linux**: `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`
- **或使用无痕模式**

---

### 第2步：访问页面

1. 访问 https://mxh0510.cn/static/decision_tree_visual_builder.html
2. 按 `F12` 打开开发者工具
3. 切换到"Console"（控制台）

---

### 第3步：点击"数据分析"

1. 点击页面右上角的"📊 数据分析"按钮
2. 在下拉菜单中选择"📈 查看使用统计"

---

### 第4步：查看统计数据

**预期结果**:

1. **弹出统计对话框**
2. **总体统计卡片显示**:
   - 总决策树数：1
   - 总调用次数：0
   - 成功调用：0
   - 覆盖率：-

3. **决策树列表显示**:
   - 疾病名称：脾胃虚寒型胃痛
   - 调用次数：0
   - 成功率：-
   - 使用率：0.0%

4. **控制台日志**:
   ```
   🔍 获取使用统计 - 医生ID: anonymous_doctor
   ```

---

### 第5步：测试时间范围切换

点击不同的时间范围按钮：

- **今日**: ✅ 应该正常显示
- **本周**: ✅ 应该正常显示
- **本月**: ✅ 应该正常显示
- **全部**: ✅ 应该正常显示

每次切换都会重新加载数据。

---

## 数据说明

### 为什么调用次数是0？

**原因**: 决策树刚保存，还没有在实际患者问诊中被使用过。

**如何增加使用次数**:

1. 当患者问诊时，系统会自动匹配相关的决策树
2. 如果匹配成功，会记录到 `consultations.used_pattern_id` 字段
3. 然后统计数据就会更新

这个功能是自动的，需要：
- 患者提交症状
- 疾病名称匹配（例如"胃痛"会匹配"脾胃虚寒型胃痛"）
- AI诊断时使用了决策树

---

### 统计字段说明

**总体统计**:
- `total_patterns`: 医生保存的决策树总数
- `total_calls`: 决策树被调用的总次数
- `success_calls`: 成功生成处方并被患者确认的次数
- `coverage_rate`: 决策树覆盖率（使用决策树的问诊占总问诊的比例）
- `total_consultations`: 总问诊次数

**单个决策树统计**:
- `disease_name`: 疾病名称
- `call_count`: 该决策树被调用次数
- `success_count`: 成功次数
- `success_rate`: 成功率
- `last_used_at`: 最后使用时间
- `avg_match_score`: 平均匹配分数
- `usage_rate`: 使用率（该决策树调用次数 / 总问诊次数）

---

## 问题排查

### 问题1: 还是报500错误

**检查**:
1. 服务是否重启：`sudo service tcm-ai status`
2. 查看服务日志：`sudo journalctl -u tcm-ai -n 50`

**解决**:
```bash
sudo service tcm-ai restart
```

---

### 问题2: 显示空数据

**检查控制台日志**:
- 医生ID是否为 `anonymous_doctor`
- API响应是否成功

**如果医生ID不对**:
- 清除浏览器缓存
- 使用无痕模式测试

---

### 问题3: 没有调试日志

**原因**: JavaScript缓存未清除

**解决**:
1. 按 `Ctrl + Shift + R` 硬刷新
2. 或使用无痕模式

---

## 相关功能

### 决策树在问诊中的使用流程

```
患者问诊
  ↓
系统提取症状和疾病
  ↓
调用决策树匹配器
  ↓
找到匹配的决策树
  ↓
AI基于决策树生成诊疗建议
  ↓
记录使用情况（consultations.used_pattern_id）
  ↓
统计数据更新
```

相关文档：
- 决策树匹配功能：`DECISION_TREE_PATIENT_MATCHING_GUIDE.md`
- 决策树构建指南：`DECISION_TREE_USER_GUIDE.md`

---

## 修复完成

**修复时间**: 2025-10-19 11:07
**修复文件**:
- `/opt/tcm-ai/api/routes/doctor_decision_tree_routes.py` (后端SQL)
- `/opt/tcm-ai/static/decision_tree_visual_builder.html` (前端ID获取)

**服务状态**: ✅ 已重启
**API测试**: ✅ 通过
**前端测试**: 等待用户验证

---

**现在请清除浏览器缓存，然后点击"📊 数据分析 → 📈 查看使用统计"测试！**
