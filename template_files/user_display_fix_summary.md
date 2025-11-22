# 用户显示名称修复总结

## 问题描述
患者账户 `maoxiaohua` 登录后，历史记录页面显示 "游客用户" 而非正确的用户名。

## 根本原因
虽然用户数据正确加载到localStorage：
```javascript
{
  username: "maoxiaohua",
  display_name: "maoxiaohua",
  primary_role: "patient",
  id: "usr_20250920_5741e17a78e8"
}
```

但是 `updateUserInfo()` 函数在页面初始化时没有被正确调用。

## 已实施的修复

### 1. 增强 loadCurrentUser() 日志追踪
**文件**: `/opt/tcm-ai/static/js/user_history_main.js` (第62-85行)

```javascript
async loadCurrentUser() {
    try {
        console.log('🔄 loadCurrentUser: 开始加载用户信息...');
        const user = await this.api.getCurrentUser();
        console.log('🔄 loadCurrentUser: API返回用户数据:', user);

        if (user) {
            this.currentUserId = user.id || user.user_id;
            console.log('✅ 当前用户ID:', this.currentUserId);

            // 🔑 关键修复：确保调用updateUserInfo
            console.log('🔄 loadCurrentUser: 调用updateUserInfo更新UI...');
            this.updateUserInfo(user);
            console.log('✅ loadCurrentUser: UI更新完成');
        } else {
            this.currentUserId = localStorage.getItem('device_id') || 'guest';
            console.warn('⚠️ 无用户数据，使用设备ID:', this.currentUserId);
        }
    } catch (error) {
        console.error('❌ 获取用户信息失败:', error);
        this.currentUserId = localStorage.getItem('device_id') || 'guest';
    }
}
```

### 2. 修复 updateUserInfo() 字段优先级
**文件**: `/opt/tcm-ai/static/js/user_history_main.js` (第149-181行)

```javascript
updateUserInfo(user) {
    const avatarEl = document.getElementById('userAvatar');
    const nameEl = document.getElementById('userName');
    const typeEl = document.getElementById('userType');

    // 🔧 修复：优先使用username或display_name，而不是name字段
    const displayName = user.username || user.display_name || user.phone_number || user.phone || user.name || '游客用户';
    const avatarText = displayName.charAt(0).toUpperCase();

    console.log('🔍 updateUserInfo - 用户数据:', {
        username: user.username,
        display_name: user.display_name,
        name: user.name,
        phone_number: user.phone_number,
        phone: user.phone,
        最终显示名: displayName
    });

    if (avatarEl) {
        avatarEl.textContent = avatarText;
        console.log('✅ 更新头像:', avatarText);
    }
    if (nameEl) {
        nameEl.textContent = displayName;
        console.log('✅ 更新用户名:', displayName);
    }
    if (typeEl) {
        const userType = (user.phone_number || user.phone) ? '已绑定手机' : '设备用户';
        typeEl.textContent = userType;
        console.log('✅ 更新用户类型:', userType);
    }
}
```

## 验证步骤

### 用户需要执行的操作
1. **硬刷新页面**: 按 `Ctrl+F5` (Windows/Linux) 或 `Cmd+Shift+R` (Mac)
2. **打开浏览器控制台**: 按 `F12`
3. **查看Console标签页**

### 预期的控制台输出
```
🚀 用户历史记录应用初始化...
🔄 loadCurrentUser: 开始加载用户信息...
✅ 从localStorage获取用户信息: {username: "maoxiaohua", display_name: "maoxiaohua", ...}
🔄 loadCurrentUser: API返回用户数据: {username: "maoxiaohua", ...}
✅ 当前用户ID: usr_20250920_5741e17a78e8
🔄 loadCurrentUser: 调用updateUserInfo更新UI...
🔍 updateUserInfo - 用户数据: {
    username: "maoxiaohua",
    display_name: "maoxiaohua",
    name: undefined,
    phone_number: undefined,
    phone: undefined,
    最终显示名: "maoxiaohua"
}
✅ 更新头像: M
✅ 更新用户名: maoxiaohua
✅ 更新用户类型: 设备用户
✅ loadCurrentUser: UI更新完成
```

### 预期的页面显示
- **用户头像**: `M` (maoxiaohua的首字母)
- **用户名**: `maoxiaohua`
- **用户类型**: `设备用户` (如果未绑定手机) 或 `已绑定手机`

## 如果仍显示"游客用户"

### 诊断步骤
1. 检查控制台是否有 `🔍 updateUserInfo - 用户数据:` 日志
   - ✅ 有日志 → 说明函数被调用，检查字段值
   - ❌ 无日志 → 说明函数未被调用，检查初始化流程

2. 检查localStorage数据：
```javascript
// 在控制台运行
console.log('当前用户数据:', JSON.parse(localStorage.getItem('currentUser')));
console.log('用户数据:', JSON.parse(localStorage.getItem('userData')));
```

3. 手动测试updateUserInfo：
```javascript
// 在控制台运行
const user = JSON.parse(localStorage.getItem('currentUser'));
const app = new UserHistoryApp();
app.updateUserInfo(user);
```

## 相关提交记录
- `dc7e5a0`: 增强用户信息初始化日志和字段映射修复
- `441b8cb`: 修复用户显示名称字段优先级
- `0aeaaef`: 创建用户数据修复工具

## 备用修复方案

如果页面刷新后仍显示"游客用户"，可以使用以下任一方法：

### 方案1: 控制台快速修复
打开浏览器控制台 (F12)，粘贴运行：
```javascript
(function() {
    const user = JSON.parse(localStorage.getItem('currentUser'));
    if (!user) {
        console.error('❌ 未找到用户数据');
        return;
    }

    const displayName = user.username || user.display_name || user.phone_number || '游客用户';

    document.getElementById('userAvatar').textContent = displayName.charAt(0).toUpperCase();
    document.getElementById('userName').textContent = displayName;
    document.getElementById('userType').textContent = user.phone_number ? '已绑定手机' : '设备用户';

    console.log('✅ 用户信息已更新:', displayName);
})();
```

### 方案2: 访问修复工具页面
访问: `http://mxh0510.cn/static/fix_user_display.html`

点击 "🔍 检查用户数据" → "✅ 自动修复" → "🔄 刷新页面"

## 技术说明

### 字段优先级逻辑
```javascript
user.username           // 优先级1: 用户名 (最准确)
|| user.display_name    // 优先级2: 显示名称
|| user.phone_number    // 优先级3: 手机号
|| user.phone           // 优先级4: 备用手机号字段
|| user.name            // 优先级5: 通用名称 (可能被污染)
|| '游客用户'            // 优先级6: 默认值
```

### 为何不优先使用name字段
在之前的bug中发现，`user.name` 字段可能被错误地设置为医生名称（如"金大夫"），因此将其优先级降到最低。

---

**最后更新**: 2025-11-19
**修复版本**: v2.9.1
