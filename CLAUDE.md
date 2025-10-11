# TCM-AI 中医智能诊断系统

## 项目概览

TCM-AI是一个基于人工智能的中医智能诊断助手系统，融合传统中医理论与现代AI技术，为患者提供专业的中医问诊服务，为医生提供智能的诊疗辅助工具。

### 核心功能
- **统一问诊服务**: 标准化AI驱动的多轮对话问诊，统一入口架构设计
- **五大名医人格**: 集成张仲景、叶天士、李东垣、郑钦安、刘渡舟五位名医的诊疗思维模式
- **智能症状分析**: 基于47个数据库表的完整症状关系网络分析系统
- **多模态诊断**: 支持舌象、面象图片的AI分析，结合传统中医望诊
- **统一认证系统**: unified_users/unified_sessions多表协同的完整用户管理体系
- **AI增强处方系统**: 智能分析引擎、风险评级、批量处理的现代化处方管理
- **医疗安全保障**: 症状编造检测、西药过滤、医疗责任边界控制
- **支付代煎服务**: 集成支付宝、微信支付和第三方中药代煎配送服务
- **智能医生工作台**: 专业化医疗工作空间，包含实时统计、AI推荐、患者关系管理

## 技术架构

### 分层架构设计
```
┌─────────────────────────────────────┐
│              API 层                 │  FastAPI路由、中间件、权限控制
├─────────────────────────────────────┤
│             CORE 层                 │  业务逻辑、算法核心、医疗模块
├─────────────────────────────────────┤
│           SERVICES 层               │  AI集成、外部服务、业务编排
├─────────────────────────────────────┤
│           DATABASE 层               │  数据访问、连接池、迁移管理
└─────────────────────────────────────┘
```

### 技术栈构成

**后端核心**
- **Web框架**: FastAPI 0.104.1 + Uvicorn 0.24.0 (高性能异步框架)
- **AI引擎**: 阿里云Dashscope 1.14.1 (通义千问系列模型)
- **数据存储**: SQLite主数据库 + 47张表的完整数据架构
- **向量检索**: FAISS 1.7.4 (本地向量数据库，毫秒级响应)
- **图像处理**: PIL 10.1.0 (多模态图像分析)
- **中文处理**: jieba 0.42.1 (症状文本分词和分析)
- **API路由**: 19个专业路由模块，覆盖完整业务流程

**前端技术**
- **原生Web技术**: HTML5/CSS3/JavaScript (无框架依赖，兼容性强)
- **响应式设计**: 支持PC、平板、手机多端适配
- **动态权限**: 基于用户角色的界面和功能动态显示
- **可视化**: Canvas/SVG (决策树、数据图表、医疗工作台)

**外部服务**
- **AI服务**: 阿里云Dashscope API (qwen-max, qwen-vl-max)
- **支付集成**: 支付宝、微信支付 API
- **代煎服务**: 第三方中药代煎商API集成

## 核心业务模块

### 🚀 统一问诊服务 (v2.5新增)
**核心优势**: 消除重复开发，保证一致性，便于维护
- **统一入口**: 智能工作流程、原系统、医生工作台使用相同问诊逻辑
- **服务模块**: `UnifiedConsultationService` - 封装完整的AI问诊功能
- **API接口**: `/api/consultation/*` - 标准化问诊API集合
- **质量保证**: 与原系统完全相同的问诊质量和医生人格

### 🏥 智能医生工作台 ⭐
**核心价值**: 专业化医疗工作空间，整合现代化医疗管理功能

**智能仪表板系统**:
- **实时统计面板**: 今日/本周/本月审查数据的动态展示和趋势分析
- **智能提醒中心**: 待审处方、随访计划、紧急事项的集中管理
- **效率分析图表**: 基于Canvas的可视化工作效率和质量评估
- **快速操作导航**: 一键跳转核心功能，优化医生工作流程

**AI增强处方管理**:
- **智能处方分析**: prescription_ai_analysis等多表协同的AI分析引擎
- **风险评级系统**: 自动识别高风险处方，智能优先级排序
- **批量处理能力**: 高效处理大量处方审查任务
- **智能推荐引擎**: AI驱动的处方优化建议和替代方案

**患者关系管理**:
- **完整病历档案**: 诊疗记录、用药历史、疗效跟踪的全生命周期管理
- **智能随访系统**: 自动提醒和后续诊疗安排
- **可视化时间线**: 病情发展和治疗效果的直观展示
- **患者智能分类**: 基于病情和治疗复杂度的自动分类管理

### 智能问诊系统  
- **多轮对话管理**: 基于中医诊疗流程的智能对话引擎
- **诊断阶段控制**: inquiry→diagnosis→prescription的渐进式问诊流程
- **知识检索增强**: 200+经典中医文档的RAG知识库支持
- **安全检查机制**: 实时检测症状编造、西药泄露、医疗边界控制

### 五大名医人格系统
```
张仲景 - 辨证论治，方证相应，重视六经理论
叶天士 - 温病学说，卫气营血，精于时令病证
李东垣 - 脾胃学说，升阳益胃，重视后天之本
郑钦安 - 火神派理论，重视阳气，善用附子温阳
刘渡舟 - 经方大师，临床实用，注重疗效验证
```

### 智能症状分析系统 ⭐
**完整数据架构**: 基于47张数据库表的专业中医症状分析体系
- **核心症状表**: tcm_symptoms, symptom_relationships, symptom_clusters
- **疾病关联**: tcm_diseases表支持的完整证候分析
- **智能缓存**: 多级缓存系统确保毫秒级响应
- **AI学习**: ai_symptom_analysis_log记录和优化分析效果

**数据覆盖**: 完整中医症状库，支持主症、兼症、舌象、脉象的全方位分析

### 处方管理系统
**完整业务闭环**:
```
AI生成处方 → 安全校验 → 医生审查 → 患者确认 → 支付订单 → 代煎配送 → 服务完成
```

**安全保障机制**:
- **君臣佐使分析**: 智能识别方剂配伍结构
- **剂量安全检查**: 药材用量安全范围验证
- **配伍禁忌检查**: 中药相互作用安全评估

### 决策树构建系统 ⭐
**医生诊疗思维可视化工具**:
- **可视化构建**: doctor_decision_tree路由支持的交互式决策树构建
- **节点智能设计**: 自动文本换行、内容管理、编辑体验优化
- **思维模式保存**: 与临床诊疗模式的深度集成
- **AI个性化**: 基于医生决策树的智能问诊定制服务

### 临床思维库系统
**医生诊疗经验管理**:
- **模式提取**: 自动分析临床决策逻辑和治疗原则
- **结构化存储**: 基于数据库的规范化诊疗经验存储
- **智能匹配**: 根据患者症状匹配相关临床经验
- **AI集成**: 与统一问诊服务的深度融合

## 系统命令

### 服务启动
```bash
# 开发环境
python api/main.py

# 生产环境 (systemd服务管理) ⚠️ 推荐方式
sudo service tcm-ai start    # 启动服务
sudo service tcm-ai restart # 重启服务  
sudo service tcm-ai stop    # 停止服务
sudo service tcm-ai status  # 查看状态

# 手动启动（调试用）
python3 /opt/tcm-ai/api/main.py

# 测试环境
python api/main_test_8002.py
```

### 数据库管理
```bash
# 数据库架构查看
sqlite3 /opt/tcm-ai/data/user_history.sqlite ".tables"

# 主数据库迁移 (根据需要选择合适版本)
sqlite3 /opt/tcm-ai/data/user_history.sqlite < database/migrations/010_unified_account_system_fixed.sql

# 数据库备份
sqlite3 /opt/tcm-ai/data/user_history.sqlite ".backup backup_$(date +%Y%m%d_%H%M%S).db"

# 系统状态检查
curl -X GET "http://localhost:8000/api/symptom/database/stats"
curl -X GET "http://localhost:8000/api/admin/system-info"
```

### 测试执行
```bash
# 完整测试套件
pytest

# 冒烟测试 (部署验证)
pytest tests/smoke/ -v

# 回归测试 (功能稳定性)
pytest -m regression

# 医疗安全测试
pytest tests/test_medical_diagnosis_safety.py
pytest tests/test_symptom_fabrication_fix.py

# 🔑 关键功能测试 (防止破坏现有功能)
python tests/test_critical_features.py
```

### 🛡️ 开发安全防护 ⚠️ 重要
**问题背景**: 反复出现"修A坏B"的情况，如修复移动端→破坏PC端

**解决方案**: 建立自动化检查系统

```bash
# 1. 修改代码后，提交前运行检查
bash scripts/pre_deploy_check.sh

# 2. Git提交（自动触发检查）
git commit -m "xxx"  # 自动运行26项检查

# 3. 紧急跳过检查（不推荐）
git commit --no-verify -m "紧急修复"
```

**检查内容**（26项）:
- ✅ 文件完整性（4项）
- ✅ 脚本加载状态（3项）
- ✅ 关键函数存在（5项）
- ✅ 异步函数正确性（3项）
- ✅ 兼容层完整性（4项）
- ✅ API端点配置（4项）
- ✅ 语法完整性（try-catch匹配）

**详细文档**: 参见 `DEVELOPMENT_SAFETY.md`

### 系统监控
```bash
# 性能监控
bash scripts/monitor_competition.sh

# 安全检查
bash scripts/quick_security.sh

# 系统预热
bash scripts/warmup_for_competition.sh
```

## 开发规范

### Git提交规范 ⚠️
**重要**: 区分问题解决的不同阶段，合理使用Git备份

**提交策略**:
1. **问题解决前备份** ⚠️ **必须执行**
   - 开始解决新问题/bug前: `git add -A && git commit -m "🔄 修改前备份: [描述即将解决的问题]"`
   
2. **问题解决过程中** ✅ **无需频繁备份**
   - 同一问题的多次尝试修改、调试、测试过程中不需要每次备份
   - 允许连续多次修改代码来解决同一个问题
   
3. **问题解决完成后** ⚠️ **必须提交**
   - 问题完全解决后: `git add -A && git commit -m "[类型] [简要描述]: [详细说明]"`

**什么时候需要备份**:
- ✅ 开始解决新问题前
- ✅ 切换到不同问题前  
- ✅ 功能开发完成后
- ❌ 同一问题的调试过程中
- ❌ 修复bug的多次尝试中

**提交类型**:
- 🐛 修复bug
- ✨ 新功能  
- 🔧 配置修改
- 📚 文档更新
- 🏗️ 架构调整
- 🧪 测试相关

**提交模板**:
```bash
git commit -m "🐛 修复[问题描述]

- [具体修改1]
- [具体修改2]
- [影响说明]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 代码风格
- **编码标准**: UTF-8, Python 3.11+
- **文档规范**: 函数/类必须包含详细文档字符串
- **类型提示**: 强制使用typing类型提示
- **命名规范**: snake_case (函数/变量), PascalCase (类)

### 🔧 开发错误防范 
**重要**: 开始开发前请先阅读 `DEVELOPMENT_GUIDELINES.md`，避免重复性错误：

- **API端点错误**: `/chat` vs `/chat_with_ai` vs `/api/consultation/chat`
- **参数格式不匹配**: 医生ID映射 (`"1"` → `"zhang_zhongjing"`)
- **响应数据结构**: `data.reply` vs `result.data.reply`
- **数据库字段名**: `id` vs `uuid`、`speciality` vs `specialties`
- **事件绑定时机**: DOM加载、异步内容处理
- **标准错误处理**: 统一的try-catch和用户反馈模式

### 医疗安全标准 ⚠️
**严格禁止**:
1. AI添加患者未明确描述的任何症状细节
2. 无图像时编造舌象脉象等体征描述
3. 推荐或泄露任何西药名称
4. 超出中医诊疗范围的医疗建议

**必须遵循**:
1. 所有诊断建议包含"仅供参考，建议面诊"声明
2. 严格的医疗责任边界控制
3. 完整的操作审计日志记录
4. 敏感医疗数据脱敏处理

### API设计规范
- **RESTful设计**: 标准REST接口规范
- **统一响应格式**: `{"success": bool, "message": str, "data": any}`
- **异常处理**: HTTPException + 详细错误信息
- **版本控制**: API版本化管理

## 数据库架构

### 主数据库表结构 (SQLite - 47张表)
```sql
-- 统一用户认证系统
unified_users                   # 统一用户表 (患者、医生、管理员)
unified_sessions               # 统一会话管理
doctors                        # 医生详细信息
user_roles                     # 用户角色管理

-- 诊疗核心系统
consultations                  # 问诊记录 (症状分析、证候、对话记录)
prescriptions                  # 处方管理 (方剂、状态流转、版本控制)
prescription_changes           # 处方变更历史

-- AI增强处方系统
prescription_ai_analysis       # AI处方分析结果
prescription_ai_recommendations # AI处方推荐
prescription_risk_ratings      # 处方风险评级

-- 智能症状分析系统
tcm_diseases                   # 中医疾病/证候表
tcm_symptoms                   # 症状表 (主症、兼症、舌象、脉象)
symptom_relationships          # 症状关系网络
symptom_clusters               # 症状聚类缓存
ai_symptom_analysis_log        # AI分析学习日志

-- 医生工作系统
doctor_work_statistics         # 医生工作统计
doctor_availability           # 医生可用性管理
doctor_patient_relationships  # 医患关系管理
doctor_sessions               # 医生会话管理

-- 订单支付系统
orders                        # 订单管理
decoction_orders             # 代煎订单

-- 安全审计系统
audit_logs                    # 操作审计日志
security_events              # 安全事件记录
security_audit_logs          # 安全审计追踪
security_alerts              # 安全告警

-- 系统管理
system_settings              # 系统配置
system_metrics              # 系统性能指标
```

### 缓存架构
```
L1: 内存缓存 (毫秒级)    # 热点症状关系、用户会话
L2: SQLite缓存          # 持久化缓存数据库  
L3: Redis集群 (可选)     # 分布式缓存
```

## 部署与运维

### 生产环境部署
```bash
# systemd服务配置 (/etc/systemd/system/tcm-ai.service)
[Unit]
Description=TCM-AI Medical Diagnosis System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tcm-ai
ExecStart=/opt/tcm01/tcm-venv/bin/python3 /opt/tcm-ai/scripts/start_service.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/tcm-ai

[Install]
WantedBy=multi-user.target

# 服务管理命令
sudo systemctl enable tcm-ai     # 开机自启
sudo systemctl daemon-reload    # 重载配置
sudo service tcm-ai restart     # 重启服务
```

### 环境配置
- **运行端口**: 8000 (生产), 8002 (测试)  
- **数据路径**: `/opt/tcm-ai/data/`
- **日志路径**: `/opt/tcm-ai/logs/api.log`
- **静态资源**: `/opt/tcm-ai/static/`
- **服务配置**: `/etc/systemd/system/tcm-ai.service`

### 依赖服务
- **阿里云Dashscope**: AI模型服务 (必需)
- **PostgreSQL**: 向量数据库 (可选，FAISS为备选)
- **systemd**: 系统服务管理，进程守护，自动重启
- **nginx**: 反向代理和SSL证书管理 (推荐)
- **Redis**: 分布式缓存 (可选)

## 安全与监控

### 安全防护
- **RBAC权限系统**: 基于角色的访问控制
- **JWT + Session**: 双重会话安全机制  
- **医疗数据保护**: 敏感信息脱敏、审计追踪
- **API安全**: 防SQL注入、参数验证、频率限制

### 监控体系
- **系统监控**: CPU、内存、磁盘使用率
- **API监控**: 响应时间、成功率、并发数
- **医疗安全监控**: 症状编造检测、西药过滤告警
- **业务监控**: 问诊量、处方审查率、支付成功率

## 版本更新记录

### v2.9 - 服务管理优化版 (2025-09-24)
**部署方式优化**: 从宝塔面板改为systemd服务管理，提高系统稳定性

**核心改进**:
- ✅ **systemd服务管理**: 替代宝塔面板，避免服务器重连中断
- ✅ **医生信息联动修复**: 数据库医生信息与问诊页面实时同步
- ✅ **API端点统一**: 修复/api/doctor/list与/api/doctors/list不一致问题
- ✅ **15位医生完整显示**: 包含数据库更新的所有医生信息

**服务管理命令**:
- `sudo service tcm-ai start/restart/stop/status` - 标准systemd管理
- 配置文件: `/etc/systemd/system/tcm-ai.service`
- 日志路径: `/opt/tcm-ai/logs/api.log`

### v2.8 - 系统架构现状版 (2025-09-24)
**文档同步更新**: 基于实际运行状态全面更新文档，确保与当前系统完全一致

**当前系统状态**:
- ✅ **统一认证体系**: unified_users, unified_sessions多表协同的完整用户管理
- ✅ **47张数据库表**: 覆盖用户、诊疗、处方、审计、安全的完整数据架构  
- ✅ **19个API路由模块**: 从认证、问诊到支付的完整业务流程覆盖
- ✅ **AI增强处方系统**: prescription_ai_*系列表支持的智能处方分析体系
- ✅ **医疗安全防护**: 症状编造检测、医疗边界控制的全面安全保障
- ✅ **智能医生工作台**: 专业化医疗工作空间，整合现代化管理功能
- ✅ **多模态诊断**: 舌象、面象图片AI分析的完整集成

### v2.6 - 智能医生工作台重构版 (2025-09-21)
**重大重构**: 医生界面从"功能低效且无意义"全面升级为专业医疗工作空间

**核心功能**:
- ✅ 智能仪表板: 实时统计、提醒中心、效率图表、快速操作面板
- ✅ AI增强处方审查: 智能分析引擎、批量处理、风险评级、7张AI分析数据表
- ✅ 患者关系管理: 档案管理、预约随访、就诊时间线、智能分类
- ✅ 统一认证集成: 完全兼容v2.5统一认证系统，支持动态权限控制
- ✅ JavaScript重构: 完全重写前端代码，修复语法错误，提升性能和稳定性
- ✅ 决策树修复: 解决决策树构建器404问题，恢复可视化诊疗思维构建功能

### v2.5 - 统一问诊服务版 (2025-09-09)
**架构统一**: 消除重复开发，建立统一问诊服务架构

**核心功能**:
- ✅ 统一问诊服务: `UnifiedConsultationService` 封装完整AI问诊功能
- ✅ API标准化: `/api/consultation/*` 标准化问诊API集合
- ✅ 多端兼容: 智能工作流程、原系统、医生工作台统一使用
- ✅ 质量保证: 与原系统完全相同的问诊质量和医生人格

### v2.1 - 智能症状分析系统 (2025-01-09)  
**架构创新**: 从硬编码症状关系升级为AI驱动的智能分析系统

**核心功能**:
- ✅ 三层智能架构: 毫秒级缓存 → 100ms数据库 → 2-3s AI分析
- ✅ 症状关系网络: 103个症状，20+病症，多维度关系管理
- ✅ 智能API接口: 7个症状分析端点，支持快速查询和完整分析
- ✅ 置信度评分: 0-1评分系统，支持expert/ai/literature多源数据

## 常见问题解决

### JavaScript按钮无响应
**问题**: 页面加载正常但按钮点击无反应，控制台显示语法错误

**解决方案**:
1. **try-catch结构修复**: 确保每个try都有对应的catch
2. **变量重复声明**: 使用全局辅助函数避免重复声明
3. **事件绑定时机**: 使用setTimeout强制重新绑定事件

### 性能优化建议
- **缓存命中率**: 维持>80%的热点数据缓存命中
- **数据库响应**: 确保<100ms的本地SQLite响应时间  
- **API调用优化**: 智能缓存避免重复AI调用
- **连接池管理**: 合理配置数据库连接池参数

### 医疗安全检查
- **症状编造监控**: 实时检测AI添加的未描述症状
- **西药过滤验证**: 确保纯中医诊疗环境
- **医疗边界控制**: 严格的责任范围和免责声明
- **审计日志完整性**: 所有医疗操作的完整追溯

### 🚨 重要开发检查清单 (每次开发前必读)

#### 🔍 系统结构全面Review
**在进行任何修改前，必须完成以下检查**：

1. **页面路由检查**：
   - ✅ 登录页面：`/login` (FastAPI路由 → auth_portal.html)
   - ✅ 智能问诊：`/smart` (FastAPI路由 → index_smart_workflow.html)
   - ✅ 管理后台：`/admin` (FastAPI路由 → admin/index.html)
   - ✅ 医生端：`/doctor` (FastAPI路由 → doctor/index.html)
   - ✅ systemd服务配置：/etc/systemd/system/tcm-ai.service

2. **API端点检查**：
   - ✅ 统一问诊：`/api/consultation/chat` 
   - ✅ 认证登录：`/api/auth/login`, `/api/v2/auth/*`, `/api/unified-auth/*`
   - ✅ 症状分析：`/api/symptom/*` (智能症状关系分析)
   - ✅ 处方管理：`/api/prescription/*` (生成、审查、确认)
   - ✅ AI处方审查：`/api/prescription-ai/*` (分析、推荐、风险评估、批量操作)
   - ✅ 医生管理：`/api/doctor/*` (医生信息、工作台数据)
   - ✅ 思维库管理：`/api/save_clinical_pattern`, `/api/get_doctor_patterns`
   - ✅ 决策树管理：`/api/doctor-decision-tree/*`
   - ✅ 数据同步：`/api/user-data-sync/*`, `/api/conversation-sync/*`
   - ✅ 系统管理：`/api/admin/*`, `/api/database-management/*`
   - ✅ 支付代煎：`/api/payment/*`, `/api/decoction/*`

3. **数据库表结构**：
   - ✅ 统一用户系统：`unified_users`, `unified_sessions`, `user_roles`, `doctors`, `users`
   - ✅ 问诊系统：`consultations`, `prescriptions`, `prescription_changes`
   - ✅ 症状分析：`tcm_symptoms`, `symptom_relationships`, `tcm_diseases`, `symptom_clusters`
   - ✅ AI处方分析：`prescription_ai_analysis`, `prescription_ai_recommendations`, `prescription_risk_ratings`
   - ✅ 医生工作：`doctor_work_statistics`, `doctor_availability`, `doctor_patient_relationships`
   - ✅ 安全审计：`audit_logs`, `security_events`, `security_audit_logs`, `security_alerts`

4. **前端组件检查**：
   - ✅ PC端 vs 移动端逻辑差异
   - ✅ 消息显示：`addMessage()` vs `addMobileMessage()`
   - ✅ 医生选择：五大名医人格系统
   - ✅ 会话管理：localStorage数据结构
   - ✅ 决策树构建：节点编辑、右键菜单、思维库保存

#### 🔧 常见错误防范
1. **路径错误**：
   - ❌ `/static/login_portal.html` → ✅ `/login` (FastAPI路由)
   - ❌ `/api/chat` → ✅ `/api/consultation/chat`
   
2. **变量名混淆**：
   - ❌ `responseData` vs `data`变量混用
   - ❌ `currentUser` vs `userData`数据结构
   
3. **权限控制遗漏**：
   - ❌ 退出不跳转 → ✅ 强制跳转登录页
   - ❌ 数据不清除 → ✅ 完整清除用户数据

#### 💡 开发流程要求
1. **修改前**：完整阅读相关代码，了解现有逻辑
2. **开发中**：添加充足的调试日志和错误处理  
3. **测试后**：验证PC端、移动端、不同用户角色
4. **提交前**：检查是否遵循项目规范和安全要求

###tips
1. ** 每次新增功能的时候或者新增web link的时候仔细核查下目前的项目里是否已经存在了，如果存在仔细看下代码，是基于已有的代码的基础上修改还是重构，重构的时候需要提供重构思路和重构具体方案给到用户确认。
2. **每次修改已有的代码后如果问题连续三次都没有解决，需要换种思路进行troubleshooting。
3. **🚨 每次回答前必须先Review系统核心功能，避免基础错误**

---

## 项目维护

**文档更新协议**: 所有重大功能变更、架构调整、重要bug修复都必须同步更新本文档

**🔧 开发质量管理**: 
- **错误防范**: 参考 `DEVELOPMENT_GUIDELINES.md` 避免重复性错误
- **代码审查**: 每次修改前后使用标准检查清单
- **持续学习**: 记录新错误模式，更新防范措施

**开发团队**: TCM-AI Development Team  
**最后更新**: 2025-09-24  
**文档版本**: v2.9 (服务管理优化版)

---

*本文档为TCM-AI项目的核心指令文档，包含系统架构、开发规范、部署指南和维护标准。请严格遵循本文档进行系统开发和维护工作。*