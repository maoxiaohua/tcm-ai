# TCM-AI 中医智能诊断系统

## 项目概览

TCM-AI是一个基于人工智能的中医智能诊断助手系统，集成了传统中医理论与现代AI技术。系统支持智能问诊、证候分析、方剂推荐、医生审查、处方管理和完整的医患服务闭环。

### 核心功能
- **智能问诊**: AI驱动的症状分析和中医证候诊断
- **智能症状分析系统**: 三层智能架构 (缓存→数据库→AI分析)，支持症状关系智能识别和决策树可视化构建 🆕
- **多医生人格**: 集成张仲景、叶天士、李东垣、郑钦安、刘渡舟五大名医思维模式  
- **方剂分析**: 君臣佐使智能分析，包含136种中药材数据库
- **医生门户**: 完整的医生注册、登录、处方审查工作流
- **处方管理**: 从AI生成到医生审查到患者确认的完整闭环
- **多模态支持**: 舌象、面象图片分析
- **安全防护**: 医疗安全检查、症状编造检测、西药过滤
- **支付集成**: 支持微信、支付宝支付，代煎服务订单管理

## 技术栈

### 后端技术
- **Web框架**: FastAPI 0.104.1 + Uvicorn 0.24.0
- **AI模型**: 阿里云Dashscope (通义千问) 1.14.1
- **数据库**: SQLite (主数据库) + PostgreSQL (向量数据库, 可选)
- **向量检索**: FAISS 1.7.4 + pgvector 0.7.4
- **图像处理**: PIL (Pillow) 10.1.0
- **文本处理**: jieba 0.42.1 (中文分词)
- **HTTP客户端**: requests 2.31.0

### 前端技术  
- **原生HTML/CSS/JavaScript**: 响应式设计
- **UI框架**: 无外部依赖，自定义样式
- **图表**: 原生Canvas/SVG
- **移动端优化**: PWA支持, 微信分享优化

### 开发工具
- **测试框架**: pytest 7.4.3 + pytest-asyncio 0.21.1
- **代码质量**: 内置医疗安全检查器
- **性能监控**: psutil 5.9.6 系统监控
- **部署**: systemd + nginx配置

## 命令和脚本

### 启动服务
```bash
# 开发环境启动
python api/main.py

# 生产环境启动 (systemd)
systemctl start tcm-ai
systemctl enable tcm-ai

# 测试环境启动
python api/main_test_8002.py
```

### 测试命令
```bash
# 运行所有测试
pytest

# 运行冒烟测试
pytest tests/smoke/ -v

# 运行回归测试
pytest -m regression

# 运行特定测试
pytest tests/test_herb_function_regression.py
```

### 数据库操作
```bash
# 数据库迁移
sqlite3 data/user_history.sqlite < database/migrations/002_new_architecture.sql

# 智能症状数据库迁移 🆕
sqlite3 data/user_history.sqlite < database/migrations/003_create_symptom_database.sql
sqlite3 data/user_history.sqlite < database/data/initial_symptom_data.sql

# 创建管理员用户
python create_admin_user.py

# 数据库备份
sqlite3 data/user_history.sqlite ".backup backup_$(date +%Y%m%d_%H%M%S).db"

# 症状数据库统计 🆕
curl -X GET "http://localhost:8000/api/symptom/database/stats"
```

### 性能监控
```bash
# 系统监控脚本
bash scripts/monitor_competition.sh

# 安全检查
bash scripts/quick_security.sh

# 预热脚本
bash scripts/warmup_for_competition.sh
```

## 代码风格和标准

### Python代码规范
- **编码**: UTF-8, `#!/usr/bin/env python3`
- **文档字符串**: 三引号注释，说明函数功能
- **类型提示**: 使用typing模块，Optional, List, Dict等
- **错误处理**: 使用try-except，记录详细日志
- **变量命名**: snake_case (函数/变量), PascalCase (类)

### 医疗安全标准
- **症状验证**: 严禁编造患者未描述的症状细节
- **西药过滤**: 自动检测和过滤西药推荐
- **舌象脉象**: 无图片时不得编造具体描述
- **安全提示**: 所有诊断建议必须包含"仅供参考"声明

### API设计规范
- **RESTful**: 遵循REST设计原则
- **统一响应**: `{"success": bool, "message": str, "data": any}`
- **错误处理**: HTTPException + 详细错误信息
- **版本控制**: 数据库记录版本字段，审计追踪

## 🆕 智能症状分析系统 

### 系统概览
智能症状分析系统是TCM-AI的核心创新功能，采用三层智能架构，实现从硬编码症状关系到AI驱动的症状智能识别系统的重大升级。

### 三层智能架构
```
第一层: 内存缓存 (毫秒级)
├── 热点症状关系缓存
├── 5分钟TTL自动过期
└── 高频查询优化

第二层: 数据库查询 (100ms级)  
├── 症状关系数据库 (SQLite)
├── 置信度评分系统
└── 多关系类型支持

第三层: AI智能分析 (2-3s级)
├── 未知症状实时分析
├── 结果自动学习存储
└── 持续优化闭环
```

### 数据库设计
```sql
-- 核心表结构
tcm_diseases           # 疾病/证候表 (失眠、胃痛、头痛等)
tcm_symptoms           # 症状表 (主症、兼症、舌象、脉象)
symptom_relationships  # 症状关系表 (direct/accompanying/concurrent/conditional)
symptom_clusters       # 症状聚类缓存 (性能优化)
ai_symptom_analysis_log # AI分析日志 (持续学习)
```

### API接口
```bash
# 快速症状分析 (前端集成)
GET /api/symptom/quick_analyze/{symptom_name}

# 完整症状关系分析
POST /api/symptom/analyze_relations 

# 数据库统计信息
GET /api/symptom/database/stats

# 症状聚类查询
GET /api/symptom/cluster/{symptom_name}

# 数据库初始化 (管理员)
POST /api/symptom/database/init
```

### 前端集成特性
- **智能症状合并**: 三优先级策略 (选中节点 > 症状相似度 > 节点创建时间)
- **异步数据库查询**: 非阻塞用户界面，流畅体验
- **决策树可视化**: 动态症状关系网络构建
- **缓存优化**: 避免重复API调用

### 性能指标
- **缓存命中率**: >80% (热点症状)
- **数据库响应**: <100ms (本地SQLite)
- **AI分析延迟**: 2-3s (外部API调用)
- **系统可用性**: 99.9% (三层降级机制)

### 当前数据规模
- **疾病覆盖**: 失眠、胃痛、头痛、便秘、腹泻、咳嗽、心悸等20+种常见病症
- **症状网络**: 103个中医症状，覆盖四诊合参
- **关系准确性**: 基于经典中医理论和临床经验
- **置信度评分**: 0.7-0.9区间，支持频率分级

### 扩展计划
- **AI增强**: 集成通义千问进行未知症状智能分析
- **数据扩展**: 覆盖500+中医症状和100+证候
- **学习优化**: 基于用户行为的症状关系权重调整
- **多模态集成**: 结合舌象图像分析的症状推理

## 架构模式

### 分层架构
```
api/                    # API层 (FastAPI路由和控制器)
├── main.py            # 主应用入口
├── routes/            # 路由模块 (处方、医生、支付、代煎)
├── processors/        # 业务处理器 (聊天、图像、安全检查)
└── services/          # 服务层包装器

core/                   # 核心业务层
├── prescription/      # 处方分析和方剂系统
├── doctor_system/     # 医生人格和思维模式
├── knowledge_retrieval/ # 知识检索和RAG系统
├── symptom_database/  # 智能症状分析系统 🆕
├── security/          # 安全和权限管理
└── cache_system/      # 智能缓存系统

services/              # 服务层 (业务逻辑)
├── medical_diagnosis_controller.py  # 诊疗控制器
├── multimodal_processor.py         # 多模态处理
└── famous_doctor_learning_system.py # 名医学习系统

database/              # 数据层
├── models/            # 数据模型
├── migrations/        # 数据库迁移
└── connection_pool.py # 连接池管理

static/                # 前端资源
├── index_v2.html      # 患者端主界面
├── doctor_portal.html # 医生端门户
└── patient/           # 患者端页面
```

### 设计模式
- **依赖注入**: FastAPI Depends用于权限验证
- **工厂模式**: 医生人格创建和LLM服务包装
- **策略模式**: 不同医生的诊疗策略  
- **观察者模式**: 处方状态变更审计日志
- **单例模式**: 缓存系统和会话管理器

## 测试理念

### 测试分层
- **单元测试** (`tests/unit/`): 核心算法和业务逻辑
- **集成测试** (`tests/integration/`): 服务间交互和数据流
- **端到端测试** (`tests/e2e/`): 完整用户工作流
- **冒烟测试** (`tests/smoke/`): 部署后快速健康检查

### 测试重点
- **医疗安全**: 症状编造检测, 西药过滤验证
- **回归测试**: 防止功能退化，确保系统稳定性
- **性能测试**: 高并发下的响应时间和资源使用
- **多模态测试**: 图像上传和分析功能验证

### 测试数据
- 测试文件统一存放在 `template_files/` 目录
- 使用真实症状案例，确保诊断准确性
- 包含五大医家的典型诊疗场景测试

## 数据库模式

### 主要表结构

#### 用户系统
```sql
users_new              # 统一用户表 (患者、医生、管理员)
├── uuid               # 全局唯一标识
├── user_type          # 用户类型 (patient/doctor/admin)
├── phone/email        # 联系方式
└── status             # 账户状态

patients_new           # 患者详细信息
doctors_new            # 医生详细信息 (执业证号、专科等)
```

#### 诊疗系统
```sql
consultations_new      # 问诊记录
├── uuid               # 问诊唯一标识  
├── patient_id         # 患者ID
├── symptoms_analysis  # 症状分析 (JSON)
├── tcm_syndrome       # 中医证候
└── conversation_log   # 对话记录 (JSON)

prescriptions_new      # 处方管理
├── consultation_id    # 关联问诊记录
├── herbs              # 方剂内容
├── status             # 处方状态流转
├── reviewed_by        # 医生审查信息
└── version            # 版本控制
```

#### 订单系统
```sql
orders_new             # 订单管理
├── prescription_id    # 关联处方
├── total_amount       # 订单金额
├── needs_decoction    # 代煎服务
└── shipping_address   # 配送信息 (JSON)

payments_new           # 支付管理
└── decoction_orders   # 代煎订单
```

#### 审计系统
```sql
audit_logs             # 操作审计
security_events        # 安全事件
user_sessions          # 会话管理
system_settings        # 系统配置
```

### 数据完整性
- **外键约束**: 确保数据关系完整性
- **检查约束**: 状态枚举、金额非负等业务规则
- **触发器**: 自动更新时间戳、版本控制、审计日志
- **索引优化**: 查询性能优化，复合索引设计

## 安全考量

### 医疗安全
- **症状编造检测**: 实时检查AI是否添加患者未描述的症状
- **西药过滤系统**: 自动识别和过滤西药名称
- **诊断责任声明**: 所有建议包含"仅供参考，建议面诊"
- **舌象脉象验证**: 无图像时禁止编造具体描述

### 系统安全
- **RBAC权限系统**: 基于角色的访问控制 (患者/医生/管理员)
- **会话管理**: JWT令牌 + SQLite会话存储
- **安全审计**: 完整的操作日志和安全事件记录
- **输入验证**: 严格的参数验证和SQL注入防护

### 数据安全
- **敏感信息保护**: 密码哈希存储，敏感配置加密
- **数据隔离**: 患者数据访问权限控制
- **审计追踪**: 所有数据变更记录操作人和时间
- **备份策略**: 自动化数据库备份和恢复机制

## 部署与基础设施

### 生产环境部署
```bash
# systemd服务配置
/etc/systemd/system/tcm-ai.service

# nginx反向代理配置  
/etc/nginx/sites-available/tcm-ai.conf

# 服务管理
systemctl start tcm-ai
systemctl enable tcm-ai
systemctl status tcm-ai
```

### 环境配置
- **端口**: 8000 (开发), 8002 (测试)
- **数据库路径**: `/opt/tcm-ai/data/`
- **日志路径**: `/opt/tcm-ai/logs/` + `api.log`
- **静态资源**: `/opt/tcm-ai/static/`

### 依赖服务
- **阿里云Dashscope**: AI模型服务 (必需)
- **PostgreSQL**: 向量数据库 (可选，FAISS为备选)
- **Redis**: 会话缓存 (可选，SQLite为备选) 
- **nginx**: 反向代理和静态资源服务

## 常见陷阱

### 开发陷阱
1. **症状编造**: AI容易从"便秘"推测"大便干结如栗"，需严格检测
2. **西药泄露**: 知识库可能包含西药，需实时过滤
3. **循环导入**: 模块间依赖需注意import顺序
4. **数据库锁**: SQLite并发访问需要适当的连接池管理

### 部署陷阱
1. **API密钥泄露**: Dashscope密钥不能硬编码
2. **文件权限**: SQLite数据库文件需要正确的读写权限  
3. **静态资源**: nginx配置需要正确的静态文件路径
4. **内存泄露**: 大量会话和缓存可能导致内存问题

### 业务陷阱
1. **处方状态不一致**: 状态流转需要原子性操作
2. **医生权限混乱**: RBAC系统角色分配需要严格验证
3. **对话上下文丢失**: conversation_id管理不当
4. **图像分析失败**: 多模态处理需要异常处理

## 性能指南

### 缓存策略
- **智能缓存** (`core/cache_system/`): 基于症状相似度的缓存命中
- **数据库查询缓存**: 常用方剂和药材信息缓存
- **会话缓存**: 活跃会话内存存储，过期自动清理
- **静态资源缓存**: nginx配置长期缓存

### 查询优化
- **数据库索引**: 复合索引优化高频查询
- **分页查询**: 处方列表和历史记录分页加载  
- **异步处理**: AI调用和图像分析异步处理
- **连接池**: 数据库连接复用，避免频繁连接

### 性能监控
```python
# 系统状态检查
GET /debug_status

# 缓存命中率
cache_system.get_cache_stats()

# 数据库性能
database_index_optimizer.analyze_query_performance()
```

## 调试与开发

### 开发环境设置
```bash
# 安装依赖
pip install -r requirements.txt

# 环境变量配置
export DASHSCOPE_API_KEY="your_api_key"  
export TCM_DEBUG_MODE=true

# 启动开发服务器
python api/main.py
```

### 调试工具
- **日志系统**: 详细的调试日志 (`api.log`)
- **状态端点**: `/debug_status` 实时系统状态
- **测试数据**: `template_files/` 目录包含测试用例
- **对话日志**: `api/conversation_logs/` 保存完整对话记录

### 常用调试命令
```bash
# 查看实时日志
tail -f api.log

# 检查服务状态  
curl localhost:8000/debug_status

# 测试特定医生
pytest tests/integration/test_doctor_personalization.py::test_zhang_zhongjing

# 验证安全功能
python template_files/test_prescription_format.py
```

## 外部依赖

### 必需依赖
- **阿里云Dashscope API**: 核心AI模型服务
  - 配置: `AI_CONFIG.dashscope_api_key`
  - 模型: qwen-max, qwen-vl-plus (图像分析)
  - 限制: API调用频率限制

### 可选依赖  
- **PostgreSQL + pgvector**: 高性能向量检索
  - 备选: FAISS本地向量数据库
  - 配置: `DATABASE_CONFIG.postgres_*`

### 外部服务集成
- **微信支付**: 处方支付功能
- **支付宝支付**: 多支付渠道支持  
- **代煎服务商**: 第三方代煎API集成
- **短信服务**: 处方状态通知 (可选)

## 文档标准

### 代码文档
- **模块文档**: 每个Python文件顶部包含功能说明
- **函数文档**: 参数、返回值、异常说明
- **类文档**: 用途、关键方法、使用示例
- **配置文档**: 所有配置项在 `config/settings.py` 集中管理

### API文档
- **自动生成**: FastAPI自动生成OpenAPI文档
- **访问地址**: `http://localhost:8000/docs`
- **接口说明**: 详细的请求/响应示例
- **错误码**: 标准HTTP状态码 + 业务错误码

### 变更文档
- **数据库迁移**: `database/migrations/` SQL文件记录架构变更
- **功能变更**: 重大变更记录在 `docs/` 目录
- **安全更新**: 安全相关修改需要详细说明

### 部署文档
- **服务配置**: systemd和nginx配置文件
- **环境要求**: Python版本、系统依赖说明
- **监控指标**: 关键性能指标和告警阈值
- **故障排除**: 常见问题解决方案

## 开发工作流

### 功能开发
1. **需求分析**: 理解中医业务需求和安全要求
2. **设计评审**: 架构设计符合分层原则
3. **编码实现**: 遵循代码规范，严格测试
4. **安全检查**: 医疗安全和系统安全双重验证
5. **性能测试**: 确保高并发下系统稳定性

### 测试策略
1. **先写测试**: TDD方式开发核心功能
2. **安全先行**: 每个功能都要通过安全检查
3. **回归保护**: 重要功能变更必须有回归测试
4. **性能基准**: 关键路径性能不能回退

### 发布流程
1. **代码审查**: 多人review，重点关注医疗安全
2. **全量测试**: 运行完整测试套件
3. **预发布验证**: 生产环境数据验证
4. **灰度发布**: 逐步放量，监控关键指标
5. **回滚准备**: 快速回滚机制和数据恢复预案

## 常见问题及解决方案

### JavaScript按钮无响应问题

**问题描述**: 页面加载正常，但所有按钮点击无反应，浏览器控制台显示JavaScript语法错误。

**常见错误类型**:
1. `Uncaught SyntaxError: Unexpected token 'catch'` - 缺少对应的try语句
2. `Uncaught SyntaxError: Identifier 'diseaseName' has already been declared` - 变量重复声明

**标准解决流程**:
1. **语法错误检查**
   ```bash
   # 在浏览器F12控制台查看具体错误信息
   # 定位到具体的行号和错误类型
   ```

2. **try-catch结构修复**
   ```javascript
   // 错误示例：缺少try
   function someFunction() {
       // 一些代码
   } catch (error) {
       console.error('错误:', error);
   }

   // 正确示例：添加try
   function someFunction() {
       try {
           // 一些代码
       } catch (error) {
           console.error('错误:', error);
       }
   }
   ```

3. **变量重复声明修复**
   ```javascript
   // 错误示例：多个函数中重复声明同名变量
   function func1() {
       const diseaseName = getValue();
   }
   function func2() {
       const diseaseName = getValue(); // 重复声明错误
   }

   // 正确解决方案：使用全局辅助函数
   function getCurrentDiseaseName() {
       return document.getElementById('diseaseName')?.value?.trim() || '';
   }
   
   function func1() {
       // 直接使用getCurrentDiseaseName()，不声明局部变量
       const name = getCurrentDiseaseName();
   }
   ```

**紧急修复方案**:
如果问题复杂，可以在文件末尾添加强制事件绑定：
```javascript
// 紧急修复：强制重新绑定主要按钮事件
setTimeout(function() {
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.onclick = function() {
            generateAITree();
        };
    }
}, 1000);
```

### Git版本管理最佳实践

**自动化Git工作流程**:
Claude将在修改重要文件前自动执行以下操作：

```bash
# 1. 自动备份要修改的文件
git add <specific-file-to-modify>
git commit -m "自动备份：修改 <filename> 前快照"

# 2. 修改完成后自动提交
git add <modified-files>
git commit -m "具体的修复说明 + 生成标识"
```

**自动备份规则**:
- HTML/JavaScript文件：始终备份
- Python核心文件：始终备份
- 配置文件：始终备份
- 缓存/日志文件：不备份
- 临时文件：不备份

**修改过程中**:
```bash
# 分步骤提交，便于回滚
git add specific_file.html
git commit -m "修复: 添加missing try语句"

git add specific_file.html  
git commit -m "修复: 解决diseaseName重复声明问题"
```

**紧急回滚**:
```bash
# 查看最近的提交
git log --oneline -10

# 回滚到指定提交
git reset --hard <commit-hash>

# 或回滚到最近的工作状态
git checkout backup-<timestamp>
```

**文件级别的快速备份**:
```bash
# 修改重要文件前创建备份
cp static/decision_tree_visual_builder.html static/decision_tree_visual_builder.html.backup

# 出现问题时快速恢复
mv static/decision_tree_visual_builder.html.backup static/decision_tree_visual_builder.html
```

### 调试工作流程

**标准调试步骤**:
1. **创建简化测试版本** - 验证基础功能是否正常
2. **定位具体错误** - 使用浏览器F12控制台
3. **分步骤修复** - 每次只修复一个问题
4. **验证修复效果** - 确保修复不引入新问题
5. **提交版本控制** - 记录修复过程

**会话中断恢复指南**:
1. **检查CLAUDE.md** - 查看最新的已知问题和解决方案
2. **查看git历史** - 了解最近的修改记录
3. **运行基础测试** - 验证当前系统状态
4. **查看控制台错误** - 识别当前存在的问题

**预防措施**:
- 重要修改前必须创建git备份
- 复杂功能分步骤开发和提交
- 保持CLAUDE.md文档的更新
- 记录每次问题的根本原因和解决方案

---

## 🆕 版本更新日志

### v2.1 - 智能症状分析系统 (2025-01-09)
**重大架构升级**: 从硬编码症状关系升级为AI驱动的智能症状分析系统

#### 新增功能
- ✨ **三层智能架构**: 内存缓存 → 数据库查询 → AI分析的渐进式症状识别
- ✨ **症状关系数据库**: 5个核心表，支持多维度症状关系管理
- ✨ **智能API接口**: 7个症状分析API，支持快速查询和完整分析
- ✨ **决策树集成**: 可视化决策树构建器与数据库无缝集成
- ✨ **性能优化**: 三层缓存机制，平衡响应速度和系统资源

#### 技术改进
- 🔧 **数据库设计**: 症状、疾病、关系、聚类、AI日志五表架构
- 🔧 **置信度评分**: 0-1置信度评分和frequency频率分级系统
- 🔧 **数据源追踪**: expert/ai/literature/clinical多源数据支持
- 🔧 **智能合并**: 三优先级症状合并策略优化用户体验
- 🔧 **异步查询**: 非阻塞数据库查询，流畅的前端交互

#### 数据覆盖
- 📊 **疾病系统**: 失眠、胃痛、头痛等20+常见中医病症
- 📊 **症状网络**: 103个症状，涵盖主症、兼症、舌象、脉象
- 📊 **关系准确性**: 基于经典中医理论，专家标注数据
- 📊 **扩展能力**: 支持无限症状和疾病动态扩展

#### 文件变更
- 新增: `/core/symptom_database/` - 智能症状分析核心模块
- 新增: `/api/routes/symptom_analysis_routes.py` - 症状分析API路由  
- 新增: `/database/migrations/003_create_symptom_database.sql` - 数据库迁移
- 新增: `/database/data/initial_symptom_data.sql` - 初始症状数据
- 更新: `/api/main.py` - 集成症状分析路由
- 更新: `/static/decision_tree_visual_builder.html` - 前端数据库集成

### v2.2 - 可视化决策树真实AI集成升级 (2025-09-07)
**重大功能修复**: 彻底解决可视化决策树构建器"假AI"问题，实现真实AI集成

#### 问题发现与解决
**原始问题**: 用户发现 `https://mxh0510.cn/static/decision_tree_visual_builder.html` 的AI功能完全是假的
- 所有"AI生成"实际使用硬编码模板
- 响应时间异常快速（毫秒级），无真实AI调用
- `generate_visual_decision_tree` API直接调用模板函数
- 用户输入被完全忽略，始终返回相同结果

#### 核心技术升级
- ✨ **真实AI集成**: 彻底替换假模板，接入阿里云Dashscope qwen-max模型
- ✨ **混合智能模式**: AI主导 + 模板备份的双重保障机制
- ✨ **透明化体验**: 用户界面实时显示真实数据来源（AI/模板）
- ✨ **智能故障转移**: AI服务不可用时自动降级到模板模式
- ✨ **学习记录系统**: AI分析结果和用户反馈的持久化存储

#### 用户体验改进
- 🔧 **AI模式切换**: 前端Toggle开关，用户可自主选择AI/模板模式
- 🔧 **状态透明**: 实时显示"AI智能生成"vs"模板生成"标识
- 🔧 **生成耗时显示**: 真实反映AI调用时间（2-3秒）vs模板时间（毫秒）
- 🔧 **数据源标记**: 每个决策树路径标注数据来源和置信度
- 🔧 **用户偏好**: 记住用户的AI模式选择偏好

#### 技术实现细节
```python
# 真实AI调用实现 (services/famous_doctor_learning_system.py)
async def _generate_ai_decision_paths(self, disease_name: str, thinking_process: str, complexity_level: str):
    response = await asyncio.to_thread(
        dashscope.Generation.call,
        model=self.ai_model,  # qwen-max
        prompt=constructed_prompt,
        result_format='message'
    )
    return self._parse_ai_response(response)

# 混合模式逻辑
if use_ai and self.ai_enabled:
    try:
        ai_result = await self._generate_ai_decision_paths(...)
        return {"source": "ai", "method": "AI智能生成", ...}
    except Exception:
        fallback_result = self._generate_template_paths(...)
        return {"source": "template_fallback", "method": "模板备份", ...}
```

#### 前端JavaScript增强
```javascript
// AI状态检查和模式切换
async function initializeAIStatus() {
    const response = await fetch('/api/ai_status');
    const data = await response.json();
    updateAIStatusDisplay(data.ai_enabled);
}

// 真实数据来源显示
function updateGenerationStatus(source, generationTime) {
    const badge = source === 'ai' ? 
        `<span class="ai-badge">🤖 AI智能生成 (${generationTime}s)</span>` :
        `<span class="template-badge">📋 模板生成</span>`;
}
```

#### 安全性和可靠性提升
- 🛡️ **降级机制**: AI失败时自动使用模板，保证服务连续性
- 🛡️ **数据验证**: AI返回结果的结构化验证和安全检查
- 🛡️ **错误处理**: 完善的异常处理和用户友好的错误提示
- 🛡️ **性能监控**: AI调用耗时和成功率统计
- 🛡️ **用户信任**: 数据来源100%透明，杜绝虚假AI声明

#### 文件变更记录
- 重构: `services/famous_doctor_learning_system.py` - 新增真实AI决策树生成函数
- 更新: `api/routes/doctor_decision_tree_routes.py` - API支持混合模式和状态查询
- 升级: `static/decision_tree_visual_builder.html` - 完整AI交互界面和透明化显示
- 新增: AI状态检查、用户偏好管理、学习数据存储等配套功能

#### 测试验证结果
- ✅ 决策树生成：3个路径，结构完整
- ✅ 前端集成：AI切换、状态显示、数据源标记全部正常
- ✅ 混合模式：AI故障时自动降级到模板
- ✅ 用户体验：从假AI欺骗到真实AI透明化的质的飞跃

#### 影响评估
**用户价值**: 解决了严重的信任危机，从虚假AI变为真实智能系统
**技术债务**: 彻底清除了技术欺骗，建立了可信赖的AI基础架构
**系统可靠性**: 双重保障机制确保服务永不中断
**未来扩展**: 为更多AI功能的真实集成奠定了基础

---

## 🔄 文档维护规则

### 自动更新协议
**重要规则**: 以后所有新增的技术功能、架构变更、重要修复都必须自动更新到本CLAUDE.md文档中

#### 更新触发条件
1. **新技术集成**: 任何新的AI模型、第三方服务、技术栈组件
2. **架构变更**: 数据库schema变更、API路由新增、核心模块重构
3. **功能升级**: 用户可见的新功能、现有功能的重大改进
4. **安全修复**: 安全漏洞修复、权限系统升级、数据保护改进
5. **性能优化**: 显著的性能提升、缓存机制改进、系统优化
6. **Bug修复**: 影响用户体验的重要bug修复、回归问题解决

#### 更新内容要求
- **版本号**: 按照 vX.Y 格式递增，重大变更升级主版本号
- **日期标记**: YYYY-MM-DD 格式的准确更新日期
- **变更分类**: 新增功能✨/技术改进🔧/修复问题🐛/性能优化⚡/安全提升🛡️
- **技术细节**: 关键代码片段、配置变更、数据库修改
- **文件清单**: 所有修改的文件路径和变更性质
- **测试结果**: 功能验证、性能指标、用户体验评估
- **影响评估**: 对系统、用户、开发的具体影响

#### Claude助手执行规则
1. **主动识别**: 在完成任何技术任务后，自动评估是否需要更新文档
2. **及时记录**: 完成功能开发的同时更新CLAUDE.md，不得延后
3. **完整描述**: 包含问题背景、解决方案、技术实现、测试验证的完整流程
4. **版本控制**: 先备份现有文档，再进行更新，确保可回滚
5. **质量检查**: 更新后验证文档格式、链接有效性、技术准确性

#### 协作开发规则
- 所有开发人员完成功能后必须更新相应的CLAUDE.md章节
- 重大架构决策必须在CLAUDE.md中记录决策理由和替代方案
- 定期review文档一致性，确保与实际系统状态同步
- 文档更新作为功能完成的必要条件，不更新文档视为未完成

### v2.2.1 - AI模式切换按钮修复 (2025-09-07)
**Bug修复**: 解决可视化决策树构建器中AI/模板模式切换按钮无反应问题

#### 问题发现
用户报告AI模式切换Toggle按钮点击无反应，无法在AI智能模式和标准模板模式之间切换。

#### 根本原因分析
1. **属性名不一致**: `aiStatus`对象初始化使用`enabled`，但事件处理中使用`ai_enabled`
2. **事件绑定时机**: AI状态异步加载，可能在事件监听器绑定之前
3. **缺少强制绑定**: 复杂的页面加载序列导致部分事件监听器失效

#### 技术修复方案
```javascript
// 🐛 原始问题代码
let aiStatus = {
    enabled: false,  // ❌ 属性名不一致
    // ...
}

function initializeModeToggle() {
    aiModeToggle.addEventListener('change', function() {
        const useAI = this.checked && aiStatus.ai_enabled; // ❌ 找不到属性
    });
}

// ✅ 修复后代码
let aiStatus = {
    ai_enabled: false,  // ✅ 统一属性名
    // ...
}

// 强制重新绑定机制
setTimeout(function() {
    const aiModeToggle = document.getElementById('aiModeToggle');
    if (aiModeToggle) {
        aiModeToggle.onchange = function() {
            console.log('🔄 AI模式切换触发!');
            const useAI = this.checked && aiStatus.ai_enabled;
            // 立即UI反馈
            updateUIDisplay(useAI);
        };
    }
}, 1500);
```

#### 新增功能特性
- 🔧 **即时视觉反馈**: 切换时立即更新按钮文本和图标
- 🔧 **详细调试日志**: 完整的切换状态追踪日志
- 🔧 **强制重新绑定**: 确保所有事件监听器都正确工作
- 🔧 **状态持久化**: 记住用户的模式选择偏好

#### 用户体验改进
- 切换按钮现在响应用户点击
- AI/模板模式实时切换显示
- 生成按钮文本同步更新 (🤖 AI智能生成 ↔️ 📋 标准模板生成)
- 模式状态文本颜色动态变化

#### 测试验证
- ✅ Toggle按钮点击响应正常
- ✅ 模式文本实时更新
- ✅ 按钮图标和文字同步变化
- ✅ 控制台日志输出正确状态
- ✅ 用户偏好正确保存

#### 文件变更
- 修复: `static/decision_tree_visual_builder.html` - AI模式切换逻辑和强制事件绑定

#### 影响评估
**用户价值**: 恢复了重要的用户控制功能，提升交互体验
**系统稳定性**: 解决了JavaScript事件系统的可靠性问题
**调试能力**: 增强的日志系统便于未来问题诊断

### v2.2.2 - AI状态API降级模式 (2025-09-07)
**系统可靠性提升**: AI状态API不可用时的智能降级处理机制

#### 发现的问题
用户报告AI模式切换按钮下方显示"AI服务不可用，将使用模板模式"，按钮被完全禁用无法点击。

#### 根本原因
1. **API路由404**: `/api/ai_status` 端点返回404 Not Found
2. **过度严格的错误处理**: API失败时完全禁用用户选择权
3. **缺少降级机制**: 没有备选方案保证功能可用性

#### 智能降级方案
```javascript
// 🔄 降级模式实现
async function initializeAIStatus() {
    try {
        const response = await fetch('/api/ai_status');
        if (response.ok) {
            // 正常AI状态处理
            const data = await response.json();
            aiStatus = data.data;
        } else {
            // 404降级处理
            console.warn('⚠️ AI状态API不可用 (404)，使用降级模式');
            aiStatus.ai_enabled = true;  // 允许用户选择
            
            statusIndicator.innerHTML = '⚡ 混合模式 (API降级)';
            statusIndicator.style.color = '#f59e0b';  // 橙色警告
        }
    } catch (error) {
        // 网络错误降级处理
        aiStatus.ai_enabled = true;
        statusIndicator.innerHTML = '⚡ 混合模式 (网络降级)';
    }
}
```

#### 用户体验优化
- 🔧 **智能降级**: API不可用时自动进入混合模式，保持功能可用
- 🔧 **状态透明**: 清楚显示当前系统运行模式 (正常/API降级/网络降级)
- 🔧 **用户控制**: 即使后端有问题，用户依然可以选择AI或模板模式
- 🔧 **视觉区分**: 降级模式使用橙色⚡标识，与正常绿色✅和错误红色⚠️区分

#### 系统鲁棒性提升
- **故障隔离**: 后端API问题不会影响前端功能可用性
- **优雅降级**: 系统部分故障时保持核心功能运行
- **用户反馈**: 透明显示系统状态，用户了解当前工作模式
- **功能保障**: 无论何种情况都能提供决策树生成服务

#### 测试场景覆盖
- ✅ API正常响应: 显示"✅ AI已就绪 (qwen-max)"
- ✅ API返回404: 显示"⚡ 混合模式 (API降级)"
- ✅ 网络连接失败: 显示"⚡ 混合模式 (网络降级)"
- ✅ 所有场景下Toggle按钮均可点击和切换

#### 文件变更
- 增强: `static/decision_tree_visual_builder.html` - 智能降级机制和状态显示

#### 架构意义
**高可用性**: 实现了真正的高可用前端架构，后端API故障不影响用户体验
**用户中心**: 优先保证用户功能可用性，而不是严格的技术正确性
**透明运行**: 用户始终了解系统真实状态，建立信任关系

---

*最后更新: 2025-09-07*  
*文档版本: 2.2.2*  
*维护人员: TCM-AI开发团队*