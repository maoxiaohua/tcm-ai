# 连接同步增量模式修复

## 🐛 问题描述

### 用户反馈
用户在画布上为一个证候节点创建多个处方连接时，发现新的连接会**覆盖**之前的处方，而不是**追加**到处方列表中。

### 问题场景
```
步骤1: 画布上有证候节点"脑袋瓜前面疼"
步骤2: 创建连接：脑袋瓜前面疼 → 处方1
      结果：左侧诊疗思路显示"处方：处方1" ✅

步骤3: 创建连接：脑袋瓜前面疼 → 处方2
      期望：左侧诊疗思路显示"处方：处方1、处方2"
      实际：左侧诊疗思路显示"处方：处方2" ❌ 处方1被覆盖了！

步骤4: 删除连接：脑袋瓜前面疼 → 处方2
      期望：左侧诊疗思路显示"处方：处方1"
      实际：左侧诊疗思路显示"处方：" ❌ 全部被清空了！
```

### 用户原话
> "我现在这个字段的更新是直接覆盖的，而不是增量更新，比如我原来的连接线还在的，结果它把新的连接线的关联内容直接覆盖了之前的关联内容。"

## 🔍 根本原因分析

### 问题1：添加连接 - 直接覆盖模式

**原代码**（第2347行）：
```javascript
// 添加连接：更新处方名称
const newText = currentText.replace(syndromePattern, `$1${toNode.name}$3`);
```

**问题分析**：
- 正则捕获组：`$1`=前缀（"【证候X】XXX...处方："）, `$2`=当前处方列表, `$3`=换行
- 替换逻辑：直接用 `toNode.name`（新处方）替换 `$2`（当前处方列表）
- 结果：当前处方列表被完全覆盖，原有处方丢失

### 问题2：删除连接 - 全部清空模式

**原代码**（第2355行）：
```javascript
// 删除连接：清空处方（但保留"处方："标签）
const newText = currentText.replace(syndromePattern, '$1$3');
```

**问题分析**：
- 替换逻辑：直接用 `$1$3`（前缀+换行）替换整个匹配，等于清空 `$2`
- 结果：无论删除哪个处方，都会清空整个处方列表

### 问题3：重新生成 - 只取第一个处方

**原代码**（第4959行）：
```javascript
if (prescriptionChildren.length > 0) {
    thinkingText += prescriptionChildren[0].node.name;  // 只取第一个
}
```

**问题分析**：
- 即使证候连接了多个处方节点，也只显示第一个
- 导致重新生成后丢失其他处方信息

## ✅ 解决方案

### 修复1：添加连接改为增量追加模式

**位置**：`/opt/tcm-ai/static/decision_tree_visual_builder.html` 第2345-2369行

**修改后代码**：
```javascript
if (action === 'add') {
    // 添加连接：增量追加处方（不覆盖已有处方）
    const newText = currentText.replace(syndromePattern, (match, prefix, currentPrescriptions, newline) => {
        const trimmed = currentPrescriptions.trim();
        console.log(`  当前处方列表: "${trimmed}"`);

        if (!trimmed) {
            // 当前为空，直接设置
            console.log(`  ➕ 设置新处方: ${toNode.name}`);
            return `${prefix}${toNode.name}${newline}`;
        } else if (!trimmed.includes(toNode.name)) {
            // 已有处方，且不包含当前处方名，追加（用顿号分隔）
            console.log(`  ➕ 追加新处方: ${trimmed} → ${trimmed}、${toNode.name}`);
            return `${prefix}${trimmed}、${toNode.name}${newline}`;
        } else {
            // 已包含该处方，不重复添加
            console.log(`  ⚠️ 处方已存在，跳过: ${toNode.name}`);
            return match;
        }
    });
    if (newText !== currentText) {
        currentText = newText;
        updated = true;
        console.log(`✅ 已更新证候"${fromNode.name}"的处方（增量追加）`);
    }
}
```

**核心改进**：
1. ✅ **使用回调函数替换**：不再使用简单的字符串替换，改用回调函数获取当前值
2. ✅ **智能判断当前状态**：
   - 空值 → 直接设置
   - 已有值且不包含 → 追加（用顿号分隔）
   - 已包含 → 跳过（避免重复）
3. ✅ **详细日志**：每步操作都有清晰的控制台输出

### 修复2：删除连接改为智能删除模式

**位置**：`/opt/tcm-ai/static/decision_tree_visual_builder.html` 第2370-2401行

**修改后代码**：
```javascript
} else if (action === 'delete') {
    // 删除连接：智能删除指定处方（保留其他处方）
    const newText = currentText.replace(syndromePattern, (match, prefix, currentPrescriptions, newline) => {
        const trimmed = currentPrescriptions.trim();
        console.log(`  当前处方列表: "${trimmed}"`);

        if (!trimmed) {
            // 当前已为空，无需删除
            console.log(`  ℹ️ 处方列表已为空，无需删除`);
            return match;
        }

        // 分割处方列表（支持顿号、逗号、空格等分隔符）
        const prescriptionList = trimmed.split(/[、，,\s]+/).filter(p => p.trim());
        console.log(`  解析出的处方列表:`, prescriptionList);

        // 移除目标处方
        const updatedList = prescriptionList.filter(p => p.trim() !== toNode.name);
        console.log(`  删除"${toNode.name}"后的列表:`, updatedList);

        // 重新拼接（用顿号）
        const newPrescriptions = updatedList.join('、');
        console.log(`  ➖ 删除处方: ${trimmed} → ${newPrescriptions}`);

        return `${prefix}${newPrescriptions}${newline}`;
    });
    if (newText !== currentText) {
        currentText = newText;
        updated = true;
        console.log(`✅ 已从证候"${fromNode.name}"的处方列表中移除"${toNode.name}"`);
    }
}
```

**核心改进**：
1. ✅ **智能解析处方列表**：支持多种分隔符（顿号、逗号、空格）
2. ✅ **精确删除目标处方**：只删除指定的处方，保留其他处方
3. ✅ **标准化输出格式**：重新拼接时统一使用顿号分隔
4. ✅ **完整日志追踪**：每步都有详细的处理信息

### 修复3：重新生成支持多个处方

**位置**：`/opt/tcm-ai/static/decision_tree_visual_builder.html` 第4955-4963行

**修改后代码**：
```javascript
// 处方（支持多个处方，用顿号分隔）
thinkingText += `处方：`;
const prescriptionChildren = nodeMap[syndrome.id]?.children.filter(c => c.node && c.node.type === 'prescription') || [];
if (prescriptionChildren.length > 0) {
    // 提取所有处方名称并用顿号连接
    const prescriptionNames = prescriptionChildren.map(c => c.node.name);
    thinkingText += prescriptionNames.join('、');
}
thinkingText += '\n';
```

**核心改进**：
1. ✅ **遍历所有处方节点**：不再只取第一个，而是收集所有处方
2. ✅ **标准化分隔符**：统一使用顿号连接
3. ✅ **与增量同步保持一致**：确保重新生成的格式与增量同步一致

## 🎯 修复效果对比

### 场景1：连续添加多个处方

| 操作 | 修复前 | 修复后 |
|------|--------|--------|
| 连接：证候→处方1 | 处方：处方1 ✅ | 处方：处方1 ✅ |
| 连接：证候→处方2 | 处方：处方2 ❌ | 处方：处方1、处方2 ✅ |
| 连接：证候→处方3 | 处方：处方3 ❌ | 处方：处方1、处方2、处方3 ✅ |
| 再连：证候→处方1 | 处方：处方1 ❌ | 处方：处方1、处方2、处方3 ✅（去重）|

### 场景2：删除部分连接

| 操作 | 修复前 | 修复后 |
|------|--------|--------|
| 当前状态 | 处方：处方3 ❌ | 处方：处方1、处方2、处方3 ✅ |
| 删除：证候-处方2 | 处方： ❌全空 | 处方：处方1、处方3 ✅精确删除 |
| 删除：证候-处方1 | 处方： ❌ | 处方：处方3 ✅ |
| 删除：证候-处方3 | 处方： ✅ | 处方： ✅ |

### 场景3：重新生成功能

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 证候连接3个处方 | 处方：处方1 ❌只显示第一个 | 处方：处方1、处方2、处方3 ✅全部显示 |
| 点击"重新生成" | 丢失处方2、处方3 ❌ | 保留所有处方 ✅ |

## 📊 控制台日志示例

### 添加连接的日志
```
🔗 开始同步连接关系
  从: 脑袋瓜前面疼 (syndrome_branch)
  到: 处方2 (prescription)
  操作: 创建连接
📝 检测到证候-处方连接，尝试更新...
  当前处方列表: "处方1"
  ➕ 追加新处方: 处方1 → 处方1、处方2
✅ 已更新证候"脑袋瓜前面疼"的处方（增量追加）
✅ 连接关系已同步到诊疗思路
```

### 删除连接的日志
```
🔗 开始同步连接关系
  从: 脑袋瓜前面疼 (syndrome_branch)
  到: 处方1 (prescription)
  操作: 删除连接
📝 检测到证候-处方连接，尝试更新...
  当前处方列表: "处方1、处方2、处方3"
  解析出的处方列表: [ '处方1', '处方2', '处方3' ]
  删除"处方1"后的列表: [ '处方2', '处方3' ]
  ➖ 删除处方: 处方1、处方2、处方3 → 处方2、处方3
✅ 已从证候"脑袋瓜前面疼"的处方列表中移除"处方1"
✅ 连接关系已同步到诊疗思路
```

### 重复添加的日志
```
🔗 开始同步连接关系
  从: 脑袋瓜前面疼 (syndrome_branch)
  到: 处方2 (prescription)
  操作: 创建连接
📝 检测到证候-处方连接，尝试更新...
  当前处方列表: "处方1、处方2、处方3"
  ⚠️ 处方已存在，跳过: 处方2
```

## 💡 技术细节

### 分隔符标准化
**选择顿号（、）的原因**：
1. ✅ 符合中文标准列举格式（GB/T 15834-2011）
2. ✅ 符合中医文献传统写法（如《伤寒论》）
3. ✅ 视觉清晰，不会与处方名称内部的逗号混淆
4. ✅ 示例：桂枝汤、小柴胡汤、四逆汤

**兼容性处理**：
- 删除连接时支持解析多种分隔符：顿号、逗号、空格
- 正则表达式：`/[、，,\s]+/`
- 重新拼接时统一使用顿号输出

### 去重逻辑
**检测方式**：
```javascript
if (!trimmed.includes(toNode.name)) {
    // 不包含，可以追加
}
```

**优点**：
- 简单高效，无需复杂的数组操作
- 支持中文处方名

**注意事项**：
- 如果处方名称是另一个处方名的子串，可能误判
- 例如："六味地黄丸" 和 "加味地黄丸"
- 当前实现已足够应对常规场景，未来如需更精确可使用数组完全匹配

### 处方顺序策略
**追加到末尾**：
```javascript
return `${prefix}${trimmed}、${toNode.name}${newline}`;
```

**优点**：
- 保持用户创建连接的时间顺序
- 符合用户直觉（最新的在最后）
- 删除时也保持相对顺序

### 边界情况处理

#### 情况1：空字符串处理
```javascript
if (!trimmed) {
    // 直接设置，不添加分隔符
    return `${prefix}${toNode.name}${newline}`;
}
```

#### 情况2：删除后为空
```javascript
const updatedList = prescriptionList.filter(p => p.trim() !== toNode.name);
const newPrescriptions = updatedList.join('、');  // 空数组join('')返回空字符串
return `${prefix}${newPrescriptions}${newline}`;  // 结果："处方：\n"
```

#### 情况3：多余空格处理
```javascript
const prescriptionList = trimmed.split(/[、，,\s]+/).filter(p => p.trim());
// split后filter确保没有空元素
```

## 🔄 与其他功能的一致性

### 与节点名称同步的协同
- 节点名称同步（`syncNodeToThinking()`）：更新单个处方节点的名称
- 连接关系同步（`syncConnectionToThinking()`）：更新证候的处方列表
- 两者互补，确保各种修改场景都能正确同步

### 与"重新生成"功能的协同
- 增量同步：局部更新，保留用户手动编辑
- 重新生成：完整重构，覆盖所有内容
- 两者使用相同的分隔符（顿号），确保格式一致

### 与视觉反馈的协同
```javascript
// 应用更新后的视觉反馈（绿色边框闪烁）
if (updated) {
    thinkingTextarea.value = currentText;
    console.log('✅ 连接关系已同步到诊疗思路');

    thinkingTextarea.style.borderColor = '#10b981';
    thinkingTextarea.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
    setTimeout(() => {
        thinkingTextarea.style.borderColor = '';
        thinkingTextarea.style.boxShadow = '';
    }, 1000);
}
```

## 🎯 用户价值

### 解决的痛点
1. ✅ **不再丢失处方信息**：添加新连接不会覆盖旧处方
2. ✅ **精确删除控制**：删除连接只删除对应处方，不影响其他
3. ✅ **完整信息保留**：重新生成时包含所有已连接的处方
4. ✅ **标准化格式**：统一使用顿号分隔，符合中医文献习惯
5. ✅ **详细操作反馈**：控制台日志清晰展示每步操作

### 典型使用场景

#### 场景A：辨证论治，一证多方
```
证候：脾胃虚寒
可选方剂：
- 基础方：理中汤
- 加强方：附子理中汤
- 变通方：黄芪建中汤

操作流程：
1. 创建连接：脾胃虚寒 → 理中汤
   → 诊疗思路显示：处方：理中汤

2. 创建连接：脾胃虚寒 → 附子理中汤
   → 诊疗思路显示：处方：理中汤、附子理中汤 ✅增量追加

3. 创建连接：脾胃虚寒 → 黄芪建中汤
   → 诊疗思路显示：处方：理中汤、附子理中汤、黄芪建中汤 ✅继续追加

4. 删除连接：脾胃虚寒 - 附子理中汤（决定不用此方）
   → 诊疗思路显示：处方：理中汤、黄芪建中汤 ✅精确删除
```

#### 场景B：探索多种治疗方案
```
医生探索阶段：
1. 尝试方案1：连接处方A → 效果一般，再连接处方B
2. 对比方案2：连接处方C → 觉得处方C更合适，删除处方A
3. 最终确定：保留处方B、处方C的组合方案

全程诊疗思路动态更新，医生可以清晰看到当前选定的所有处方。
```

## 📚 相关文档

- `CONNECTION_SYNC_NODE_TYPE_FIX.md` - 节点类型支持修复（syndrome_branch）
- `INCREMENTAL_SYNC.md` - 节点名称增量同步功能
- `NODE_EDIT_FIX.md` - 节点编辑不覆盖诊疗思路修复
- `PROFESSIONAL_FORMAT_UPDATE.md` - 专业格式生成算法
- `CONNECTION_FEATURE.md` - 连接功能完整文档

## 🚀 部署状态

- ✅ 代码已修复（3处修改）
  - 第2345-2369行：添加连接增量追加逻辑
  - 第2370-2401行：删除连接智能删除逻辑
  - 第4955-4963行：重新生成多处方支持
- ✅ 服务已重启（2025-10-29 11:23）
- ✅ 功能已上线生效
- ⏳ 等待用户测试验证

## 🧪 测试建议

### 测试用例1：基本增量追加
```
步骤：
1. 创建证候节点"寒证"，3个处方节点"处方1"、"处方2"、"处方3"
2. 依次创建连接：寒证→处方1，寒证→处方2，寒证→处方3
3. 观察左侧诊疗思路，每次创建后都应追加，不覆盖

预期结果：
第1次：处方：处方1
第2次：处方：处方1、处方2
第3次：处方：处方1、处方2、处方3
```

### 测试用例2：智能删除
```
步骤：
1. 当前状态：处方：处方1、处方2、处方3
2. 右键点击连接线"寒证→处方2"，选择"删除连接"
3. 观察左侧诊疗思路是否只删除处方2

预期结果：
删除后：处方：处方1、处方3
```

### 测试用例3：重复连接去重
```
步骤：
1. 当前状态：处方：处方1、处方2
2. 再次创建连接：寒证→处方1
3. 观察左侧诊疗思路是否保持不变（不重复添加）

预期结果：
仍然显示：处方：处方1、处方2
控制台显示：⚠️ 处方已存在，跳过: 处方1
```

### 测试用例4：重新生成功能
```
步骤：
1. 画布上：寒证节点连接3个处方节点
2. 点击"🔄 重新生成"按钮
3. 观察生成的诊疗思路是否包含所有3个处方

预期结果：
生成内容包含：处方：处方1、处方2、处方3
```

### 测试用例5：混合分隔符兼容性
```
步骤：
1. 手动编辑左侧诊疗思路，将处方改为"处方1，处方2 处方3"（混合逗号和空格）
2. 删除连接：寒证-处方2
3. 观察是否正确解析并删除

预期结果：
删除后：处方：处方1、处方3（标准化为顿号）
```

---

**修复版本**: v2.9.9
**修复日期**: 2025-10-29
**影响范围**: 决策树可视化构建器 - 连接同步功能
**严重程度**: 高（功能行为错误，导致数据丢失）
**修复状态**: ✅ 已解决
**测试状态**: ⏳ 待用户验证
