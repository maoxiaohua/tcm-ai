# TCM-AI 中医智能诊断系统

## 项目概览

TCM-AI是一个基于人工智能的中医智能诊断助手系统，融合传统中医理论与现代AI技术，为患者提供专业的中医问诊服务，为医生提供智能的诊疗辅助工具。

### 核心功能
- **智能问诊系统**: AI驱动的多轮对话问诊，支持症状分析和中医证候诊断
- **五大名医人格**: 集成张仲景、叶天士、李东垣、郑钦安、刘渡舟五位名医的诊疗思维模式
- **智能症状分析**: 三层智能架构(缓存→数据库→AI)，103个症状的关系网络分析
- **多模态诊断**: 支持舌象、面象图片的AI分析，结合传统中医望诊
- **处方管理系统**: 从AI生成到医生审查到患者确认的完整医疗服务闭环
- **医疗安全保障**: 症状编造检测、西药过滤、医疗责任边界控制
- **支付代煎服务**: 集成支付宝、微信支付和第三方中药代煎配送服务
- **可视化决策树**: 医生诊疗思维可视化构建工具，支持节点编辑和思维库管理
- **思维库系统**: 医生临床诊疗模式保存与AI个性化问诊集成

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
- **数据存储**: SQLite (主数据库) + PostgreSQL + pgvector (向量数据库)
- **向量检索**: FAISS 1.7.4 (本地向量数据库，毫秒级响应)
- **图像处理**: PIL 10.1.0 (多模态图像分析)
- **中文处理**: jieba 0.42.1 (症状文本分词和分析)

**前端技术**
- **原生Web技术**: HTML5/CSS3/JavaScript (无框架依赖，兼容性强)
- **响应式设计**: 支持PC、平板、手机多端适配
- **PWA支持**: 渐进式Web应用，支持离线访问
- **可视化**: Canvas/SVG (决策树、数据图表)

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

### 🏥 智能医生工作台 (v2.6新增) ⭐
**核心价值**: 将原有"功能低效且无意义"的医生界面升级为专业高效的医疗工作空间

**智能仪表板系统**:
- **实时统计卡片**: 今日审查、本周审查、本月审查、患者总数的动态数据展示
- **提醒中心**: 待审处方提醒、随访提醒、紧急事项的智能推送系统  
- **效率图表**: Canvas绘制的审查效率趋势图，支持周度和月度分析
- **快速操作面板**: 一键跳转常用功能，提升工作流程效率

**AI增强处方审查系统**:
- **智能分析引擎**: 基于中医理论的处方自动分析和风险评估
- **批量处理功能**: 支持多处方同时审查，提升大批量工作效率
- **AI推荐系统**: 智能推荐处方优化建议和替代方案
- **风险评级**: 自动识别高风险处方，优先级智能排序
- **7张数据库表**: prescription_ai_analysis, prescription_ai_recommendations等完整AI分析体系

**患者关系管理**:
- **患者档案**: 完整的病历记录、用药历史、疗效跟踪
- **预约随访**: 智能提醒系统，自动安排后续诊疗
- **就诊时间线**: 可视化病情变化趋势和治疗效果
- **患者分类**: 基于病情严重程度和治疗复杂度的智能分类

**技术架构优势**:
- **统一认证**: 完全集成v2.5统一认证系统，支持session_token
- **响应式设计**: 完美适配桌面和移动设备的医疗工作场景
- **JavaScript重构**: 完全重写JavaScript代码，修复语法错误和性能问题
- **动态权限**: 基于登录用户的动态权限和信息显示

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
**三层智能架构**:
- **第一层**: 内存缓存 (毫秒级，热点症状关系，5分钟TTL)
- **第二层**: SQLite数据库 (100ms级，103个症状关系网络，置信度评分)
- **第三层**: AI实时分析 (2-3秒，未知症状智能推理，自动学习存储)

**数据覆盖**: 失眠、胃痛、头痛、便秘等20+常见病症，覆盖主症、兼症、舌象、脉象

### 处方管理系统
**完整业务闭环**:
```
AI生成处方 → 安全校验 → 医生审查 → 患者确认 → 支付订单 → 代煎配送 → 服务完成
```

**安全保障机制**:
- **君臣佐使分析**: 智能识别方剂配伍结构
- **剂量安全检查**: 药材用量安全范围验证
- **配伍禁忌检查**: 中药相互作用安全评估

### 可视化决策树构建器 ⭐
**医生诊疗思维可视化工具**:
- **智能节点设计**: 固定220px宽度，自动文本换行，内容截断和展开功能
- **统一编辑体验**: 双击和右键编辑使用相同的美观对话框界面
- **思维库集成**: 临床决策模式保存，与AI问诊系统深度集成
- **个性化AI**: 基于医生诊疗风格的智能问诊定制化服务

### 思维库系统
**医生诊疗经验知识管理**:
- **临床模式提取**: 自动分析决策树中的诊断逻辑、治疗原则
- **结构化存储**: 决策点、诊断流程、治疗原则的规范化数据存储
- **AI问诊集成**: 统一问诊服务调用医生个性化诊疗模式
- **智能匹配**: 根据患者症状智能匹配相关临床经验模式

## 系统命令

### 服务启动
```bash
# 开发环境
python api/main.py

# 生产环境 (systemd) ⚠️ 重要：代码修改后必须重启服务
sudo systemctl restart tcm-ai  # 重启服务 (代码更新后必须)
sudo systemctl status tcm-ai   # 检查状态
sudo systemctl start tcm-ai    # 启动服务
sudo systemctl enable tcm-ai   # 开机自启

# 测试环境
python api/main_test_8002.py
```

### 数据库管理
```bash
# 主数据库迁移
sqlite3 data/user_history.sqlite < database/migrations/002_new_architecture.sql

# 智能症状分析系统初始化
sqlite3 data/user_history.sqlite < database/migrations/003_create_symptom_database.sql
sqlite3 data/user_history.sqlite < database/data/initial_symptom_data.sql

# 数据库备份
sqlite3 data/user_history.sqlite ".backup backup_$(date +%Y%m%d_%H%M%S).db"

# 症状数据库统计
curl -X GET "http://localhost:8000/api/symptom/database/stats"
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
```

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

### 主数据库表结构 (SQLite)
```sql
-- 用户系统
users_new              # 统一用户表 (患者、医生、管理员)
patients_new           # 患者详细信息 
doctors_new            # 医生详细信息 (执业证号、专科)

-- 诊疗系统
consultations_new      # 问诊记录 (症状分析、证候、对话记录)
prescriptions_new      # 处方管理 (方剂、状态流转、版本控制)

-- AI增强处方审查系统 (v2.6新增)
prescription_ai_analysis        # AI处方分析结果表
prescription_ai_recommendations # AI处方推荐表
prescription_risk_ratings       # 处方风险评级表
prescription_batch_operations   # 批量操作记录表
prescription_audit_trail        # 处方审查审计追踪表
doctor_review_patterns         # 医生审查模式学习表
ai_analysis_cache             # AI分析结果缓存表

-- 智能症状分析系统
tcm_diseases          # 中医疾病/证候表
tcm_symptoms          # 症状表 (主症、兼症、舌象、脉象)
symptom_relationships # 症状关系表 (置信度、频率、数据源)
symptom_clusters      # 症状聚类缓存 (性能优化)
ai_symptom_analysis_log # AI分析日志 (学习优化)

-- 思维库系统
clinical_patterns     # 临床诊疗模式表 (医生诊疗经验存储)
decision_trees        # 决策树数据表 (可视化决策构建)

-- 订单系统  
orders_new            # 订单管理 (金额、代煎服务、配送)
payments_new          # 支付记录
decoction_orders      # 代煎订单

-- 审计系统
audit_logs           # 操作审计 (用户行为、系统事件)
security_events      # 安全事件 (症状编造、违规操作)
user_sessions        # 会话管理
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
# systemd服务配置
/etc/systemd/system/tcm-ai.service

# nginx反向代理
/etc/nginx/sites-available/tcm-ai.conf

# 服务管理
systemctl start tcm-ai && systemctl enable tcm-ai
```

### 环境配置
- **运行端口**: 8000 (生产), 8002 (测试)  
- **数据路径**: `/opt/tcm-ai/data/`
- **日志路径**: `/opt/tcm-ai/logs/ + api.log`
- **静态资源**: `/opt/tcm-ai/static/`

### 依赖服务
- **阿里云Dashscope**: AI模型服务 (必需)
- **PostgreSQL**: 向量数据库 (可选，FAISS为备选)
- **nginx**: 反向代理和静态资源服务
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
   - ✅ nginx配置：`/etc/nginx/conf.d/tcm-ai.conf`

2. **API端点检查**：
   - ✅ 统一问诊：`/api/consultation/chat` 
   - ✅ 认证登录：`/api/auth/login`, `/api/v2/auth/*`
   - ✅ 症状分析：`/api/symptom/*`
   - ✅ 处方管理：`/api/prescription/*`
   - ✅ AI处方审查：`/api/prescription-ai/*` (分析、推荐、风险评估、批量操作)
   - ✅ 思维库管理：`/api/save_clinical_pattern`, `/api/get_doctor_patterns`
   - ✅ 医生工作台：`/api/prescription/doctor/stats`, `/api/prescription/pending`

3. **数据库表结构**：
   - ✅ 用户系统：`users_new`, `patients_new`, `doctors_new`
   - ✅ 问诊系统：`consultations_new`, `prescriptions_new`
   - ✅ 症状分析：`tcm_symptoms`, `symptom_relationships`
   - ✅ 思维库系统：`clinical_patterns`, `decision_trees`

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
**最后更新**: 2025-09-21  
**文档版本**: v2.6 (智能医生工作台重构版)

---

*本文档为TCM-AI项目的核心指令文档，包含系统架构、开发规范、部署指南和维护标准。请严格遵循本文档进行系统开发和维护工作。*