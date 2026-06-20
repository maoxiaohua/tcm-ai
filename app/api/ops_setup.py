"""Operational/health route setup helpers (stage-5)."""

from datetime import datetime
from typing import Any, Callable, Dict, Optional
import time

from fastapi import FastAPI


def register_operational_routes(
    app: FastAPI,
    *,
    logger: Any,
    debug_status_provider: Callable[[], Dict[str, Any]],
    cache_system_available: bool,
    dashscope_api_key: Optional[str],
) -> None:
    """Register health/status/ops routes without changing behavior."""

    @app.get("/debug_status")
    async def debug_status_endpoint():
        try:
            return debug_status_provider()
        except Exception as e:
            logger.error(f"Error in debug_status: {e}")
            return {"error": str(e)}

    @app.get("/db_stats")
    async def get_database_stats():
        try:
            from simple_db_pool import get_db_pool

            pool = get_db_pool()
            stats = pool.get_stats()

            return {
                "status": "healthy",
                "active_connections": stats["active_connections"],
                "total_connections": stats["total_connections"],
                "max_connections": stats["max_connections"],
                "total_queries": stats["total_queries"],
                "uptime_minutes": stats["uptime_minutes"],
            }
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {"error": str(e)}

    @app.get("/health")
    async def health_check():
        start_time = time.time()

        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "checks": {
                    "api": "ok",
                    "database": "ok",
                    "cache": "ok",
                    "ai_service": "ok",
                },
            }

            try:
                from simple_db_pool import db_execute

                result = db_execute("SELECT 1", fetch="one")
                if not result:
                    health_status["checks"]["database"] = "error"
                    health_status["status"] = "unhealthy"
            except Exception:
                health_status["checks"]["database"] = "error"
                health_status["status"] = "unhealthy"

            if not cache_system_available:
                health_status["checks"]["cache"] = "warning"

            if not dashscope_api_key:
                health_status["checks"]["ai_service"] = "error"
                health_status["status"] = "unhealthy"

            response_time = round((time.time() - start_time) * 1000, 2)
            health_status["response_time"] = response_time

            return health_status

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    @app.get("/api/system/health")
    async def get_system_health_api():
        try:
            from system_health_monitor import get_system_health

            health_data = await get_system_health()
            return health_data
        except Exception as e:
            logger.error(f"系统健康检查失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "critical",
                "error": f"监控系统异常: {str(e)}",
                "checks": {},
            }

    @app.get("/api/system/health/trends")
    async def get_health_trends_api():
        try:
            from system_health_monitor import get_health_trends

            trends_data = get_health_trends()
            return trends_data
        except Exception as e:
            logger.error(f"获取健康趋势失败: {e}")
            return {"error": f"趋势分析异常: {str(e)}", "message": "No health history available"}

    @app.get("/api/integration/status")
    async def get_integration_status():
        try:
            return {
                "status": "healthy",
                "services": {
                    "qwen_turbo": "available",
                    "qwen_vl_plus": "available",
                    "dashscope_api": "configured",
                    "postgresql": "connected",
                    "cache_system": "active",
                },
                "integration_type": "unified_monitoring",
                "message": "所有服务正常集成运行",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"获取集成状态失败: {e}")
            return {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()}

    @app.get("/security_status")
    async def get_security_status():
        try:
            return {
                "medical_safety_enabled": True,
                "hallucination_detection_active": True,
                "prescription_safety_enabled": True,
                "safety_checks_total": 1247,
                "risks_detected": 3,
                "last_check": datetime.now().isoformat(),
                "security_modules": {
                    "medical_safety": "active",
                    "hallucination_filter": "active",
                    "prescription_validator": "active",
                    "content_sanitizer": "active",
                },
            }
        except Exception as e:
            return {
                "error": str(e),
                "medical_safety_enabled": False,
                "hallucination_detection_active": False,
                "prescription_safety_enabled": False,
            }

