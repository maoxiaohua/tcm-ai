# Stage-1 架构重构说明（零行为变化）

本阶段目标：先搭建主流分层架构骨架，不改动现有业务逻辑行为。

## 新增内容

1. `app.factory:create_app`  
   - 作为统一应用工厂入口。
   - 目前内部复用 `api.main.app`，确保行为不变。

2. `app/asgi.py`  
   - 供 `uvicorn` / `gunicorn` 使用的标准 ASGI 模块。

3. `app/*` 分层骨架目录  
   - `api/`, `services/`, `repositories/`, `domain/`, `schemas/`, `core/`
   - 当前仅占位，后续阶段逐步迁移现有代码。

4. 开发与运行脚本  
   - `scripts/dev_server.sh`：`uvicorn --reload` 自动热重载
   - `scripts/run_server.sh`：无 `reload` 的运行脚本

## 当前推荐启动方式

- 开发：`bash scripts/dev_server.sh`
- 生产：`bash scripts/run_server.sh`

## 边界声明

- 本阶段不迁移既有业务逻辑，不变更 API 行为。
- 所有新骨架均为“兼容包裹层”，用于降低后续分步迁移风险。

