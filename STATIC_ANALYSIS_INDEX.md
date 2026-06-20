# TCM-AI 静态文件分析报告索引

**分析日期**: 2025-01-29  
**分析范围**: `/opt/tcm-ai/static` 目录  
**总文件数**: 121个文件  
**分析工具**: Glob + Grep + FastAPI Route Parser

---

## 📄 报告文件清单

### 1. **STATIC_FILES_CLEANUP_REPORT.md** (12KB)
   - **用途**: 完整的清理建议报告 ⭐ **主要报告**
   - **内容**:
     - 详细的文件分类分析
     - 风险评估和清理策略
     - 三阶段清理计划
     - 检查清单和执行步骤
     - 后续改进建议
   - **推荐**: 🔖 首先阅读此报告

### 2. **STATIC_FILES_DETAILED_LIST.txt** (8.3KB)
   - **用途**: 所有文件的详细列表 📋 **参考清单**
   - **内容**:
     - [A] 可删除文件清单 (21个)
     - [B] 必须保留的文件 (40个)
     - [C] 需要审查的文件 (35个)
     - 统计汇总和执行步骤
   - **推荐**: 🔍 执行删除前参考

### 3. **cleanup_static_phase1.sh** (在 scripts/ 目录)
   - **用途**: 自动化清理脚本 🔧 **可执行**
   - **功能**:
     - 创建完整备份
     - 自动删除Phase 1文件
     - 安全确认机制
     - 统计信息输出
   - **使用**: `bash /opt/tcm-ai/scripts/cleanup_static_phase1.sh`

---

## 🎯 快速开始

### 第一步: 阅读报告
```bash
cat /opt/tcm-ai/STATIC_FILES_CLEANUP_REPORT.md
```

### 第二步: 查看文件清单
```bash
cat /opt/tcm-ai/STATIC_FILES_DETAILED_LIST.txt
```

### 第三步: 备份 (推荐)
```bash
tar -czf /opt/tcm-ai/static_backup_$(date +%Y%m%d_%H%M%S).tar.gz /opt/tcm-ai/static/
```

### 第四步: 执行清理 (Phase 1)
```bash
bash /opt/tcm-ai/scripts/cleanup_static_phase1.sh
```

### 第五步: 验证应用
```bash
# 访问并测试:
# - http://localhost:8000/smart (主应用)
# - http://localhost:8000/doctor (医生端)
# - http://localhost:8000/admin (管理端)
```

---

## 📊 分析结果概览

| 分类 | 数量 | 风险等级 | 建议 |
|------|------|--------|------|
| 可删除 (test/debug/backup) | 21 | 🟢 无 | 立即删除 |
| 必须保留 (核心文件) | 40 | 🟢 无 | 保留 |
| 版本变体 | 5 | 🟡 低 | 审查后删除 |
| 可能未使用的JS/CSS | 30 | 🟠 中 | 系统测试后决定 |

---

## 🔍 分析方法

1. **文件名模式识别**: test_, debug_, _backup, _original等关键词
2. **交叉引用查询**: 检查HTML/JS中的导入语句
3. **FastAPI路由分析**: 扫描main.py中的FileResponse调用
4. **动态加载检测**: 识别可能的fetch/require调用

---

## ⚠️ 重要提示

1. **在执行删除前**:
   - ✅ 创建完整备份
   - ✅ 在非生产环境测试
   - ✅ 查看git历史确认用途

2. **Phase 1 (立即删除)**:
   - 21个明确的test/debug/backup文件
   - 风险: 无 (0风险)
   - 节省空间: ~1-2 MB

3. **Phase 2 & 3 (需要审查)**:
   - 35个可能废弃的文件
   - 需要代码审查和系统测试
   - 节省空间: ~3-6 MB

---

## 📈 预期收益

### 磁盘空间
- Phase 1: 1-2 MB
- Phase 2: 200-500 KB
- Phase 3: 3-5 MB
- **总计**: 4-8 MB

### 代码质量
- ✅ 减少混淆 (clear up old versions)
- ✅ 加快文件查找速度
- ✅ 降低误用风险
- ✅ 简化版本控制

---

## 📞 问题排查

### 删除后应用出现问题
```bash
# 1. 恢复备份
tar -xzf /opt/tcm-ai/.backups/static_backup_YYYYMMDD_HHMMSS.tar.gz -C /opt/tcm-ai/

# 2. 检查错误日志
tail -f /opt/tcm-ai/logs/api.log

# 3. 查看浏览器控制台
# 按F12打开浏览器开发者工具，查看是否有404错误
```

### 确认某个文件是否被使用
```bash
# 在整个项目中搜索引用
grep -r "filename.html\|filename.js" /opt/tcm-ai/

# 在FastAPI中搜索
grep -r "filename" /opt/tcm-ai/api/main.py
```

---

## 📝 后续建议

### 短期 (1-2周)
- [ ] 执行Phase 1清理 (21个文件)
- [ ] 验证系统正常运行
- [ ] 查看git历史确认旧版本用途

### 中期 (1-2月)
- [ ] Phase 2审查 (版本变体)
- [ ] 系统测试确保无回归
- [ ] 执行中期清理

### 长期 (持续)
- [ ] 建立文件管理规范
- [ ] 设置自动化清理检查
- [ ] 使用构建工具(webpack)统一资源管理

---

## 🔗 相关文件

| 文件路径 | 说明 |
|---------|------|
| `/opt/tcm-ai/STATIC_FILES_CLEANUP_REPORT.md` | 主要报告 |
| `/opt/tcm-ai/STATIC_FILES_DETAILED_LIST.txt` | 详细清单 |
| `/opt/tcm-ai/scripts/cleanup_static_phase1.sh` | 清理脚本 |
| `/opt/tcm-ai/CLAUDE.md` | 项目开发规范 |
| `/opt/tcm-ai/api/main.py` | FastAPI主应用 |

---

**分析完成时间**: 2025-01-29  
**下一步**: 👉 阅读 `STATIC_FILES_CLEANUP_REPORT.md`

