# TCM-AI 静态文件清理建议报告

**报告日期**: 2025-01-29  
**分析对象**: `/opt/tcm-ai/static` 目录 (121个文件)  
**总体结论**: 存在21个可安全删除的文件 + 35个需要谨慎审查的文件

---

## 📊 整体统计

| 文件类型 | 总数 | 正在使用 | 未使用 |
|---------|------|---------|--------|
| HTML    | 57   | 23      | 34     |
| JS      | 36   | 13      | 23     |
| CSS     | 8    | 4       | 4      |
| **合计**| **121** | **40** | **81** |

---

## 🟢 A. 可以安全删除的文件（21个）

这些文件具有明确的测试/调试/备份标识，且不被任何系统使用。

### HTML 文件 (20个)
```
1. admin/index_original.html                    # 原始版本备份
2. ai_mindmap_test.html                         # 测试文件
3. chrome_test.html                             # Chrome测试
4. debug_login_token.html                       # 调试文件
5. debug_prescription.html                      # 调试文件
6. debug_prescription_payment.html              # 调试文件
7. debug_prescription_status.html               # 调试文件
8. doctor/index_backup_20250921_113856.html     # 时间戳备份
9. doctor/index_optimized_backup.html           # 优化版备份
10. doctor/index_original.html                  # 原始版本备份
11. index_smart_workflow_backup.html            # 备份文件
12. simple_mobile_test.html                     # 测试文件
13. test_decision_tree_fix.html                 # 测试文件
14. test_doctor_login.html                      # 测试文件
15. test_edit_debug.html                        # 测试文件
16. test_pc_functions.html                      # 测试文件
17. test_prescription_logic.html                # 测试文件
18. test_prescription_rendering.html            # 测试文件
19. test_prescription_restore.html              # 测试文件
20. test_prescription_unlock.html               # 测试文件 (注：main.py引用但仅用于测试)
```

### JS 文件 (1个)
```
1. js/prescription_debug_helper.js              # 调试助手
```

### 删除前验证
```bash
# 检查是否真的没有被引用
grep -r "ai_mindmap_test\|chrome_test\|debug_prescription" /opt/tcm-ai/api/ 
grep -r "ai_mindmap_test\|chrome_test\|debug_prescription" /opt/tcm-ai/static/*.html

# 安全删除
rm -f /opt/tcm-ai/static/admin/index_original.html
rm -f /opt/tcm-ai/static/ai_mindmap_test.html
# ... 等等
```

**预期清理空间**: ~500KB - 2MB

---

## 🟡 B. 必须保留的文件（40个）

### 核心HTML页面 (23个)
这些HTML文件由FastAPI路由直接提供或被其他页面引用：

```
1. admin/index.html                             # 管理后台
2. admin/login.html                             # 管理登录 ⚠️ 需确认
3. auth_portal.html                             # 认证门户
4. decision_tree_visual_builder.html            # 决策树构建
5. doctor/index.html                            # 医生工作台
6. doctor/login.html                            # 医生登录
7. doctor_management.html                       # 医生管理
8. doctor_portal.html                           # 医生门户
9. doctor_review_portal.html                    # 处方审查门户
10. doctor_thinking_input.html                  # 思维输入
11. doctor_thinking_input_v2.html               # 思维输入 v2
12. index_smart_workflow.html                   # 智能问诊主页 ⭐ 核心应用
13. login_portal.html                           # 登录门户 ⚠️ 需确认
14. mindmap/index.html                          # 思维导图
15. navigation.html                             # 导航页面
16. patient_prescription_confirm.html           # 患者处方确认
17. phone_binding.html                          # 手机绑定 ⚠️ 需确认
18. prescription_checker_v2.html                # 处方检查器
19. prescription_learning_dashboard.html        # 处方学习仪表板
20. qr_code_gallery.html                        # 二维码库
21. register.html                               # 注册页面 ⚠️ 需确认
22. unified_system_monitor.html                 # 系统监控
23. user_history.html                           # 用户历史
```

### 核心CSS样式表 (4个)
```
1. css/prescription_styles.css                  # 处方样式
2. css/user_history.css                         # 历史记录样式
3. doctor_thinking_style.css                    # 思维输入样式
4. style.css                                    # 全局样式
```

### 必须使用的JS文件 (13个)
```
1. doctor_thinking_script.js                    # 思维输入脚本
2. doctor_thinking_v2_script.js                 # 思维输入 v2 脚本
3. js/auth_manager.js                           # 认证管理器
4. js/prescription_renderer.js                  # 处方渲染器
5. js/simple_prescription_manager.js            # 简单处方管理
6. js/user_history_main.js                      # 历史记录主脚本
```

**重要说明**: 包括CDN导入的库（Vue, Element Plus, ECharts等）

---

## 🔴 C. 存疑文件（35个 - 需要进一步确认）

### 未被直接引用的CSS文件 (4个)
```
1. css/smart_workflow_base.css                  # ⚠️ 被 index_smart_workflow.html 导入
2. css/smart_workflow_chat.css                  # ⚠️ 被 index_smart_workflow.html 导入
3. css/smart_workflow_doctor.css                # ⚠️ 被 index_smart_workflow.html 导入
4. css/smart_workflow_prescription.css          # ⚠️ 被 index_smart_workflow.html 导入
```

**这些文件应被保留** - 虽然在直接扫描时未被检测，但实际上由index_smart_workflow.html导入。

### 版本变体文件 (5个 - 可能废弃)
```
1. decision_tree_v3.html                        # 可能被 decision_tree_v3_data_driven.html 替代
2. decision_tree_v3_data_driven.html            # 数据驱动版本
3. decision_tree_visual_builder_simple.html     # 简化版本
4. doctor/index_optimized.html                  # 优化版本 (有_optimized_backup)
5. index_v2.html                                # v2版本
```

**建议**: 检查是否仍有路由指向这些文件

### 可能未使用的JS文件 (23个)
```
# 模块化utilities (可能被其他页面动态加载)
- js/modules/history_api.js
- js/modules/history_data.js
- js/modules/history_ui.js
- js/modules/user/index.js
- js/modules/user/user_auth.js
- js/modules/user/user_session.js
- js/modules/utils/dom_utils.js
- js/modules/utils/format_utils.js
- js/modules/utils/index.js
- js/modules/utils/storage_utils.js

# smart_workflow 系列 (可能被动态导入)
- js/smart_workflow_chat.js
- js/smart_workflow_core.js
- js/smart_workflow_doctor.js
- js/smart_workflow_history.js
- js/smart_workflow_init.js
- js/smart_workflow_mobile.js
- js/smart_workflow_prescription.js
- js/smart_workflow_records.js
- js/smart_workflow_utils.js

# 其他潜在未使用
- js/auto_sync_manager.js
- js/conversation_manager.js
- js/conversation_state_manager.js
- js/decision_tree_data_driven.js
- js/realtime_sync.js
- js/restore_pending_prescription.js
- js/session_manager.js
- js/simple_recovery.js
- fix_user_name.js
```

**重要**: 这些文件可能通过以下方式被使用：
- 动态 `fetch()` 或 `eval()` 加载
- 其他非HTML的served页面导入
- FastAPI模板字符串中动态生成的脚本标签

---

## 🔍 三阶段清理计划

### 第一阶段：无风险删除（15分钟）
**可立即执行的文件**：
```bash
# 删除明确的备份文件
rm -f /opt/tcm-ai/static/admin/index_original.html
rm -f /opt/tcm-ai/static/doctor/index_backup_20250921_113856.html
rm -f /opt/tcm-ai/static/doctor/index_optimized_backup.html
rm -f /opt/tcm-ai/static/doctor/index_original.html
rm -f /opt/tcm-ai/static/index_smart_workflow_backup.html

# 删除明确的测试文件
rm -f /opt/tcm-ai/static/ai_mindmap_test.html
rm -f /opt/tcm-ai/static/chrome_test.html
rm -f /opt/tcm-ai/static/simple_mobile_test.html
rm -f /opt/tcm-ai/static/test_decision_tree_fix.html
rm -f /opt/tcm-ai/static/test_doctor_login.html
rm -f /opt/tcm-ai/static/test_edit_debug.html
rm -f /opt/tcm-ai/static/test_pc_functions.html
rm -f /opt/tcm-ai/static/test_prescription_logic.html
rm -f /opt/tcm-ai/static/test_prescription_rendering.html
rm -f /opt/tcm-ai/static/test_prescription_restore.html

# 删除明确的调试文件
rm -f /opt/tcm-ai/static/debug_login_token.html
rm -f /opt/tcm-ai/static/debug_prescription.html
rm -f /opt/tcm-ai/static/debug_prescription_payment.html
rm -f /opt/tcm-ai/static/debug_prescription_status.html

# 删除调试JS
rm -f /opt/tcm-ai/static/js/prescription_debug_helper.js
```

**需要特别验证**:
- `test_prescription_unlock.html` - 虽然被main.py引用，但应检查其用途

### 第二阶段：审慎删除（需要代码审查）
**执行前需要**：
1. 检查FastAPI routes中是否存在这些页面的路由
2. 搜索是否被其他HTML文件引用
3. 检查是否被JavaScript动态加载

```bash
# 版本变体文件 - 需要决策
- decision_tree_v3.html
- decision_tree_v3_data_driven.html  
- doctor/index_optimized.html
- index_v2.html

# 可能的冗余文件 - 需要检查
- decision_tree_visual_builder_simple.html
- database_manager.html
- doctor_dashboard.html
```

### 第三阶段：长期审查（需要测试）
**这些文件需要运行系统测试后才能决定**：
- 所有smart_workflow系列JS文件
- 模块化utils JS文件
- 其他管理脚本

---

## 📋 检查清单

在执行任何删除前，请执行以下检查：

```bash
# 1. 检查FastAPI中是否存在引用
grep -r "test_prescription_unlock\|debug_prescription\|index_optimized" /opt/tcm-ai/api/main.py

# 2. 检查是否被其他HTML引用
grep -r "index_optimized\|decision_tree_v3\|index_v2" /opt/tcm-ai/static/*.html

# 3. 查看最近修改时间
find /opt/tcm-ai/static -name "*backup*" -o -name "*test*" -o -name "*debug*" | xargs ls -lt | head -30

# 4. 验证磁盘使用
du -sh /opt/tcm-ai/static/
find /opt/tcm-ai/static -type f \( -name "*backup*" -o -name "*test*" -o -name "*debug*" \) | xargs du -ch | tail -1

# 5. 完整性检查 - 删除前备份
tar -czf /opt/tcm-ai/static_backup_$(date +%Y%m%d_%H%M%S).tar.gz /opt/tcm-ai/static/
```

---

## 🎯 优先级建议

| 优先级 | 文件类型 | 数量 | 风险 | 行动 |
|------|---------|------|------|------|
| **高**   | 明确的test/debug/backup文件 | 21 | 无  | ✅ 立即删除 |
| **中**   | 版本变体(_v2, _v3, _optimized) | 5  | 低  | ⚠️ 审查后删除 |
| **低**   | 未导入的JS/CSS | 35 | 中  | 🔍 系统测试后决定 |

---

## 📊 预期收益

### 磁盘空间节省
- **第一阶段**: ~1-2 MB（明确的测试/调试文件）
- **第二阶段**: ~200-500 KB（版本变体）
- **第三阶段**: ~3-5 MB（未使用的JS/CSS）
- **总计**: ~4-8 MB

### 代码维护收益
✅ 减少混淆（clear up confusing old versions）  
✅ 加快静态文件查找速度  
✅ 降低误用风险（引用错误的文件）  
✅ 简化版本控制  

---

## ⚠️ 风险提示

1. **不要删除**:
   - 被FastAPI直接提供的页面
   - 被HTML/JS导入的任何资源
   - 生产环境使用的文件

2. **删除前必须**:
   - 在非生产环境测试
   - 备份整个static目录
   - 查看git历史确认用途

3. **运维建议**:
   - 建立.gitignore规则排除临时文件
   - 使用统一的命名规范（test/, debug/, backup/）
   - 定期清理过期文件

---

## 📝 后续建议

1. **建立管理规范**:
   ```
   - 新增测试文件：test_XXX.html / debug_XXX.html
   - 保留时间：3个月后删除
   - 定期审查（月度）
   ```

2. **自动化清理**:
   ```bash
   # 添加到git pre-commit hook
   find static -name "*test*.html" -o -name "*debug*.html" -o -name "*backup*" | exit 1
   ```

3. **持续改进**:
   - 整合JS文件减少HTTP请求
   - 使用构建工具(webpack/vite)管理资源
   - 设置CDN缓存策略

---

**报告完成时间**: 2025-01-29  
**分析方法**: 文件名模式识别 + 交叉引用查询 + FastAPI路由分析

