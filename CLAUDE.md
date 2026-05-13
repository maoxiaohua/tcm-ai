# CLAUDE.md

# Claude Code Project Rules
你是我的项目开发助手。我不是专业开发者，所以你必须主动控制风险，不能为了快速完成而跳过验证。
## 核心原则
1. 不要偏离用户原始需求。
2. 不要做无关重构。
3. 不要随意修改目录结构。
4. 不要删除已有功能。
5. 不要引入不必要的新依赖。
6. 不要只改前端忘记后端。
7. 不要只改后端忘记前端。
8. 不要声称问题解决，除非真实验证过。
9. 如果无法验证，必须明确说“无法完全验证”。
10. 所有修改都要以减少 bug 为目标，而不是看起来更复杂。
## 开发前必须做
每次写代码前先说明：
- 用户要解决的问题
- 涉及范围
- 计划修改的文件
- 不会修改的内容
- 风险点
- 验证方法
## 前后端规则
如果修改前端：
- 必须检查后端接口是否存在
- 必须检查请求 method 是否一致
- 必须检查字段名是否一致
- 必须检查返回数据是否匹配
- 必须检查错误提示和 loading 状态
如果修改后端：
- 必须检查前端是否调用该接口
- 必须检查前端字段是否同步
- 必须检查错误格式是否前端可识别
- 必须检查接口是否可以真实访问
## UI 规则
所有按钮必须检查：
- 文字颜色
- 图标颜色
- 背景颜色
- hover 状态
- disabled 状态
- loading 状态
禁止出现：
- 白字白底
- 黑字黑底
- 图标和背景同色
- hover 后文字消失
- disabled 后完全看不见
- 危险按钮和普通按钮没有区别
## 测试规则
修改完成后必须说明：
- 运行了什么命令
- 命令是否成功
- 是否验证了用户真正的问题
- 哪些部分没有验证
- 最终结论是：已解决 / 部分解决 / 未解决 / 无法完全验证
禁止：
- 只跑 build 就说功能完成
- 只跑 lint 就说 bug 修复
- 没运行测试却说已测试
- 测试失败但说完成
- 修改测试来掩盖问题
## 默认工作流
1. 理解需求
2. 限定范围
3. 找相关文件
4. 最小修改
5. 检查前后端一致性
6. 检查 UI 可见性
7. 运行真实测试
8. 汇报已验证和未验证内容
## 推荐使用的 agents
- project-manager：开发前控制范围
- frontend-backend-reviewer：检查前后端一致性
- ui-quality-reviewer：检查按钮、图标、文字可见性
- test-verifier：确认是否真实解决
- bug-hunter：查隐藏 bug
## 推荐使用的 skills
- /project-guard
- /minimal-change
- /frontend-backend-sync
- /ui-visibility-check
- /real-test-verification

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

TCM-AI 中医智能诊断系统 — FastAPI + SQLite + 阿里云Dashscope AI，融合多位名医人格的智能问诊/处方/医生工作台系统。当前活跃医生由 `doctors` 表中 `status = 'active'` 的记录决定。

## 常用命令

```bash
# 开发启动
python api/main.py                          # 开发环境 (端口 8000)
python api/main_test_8002.py                # 测试环境 (端口 8002)

# 生产环境 (systemd，走 scripts/start_service.py → api/main.py)
sudo service tcm-ai start|restart|stop|status

# Gunicorn (端口 7999, 4 workers)
gunicorn -c gunicorn_conf.py api.main:app

# 测试
pytest                                      # 完整测试套件
pytest tests/smoke/ -v                      # 冒烟测试
pytest tests/test_medical_diagnosis_safety.py
python tests/test_critical_features.py

# 数据库
sqlite3 data/user_history.sqlite ".tables"  # 查看所有表 (67+)
sqlite3 data/user_history.sqlite ".schema <table>"

# 部署前检查
bash scripts/pre_deploy_check.sh
```

## 架构

```
api/                  # FastAPI 应用入口 + 32 个路由模块
  main.py             # 应用工厂，注册所有路由和中间件
  routes/             # 按业务域拆分的路由文件
  services/           # 路由层服务 (UnifiedConsultationService 等)
  middleware/         # 认证、权限、日志中间件
core/                 # 业务逻辑核心
  consultation/       # 问诊引擎
  prescription/       # 处方生成/校验
  medical_safety/     # 症状编造检测、西药过滤、边界控制
  knowledge_retrieval/ # RAG 知识检索 (200+ 中医文档)
  symptom_database/   # 症状关系网络
services/             # 跨模块服务 (多模态处理、医生学习系统、邮件等)
config/settings.py    # 统一配置 (优先读 config/.env)
app/core/settings.py  # Stage-2 兼容层，re-export config/settings.py
static/               # 原生 HTML/CSS/JS 前端 (无框架)
  js/                 # 按功能拆分的 JS 模块 (smart_workflow_*.js 等)
database/             # 数据库迁移 SQL 文件
```

### 关键路由和前端页面

| 页面路由 | 模板文件 | API 前缀 |
|---------|---------|---------|
| `/login` | `auth_portal.html` | `/api/auth/*`, `/api/unified-auth/*` |
| `/smart` | `index_smart_workflow.html` | `/api/consultation/*` |
| `/doctor` | `doctor/index.html` | `/api/doctor/*`, `/api/prescription-ai/*` |
| `/admin` | `admin/index.html` | `/api/admin/*` |

## 核心业务规则

### 医疗安全 (最高优先级)
- **绝对禁止** AI 编造患者未描述的症状、舌象、脉象
- **绝对禁止** 推荐或泄露西药名称
- **绝对禁止** 超出中医诊疗范围的建议
- 所有诊断必须包含"仅供参考，建议面诊"
- 详细规则见 `DEVELOPMENT_GUIDELINES.md` 和 `core/medical_safety/`

### API 响应格式
统一格式: `{"success": bool, "message": str, "data": any}`

### 常见坑 (来自 DEVELOPMENT_GUIDELINES.md)
- **API 端点**: 统一问诊用 `/api/consultation/chat`，不是 `/chat` 或 `/api/chat`
- **医生 ID 映射**: 前端数字 `"1"` → 后端 `"zhang_zhongjing"`，需要显式映射
- **响应结构**: 统一问诊返回 `result.data.reply`，原系统返回 `result.reply`，需兼容处理
- **DB 字段**: 不同表用 `id` vs `uuid`，`speciality` vs `specialties`，先 `.schema` 确认
- **前后端双重逻辑**: PC 端和移动端有独立的函数 (`addMessage` vs `addMobileMessage`)，修改时两端都要检查

## 数据库核心表

67+ 张表，核心分组如下:
- **用户认证**: `unified_users`, `unified_sessions`, `user_roles`, `doctors`, `users`
- **问诊处方**: `consultations`, `prescriptions`, `prescription_changes`, `prescription_review_history`
- **AI 处方**: `prescription_ai_analysis`, `prescription_ai_recommendations`, `prescription_risk_ratings`
- **症状系统**: `tcm_symptoms`, `tcm_diseases`, `symptom_relationships`, `symptom_clusters`
- **医生工作**: `doctor_work_statistics`, `doctor_patient_relationships`, `doctor_clinical_patterns`, `mindmaps`
- **安全审计**: `audit_logs`, `security_events`, `security_audit_logs`, `security_alerts`
- **订单代煎**: `orders`, `decoction_orders`, `prescription_payment_logs`

## 开发约定

### 行为准则
- **不要做用户没要求的事情** — 不自动清理测试数据、不修改用户数据、不确定时先问
- 测试用临时数据，完成后询问是否清理
- 临时文件放 `template_files/` 目录

### Git 提交策略
- 开始解决新问题前: `git add -A && git commit -m "🔄 修改前备份: [描述]"`
- 同一问题的多次调试不需要中间备份
- 问题完全解决后: `git commit -m "[类型] [简要描述]"`
- 类型: 🐛 bug修复 / ✨ 新功能 / 🔧 配置 / 📚 文档 / 🏗️ 架构 / 🧪 测试

### Tips
1. 新增功能或链接前，先检查项目中是否已存在类似实现
2. 同一问题连续三次没解决，换思路
3. 每次回答前先 Review 系统核心功能，避免基础错误
4. 临时文件放 `template_files/`，保持根目录整洁
