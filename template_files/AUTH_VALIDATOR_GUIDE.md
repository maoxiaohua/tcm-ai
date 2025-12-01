# Session认证验证器 - 使用指南

## 🎯 功能概述

新增的`AuthValidator`系统自动监控用户登录状态，当session过期时友好提示用户，避免"看起来已登录但实际已过期"的困惑。

---

## ✨ 新增功能

### 1. 页面加载时自动验证
- 页面加载2秒后自动验证session
- 如果发现已过期，立即提示并清理状态

### 2. 定期心跳检查
- 每5分钟自动验证一次session
- 防止用户长时间停留后操作失败

### 3. 全局API错误拦截
- 拦截所有API请求的401错误
- 自动触发登录过期处理流程

### 4. 友好的过期提示
- 美观的模态框提示，而不是简单的alert
- 自动清理本地数据
- 5秒后自动跳转登录页

---

## 📊 用户体验流程

### 场景1: 页面刚加载，session已过期

```
用户操作                 系统响应
───────────────────────────────────────────────
打开页面                 ✅ 页面正常加载
                        ✅ auth_validator.js加载
                        ⏳ 2秒后开始验证...
                        🔍 调用 /api/auth/validate-session
                        ❌ 返回 valid: false
                        💬 显示友好提示模态框:
                           ┌──────────────────────┐
                           │       ⏰             │
                           │   登录已过期         │
                           │  请重新登录          │
                           │  [重新登录按钮]       │
                           └──────────────────────┘
                        🧹 清除本地token和用户信息
                        🎨 UI切换到登出状态
                        ⏱️ 5秒后自动跳转 /login
```

### 场景2: 用户正在使用，切换医生时session过期

```
用户操作                 系统响应
───────────────────────────────────────────────
点击"张仲景"头像         🔄 调用 SessionManager.switchDoctor()
                        📡 POST /api/conversation/switch-doctor
                        ❌ 返回 401 Unauthorized

                        🛡️ 全局拦截器捕获401
                        💬 显示"登录已过期"模态框
                        🧹 清除过期数据
                        ⏱️ 1秒后跳转登录页
```

### 场景3: 用户长时间停留（超过5分钟）

```
时间轴                   系统行为
───────────────────────────────────────────────
09:00  用户登录          ✅ Session有效
09:05  心跳检查          ✅ Session有效
09:10  心跳检查          ✅ Session有效
09:15  心跳检查          ❌ Session已过期
                        💬 立即显示过期提示
                        🔄 引导用户重新登录
```

---

## 🔧 技术实现

### 新增文件

1. **`/static/js/auth_validator.js`**
   - AuthValidator类：核心验证逻辑
   - 全局实例：`window.authValidator`

2. **后端API**
   - `GET /api/auth/validate-session`
   - 轻量级session验证端点

### 修改文件

1. **`/static/index_smart_workflow.html`**
   - 新增：`<script src="/static/js/auth_validator.js?v=20251201001"></script>`

2. **`/static/js/smart_workflow_init.js`**
   - 新增：AuthValidator启动代码
   ```javascript
   if (window.authValidator) {
       window.authValidator.setupGlobalErrorHandler();
       window.authValidator.startHeartbeat();
   }
   ```

3. **`/static/js/session_manager.js`**
   - 增强：401错误特殊处理
   - 添加：自动清理和跳转逻辑

---

## 🧪 测试场景

### 测试1: 模拟session过期

**方法A**: 直接修改数据库（推荐）
```bash
# 将session状态改为expired
sqlite3 /opt/tcm-ai/data/user_history.sqlite "UPDATE unified_sessions SET session_status='expired' WHERE user_id='usr_20250920_5741e17a78e8';"

# 刷新页面，应该看到过期提示
```

**方法B**: 等待自然过期
```bash
# 查看session过期时间
sqlite3 /opt/tcm-ai/data/user_history.sqlite "SELECT expires_at FROM unified_sessions WHERE user_id='usr_20250920_5741e17a78e8';"

# 等到过期时间后刷新页面
```

### 测试2: 验证API调用时的401拦截

1. 确保session已过期
2. 刷新页面，忽略提示
3. 尝试切换医生
4. 应该看到"登录已过期"提示

### 测试3: 心跳检查

1. 登录系统
2. 打开Console，观察日志
3. 2秒后应该看到：`✅ Session验证通过`
4. 5分钟后应该再次看到验证日志

---

## 📝 配置选项

### 修改心跳检查间隔

编辑 `/static/js/auth_validator.js`:
```javascript
this.checkInterval = 5 * 60 * 1000; // 默认5分钟
// 改为3分钟:
this.checkInterval = 3 * 60 * 1000;
```

### 修改自动跳转延迟

编辑 `/static/js/auth_validator.js`:
```javascript
setTimeout(() => {
    window.location.href = '/login';
}, 5000);  // 默认5秒

// 改为10秒:
}, 10000);
```

### 禁用自动验证（调试用）

编辑 `/static/js/smart_workflow_init.js`:
```javascript
// 注释掉这两行
// window.authValidator.setupGlobalErrorHandler();
// window.authValidator.startHeartbeat();
```

---

## 🐛 问题排查

### 问题1: 提示框不显示

**检查**:
1. Console是否有错误？
2. `window.authValidator`是否存在？
3. auth_validator.js是否正确加载？

**解决**:
```javascript
// 在Console中测试
window.authValidator.showExpirationNotice();
```

### 问题2: 心跳检查过于频繁

**症状**: 大量日志输出
**原因**: 多个组件重复调用
**解决**: 检查`this.isValidating`标志是否生效

### 问题3: 401错误未被拦截

**检查**:
```javascript
// 在Console中检查fetch是否被重写
console.log(window.fetch.toString().includes('authValidator'));
// 应该返回 true
```

---

## 🎨 界面定制

### 修改模态框样式

编辑 `/static/js/auth_validator.js` 的 `showExpirationNotice()` 方法：

```javascript
// 修改颜色
background: #4CAF50;  // 改为其他颜色，如 #2196F3 (蓝色)

// 修改图标
<div style="font-size: 48px;">⏰</div>
// 改为其他emoji: 🔒 🚪 ⚠️

// 修改文案
<h2>登录已过期</h2>
// 改为: <h2>会话超时</h2>
```

---

## 📊 监控和日志

### Console日志输出

正常情况：
```
🔐 认证验证器已初始化
✅ AuthValidator全局实例已创建: window.authValidator
🛡️ 全局API错误拦截器已启动
💓 Session心跳检查已启动（间隔: 300秒）
✅ Session验证通过
```

Session过期时：
```
⚠️ Session已过期（后端返回401）
❌ Session已过期 (原因: backend_validation_failed)
🧹 已清除本地认证数据
🎨 UI已更新为登出状态
💬 已显示过期提示模态框
```

### 后端日志

```bash
# 查看session验证日志
sudo journalctl -u tcm-ai -f | grep "validate-session"

# 应该看到类似输出:
# INFO: GET /api/auth/validate-session
# INFO: Session验证: valid=false, reason=session_not_found_or_expired
```

---

## 🔄 版本历史

### v4.1 (2025-12-01)
- ✅ 新增 AuthValidator 系统
- ✅ 新增 `/api/auth/validate-session` API
- ✅ 全局401错误拦截
- ✅ 友好的过期提示UI

---

## 💡 最佳实践

1. **定期监控session过期率**
   - 如果过期频繁，考虑延长session有效期

2. **用户友好提示**
   - 当前实现已经很友好，避免简单粗暴的alert()

3. **自动重试机制**（可选）
   - 对于某些非关键API，可以静默刷新token后重试

4. **离线检测**
   - 区分"网络离线"和"session过期"，提供不同提示

---

## 🎯 下一步优化建议

### 短期优化
1. 添加"记住我"功能，延长session有效期
2. 在过期前5分钟弹出"即将过期"提示
3. 支持静默刷新token（无感知续期）

### 长期优化
1. 使用JWT替代session，减少数据库查询
2. 支持多设备登录管理
3. 添加异常登录检测（IP变化、设备变化）

---

**总结**: 新的AuthValidator系统彻底解决了"看起来已登录但实际已过期"的用户体验问题，提供了专业、友好的session管理机制。
