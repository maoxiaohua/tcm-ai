# 历史决策树功能调试指南 - 2025-10-19

## ✅ 后端已修复并验证

### 修复内容
1. ✅ 添加了缺失的 `import sqlite3`
2. ✅ 统一医生ID为 `anonymous_doctor`
3. ✅ 修复了字段名（`id` vs `pattern_id`）

### API测试验证
```bash
curl -X GET "http://127.0.0.1:8000/api/get_doctor_patterns/anonymous_doctor"
```

**结果**: ✅ 成功返回1条决策树数据

```json
{
    "success": true,
    "message": "找到 1 个临床决策模式",
    "data": {
        "doctor_id": "anonymous_doctor",
        "patterns": [
            {
                "pattern_id": "f20c3d0a-265d-4aba-b17e-79dc54339a1b",
                "disease_name": "脾胃虚寒型胃痛",
                ...
            }
        ],
        "total_count": 1
    }
}
```

---

## 🔍 前端调试步骤

### 第1步：清除浏览器缓存

**⚠️ 非常重要！必须清除缓存才能加载新的JavaScript代码**

#### 方法1：硬刷新（推荐）
- **Windows/Linux**: `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`

#### 方法2：手动清除
1. 按 `F12` 打开开发者工具
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

#### 方法3：无痕模式
- **Windows/Linux**: `Ctrl + Shift + N`
- **Mac**: `Cmd + Shift + N`
- 访问 https://mxh0510.cn/static/decision_tree_visual_builder.html

---

### 第2步：打开浏览器控制台

1. 访问 https://mxh0510.cn/static/decision_tree_visual_builder.html
2. 按 `F12` 打开开发者工具
3. 切换到"Console"（控制台）标签页

---

### 第3步：点击"📋 历史"按钮

点击页面顶部的"📋 历史"按钮

---

### 第4步：查看控制台输出

**应该看到以下调试日志**：

```
🔍 查询历史决策树 - 医生ID: anonymous_doctor
🔍 当前用户信息: {...}
🔍 localStorage userData: ...
🔍 API响应状态: 200 OK
🔍 API返回数据: {success: true, message: '找到 1 个临床决策模式', data: {...}}
🔍 data.success: true
🔍 data.data: {doctor_id: 'anonymous_doctor', patterns: Array(1), total_count: 1}
🔍 data.data.patterns: [{pattern_id: '...', disease_name: '脾胃虚寒型胃痛', ...}]
🔍 patterns数量: 1
✅ 找到决策树，准备显示: 1 条
```

---

## 📊 根据日志诊断问题

### 情况1: 医生ID不是anonymous_doctor

**日志显示**:
```
🔍 查询历史决策树 - 医生ID: null
```
或
```
🔍 查询历史决策树 - 医生ID: some_other_id
```

**原因**: 浏览器缓存了旧的JavaScript代码

**解决**: 强制硬刷新（Ctrl + Shift + R）

---

### 情况2: API返回失败

**日志显示**:
```
🔍 API响应状态: 500 Internal Server Error
```
或
```
🔍 data.success: false
```

**原因**: 服务器错误

**解决**:
```bash
# 查看服务器日志
sudo journalctl -u tcm-ai -n 50

# 重启服务
sudo service tcm-ai restart
```

---

### 情况3: 没有调试日志

**症状**: 点击历史按钮后，控制台没有任何 `🔍` 开头的日志

**原因**:
1. JavaScript缓存未清除
2. JavaScript加载失败
3. 事件绑定失败

**解决**:
1. 硬刷新页面
2. 检查控制台是否有JavaScript错误（红色文字）
3. 使用无痕模式重新测试

---

### 情况4: API返回数据但不显示

**日志显示**:
```
🔍 API返回数据: {success: true, ...}
🔍 patterns数量: 1
⚠️ 没有找到决策树或数据格式错误
```

**原因**: 数据格式判断逻辑有问题

**解决**: 请将完整的控制台日志截图发给我分析

---

## 🧪 完整测试流程

### 测试A: 保存新决策树

1. 清除浏览器缓存
2. 访问决策树页面
3. 填写信息并生成决策树
4. 点击"💾 保存"
5. 填写表单（临床思维描述可留空）
6. 点击"🧠 保存到思维库"
7. **预期**: 提示保存成功

---

### 测试B: 查看历史记录

1. 按 `F12` 打开控制台
2. 点击"📋 历史"按钮
3. **查看控制台日志**
4. **预期**:
   - 看到完整的调试日志
   - 弹窗显示1条决策树

---

### 测试C: 加载历史决策树

1. 在历史列表中点击"📖 加载"按钮
2. **预期**: 决策树加载到画布上

---

## 🔧 数据库验证

如果前端显示有问题，可以验证数据库：

```bash
# 查看所有决策树
sqlite3 /opt/tcm-ai/data/user_history.sqlite \
  "SELECT id, doctor_id, disease_name FROM doctor_clinical_patterns;"

# 输出应该类似：
# f20c3d0a-265d-4aba-b17e-79dc54339a1b|anonymous_doctor|脾胃虚寒型胃痛
```

---

## 📸 需要的调试信息

如果问题仍未解决，请提供以下信息：

1. **浏览器控制台截图**
   - 显示所有 `🔍` 开头的日志
   - 显示任何红色的错误信息

2. **网络请求信息**
   - 在开发者工具中切换到"Network"标签
   - 点击"📋 历史"按钮
   - 找到 `get_doctor_patterns` 请求
   - 查看响应内容

3. **页面显示**
   - 历史对话框的截图

---

## 🎯 已知问题和解决方案

### 问题1: "暂无历史决策树"但数据库有数据

**原因**: 医生ID不匹配或浏览器缓存

**解决**:
1. 硬刷新（Ctrl + Shift + R）
2. 查看控制台日志中的医生ID
3. 如果不是 `anonymous_doctor`，使用无痕模式

---

### 问题2: 保存成功但立即查看历史为空

**原因**:
- 保存和查询使用了不同的医生ID（已修复）
- 浏览器缓存

**解决**:
1. 刷新页面
2. 重新点击"📋 历史"

---

### 问题3: 控制台没有任何日志

**原因**: JavaScript文件被缓存

**解决**:
1. 按 `Ctrl + Shift + R` 硬刷新
2. 或在无痕窗口中打开页面

---

## 📋 完整检查清单

测试前请确认：

- [ ] 已清除浏览器缓存（硬刷新或无痕模式）
- [ ] 已打开浏览器开发者工具（F12）
- [ ] 已切换到Console控制台标签页
- [ ] 服务器正在运行（`sudo service tcm-ai status`）
- [ ] 数据库中有决策树数据（使用SQL查询验证）

测试步骤：

- [ ] 点击"📋 历史"按钮
- [ ] 查看控制台日志
- [ ] 检查医生ID是否为 `anonymous_doctor`
- [ ] 检查API是否返回成功
- [ ] 检查patterns数组是否有数据
- [ ] 截图控制台日志（如果有问题）

---

## 🚀 预期结果

成功后应该看到：

1. **控制台日志**:
   ```
   ✅ 找到决策树，准备显示: 1 条
   ```

2. **历史对话框**:
   - 显示决策树列表
   - 包含疾病名称、节点数、创建时间
   - 有"📖 加载"和"🗑️ 删除"按钮

3. **点击加载**:
   - 决策树显示在画布上
   - 包含所有节点和连接

---

## 联系支持

如果按照上述步骤仍无法解决，请提供：

1. 完整的浏览器控制台日志截图
2. Network面板中API请求的截图
3. 历史对话框的截图
4. 使用的浏览器和版本信息

---

**更新时间**: 2025-10-19 10:54
**状态**: 等待用户测试反馈
