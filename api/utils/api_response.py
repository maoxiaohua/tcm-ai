#!/usr/bin/env python3
"""
API响应格式统一辅助类
"""

from typing import Any, Optional
from datetime import datetime
from fastapi.responses import JSONResponse

class APIResponse:
    """统一API响应格式辅助类"""
    
    @staticmethod
    def success(data: Any = None, message: str = "", status_code: int = 200) -> JSONResponse:
        """成功响应"""
        response_data = {
            "success": True,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if message:
            response_data["message"] = message
            
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @staticmethod
    def error(code: str, message: str, details: str = "", status_code: int = 400) -> JSONResponse:
        """错误响应"""
        response_data = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if details:
            response_data["error"]["details"] = details
            
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @staticmethod
    def not_found(resource: str = "资源") -> JSONResponse:
        """404 响应"""
        return APIResponse.error(
            code="NOT_FOUND",
            message=f"{resource}不存在",
            status_code=404
        )
    
    @staticmethod
    def unauthorized(message: str = "未授权访问") -> JSONResponse:
        """401 响应"""
        return APIResponse.error(
            code="UNAUTHORIZED", 
            message=message,
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: str = "权限不足") -> JSONResponse:
        """403 响应"""
        return APIResponse.error(
            code="FORBIDDEN",
            message=message, 
            status_code=403
        )
