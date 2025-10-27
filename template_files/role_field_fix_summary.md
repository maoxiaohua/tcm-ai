# 角色字段不匹配问题修复

## 问题现象
- 访问决策树构建器时提示："此页面仅限医生账户访问"
- 明明使用的是医生账户（jingdaifu/金大夫），但仍然无法访问

## 根本原因

### 1. API返回字段不一致
**后端API** (`/api/v2/auth/profile`) 返回的用户数据结构：
```json
{
  "success": true,
  "user": {
    "id": "usr_20250920_575ba94095a7",
    "username": "jingdaifu",
    "display_name": "金大夫",
    "primary_role": "doctor",  ← 字段名是 primary_role
    ...
  }
}
```

**前端代码**期望的字段名：
```javascript
if (data.role !== 'doctor') {  ← 期望的是 role 字段
    alert('⚠️ 此页面仅限医生账户访问');
    redirectToLogin();
    return;
}
```

### 2. 字段名映射错误
- 后端使用：`primary_role`
- 前端期望：`role`
- 结果：`data.role` 为 `undefined`
- 判断：`undefined !== 'doctor'` → true → 拒绝访问

## 修复方案

### 修复前
```javascript
const data = result.user || result;

// ❌ 错误：直接使用 data.role
if (data.role !== 'doctor') {
    alert('⚠️ 此页面仅限医生账户访问');
    redirectToLogin();
    return;
}

currentUser = {
    user_id: data.global_user_id || data.user_id,
    name: data.display_name || data.username,
    role: data.role,  // ← undefined
    username: data.username
};
```

### 修复后
```javascript
const data = result.user || result;

// ✅ 修复：兼容多种字段名
const userRole = data.primary_role || data.role;
console.log('👤 用户角色:', userRole);

if (userRole !== 'doctor') {
    alert(`⚠️ 此页面仅限医生账户访问\n当前角色: ${userRole || '未知'}`);
    redirectToLogin();
    return;
}

currentUser = {
    user_id: data.id || data.global_user_id || data.user_id,
    name: data.display_name || data.username,
    role: userRole,  // ✅ 正确获取角色
    username: data.username
};
```

## 增强的调试功能

添加了详细的日志输出，便于排查类似问题：
```javascript
console.log('📊 用户数据详情:', JSON.stringify(data, null, 2));
console.log('👤 用户角色:', userRole);
console.log('💾 用户数据已保存:', currentUser);
```

## 修复后的完整流程

```
1. 用户访问页面
   ↓
2. checkExistingAuth() 检查localStorage中的token
   ↓
3. 调用 GET /api/v2/auth/profile
   ↓
4. 后端返回：{ user: { primary_role: "doctor", ... } }
   ↓
5. 前端提取：userRole = data.primary_role || data.role
   ↓
6. 验证角色：userRole === "doctor" ✅
   ↓
7. 设置 currentUser 和 isAuthenticated
   ↓
8. 保存到 localStorage
   ↓
9. 加载历史特色诊疗方案
   ↓
10. 页面正常显示 ✅
```

## 相关代码位置

- **前端文件**: `/opt/tcm-ai/static/decision_tree_visual_builder.html`
  - 函数：`checkExistingAuth()` (第1172行)
  
- **后端API**: `/opt/tcm-ai/api/routes/unified_auth_routes.py`
  - 端点：`GET /api/v2/auth/profile` (第308行)
  - 函数：`format_user_response()` (第99行)

## 验证步骤

1. 清除浏览器缓存和localStorage
2. 以医生账户登录（jingdaifu）
3. 从医生管理界面点击"决策树可视化构建器"
4. 打开浏览器开发者工具（F12）→ Console
5. 观察日志输出：
   ```
   📡 API响应状态: 200
   ✅ 认证成功: {...}
   📊 用户数据详情: {...}
   👤 用户角色: doctor
   💾 用户数据已保存: {...}
   ```
6. 页面应该正常显示，不再提示"仅限医生账户访问"

## 总结

这是一个典型的**前后端数据契约不一致**问题：
- 后端API字段命名变更（`role` → `primary_role`）
- 前端代码未同步更新
- 导致字段读取失败，角色验证失败

修复方法是采用**兼容性读取**：
```javascript
const userRole = data.primary_role || data.role;
```

这样既支持新的字段名，也兼容可能存在的旧字段名。
