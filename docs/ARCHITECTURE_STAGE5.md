# Stage-5 架构重构说明（运维状态端点解耦）

本阶段目标：在不改变 API 行为的前提下，将 `api/main.py` 中健康检查与运维状态端点注册逻辑抽离。

## 变更内容

1. 新增运维端点装配模块
   - `app/api/ops_setup.py`
   - 职责：
     - 注册 `/debug_status`
     - 注册 `/db_stats`
     - 注册 `/health`
     - 注册 `/api/system/health`
     - 注册 `/api/system/health/trends`
     - 注册 `/api/integration/status`
     - 注册 `/security_status`

2. `api/main.py` 改造
   - 新增 `_build_debug_status_payload()` 用于保持原有调试状态字段输出。
   - 原先散落在主文件中的上述运维端点，改为通过 `register_operational_routes(...)` 注册。

## 边界声明

- 本阶段仅迁移“端点注册与装配代码”，不调整业务语义。
- 路径与响应字段保持兼容。

