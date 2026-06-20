# Stage-2 架构重构说明（配置与日志模块）

本阶段目标：在不改变 API 行为的前提下，把“配置与日志”抽到新骨架中，作为后续模块迁移基础设施。

## 变更内容

1. 新增配置门面
   - `app/core/settings.py`
   - 作用：统一从新路径访问配置；内部暂时复用 `config.settings`，保证兼容。

2. 新增日志配置模块
   - `app/core/logging_config.py`
   - 作用：集中日志初始化逻辑（文件+stdout，文件失败自动降级）。

3. 已接入新模块的文件（行为保持不变）
   - `api/main.py`：日志初始化切换为 `configure_app_logging(...)`
   - `api/main.py`：配置导入切换为 `app.core.settings`
   - `api/routes/doctor_decision_tree_routes.py`：配置导入切换为 `app.core.settings`
   - `core/knowledge_retrieval/tcm_knowledge_graph.py`：路径配置导入切换为 `app.core.settings`

## 边界声明

- 本阶段不迁移业务逻辑，只迁移基础设施访问入口。
- 老路径 `config.settings` 仍可继续使用，后续阶段逐步收敛到 `app.core.settings`。

