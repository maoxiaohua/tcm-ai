"""Site/static route setup helpers (stage-4)."""

import os
from typing import Any, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import Response, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


def register_common_browser_file_routes(app: FastAPI) -> None:
    """Register lightweight handlers for browser auto-requests."""

    @app.get("/favicon.ico")
    @app.get("/robots.txt")
    @app.get("/sitemap.xml")
    @app.get("/ads.txt")
    @app.get("/apple-touch-icon.png")
    @app.get("/apple-touch-icon-precomposed.png")
    async def common_browser_files():
        return Response(status_code=204)


def setup_static_and_site_routes(
    app: FastAPI,
    logger: Any,
    paths: Mapping[str, Any],
) -> None:
    """Mount static files and register site utility routes."""
    try:
        static_dir = str(paths["static_dir"])
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/mobile-modal-test")
        async def mobile_modal_test():
            with open(str(paths["static_dir"] / "mobile_modal_test.html"), "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)

        @app.get("/MP_verify_{filename}.txt")
        async def wechat_verification_dynamic(filename: str):
            try:
                file_path = os.path.join(static_dir, f"MP_verify_{filename}.txt")
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        content = f.read().strip()
                    logger.info(f"成功读取微信验证文件: MP_verify_{filename}.txt")
                    return PlainTextResponse(content)
                logger.warning(f"微信验证文件不存在: MP_verify_{filename}.txt")
                return PlainTextResponse("File not found", status_code=404)
            except Exception as e:
                logger.error(f"读取微信验证文件失败: {e}")
                return PlainTextResponse("Error reading verification file", status_code=500)

        @app.get("/9bc1b8fbf3176b5ca5254dc9d18d84fb.txt")
        async def domain_verification_txt():
            try:
                file_path = os.path.join(static_dir, "9bc1b8fbf3176b5ca5254dc9d18d84fb.txt")
                with open(file_path, "r") as f:
                    content = f.read()
                return PlainTextResponse(content)
            except Exception as e:
                logger.error(f"读取域名验证文件失败: {e}")
                return PlainTextResponse("File not found", status_code=404)

        @app.get("/MP_verify_wechat_verification.txt")
        async def wechat_verification():
            try:
                with open(os.path.join(static_dir, "MP_verify_wechat_verification.txt"), "r") as f:
                    content = f.read()
                return PlainTextResponse(content)
            except Exception:
                return PlainTextResponse("wechat_verification_tcm_ai_medical_system")

        @app.get("/robots.txt")
        async def robots_txt():
            try:
                with open(os.path.join(static_dir, "robots.txt"), "r") as f:
                    content = f.read()
                return PlainTextResponse(content)
            except Exception:
                return PlainTextResponse("User-agent: *\nAllow: /")

        @app.get("/sitemap.xml")
        async def sitemap_xml():
            sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://mxh0510.cn/</loc>
    <lastmod>2025-08-06</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://mxh0510.cn/register</loc>
    <lastmod>2025-08-06</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>"""
            return Response(content=sitemap_content, media_type="application/xml")

        @app.post("/api/log_wechat_visit")
        async def log_wechat_visit(request: Request):
            try:
                data = await request.json()
                logger.info(f"微信公众号访问统计: {data}")

                _ = {
                    "timestamp": data.get("timestamp"),
                    "source": data.get("source", "unknown"),
                    "from_wechat": data.get("from_wechat", False),
                    "is_wechat_browser": data.get("is_wechat_browser", False),
                    "page": data.get("page", "unknown"),
                    "ip": request.client.host if hasattr(request, "client") else "unknown",
                }

                return {"status": "success", "message": "微信访问记录成功"}
            except Exception as e:
                logger.error(f"记录微信访问失败: {e}")
                return {"status": "error", "message": str(e)}

    except Exception as e:
        logger.warning(f"Static files not mounted: {e}")

