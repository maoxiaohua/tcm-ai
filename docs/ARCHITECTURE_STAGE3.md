# Stage-3 架构重构说明（路由与中间件注册解耦）

本阶段目标：在不改变 API 行为的前提下，将 `api/main.py` 中“路由注册/异常处理/安全保护/CORS”的装配逻辑抽离。

## 变更内容

1. 新增注册模块
   - `app/api/registration.py`
   - 职责：
     - `register_all_routes(...)`
     - `setup_exception_and_security(...)`
     - `setup_cors_middleware(...)`

2. `api/main.py` 改造
   - 原先散落在主文件中的注册流程，改为调用 `app/api/registration.py` 提供的方法。
   - 保留原有路由模块导入时机，避免历史 `sys.path` 副作用引发行为变化。

## 边界声明

- 本阶段仅做“装配代码”迁移，不迁移业务逻辑实现。
- API 路径、响应结构、路由顺序保持不变。

