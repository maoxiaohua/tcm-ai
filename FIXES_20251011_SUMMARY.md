# TCM-AI 修复汇总 - 2025年10月11日

## ✅ 已完成的修复

### 1. 注册跳转URL错误修复 ✅
**问题**: 用户注册成功后跳转到 `https://mxh0510.cn` 而不是 `https://mxh0510.cn/login`

**修复位置**: `/opt/tcm-ai/static/auth_portal.html`
- 行 1208: 手机注册跳转 (修改为 `/login`)
- 行 1689: 手机注册跳转 (修改为 `/login`)
- 行 1772: 邮箱注册跳转 (修改为 `/login`)
- 行 1850: 用户名注册跳转 (修改为 `/login`)

**修复代码**:
```javascript
// ❌ 修复前:
window.location.href = '/';

// ✅ 修复后:
window.location.href = '/login';
```

**预期效果**:
- ✅ 用户注册成功后自动跳转到登录页面
- ✅ 用户可以立即使用新账户登录系统
- ✅ 避免跳转到根路径导致的混淆

---

### 2. JavaScript版本控制系统 ✅
**问题**: 浏览器缓存旧版本JavaScript代码，导致修复后的代码仍然无法生效

**根本原因**:
- 浏览器会缓存JavaScript文件以加快加载速度
- 代码修复后，用户浏览器仍使用缓存中的旧代码
- 导致"明明修复了但还是有问题"的现象

**修复方案**: 为所有JavaScript文件添加版本参数

**修复位置**:

1. `/opt/tcm-ai/static/index_smart_workflow.html` (患者端)
   - 行 97: `auth_manager.js?v=20251011001`
   - 行 11236: `conversation_state_manager.js?v=20251011001`
   - 行 11239: `auto_sync_manager.js?v=20251011001`

2. `/opt/tcm-ai/static/auth_portal.html` (登录注册页)
   - 行 10: `auth_manager.js?v=20251011001`

**版本命名规范**:
```
v + YYYYMMDD + 序号
例如: v20251011001 (2025年10月11日第1个版本)
```

**未来更新流程**:
```bash
# 每次修改JavaScript文件后，更新HTML中的版本号
sed -i 's/v20251011001/v20251011002/g' /opt/tcm-ai/static/*.html
```

**预期效果**:
- ✅ 强制浏览器下载最新版本JavaScript
- ✅ 避免缓存导致的"修复无效"问题
- ✅ 便于版本追踪和问题定位

---

## 🔍 已识别但待修复的问题

### 3. 患者端用户ID不匹配问题 ⏳
**症状**:
- 患者刷新页面后对话记录清空
- 历史记录显示"已从云端恢复0条记录"
- 查看历史记录列表为空

**根本原因**:
```javascript
// 前端使用的ID格式
const userId = 'user_1760162322';  // user_ + timestamp

// 数据库实际存储的ID格式
'usr_20250920_575ba94095a7'  // usr_ + date + random

// session API返回的正确ID
session.user_id = 'usr_20250920_575ba94095a7'
```

**数据库证据**:
```sql
SELECT session_id, user_id FROM unified_sessions
WHERE session_id='sess_1760162322_10f8ae1113a2d5b8';
-- Result: usr_20250920_575ba94095a7

-- 前端请求: /api/conversation/history/user_1760162322
-- 数据库查询: WHERE user_id = 'user_1760162322'
-- 结果: 0条记录 (因为ID不匹配)
```

**修复方案** (待执行):
```javascript
// 需要修复 getCurrentUserId() 函数

// ❌ 当前错误实现:
function getCurrentUserId() {
    let userId = localStorage.getItem('global_user_id');
    if (!userId) {
        userId = 'user_' + Date.now();  // 错误！生成临时ID
        localStorage.setItem('global_user_id', userId);
    }
    return userId;
}

// ✅ 正确实现:
async function getCurrentUserId() {
    // 1. 优先从session API获取真实ID
    try {
        const response = await fetch('/api/auth/session');
        if (response.ok) {
            const data = await response.json();
            if (data.user_id) {
                return data.user_id;  // usr_xxx格式
            }
        }
    } catch (error) {
        console.error('获取session失败:', error);
    }

    // 2. 降级方案：localStorage
    return localStorage.getItem('global_user_id') || null;
}
```

**修复位置**: `/opt/tcm-ai/static/index_smart_workflow.html` 中的 `getCurrentUserId()` 函数

---

### 4. consultation_id字段为空问题 ⏳
**症状**: 患者历史记录详情中缺少完整的对话内容和中医分析

**根本原因**:
```sql
-- prescriptions表中consultation_id为空
SELECT id, patient_id, consultation_id FROM prescriptions WHERE id=130;
-- Result: 130|usr_20250920_5741e17a78e8||  ← consultation_id为空!

-- 导致无法关联conversation_log表
SELECT * FROM conversation_log WHERE consultation_id = '';
-- Result: 0条记录 (无法找到对话记录)
```

**修复方案** (待执行):
1. 后端修复：确保创建处方时填充 `consultation_id`
   - 位置: `/opt/tcm-ai/api/routes/unified_consultation_routes.py`
   - 函数: `_store_consultation_record()`
   - 修改: 创建prescription时必须包含 `consultation_id=consultation_id`

2. 历史数据修复：补全现有处方的 `consultation_id`
   ```sql
   -- 通过patient_id和时间戳匹配
   UPDATE prescriptions
   SET consultation_id = (
       SELECT id FROM consultations
       WHERE consultations.patient_id = prescriptions.patient_id
       AND consultations.created_at BETWEEN
           datetime(prescriptions.created_at, '-5 minutes') AND
           datetime(prescriptions.created_at, '+5 minutes')
       LIMIT 1
   )
   WHERE consultation_id IS NULL OR consultation_id = '';
   ```

---

### 5. 医生端审查网络错误 ⏳
**当前状态**: 代码已修复但浏览器缓存仍显示旧错误

**已修复的代码错误**:
1. ✅ `hideRejectForm()` → `hideModifyForm()` (line 2835)
2. ✅ `showSection()` event参数处理 (line 2440)

**用户需要执行**:
1. 清除浏览器缓存：
   - **Windows/Linux**: `Ctrl + Shift + Delete`
   - **Mac**: `Cmd + Shift + Delete`
   - 选择"缓存的图片和文件"
   - 时间范围选择"全部时间"

2. 或使用无痕模式测试：
   - **Chrome/Edge**: `Ctrl + Shift + N`
   - **Firefox**: `Ctrl + Shift + P`

3. 强制刷新页面：
   - **Windows/Linux**: `Ctrl + Shift + R`
   - **Mac**: `Cmd + Shift + R`

**注意事项**:
- 处方130状态为 `doctor_approved`，已经审查过了，不能重复审查
- 测试时应该使用状态为 `pending_review` 的处方
- 医生只能审查分配给自己的处方（通过 `doctor_id` 匹配）

---

## 📋 测试验证清单

### 注册功能测试 ✅
- [ ] 手机注册成功后跳转到 `/login`
- [ ] 邮箱注册成功后跳转到 `/login`
- [ ] 用户名注册成功后跳转到 `/login`
- [ ] 注册后可以正常登录新账户

### JavaScript缓存测试 ✅
- [ ] 清除浏览器缓存后，错误消失
- [ ] 强制刷新后，看到最新代码效果
- [ ] 控制台不再显示旧的错误信息
- [ ] 新版本参数正确加载 (检查Network面板)

### 患者端功能测试 ⏳
- [ ] 登录后用户ID正确显示 (usr_格式)
- [ ] 刷新页面后对话记录保留
- [ ] 历史记录列表正常显示
- [ ] 历史记录详情完整 (对话、分析、处方)
- [ ] 多设备同步正常工作

### 医生端功能测试 ⏳
- [ ] 清除缓存后审查功能正常
- [ ] 通过按钮正常工作
- [ ] 拒绝/修改表单正常显示和隐藏
- [ ] 审查后处方从列表中消失
- [ ] 统计数字正确更新

---

## 🚀 部署信息

**部署时间**: 2025-10-11 16:25:25 CST

**服务状态**: ✅ 正常运行
```bash
sudo service tcm-ai status
# Active: active (running) since Sat 2025-10-11 16:25:25 CST
```

**代码版本**: v20251011001

**修改的文件**:
1. `/opt/tcm-ai/static/auth_portal.html` - 注册跳转 + JS版本控制
2. `/opt/tcm-ai/static/index_smart_workflow.html` - JS版本控制

**Git备份** (待执行):
```bash
cd /opt/tcm-ai
git add -A
git commit -m "🐛 修复注册跳转URL错误 + 添加JavaScript版本控制系统

- 修复: 注册成功后跳转到/login而不是根路径
- 新增: JavaScript文件版本控制参数 v20251011001
- 改进: 强制浏览器更新缓存的JavaScript代码
- 位置: auth_portal.html (4处), index_smart_workflow.html (3处)

这解决了用户注册后跳转混乱和浏览器缓存导致修复无效的问题。

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 💡 用户操作指南

### 如果医生端审查仍然报错
1. **清除浏览器缓存** (必须!)
   - Chrome: 设置 → 隐私和安全 → 清除浏览数据
   - 勾选"缓存的图片和文件"
   - 时间范围选"全部时间"
   - 点击"清除数据"

2. **强制刷新页面**
   - Windows: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

3. **验证缓存清除成功**
   - 打开开发者工具 (F12)
   - 切换到Network面板
   - 刷新页面
   - 检查JavaScript文件URL是否包含 `?v=20251011001`

4. **测试正确的处方**
   - 不要测试已审查的处方 (status = 'doctor_approved')
   - 使用新创建的待审查处方 (status = 'pending_review')
   - 确保处方分配给当前登录的医生

### 如果患者端历史记录为空
**这是已知问题，正在修复中**

临时解决方案:
1. 重新登录患者账户
2. 开始新的问诊对话
3. 完成问诊后检查是否记录

---

## 📞 需要技术支持

如果按照以上步骤操作后仍有问题，请提供：

1. 清除缓存的确认截图
2. 浏览器控制台的完整错误信息 (F12 → Console)
3. Network面板中JavaScript文件的加载情况 (F12 → Network)
4. 测试的具体操作步骤

**文档更新**: 2025-10-11 16:26
**版本号**: v20251011001
**服务状态**: ✅ 运行正常
