"""Page/portal route setup (stage-7)."""

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response


def register_three_interface_page_routes(app: FastAPI) -> None:
    """Register three-interface page routes while preserving legacy behavior."""

    @app.get("/doctor/login")
    async def doctor_login():
        """医生登录页面"""
        return FileResponse("/home/ute/tcm-ai/static/doctor/login.html")

    @app.get("/doctor/login.html")
    async def doctor_login_html():
        """医生登录页面 - 兼容.html后缀"""
        return FileResponse("/home/ute/tcm-ai/static/doctor/login.html")

    @app.get("/smart")
    async def smart_workflow():
        """智能工作流程 - 症状收集→医生推荐→AI问诊"""
        try:
            with open("/home/ute/tcm-ai/static/index_smart_workflow.html", "r", encoding="utf-8") as f:
                content = f.read()
                response = Response(content=content, media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
        except FileNotFoundError:
            return HTMLResponse(
                """
        <html>
            <head><title>智能工作流程页面未找到</title></head>
            <body>
                <h1>页面未找到</h1>
                <p>智能工作流程页面暂时不可用</p>
                <a href="/">返回主页</a>
            </body>
        </html>
        """
            )

    @app.get("/chrome-test")
    async def chrome_test():
        """Chrome浏览器兼容性测试页面"""
        try:
            with open("/home/ute/tcm-ai/static/chrome_test.html", "r", encoding="utf-8") as f:
                content = f.read()
                response = Response(content=content, media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
        except FileNotFoundError:
            return HTMLResponse("<h1>测试页面未找到</h1>")

    @app.get("/simple-test")
    async def simple_mobile_test():
        """简化版移动端测试页面"""
        try:
            with open("/home/ute/tcm-ai/static/simple_mobile_test.html", "r", encoding="utf-8") as f:
                content = f.read()
                response = Response(content=content, media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
        except FileNotFoundError:
            return HTMLResponse("<h1>测试页面未找到</h1>")

    @app.get("/doctor-dashboard")
    @app.get("/doctor_dashboard.html")
    async def doctor_dashboard():
        """医生工作台 - 现代化医生门户"""
        try:
            with open("/home/ute/tcm-ai/static/doctor_dashboard.html", "r", encoding="utf-8") as f:
                content = f.read()
                response = Response(content=content, media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
        except FileNotFoundError:
            return HTMLResponse(
                """
        <html>
            <head><title>医生工作台页面未找到</title></head>
            <body>
                <h1>页面未找到</h1>
                <p>医生工作台页面暂时不可用</p>
                <a href="/">返回主页</a>
            </body>
        </html>
        """
            )

    @app.get("/history")
    async def user_history():
        """用户历史记录页面"""
        try:
            with open("/home/ute/tcm-ai/static/user_history.html", "r", encoding="utf-8") as f:
                content = f.read()
                response = Response(content=content, media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
        except FileNotFoundError:
            return HTMLResponse(
                """
        <html>
            <head><title>用户历史页面未找到</title></head>
            <body>
                <h1>页面未找到</h1>
                <p>用户历史页面暂时不可用</p>
                <a href="/">返回主页</a>
            </body>
        </html>
        """
            )

    @app.get("/patient-portal")
    async def patient_portal_redirect():
        """患者门户 - 重定向到智能工作流程"""
        return RedirectResponse(url="/smart", status_code=301)

    @app.get("/database")
    async def database_manager():
        """数据库管理界面"""
        return FileResponse("/home/ute/tcm-ai/static/database_manager.html")

    @app.get("/nav")
    async def navigation_page():
        """导航页面 - 选择不同的功能入口"""
        try:
            with open("/home/ute/tcm-ai/static/navigation.html", "r", encoding="utf-8") as f:
                content = f.read()
                response = Response(content=content, media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
        except FileNotFoundError:
            return HTMLResponse(
                """
        <html>
            <head><title>导航页面未找到</title></head>
            <body>
                <h1>页面未找到</h1>
                <p>导航页面暂时不可用</p>
                <a href="/">返回主页</a>
            </body>
        </html>
        """
            )


def register_auth_portal_routes(app: FastAPI) -> None:
    """Register auth portal routes while preserving legacy behavior."""

    @app.get("/login")
    async def login_portal():
        """现代化统一认证门户"""
        return FileResponse("/home/ute/tcm-ai/static/auth_portal.html")

    @app.get("/login-test")
    async def login_test_page():
        """登录功能调试页面"""
        return FileResponse("/home/ute/tcm-ai/template_files/simple_login_test.html")

    @app.get("/admin/login")
    async def admin_login():
        """管理员登录页面 - 重定向到统一认证门户角色选择"""
        return RedirectResponse(url="/login?tab=roles")

    @app.get("/doctor/login-portal")
    async def doctor_login_portal():
        """医生登录门户 - 重定向到统一认证门户角色选择"""
        return RedirectResponse(url="/login?tab=roles")
