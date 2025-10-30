# 🔍 TCM-AI 代码一致性检查系统

## 📌 系统简介

这是一个**全自动化的代码一致性检查系统**，专门用于防止"修A坏B"问题，确保API接口、数据库接口、前后端关联关系的一致性。

### 核心组件

```
tcm-ai/
├── scripts/
│   ├── consistency_checker.py          # 核心检查引擎 ⭐
│   ├── view_consistency_report.sh      # 报告查看器 ⭐
│   └── pre_deploy_check.sh             # 部署前检查
├── .git/hooks/
│   └── pre-commit                      # Git提交钩子 ⭐
└── template_files/
    ├── consistency_check_report.json   # 检查报告
    ├── 代码一致性检查系统使用指南.md
    ├── API_INVENTORY.md                # 后端API清单
    └── 前端API调用完整清单.md           # 前端API清单
```

---

## 🚀 快速开始

### 方式1: 手动运行检查（推荐）

```bash
# 进入项目目录
cd /opt/tcm-ai

# 运行完整检查
python3 scripts/consistency_checker.py

# 查看友好的报告界面
bash scripts/view_consistency_report.sh
```

### 方式2: Git提交时自动检查

```bash
# 正常的Git工作流程
git add .
git commit -m "修复某个功能"

# 系统会自动运行两项检查：
# [1/2] 基础功能检查 (26项)
# [2/2] 代码一致性检查 (7大类)

# 如果发现问题，会提示修复
# 修复后重新提交即可
```

### 方式3: 持续监控（开发中）

```bash
# 开发前：了解现有架构
python3 scripts/consistency_checker.py

# 开发中：定期检查
watch -n 300 "python3 scripts/consistency_checker.py"  # 每5分钟

# 提交前：最终检查
bash scripts/view_consistency_report.sh
```

---

## 🔍 检查内容详解

### 1️⃣ API接口一致性检查 ⭐⭐⭐

**检查目标**: 确保前后端API完全匹配

**检查项目**:
- ✅ 前端调用的API是否在后端定义
- ✅ 后端定义的API是否被前端使用
- ✅ API路径参数是否正确匹配

**数据来源**:
- 后端: 扫描 `api/routes/*.py` (28个路由文件, 154个端点)
- 前端: 扫描 `static/**/*.html` 和 `static/**/*.js` (94个调用)

**典型问题示例**:
```
❌ 错误: 前端调用的API不存在于后端
   /api/v2/auth/profile
   调用文件: doctor/index_optimized.html

原因: 后端实际端点是 /api/v2/auth/login
修复: 修改前端调用或添加后端路由
```

### 2️⃣ 参数命名一致性检查 ⭐⭐⭐

**检查目标**: 统一参数命名规范

**常见问题**:
| 混用情况 | 标准名称 | 常见别名 |
|---------|---------|---------|
| 用户ID | `user_id` | userId, patient_id, patientId |
| 医生ID | `doctor_id` | doctorId, selected_doctor, doctor_name |
| 会话ID | `conversation_id` | conversationId, session_id, sessionId |
| 消息内容 | `message` | content, msg, text |

**检查示例**:
```
⚠️  警告: API参数命名不一致
   /api/consultation/chat
   - 使用 'selected_doctor', 建议 'doctor_id'
   - 使用 'patient_id', 建议 'user_id'
```

### 3️⃣ 数据库字段引用检查 ⭐⭐

**检查目标**: 避免引用不存在的数据库字段

**检查范围**:
- 数据库: user_history.sqlite (61张表)
- 数据库: famous_doctors.sqlite (8张表)
- 代码: `api/**/*.py` 中的SQL查询

**典型问题**:
```
❌ 错误: 字段不存在
   表: doctors
   字段: specialties (实际是 speciality)
   文件: doctor_routes.py
```

### 4️⃣ 前后端数据结构一致性 ⭐⭐

**检查目标**: 确保前后端数据格式匹配

**常见问题**:
- 响应格式不统一 (`data.reply` vs `result.data.reply`)
- 医生ID格式错误 (数字 vs 字符串名称)
- 数据访问路径错误

**检查示例**:
```
⚠️  警告: 响应数据结构不一致
   文件: index_smart_workflow.html
   问题: 直接访问.reply可能失败
   建议: 应检查 data.reply 或 result.data.reply
```

### 5️⃣ 常见错误模式检查 ⭐⭐

**检查内容**:
- ❌ 错误的API端点 (缺少 `/api/` 前缀)
- ❌ try-catch块不匹配
- ❌ 医生ID格式错误
- ❌ 响应数据访问错误

### 6️⃣ 未使用API检测 ⭐

**检查目标**: 发现定义但未被使用的后端API

**价值**:
- 清理冗余代码
- 发现遗漏的前端集成
- 评估API使用情况

### 7️⃣ 数据库Schema完整性 ⭐

**检查目标**: 确保数据库表和字段的完整性

**统计信息**:
- 总表数: 68张
- 主数据库: user_history.sqlite (61表)
- 辅助数据库: famous_doctors.sqlite (8表)

---

## 📊 检查报告详解

### 报告格式

运行检查后，会生成两种格式的报告：

#### 1. 终端输出（实时）

```
🔍 TCM-AI 代码一致性检查
════════════════════════════════════════

▶ 扫描后端API路由
──────────────────────────────────────
✓ 发现 154 个后端API端点

▶ 扫描前端API调用
──────────────────────────────────────
✓ 发现 94 个前端API调用

... (其他检查项) ...

📊 一致性检查报告
════════════════════════════════════════

统计信息:
  后端API: 154 个
  前端API调用: 94 个
  数据库表: 68 张

问题汇总:
  错误: 56 个  (🔴 必须修复)
  警告: 9 个   (🟡 建议修复)
  信息: 3 个   (🟢 仅供参考)
```

#### 2. JSON报告（详细）

保存位置: `template_files/consistency_check_report.json`

```json
{
  "timestamp": "2025-10-29T16:06:13.027603",
  "statistics": {
    "backend_apis": 154,
    "frontend_apis": 94,
    "database_tables": 68
  },
  "summary": {
    "errors": 56,
    "warnings": 9,
    "info": 3
  },
  "details": {
    "errors": [...],    // 所有错误的详细信息
    "warnings": [...],  // 所有警告的详细信息
    "info": [...]       // 统计信息
  }
}
```

### 使用报告查看器

```bash
bash scripts/view_consistency_report.sh
```

会显示交互式菜单：

```
╔════════════════════════════════════════════════════════════════╗
║          TCM-AI 代码一致性检查报告查看器                      ║
╚════════════════════════════════════════════════════════════════╝

📊 统计摘要
─────────────────────────────────────────────────────────
  后端API端点:    154 个
  前端API调用:    94 个
  数据库表:       68 张

🔍 问题统计
─────────────────────────────────────────────────────────
  错误:          56 个  (必须修复)
  警告:          9 个   (建议修复)
  信息:          3 个   (仅供参考)

💯 代码健康度
─────────────────────────────────────────────────────────
  ⚠️  一般  (总问题数: 65)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
快速操作:

  1️⃣  查看所有错误详情
  2️⃣  查看所有警告详情
  3️⃣  查看完整JSON报告
  4️⃣  导出错误到文件
  5️⃣  重新运行检查
  0️⃣  退出

请选择操作 (0-5):
```

---

## 🛠️ 使用场景

### 场景1: 新功能开发前

```bash
# 1. 了解现有API架构
python3 scripts/consistency_checker.py

# 2. 查看API清单
cat template_files/API_INVENTORY.md | less
cat template_files/前端API调用完整清单.md | less

# 3. 规划新API，确保不与现有冲突
```

### 场景2: 代码审查

```bash
# 1. 运行完整检查
python3 scripts/consistency_checker.py

# 2. 查看报告
bash scripts/view_consistency_report.sh

# 3. 逐项检查错误和警告
# 选择 1 - 查看所有错误详情
# 选择 2 - 查看所有警告详情

# 4. 记录需要修复的问题
```

### 场景3: 重构代码

```bash
# 1. 重构前：备份当前检查结果
python3 scripts/consistency_checker.py
cp template_files/consistency_check_report.json \
   template_files/consistency_report_before_refactor.json

# 2. 进行重构

# 3. 重构后：对比检查结果
python3 scripts/consistency_checker.py

# 4. 确保没有引入新问题
diff template_files/consistency_report_before_refactor.json \
     template_files/consistency_check_report.json
```

### 场景4: 持续集成

```bash
# 在CI/CD pipeline中集成

# .gitlab-ci.yml 或 .github/workflows/ci.yml
consistency_check:
  script:
    - python3 scripts/consistency_checker.py
    - |
      ERRORS=$(cat template_files/consistency_check_report.json | \
               python3 -c "import sys, json; print(json.load(sys.stdin)['summary']['errors'])")
      if [ "$ERRORS" -gt 0 ]; then
        echo "发现 $ERRORS 个错误，构建失败"
        exit 1
      fi
  artifacts:
    paths:
      - template_files/consistency_check_report.json
```

---

## 🔧 高级配置

### 自定义检查规则

编辑 `scripts/consistency_checker.py`:

```python
# 在 check_common_error_patterns() 方法中添加
error_patterns = [
    {
        'name': '禁止使用已废弃的API',
        'pattern': r'fetch\s*\(\s*["\']/(old-api|deprecated)["\']',
        'message': '检测到使用已废弃的API端点'
    },
    {
        'name': '强制使用HTTPS',
        'pattern': r'http://(?!localhost)',
        'message': '生产环境必须使用HTTPS'
    }
]
```

### 调整检查严格度

```python
# 在 check_api_consistency() 中

# 宽松模式：只报告明确错误
if not matched and not self._is_optional_api(fe_api):
    self.add_error(...)

# 严格模式：所有不匹配都报错
if not matched:
    self.add_error(...)
```

### 过滤已知问题

```python
# 在相应检查方法中添加白名单

KNOWN_ISSUES = [
    '/api/auth/send-verification-code',  # 计划在v3.0实现
    '/api/share_visit',                  # 仅用于测试
]

if api_path in KNOWN_ISSUES:
    continue  # 跳过检查
```

---

## 📖 最佳实践

### ✅ DO（推荐做法）

1. **开发前检查**
   ```bash
   # 了解现有架构，避免冲突
   python3 scripts/consistency_checker.py
   ```

2. **提交前检查**
   ```bash
   # 自动检查会在git commit时运行
   git add .
   git commit -m "新增功能"
   ```

3. **定期审查**
   ```bash
   # 每周运行一次全面检查
   python3 scripts/consistency_checker.py
   bash scripts/view_consistency_report.sh
   ```

4. **记录技术债务**
   ```bash
   # 导出问题清单，规划修复
   bash scripts/view_consistency_report.sh
   # 选择 4 - 导出错误到文件
   ```

### ❌ DON'T（不推荐做法）

1. **频繁跳过检查**
   ```bash
   # 不要经常使用 --no-verify
   git commit --no-verify -m "快速修复"  # ❌ 不推荐
   ```

2. **忽略警告**
   ```
   # 警告虽不会阻止提交，但应该重视
   # 累积的警告最终会变成错误
   ```

3. **不查看报告**
   ```bash
   # 不要只运行检查而不查看结果
   python3 scripts/consistency_checker.py  # ❌ 运行后应查看报告
   ```

4. **盲目修复**
   ```
   # 修复问题前先理解根本原因
   # 不要为了通过检查而引入新问题
   ```

---

## 🐛 故障排除

### 问题1: 检查脚本无法运行

**症状**: `python3 scripts/consistency_checker.py` 失败

**解决方案**:
```bash
# 检查Python版本（需要3.7+）
python3 --version

# 检查文件权限
chmod +x scripts/consistency_checker.py

# 查看详细错误
python3 scripts/consistency_checker.py 2>&1 | tee error.log
```

### 问题2: Git hook不生效

**症状**: git commit时没有运行检查

**解决方案**:
```bash
# 检查hook文件
ls -la .git/hooks/pre-commit

# 添加执行权限
chmod +x .git/hooks/pre-commit

# 手动测试hook
bash .git/hooks/pre-commit
```

### 问题3: 大量误报

**症状**: 报告中有很多实际不是问题的"问题"

**解决方案**:
1. 分析误报模式
2. 在代码中添加过滤规则
3. 调整正则表达式精度
4. 更新API清单

### 问题4: 检查速度慢

**症状**: 检查运行时间过长

**优化方案**:
```python
# 在 scan_frontend_apis() 中
# 跳过不必要的文件
if file_path.name.endswith('_backup.html'):
    continue

# 限制扫描深度
if file_path.relative_to(static_dir).parts[0] in ['archive', 'deprecated']:
    continue
```

---

## 📚 相关文档

| 文档 | 用途 | 位置 |
|------|------|------|
| **代码一致性检查系统使用指南** | 详细使用说明 | template_files/ |
| **API_INVENTORY.md** | 后端API完整清单 | 项目根目录 |
| **前端API调用完整清单.md** | 前端API调用详情 | template_files/ |
| **DEVELOPMENT_GUIDELINES.md** | 开发规范 | 项目根目录 |
| **CLAUDE.md** | 项目总体架构 | 项目根目录 |

---

## 🔄 更新日志

### v1.0 (2025-10-29)
- ✅ 初始版本发布
- ✅ 7大类检查功能
- ✅ Git hook集成
- ✅ 交互式报告查看器
- ✅ JSON格式报告
- ✅ 完整文档

---

## 🤝 贡献

### 发现新的错误模式？

1. 记录错误特征
2. 编写检测规则
3. 更新检查脚本
4. 提交改进建议

### 改进建议

- 提高检查精度
- 减少误报率
- 新增检查维度
- 优化报告格式

---

## 📞 支持

遇到问题？

1. 查看本文档的故障排除章节
2. 查看详细的错误日志
3. 检查相关文档
4. 提交问题反馈

---

**维护团队**: TCM-AI Development Team
**文档版本**: v1.0
**更新时间**: 2025-10-29

**记住**: 一致性检查不是负担，而是**防止bug的第一道防线**！ 🛡️
