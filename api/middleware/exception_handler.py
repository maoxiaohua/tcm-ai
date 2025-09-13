#!/usr/bin/env python3
"""
全局异常处理中间件
统一处理所有API异常，确保响应格式一致
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime
from typing import Union
import traceback

logger = logging.getLogger(__name__)

def setup_exception_handlers(app: FastAPI):
    """设置全局异常处理器"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP异常处理器 - 统一响应格式"""
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        
        # 映射状态码到错误代码
        error_codes = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED", 
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_ERROR",
            503: "SERVICE_UNAVAILABLE"
        }
        
        error_code = error_codes.get(exc.status_code, "UNKNOWN_ERROR")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": str(exc.detail),
                    "details": f"HTTP {exc.status_code}"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    
    @app.exception_handler(StarletteHTTPException) 
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Starlette HTTP异常处理器"""
        return await http_exception_handler(request, HTTPException(status_code=exc.status_code, detail=exc.detail))
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """值错误处理器"""
        logger.error(f"Value Error: {exc}")
        
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_VALUE",
                    "message": "提供的数据格式不正确",
                    "details": str(exc)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理器 - 处理所有未捕获的异常"""
        logger.error(f"Unhandled Exception: {type(exc).__name__}: {exc}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 生产环境不暴露详细错误信息
        error_details = str(exc) if logger.level == logging.DEBUG else "内部服务器错误"
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误，请稍后重试",
                    "details": error_details
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

class APIExceptionHandler:
    """API异常处理辅助类"""
    
    @staticmethod
    def wrap_async_endpoint(endpoint_func):
        """装饰器：包装异步端点，统一异常处理"""
        async def wrapper(*args, **kwargs):
            try:
                result = await endpoint_func(*args, **kwargs)
                
                # 如果返回的不是JSONResponse，包装为标准格式
                if not isinstance(result, JSONResponse):
                    if isinstance(result, dict) and "success" not in result:
                        return JSONResponse(
                            status_code=200,
                            content={
                                "success": True,
                                "data": result,
                                "timestamp": datetime.utcnow().isoformat() + "Z"
                            }
                        )
                
                return result
                
            except HTTPException:
                # HTTPException将被全局处理器捕获
                raise
            except Exception as e:
                logger.error(f"Endpoint error in {endpoint_func.__name__}: {e}")
                # 其他异常也将被全局处理器捕获
                raise
        
        return wrapper
    
    @staticmethod
    def wrap_sync_endpoint(endpoint_func):
        """装饰器：包装同步端点，统一异常处理"""
        def wrapper(*args, **kwargs):
            try:
                result = endpoint_func(*args, **kwargs)
                
                # 如果返回的不是JSONResponse，包装为标准格式
                if not isinstance(result, JSONResponse):
                    if isinstance(result, dict) and "success" not in result:
                        return JSONResponse(
                            status_code=200,
                            content={
                                "success": True,
                                "data": result,
                                "timestamp": datetime.utcnow().isoformat() + "Z"
                            }
                        )
                
                return result
                
            except HTTPException:
                # HTTPException将被全局处理器捕获
                raise
            except Exception as e:
                logger.error(f"Endpoint error in {endpoint_func.__name__}: {e}")
                # 其他异常也将被全局处理器捕获
                raise
        
        return wrapper

# 便捷的异常创建函数
def create_http_exception(status_code: int, message: str, details: str = ""):
    """创建HTTP异常的便捷函数"""
    detail = message
    if details:
        detail = f"{message}: {details}"
    return HTTPException(status_code=status_code, detail=detail)

# 常用异常快捷方式
def bad_request(message: str, details: str = ""):
    """400 Bad Request"""
    return create_http_exception(400, message, details)

def unauthorized(message: str = "未授权访问"):
    """401 Unauthorized"""  
    return create_http_exception(401, message)

def forbidden(message: str = "权限不足"):
    """403 Forbidden"""
    return create_http_exception(403, message)

def not_found(resource: str = "资源"):
    """404 Not Found"""
    return create_http_exception(404, f"{resource}不存在")

def internal_error(message: str, details: str = ""):
    """500 Internal Server Error"""
    return create_http_exception(500, message, details)