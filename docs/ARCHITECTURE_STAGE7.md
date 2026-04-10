# Stage-7 架构重构说明（三界面/门户页面路由解耦）

本阶段目标：在不改变 API 行为的前提下，将 `api/main.py` 中三界面页面路由与认证门户页面路由的注册逻辑抽离。

## 变更内容

1. 新增页面装配模块
   - `app/api/page_setup.py`
   - 职责：
     - `register_three_interface_page_routes(app)`：
       - `/doctor/login`
       - `/doctor/login.html`
       - `/smart`
       - `/chrome-test`
       - `/simple-test`
       - `/doctor-dashboard`
       - `/doctor_dashboard.html`
       - `/history`（保留历史重复定义行为）
       - `/patient-portal`
       - `/database`
       - `/nav`
     - `register_auth_portal_routes(app)`：
       - `/login`
       - `/login-test`
       - `/admin/login`
       - `/doctor/login-portal`

2. `api/main.py` 改造
   - 将上述页面类路由的内联定义替换为装配函数调用。
   - 保持原有调用位置与注册顺序，降低行为漂移风险。

## 边界声明

- 本阶段仅迁移“页面路由装配代码”，不改动业务处理语义。
- 路径、返回内容、缓存头与重定向状态码保持兼容。
