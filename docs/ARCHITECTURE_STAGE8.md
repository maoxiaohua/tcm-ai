# Stage-8 架构重构说明（控制台/测试/医生工具页面路由解耦）

本阶段目标：在不改变 API 行为的前提下，将 `api/main.py` 中剩余的控制台页面、测试页面、医生工具页面和认证入口页面的路由注册逻辑抽离。

## 变更内容

1. 新增页面装配模块
   - `app/api/feature_page_setup.py`
   - 职责：
     - `register_console_and_test_page_routes(app)`：
       - `/doctor`
       - `/admin`
       - `/mindmap`
       - `/decision_tree_visual_builder.html`
       - `/debug-doctor`
       - `/test-prescription`
       - `/test-persistence`
       - `/test-cross-device`
       - `/test-history-sync`
       - `/test-history-load`
       - `/test-quick-chat`
       - `/test-consultation-detail`
       - `/test-prescription-status`
       - `/debug-user-api`
     - `register_doctor_tool_page_routes(app)`：
       - `/doctor/portal`
       - `/doctor/review`
       - `/prescription/confirm`
       - `/doctor/thinking`
       - `/doctor/thinking-v2`
       - `/doctor/management`
       - `/doctor-test`
       - `/test-doctor-selection`
       - `/doctor_portal`
       - `/user_history`
       - `/qr_gallery`
     - `register_auth_entry_routes(app, logger)`：
       - `/phone-binding`
       - `/register`

2. `api/main.py` 改造
   - 将上述页面类路由的内联定义替换为装配函数调用。
   - 保持原有调用位置与注册顺序，降低行为漂移风险。

## 边界声明

- 本阶段仅迁移“页面路由装配代码”，不改动业务处理语义。
- 路径、返回内容、重定向状态码与异常回退行为保持兼容。
