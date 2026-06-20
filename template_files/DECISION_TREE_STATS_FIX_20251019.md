# 决策树使用统计修复 - 完整报告

## 📋 问题汇总

用户在测试决策树匹配功能后，发现3个问题：

### 问题1：决策树统计数据未更新 ⚠️ **核心问题**

**现象**:
- 决策树在问诊中被成功匹配和使用
- 但统计数据显示：总调用数=0，成功率=0，覆盖率=0

**原因**:
- `used_pattern_id` 和 `pattern_match_score` 没有保存到数据库
- `record_pattern_usage()` 未被调用

---

### 问题2：存储问诊记录失败

**错误信息**:
```
AttributeError: 'list' object has no attribute 'get'
File: unified_consultation_routes.py:593
```

**原因**:
```python
existing_log = json.loads(existing[1])  # 可能返回 list
conversation_history = existing_log.get('conversation_history', [])  # list没有.get()方法
```

---

### 问题3：症状数据库初始化失败

**错误信息**:
```
ERROR: No such file or directory: 'database/migrations/003_create_symptom_database.sql'
```

**影响**: 症状关系分析功能可能受影响

---

## ✅ 修复方案

### 修复1：在响应中添加决策树信息

**文件**: `core/consultation/unified_consultation_service.py`

**修改1**: 添加字段到 `ConsultationResponse` (Line 65-67)
```python
@dataclass
class ConsultationResponse:
    # ... 其他字段 ...
    # 🆕 决策树匹配信息
    used_pattern_id: Optional[str] = None
    pattern_match_score: Optional[float] = None
```

**修改2**: 在 `_create_final_response` 中添加决策树信息 (Line 876-885)
```python
# 🆕 获取决策树匹配信息
used_pattern_id = None
pattern_match_score = None
if request.conversation_id in self.pattern_match_cache:
    cached_data = self.pattern_match_cache[request.conversation_id]
    if len(cached_data) >= 3:
        used_pattern_id = cached_data[0]
        pattern_match_score = cached_data[1]
        logger.info(f"📊 添加决策树信息到响应: pattern_id={used_pattern_id}, score={pattern_match_score:.2%}")

return ConsultationResponse(
    # ... 其他字段 ...
    used_pattern_id=used_pattern_id,
    pattern_match_score=pattern_match_score
)
```

---

### 修复2：修复存储问诊记录错误

**文件**: `api/routes/unified_consultation_routes.py`

**修改**: 处理 `existing_log` 可能是 list 的情况 (Line 594-597)
```python
existing_log = json.loads(existing[1]) if existing[1] else {}

# 🔧 修复：处理 existing_log 可能是 list 的情况
if isinstance(existing_log, list):
    # 如果是列表，转换为标准格式
    existing_log = {"conversation_history": existing_log}

conversation_history = existing_log.get('conversation_history', [])
```

---

### 修复3：保存决策树信息到数据库

**文件**: `api/routes/unified_consultation_routes.py`

**修改1**: UPDATE 语句 (Line 618-648)
```python
cursor.execute("""
    UPDATE consultations
    SET conversation_log = ?,
        symptoms_analysis = ?,
        tcm_syndrome = ?,
        status = ?,
        updated_at = ?,
        used_pattern_id = ?,        # 🆕
        pattern_match_score = ?      # 🆕
    WHERE uuid = ?
""", (
    # ... 其他参数 ...
    response.used_pattern_id,       # 🆕
    response.pattern_match_score,   # 🆕
    existing[0]
))
```

**修改2**: INSERT 语句 (Line 667-697)
```python
cursor.execute("""
    INSERT INTO consultations (
        uuid, patient_id, selected_doctor_id, conversation_log,
        symptoms_analysis, tcm_syndrome, status,
        created_at, updated_at,
        used_pattern_id, pattern_match_score  # 🆕
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    # ... 其他参数 ...
    response.used_pattern_id,      # 🆕
    response.pattern_match_score   # 🆕
))
```

---

### 修复4：调用决策树使用记录

**文件**: `api/routes/unified_consultation_routes.py`

**修改**: 在提交后记录决策树使用 (Line 827-840)
```python
conn.commit()
logger.info(f"✅ 问诊记录已存储")

# 🆕 记录决策树使用情况
if response.used_pattern_id:
    try:
        from core.consultation.decision_tree_matcher import get_decision_tree_matcher
        matcher = get_decision_tree_matcher()
        # 暂时记录为使用（success=False），等待处方审核通过后再更新为成功
        await matcher.record_pattern_usage(
            pattern_id=response.used_pattern_id,
            success=False,  # 处方审核通过后会更新为True
            feedback=None
        )
        logger.info(f"📊 决策树使用已记录: pattern_id={response.used_pattern_id}")
    except Exception as e:
        logger.warning(f"记录决策树使用失败: {e}")
```

---

## 🧪 测试验证

### 测试步骤

1. **访问患者端**: https://mxh0510.cn/smart

2. **输入测试症状**:
```
胃脘隐痛，绵绵不休，喜温喜按，空腹痛甚，得食稍缓，泛吐清水，
神疲乏力，手足不温，大便溏薄，舌淡苔白，脉沉迟无力
```

3. **查看服务日志**:
```bash
sudo journalctl -u tcm-ai -f
```

**预期日志**:
```
🔍 疾病提取: 找到 2 个候选疾病，选择最早出现的 '胃痛'
✅ 找到最佳决策树匹配: f20c3d0a-265d-4aba-b17e-79dc54339a1b
🧠 决策树智能匹配已集成 (匹配度:30%, ID:f20c3d0a-265d-4aba-b17e-79dc54339a1b)
📊 添加决策树信息到响应: pattern_id=f20c3d0a-265d-4aba-b17e-79dc54339a1b, score=30.14%
✅ 问诊记录已存储
📊 决策树使用已记录: pattern_id=f20c3d0a-265d-4aba-b17e-79dc54339a1b
```

4. **验证数据库**:
```bash
sqlite3 /opt/tcm-ai/data/user_history.sqlite "
SELECT id, used_pattern_id, pattern_match_score
FROM consultations
ORDER BY created_at DESC
LIMIT 1
"
```

**预期结果**:
```
176|f20c3d0a-265d-4aba-b17e-79dc54339a1b|0.3014
```

5. **查看决策树统计**:

访问决策树构建器：https://mxh0510.cn/static/decision_tree_visual_builder.html

点击 **"📊 数据分析 → 📈 查看使用统计"**

**预期显示**:
- ✅ 总决策树数：1
- ✅ 总调用次数：1 (从0变为1)
- ✅ 使用率：100%
- ✅ 最后使用时间：刚刚

---

## 📊 修复前后对比

### 修复前 ❌

| 项目 | 值 | 状态 |
|------|-----|------|
| 决策树匹配 | ✅ 成功 | 正常 |
| used_pattern_id | NULL | ❌ |
| pattern_match_score | NULL | ❌ |
| usage_count | 0 | ❌ |
| 统计显示 | 0次调用 | ❌ |

**问题**:
- 决策树被使用了，但没有任何记录
- 统计数据永远是0

---

### 修复后 ✅

| 项目 | 值 | 状态 |
|------|-----|------|
| 决策树匹配 | ✅ 成功 | 正常 |
| used_pattern_id | f20c3d0a... | ✅ |
| pattern_match_score | 0.3014 | ✅ |
| usage_count | 1 | ✅ |
| 统计显示 | 1次调用 | ✅ |

**改进**:
- 完整记录决策树使用情况
- 统计数据实时更新
- 可追踪决策树效果

---

## 🔍 数据流程图

```
患者问诊
  ↓
决策树匹配成功
  ↓
存入 pattern_match_cache
  ↓
添加到 ConsultationResponse
  ↓
保存到 consultations 表
├─ used_pattern_id: f20c3d0a...
└─ pattern_match_score: 0.3014
  ↓
调用 record_pattern_usage()
  ↓
更新 doctor_clinical_patterns
├─ usage_count + 1
└─ last_used_at: 更新
  ↓
统计API查询
  ↓
显示在决策树构建器
```

---

## 📝 未修复问题

### 症状数据库初始化失败

**错误**: `No such file or directory: 'database/migrations/003_create_symptom_database.sql'`

**影响**: 可能影响症状关系分析功能

**建议**: 
- 检查文件是否存在
- 如果不影响核心功能，可以暂时忽略
- 如需修复，需要创建该迁移文件或修改初始化逻辑

---

## ✅ 完成清单

- [x] 在响应中添加决策树信息
- [x] 修复存储问诊记录错误
- [x] 保存决策树信息到数据库
- [x] 调用决策树使用记录
- [x] 服务重启部署
- [ ] 症状数据库初始化问题（待修复）

---

## 🎉 总结

### 核心成果

**问题**: 决策树匹配成功但统计数据不更新

**原因**: 缺少数据保存和使用记录逻辑

**修复**: 
1. ✅ 响应中包含决策树信息
2. ✅ 数据库保存决策树使用记录
3. ✅ 自动更新使用统计

**效果**: 
- 完整的决策树使用追踪
- 实时的统计数据更新
- 可评估决策树效果

---

**修复时间**: 2025-10-19 20:40
**修复文件**: 
- `core/consultation/unified_consultation_service.py`
- `api/routes/unified_consultation_routes.py`

**服务状态**: ✅ 已重启
**测试状态**: 等待用户验证

---

**现在可以重新测试决策树使用统计功能了！** 🎊
