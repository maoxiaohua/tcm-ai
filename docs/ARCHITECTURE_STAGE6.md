# Stage-6 架构重构说明（监控与调试路由解耦）

本阶段目标：在不改变 API 行为的前提下，将 `api/main.py` 中监控页面与调试/错误上报路由注册逻辑抽离。

## 变更内容

1. 新增监控装配模块
   - `app/api/monitor_setup.py`
   - 职责：
     - 注册 `/system_monitor`（监控页）
     - 注册 `/error_stats`
     - 注册 `/report_error`
     - 注册 `/system/monitor`
     - 注册 `/debug/layout`
     - 保留历史兼容的 `/system_monitor` 重定向定义

2. `api/main.py` 改造
   - 原先内联的上述监控/调试端点，改为调用 `register_monitor_and_debug_routes(app, logger)` 注册。
   - 保持原有调用时机，避免行为漂移。

## 边界声明

- 本阶段仅迁移“路由装配代码”，不调整业务语义。
- 端点路径、响应字段与兼容性行为保持不变。
