# Stage-4 架构重构说明（静态与站点辅助路由解耦）

本阶段目标：在不改变 API 行为的前提下，将 `api/main.py` 中静态文件挂载与站点辅助路由注册逻辑抽离。

## 变更内容

1. 新增站点装配模块
   - `app/api/site_setup.py`
   - 职责：
     - `register_common_browser_file_routes(app)`
     - `setup_static_and_site_routes(app, logger, PATHS)`

2. `api/main.py` 改造
   - 原先内联的浏览器自动请求路由（favicon/robots/sitemap等）改为调用装配函数。
   - 原先内联的静态挂载与微信验证/站点地图/访问日志路由改为调用装配函数。
   - 保持调用时机与注册顺序，避免行为漂移。

## 边界声明

- 本阶段仅迁移“路由装配代码”，不迁移业务处理逻辑。
- 路径、响应结构、路由注册顺序保持不变。

