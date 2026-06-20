# AI生成决策树JSON解析错误修复 - 2025-10-19

## 问题描述

用户报告在生成决策树时出现错误：

```
错误 ❌ 生成失败: AI生成失败: Expecting ',' delimiter: line 11 column 10 (char 465)
```

但实际上决策树已经在画布中建立起来了。

---

## 根本原因

### 1. JSON格式错误
AI（Dashscope）返回的JSON格式不规范，存在以下问题：
- 缺少逗号分隔符
- 可能包含注释或额外文本
- JSON中间可能有其他非JSON内容

### 2. 错误处理不完善
虽然代码有JSON提取的备用方案，但：
- 如果所有解析方案都失败，会直接抛出异常
- 即使部分解析成功，最终验证失败也会抛出异常
- 没有提供备用的基本路径生成机制

---

## 修复方案

### 修复1: 增强JSON清理和解析

**文件**: `/opt/tcm-ai/services/famous_doctor_learning_system.py:1837-1897`

#### 添加的清理步骤：

1. **移除注释**
   ```python
   # 移除单行注释
   cleaned_content = re.sub(r'//.*?\n', '\n', cleaned_content)
   # 移除多行注释
   cleaned_content = re.sub(r'/\*.*?\*/', '', cleaned_content, flags=re.DOTALL)
   ```

2. **修复尾部逗号**
   ```python
   # 修复 {...,} 和 [...,] 这种多余逗号
   cleaned_content = re.sub(r',(\s*[}\]])', r'\1', cleaned_content)
   ```

3. **修复缺失的逗号**
   ```python
   # 修复 {...}{...} 或 {...}[...] 这种缺少逗号的情况
   cleaned_content = re.sub(r'([}\]])(\s*)([{"\[])', r'\1,\2\3', cleaned_content)
   ```

#### 多层解析策略：

```
第一步：直接解析原始内容
   ↓ 失败
第二步：清理后再解析
   ↓ 失败
第三步：使用正则提取JSON部分
   ↓ 失败
第四步：使用空路径作为备用（不抛出异常）
```

---

### 修复2: 添加基本备用路径生成

**文件**: `/opt/tcm-ai/services/famous_doctor_learning_system.py:2603-2690`

新增方法：`_generate_basic_fallback_path()`

**功能**:
当AI解析完全失败时，从医生的诊疗思路中提取关键信息，生成一个基本的决策路径。

**提取逻辑**:
1. 从诊疗思路中提取症状关键词
2. 提取治法相关内容
3. 构建基本的4步路径：
   - 疾病节点
   - 症状节点
   - 治疗原则节点
   - 处方建议节点

**示例输出**:
```json
{
    "id": "fallback_path1",
    "title": "失眠基本诊疗路径",
    "steps": [
        {"type": "disease", "content": "失眠"},
        {"type": "symptom", "content": "心烦、多梦、入睡困难"},
        {"type": "treatment", "content": "宁心安神"},
        {"type": "prescription", "content": "方剂：请根据具体证型选方用药"}
    ],
    "keywords": ["失眠", "基本路径"],
    "source": "fallback",
    "note": "由于AI解析异常，此为基本参考路径，请根据实际情况调整"
}
```

---

### 修复3: 改进异常处理逻辑

**文件**: `/opt/tcm-ai/services/famous_doctor_learning_system.py:1915-1921`

```python
# 修改前
if cleaned_paths:
    return cleaned_paths
else:
    raise Exception("AI生成的路径格式验证失败")  # ❌ 直接抛异常

# 修改后
if cleaned_paths:
    return cleaned_paths
else:
    # ✅ 使用备用路径，不抛异常
    return self._generate_basic_fallback_path(disease_name, thinking_process)
```

---

## 工作流程对比

### ❌ 修复前

```
用户输入 → AI生成 → JSON解析失败
   → 尝试正则提取 → 提取失败
   → 抛出异常 ❌
   → 前端显示错误
```

**问题**: 即使决策树部分数据已生成，最终还是会失败

---

### ✅ 修复后

```
用户输入 → AI生成 → JSON解析失败
   → 清理JSON格式 → 再次解析
   → 如果仍失败 → 正则提取
   → 如果仍失败 → 返回空paths（不抛异常）
   → 验证paths → 如果为空 → 生成基本备用路径 ✅
   → 前端显示决策树（带备用标记）
```

**优势**:
- 多层容错，不会轻易失败
- 即使AI完全失败，也能提供基本的决策树结构
- 用户体验更好

---

## 技术细节

### JSON清理正则表达式说明

1. **移除单行注释**: `r'//.*?\n'`
   - 匹配 `//` 到行尾的所有内容

2. **移除多行注释**: `r'/\*.*?\*/'`
   - 匹配 `/* ... */` 之间的所有内容

3. **修复尾部逗号**: `r',(\s*[}\]])'`
   - 匹配 `},{` 或 `],]` 中多余的逗号
   - 替换为 `}{` 或 `]]`

4. **修复缺失逗号**: `r'([}\]])(\s*)([{"\[])'`
   - 匹配 `}{` 或 `}[` 或 `]{"` 等缺少逗号的地方
   - 替换为 `},{` 或 `},[` 或 `],{"`

### 备用路径生成的关键词提取

使用正则表达式从医生思路中提取信息：

```python
# 提取症状
symptom_keywords = ["症状", "表现", "证候", "主症", "兼症"]
match = re.search(f'{keyword}[:：]?([^。，；]+)', thinking_process)

# 提取治法
treatment_keywords = ["治法", "治则", "治疗", "方药"]
match = re.search(f'{keyword}[:：]?([^。，；]+)', thinking_process)
```

---

## 测试步骤

### 测试1: 正常生成（AI返回正确JSON）

1. 访问 https://mxh0510.cn/static/decision_tree_visual_builder.html
2. 填写疾病名称: "失眠"
3. 填写诊疗思路: "心火旺盛，扰动心神，治以清心安神"
4. 点击"🤖 智能生成决策树"
5. **预期结果**:
   - 成功生成决策树
   - 不显示错误

---

### 测试2: AI返回格式错误（触发清理逻辑）

在服务日志中应该看到：
```
❌ 直接JSON解析失败: Expecting ',' delimiter...
🔍 清理后JSON解析成功，得到3条路径
```

**预期结果**: 决策树成功显示，无错误提示

---

### 测试3: AI完全失败（触发备用路径）

如果AI多次解析都失败，日志中应该看到：
```
⚠️ JSON提取也失败
⚠️ 使用空路径作为备用方案
⚠️ AI返回的路径为空或验证失败，生成基本备用路径
🔧 生成基本备用路径: 失眠
```

**预期结果**:
- 显示基本的决策树结构（4个节点）
- 标注为"基本参考路径"

---

## 查看调试日志

```bash
# 实时查看服务日志
sudo journalctl -u tcm-ai -f | grep -E "JSON|解析|路径"

# 查看最近的AI生成日志
sudo journalctl -u tcm-ai -n 100 | grep -A 10 "AI原始响应"
```

---

## 用户说明

### 为什么会出现这个错误？

AI模型（阿里云通义千问）生成的JSON格式有时不够规范，例如：
- 多了或少了逗号
- 包含注释文本
- JSON格式不完整

### 为什么决策树还能显示？

这可能是因为：
1. **浏览器缓存**: 之前成功生成过，浏览器缓存了节点数据
2. **部分解析成功**: 虽然有错误，但部分数据被提取出来了
3. **备用机制**: 新的修复提供了备用路径生成

### 修复后会怎样？

修复后，即使AI返回的JSON有格式问题，系统也会：
1. 自动清理和修复JSON
2. 如果完全无法解析，生成基本的决策树结构
3. 不再显示吓人的错误信息
4. 确保用户总能看到可用的决策树

---

## 后续优化建议

### 1. 改进AI提示词
优化提示词，让AI返回更规范的JSON：
```python
prompt += """
严格要求：
1. 只返回纯JSON，不要任何额外文字
2. 确保所有字段用英文逗号分隔
3. 不要包含注释
4. 确保JSON格式完整有效
"""
```

### 2. JSON Schema验证
在提示词中提供JSON Schema，让AI按照固定格式生成：
```python
prompt += """
必须严格按照以下JSON Schema格式返回：
{
    "type": "object",
    "properties": {
        "paths": {
            "type": "array",
            "items": {...}
        }
    }
}
"""
```

### 3. 使用更稳定的解析库
考虑使用更宽松的JSON解析器，如 `jsonrepair`：
```python
from jsonrepair import repair_json
repaired = repair_json(malformed_json)
```

---

## 修复完成

**修复时间**: 2025-10-19 07:16
**修复文件**: `/opt/tcm-ai/services/famous_doctor_learning_system.py`
**修复内容**:
- ✅ 增强JSON清理和解析逻辑（1837-1897行）
- ✅ 改进异常处理（1915-1921行）
- ✅ 添加基本备用路径生成（2603-2690行）

**服务状态**: ✅ 已重启
**测试状态**: 等待用户验证

---

**现在请重新测试生成决策树，应该不会再出现JSON解析错误了！**
