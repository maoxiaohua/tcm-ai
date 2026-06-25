"""Additional page route setup helpers (stage-8)."""

from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse


def register_console_and_test_page_routes(app: FastAPI) -> None:
    """Register console/test pages while preserving legacy behavior."""

    @app.get("/doctor")
    async def doctor_main():
        """医生工作台主页 - 完整功能版本"""
        return FileResponse("/home/ute/tcm-ai/static/doctor/index.html")

    @app.get("/admin")
    async def admin_main():
        """管理员系统主页"""
        return FileResponse("/home/ute/tcm-ai/static/admin/index.html")

    @app.get("/mindmap")
    async def mindmap_main():
        """AI智能思维导图生成器"""
        return FileResponse("/home/ute/tcm-ai/static/mindmap/index.html")

    @app.get("/decision_tree_visual_builder.html")
    async def decision_tree_builder():
        """决策树可视化构建器 - 向后兼容路由"""
        return FileResponse("/home/ute/tcm-ai/static/decision_tree_visual_builder.html")

    @app.get("/debug-doctor")
    async def get_debug_doctor_page():
        """医生工作台调试页面"""
        return FileResponse("/home/ute/tcm-ai/debug_doctor.html")

    @app.get("/test-prescription")
    async def get_test_prescription_page():
        """处方解锁功能测试页面"""
        return FileResponse("/home/ute/tcm-ai/static/test_prescription_unlock.html")

    @app.get("/test-persistence")
    async def test_persistence_page():
        """测试页面刷新持久性"""
        return FileResponse("/home/ute/tcm-ai/test_persistence.html")

    @app.get("/test-cross-device")
    async def test_cross_device_page():
        """测试跨设备支付同步"""
        return FileResponse("/home/ute/tcm-ai/test_cross_device.html")

    @app.get("/test-history-sync")
    async def test_history_sync_page():
        """测试跨设备历史记录同步"""
        return FileResponse("/home/ute/tcm-ai/test_cross_device_history.html")

    @app.get("/test-history-load")
    async def test_history_load_page():
        """测试历史记录从数据库加载"""
        return FileResponse("/home/ute/tcm-ai/template_files/test_history_load.html")

    @app.get("/test-quick-chat")
    async def test_quick_chat_page():
        """快速测试问诊功能"""
        return FileResponse("/home/ute/tcm-ai/template_files/quick_test_chat.html")

    @app.get("/test-consultation-detail")
    async def test_consultation_detail_page():
        """测试问诊详情显示功能"""
        return FileResponse("/home/ute/tcm-ai/template_files/test_consultation_detail.html")

    @app.get("/test-prescription-status")
    async def test_prescription_status_page():
        """测试处方状态显示功能"""
        return FileResponse("/home/ute/tcm-ai/template_files/test_prescription_status.html")

    @app.get("/debug-user-api")
    async def debug_user_api_page():
        """调试用户API"""
        return FileResponse("/home/ute/tcm-ai/debug_user_api.html")


def register_doctor_tool_page_routes(app: FastAPI) -> None:
    """Register doctor tooling pages while preserving legacy behavior."""

    @app.get("/doctor/portal")
    async def doctor_portal():
        """医生门户 - 友好URL"""
        return FileResponse("/home/ute/tcm-ai/static/doctor_portal.html")

    @app.get("/doctor/review")
    async def doctor_review_portal():
        """医生处方审查门户"""
        return FileResponse("/home/ute/tcm-ai/static/doctor_review_portal.html")

    @app.get("/prescription/confirm")
    async def patient_prescription_confirm():
        """患者处方确认页面"""
        return FileResponse("/home/ute/tcm-ai/static/patient_prescription_confirm.html")

    @app.get("/doctor/thinking")
    async def doctor_thinking():
        """医生思维录入 - 友好URL"""
        return FileResponse("/home/ute/tcm-ai/static/doctor_thinking_input.html")

    @app.get("/doctor/thinking-v2")
    async def doctor_thinking_v2():
        """医生思维录入V2 - 友好URL (推荐)"""
        return FileResponse("/home/ute/tcm-ai/static/doctor_thinking_input_v2.html")

    @app.get("/doctor/management")
    async def doctor_management():
        """医生管理 - 友好URL"""
        return FileResponse("/home/ute/tcm-ai/static/doctor_management.html")

    @app.get("/doctor-test")
    async def doctor_selection_test():
        """医生选择测试页面"""
        return FileResponse("/home/ute/tcm-ai/static/doctor_test.html")

    @app.get("/test-doctor-selection")
    async def test_doctor_selection_simple():
        """简单医生选择功能测试"""
        return FileResponse("test_doctor_selection.html")

    @app.get("/doctor_portal")
    async def doctor_portal_direct():
        """医生门户 - 直接URL (兼容性)"""
        return FileResponse("/home/ute/tcm-ai/static/doctor_portal.html")

    @app.get("/user_history")
    async def user_history_page():
        """用户历史记录页面"""
        return FileResponse("/home/ute/tcm-ai/static/user_history.html")

    @app.get("/qr_gallery")
    async def qr_gallery_page():
        """二维码管理页面"""
        return FileResponse("/home/ute/tcm-ai/static/qr_code_gallery.html")


def register_auth_entry_routes(app: FastAPI, logger: Any) -> None:
    """Register auth entry pages while preserving legacy behavior."""

    @app.get("/phone-binding")
    async def phone_binding_page():
        """手机号绑定页面"""
        try:
            with open("/home/ute/tcm-ai/static/phone_binding.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(html_content)
        except Exception as e:
            logger.error(f"加载手机绑定页面失败: {e}")
            return HTMLResponse("<h1>页面加载失败</h1>", status_code=500)

    @app.get("/register")
    async def register_page():
        """现代化统一认证门户 - 注册模式（自动切换到注册标签页）"""
        return RedirectResponse(url="/login?tab=register", status_code=302)
