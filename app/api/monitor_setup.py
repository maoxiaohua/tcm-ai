"""Monitor/debug page and error-report route setup (stage-6)."""

from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse


def register_monitor_and_debug_routes(app: FastAPI, logger: Any) -> None:
    """Register monitor and debug routes while keeping legacy behavior."""

    @app.get("/system_monitor")
    async def system_monitor():
        """系统监控面板页面"""
        try:
            with open("static/system_monitor.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(html_content)
        except Exception as e:
            logger.error(f"加载监控面板页面失败: {e}")
            return HTMLResponse("<h1>监控面板加载失败</h1>", status_code=500)

    @app.get("/error_stats")
    async def get_error_statistics():
        """获取错误统计信息"""
        try:
            from enhanced_error_handler import get_error_handler

            handler = get_error_handler()
            stats = handler.get_error_statistics()
            return stats
        except Exception as e:
            logger.error(f"获取错误统计失败: {e}")
            return {"error": str(e)}

    @app.post("/report_error")
    async def report_client_error(error_data: dict):
        """接收客户端错误报告"""
        try:
            from enhanced_error_handler import get_error_handler, ErrorCategory

            handler = get_error_handler()

            error_type = error_data.get("type", "unknown")
            if "network" in error_type.lower() or "fetch" in error_type.lower():
                category = ErrorCategory.NETWORK
            elif "validation" in error_type.lower() or "input" in error_type.lower():
                category = ErrorCategory.VALIDATION
            else:
                category = ErrorCategory.SYSTEM

            client_error = Exception(error_data.get("message", "Client error"))

            result = handler.handle_error(
                client_error,
                category,
                context=error_data.get("context", {}),
                user_id=error_data.get("user_id"),
                language=error_data.get("language", "zh")
            )

            return result

        except Exception as e:
            logger.error(f"处理客户端错误报告失败: {e}")
            return {
                "success": False,
                "message": "错误报告处理失败",
                "error": str(e)
            }

    @app.get("/system/monitor")
    async def unified_system_monitor():
        """统一系统监控面板 - 集成性能和安全监控"""
        try:
            return FileResponse("/opt/tcm-ai/static/unified_system_monitor.html")
        except Exception as e:
            return HTMLResponse(f"<h1>统一监控面板加载失败</h1><p>{str(e)}</p>")

    @app.get("/debug/layout")
    async def debug_layout():
        """页面布局调试工具"""
        try:
            return FileResponse("/opt/tcm-ai/static/debug_layout.html")
        except Exception as e:
            return HTMLResponse(f"<h1>调试工具加载失败</h1><p>{str(e)}</p>")

    @app.get("/system_monitor")
    async def legacy_system_monitor():
        """重定向到统一监控面板"""
        return RedirectResponse(url="/system/monitor")

