# 决策树构建器认证修复测试

## 修复的问题
1. **API端点错误**: `/api/auth/doctor/current` (404) → `/api/v2/auth/profile` (正确)
2. **用户数据持久化**: 页面刷新时丢失 `currentUser` 和 `isAuthenticated`
3. **数据结构适配**: 适配新的统一认证API返回格式

## 修复内容

### 1. API端点修正
```javascript
// 修复前
const response = await fetch('/api/auth/doctor/current', {
    headers: { 'Authorization': `Bearer ${token}` }
});

// 修复后
const response = await fetch('/api/v2/auth/profile', {
    headers: { 'Authorization': `Bearer ${token}` }
});
```

### 2. 数据提取和适配
```javascript
// 修复后：适配统一认证API的响应格式
const result = await response.json();
const data = result.user || result;

// 构建标准化的currentUser对象
currentUser = {
    user_id: data.global_user_id || data.user_id,
    name: data.display_name || data.username,
    role: data.role,
    username: data.username
};

// 持久化到localStorage
localStorage.setItem('userData', JSON.stringify(currentUser));
```

### 3. 数据流向
```
页面加载
  ↓
DOMContentLoaded事件
  ↓
initializeAuth()
  ↓
checkExistingAuth()
  ↓
GET /api/v2/auth/profile (带token)
  ↓
认证成功 → 设置currentUser + isAuthenticated
  ↓
保存到localStorage('userData')
  ↓
loadDoctorHistoryTrees()
  ↓
getCurrentDoctorId() → 从currentUser.user_id获取
  ↓
GET /api/get_doctor_patterns/{user_id}
```

## 测试步骤

1. 清除浏览器缓存和localStorage
2. 以医生账户登录系统
3. 进入决策树构建器页面
4. 观察控制台日志：
   - ✅ 应该看到 "📡 API响应状态: 200"
   - ✅ 应该看到 "✅ 认证成功" 和用户数据
   - ✅ 应该看到 "🔄 认证成功,开始加载历史特色诊疗方案..."
5. 刷新页面
6. 验证：
   - ✅ 页面不应该跳转到医生管理界面
   - ✅ 用户状态应该保持
   - ✅ 可以正常使用AI生成功能

## 预期日志

### 成功的日志：
```
🔐 开始认证初始化...
🔍 检查认证状态: {hasToken: true, ...}
📡 API响应状态: 200
✅ 认证成功: {user: {...}, ...}
👤 当前用户: {user_id: "usr_...", name: "金大夫", ...}
🔄 认证成功,开始加载历史特色诊疗方案...
✅ 历史特色诊疗方案加载完成
```

### 失败的日志（修复前）：
```
📡 API响应状态: 404
❌ 认证失败: 404 Not Found
→ 重定向到登录页
```

## 相关文件
- `/opt/tcm-ai/static/decision_tree_visual_builder.html` (前端修复)
- `/opt/tcm-ai/api/routes/unified_auth_routes.py` (后端API)

