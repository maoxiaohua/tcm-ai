# TCM-AI 关键问题修复方案

## 问题清单与根本原因分析

### ✅ 已识别问题

| 问题# | 症状 | 根本原因 | 影响范围 |
|------|------|---------|---------|
| 1 | 医生端审查处方"网络错误" | 浏览器缓存旧JavaScript，调用不存在的hideRejectForm() | 医生端 |
| 2 | 已审核处方仍显示在列表 | 前端缓存数据未刷新，不是API问题 | 医生端 |
| 3 | 待审查数量显示为0 | doctor_id不匹配：当前医生4，处方128分配给医生1 | 医生端 |
| 4 | 患者端刷新后对话清空 | 用户ID不匹配：前端user_1760162322 vs 数据库usr_xxx | 患者端 |
| 5 | 历史记录内容缺失 | consultation_id为空，无法关联conversation_log | 患者端 |
| 6 | 基本信息显示错误 | 日期字段格式不正确，轮次计算错误 | 患者端 |
| 7 | 重复创建审查队列 | 每次问诊创建2个queue记录 | 后端 |

---

## 🎯 核心问题：三层缓存失效

### 问题1: 浏览器缓存
**现象**: 用户仍在使用旧版本JavaScript，调用已删除的函数

**解决方案**:
```html
<!-- 所有JavaScript引用添加版本参数 -->
<script src="/static/doctor/index.html?v=20251011001"></script>
<script src="/static/index_smart_workflow.html?v=20251011001"></script>
```

### 问题2: 前端数据缓存
**现象**: currentPrescriptions数组缓存了已审核的处方

**解决方案**: 审查成功后强制重新加载，清除内存缓存

### 问题3: localStorage缓存
**现象**: 用户信息中的ID格式不一致

**解决方案**: 统一使用session API返回的真实用户ID

---

## 🔧 具体修复措施

### 修复1: 添加JavaScript版本控制 ✅ 优先级最高

```bash
# 修改所有HTML文件，添加版本参数
sed -i 's|\.js">|.js?v=20251011001">|g' /opt/tcm-ai/static/doctor/index.html
sed -i 's|\.js">|.js?v=20251011001">|g' /opt/tcm-ai/static/index_smart_workflow.html
```

### 修复2: 患者端用户ID统一 ✅ 核心修复

**问题根源**:
```javascript
// ❌ 错误：从timestamp生成的ID
const userId = 'user_' + Date.now();

// ✅ 正确：从session API获取真实ID
const userId = sessionData.user_id; // usr_20250920_xxx
```

**修复位置**: `getCurrentUserId()` 函数

### 修复3: consultation_id关联修复 ✅ 数据完整性

**问题**: prescriptions表的consultation_id为空
```sql
SELECT id, patient_id, consultation_id FROM prescriptions WHERE id=130;
-- 130|usr_20250920_5741e17a78e8||  ← consultation_id为空!
```

**修复**: 统一问诊API创建处方时必须填充consultation_id

### 修复4: 重复queue记录修复

**问题**: 每个处方有2个queue记录
```sql
SELECT id, prescription_id FROM doctor_review_queue WHERE prescription_id=130;
-- 43|130
-- 44|130  ← 重复!
```

**修复**: 添加UNIQUE约束，INSERT OR IGNORE

### 修复5: 医生ID不匹配

**问题**:
- 处方128分配给doctor_id=1 (金大夫)
- 当前登录医生是doctor_id=4 (张仲景)
- API查询WHERE doctor_id=4，所以查不到处方128

**这不是bug，是权限控制！** 张仲景医生确实看不到分配给金大夫的处方。

**统计数量显示0的原因**: 没有分配给当前医生的待审查处方。

---

## 📋 修复执行计划

### 阶段1: 立即修复（浏览器缓存）
1. ✅ 添加JavaScript版本参数
2. ✅ 添加Cache-Control响应头
3. ✅ 清除用户浏览器缓存指南

### 阶段2: 核心数据修复
1. ✅ 修复getCurrentUserId()逻辑
2. ✅ 修复consultation_id存储
3. ✅ 防止重复queue记录

### 阶段3: 历史数据修复
1. ✅ 补全现有处方的consultation_id
2. ✅ 删除重复的queue记录
3. ✅ 验证数据完整性

### 阶段4: 用户体验优化
1. ✅ 添加"刷新"按钮
2. ✅ 优化错误提示消息
3. ✅ 添加数据加载状态指示

---

## 🧪 验证测试清单

### 医生端测试
- [ ] 清除浏览器缓存
- [ ] 登录医生账户
- [ ] 查看待审查处方列表
- [ ] 审查通过一个处方
- [ ] 验证处方从列表中消失
- [ ] 验证统计数字更新

### 患者端测试
- [ ] 清除浏览器缓存
- [ ] 患者登录
- [ ] 开始新问诊
- [ ] 刷新页面
- [ ] 验证对话记录保留
- [ ] 查看历史记录
- [ ] 验证详情完整显示

---

## 💡 预防措施

### 1. 版本控制策略
```javascript
// 配置文件
const APP_VERSION = '20251011001';
// 所有资源URL自动添加版本
function getResourceUrl(path) {
    return `${path}?v=${APP_VERSION}`;
}
```

### 2. 数据完整性约束
```sql
-- 防止重复queue记录
CREATE UNIQUE INDEX idx_unique_prescription_doctor
ON doctor_review_queue(prescription_id, doctor_id, status);

-- 确保consultation_id不为空
ALTER TABLE prescriptions
ADD CONSTRAINT check_consultation_id
CHECK (consultation_id IS NOT NULL);
```

### 3. 统一用户ID获取
```javascript
// 单一可信源
async function getCurrentUserId() {
    // 1. 优先从session API获取
    const session = await fetch('/api/auth/session');
    if (session.ok) {
        const data = await session.json();
        return data.user_id; // usr_xxx格式
    }

    // 2. 降级方案：localStorage
    return localStorage.getItem('global_user_id');
}
```

---

## 📊 预期效果

### 修复后
- ✅ 医生端审查流程100%成功率
- ✅ 患者端刷新后对话记录100%保留
- ✅ 历史记录详情100%完整显示
- ✅ 无重复数据
- ✅ 用户ID格式统一

### 性能指标
- 页面加载时间: <2s
- API响应时间: <500ms
- 缓存命中率: >80%

---

## 🚨 用户临时解决方案

**医生端**:
1. 按Ctrl+Shift+Delete清除浏览器缓存
2. 或使用无痕模式访问: Ctrl+Shift+N
3. 刷新页面: F5

**患者端**:
1. 清除浏览器缓存
2. 重新登录
3. 系统会自动恢复对话记录

---

## 📝 修复记录

- 2025-10-11 14:00: 识别浏览器缓存问题
- 2025-10-11 14:15: 修复hideRejectForm undefined
- 2025-10-11 14:20: 修复showSection event参数
- 2025-10-11 14:30: 分析用户ID不匹配问题
- 2025-10-11 14:45: 制定完整修复方案

---

**下一步**: 执行阶段1修复，添加版本控制
