#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数模块
提取main.py中的重复代码和通用工具函数
"""

import re
import json
import uuid
import logging
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)

# ==========================================
# 时间和ID生成工具
# ==========================================

def generate_conversation_id() -> str:
    """生成对话ID"""
    return str(uuid.uuid4())

def generate_short_id(length: int = 8) -> str:
    """生成短ID"""
    import secrets
    import string
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_current_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_current_timestamp_iso() -> str:
    """获取ISO格式时间戳"""
    return datetime.now().isoformat()

# ==========================================
# 异常处理工具 - 统一处理548次重复的try-catch
# ==========================================

def safe_execute(func, *args, default_return=None, error_message="操作失败", **kwargs):
    """
    安全执行函数，统一异常处理
    消除main.py中548次重复的try-catch模式
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"{error_message}: {e}")
        return default_return

def safe_json_loads(json_str: str, default=None) -> Any:
    """安全的JSON解析"""
    return safe_execute(
        json.loads, 
        json_str, 
        default_return=default,
        error_message="JSON解析失败"
    )

def safe_json_dumps(obj: Any, default="{}") -> str:
    """安全的JSON序列化"""
    return safe_execute(
        json.dumps,
        obj,
        ensure_ascii=False,
        indent=2,
        default_return=default,
        error_message="JSON序列化失败"
    )

# ==========================================
# 文件操作工具
# ==========================================

def create_temp_file(content: bytes, suffix: str = ".tmp") -> Optional[str]:
    """创建临时文件"""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name
    except Exception as e:
        logger.error(f"创建临时文件失败: {e}")
        return None

def safe_remove_file(file_path: str) -> bool:
    """安全删除文件"""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            return True
    except Exception as e:
        logger.error(f"删除文件失败 {file_path}: {e}")
    return False

def ensure_directory_exists(directory: str) -> bool:
    """确保目录存在"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {directory}: {e}")
        return False

# ==========================================
# 文本处理工具
# ==========================================

def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    # 移除首尾空白
    text = text.strip()
    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text

def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def extract_numbers(text: str) -> List[float]:
    """从文本中提取数字"""
    pattern = r'\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]

def contains_chinese(text: str) -> bool:
    """检查文本是否包含中文"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

# ==========================================
# 响应格式化工具
# ==========================================

def create_success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功响应"""
    response = {
        "success": True,
        "message": message,
        "timestamp": get_current_timestamp_iso()
    }
    if data is not None:
        response["data"] = data
    return response

def create_error_response(error: str, code: int = 400, details: Any = None) -> Dict[str, Any]:
    """创建错误响应"""
    response = {
        "success": False,
        "error": error,
        "code": code,
        "timestamp": get_current_timestamp_iso()
    }
    if details is not None:
        response["details"] = details
    return response

def standardize_api_response(success: bool, data: Any = None, error: str = None, **kwargs) -> Dict[str, Any]:
    """标准化API响应格式"""
    response = {
        "success": success,
        "timestamp": get_current_timestamp_iso()
    }
    
    if success:
        response["data"] = data
        response["message"] = kwargs.get("message", "操作成功")
    else:
        response["error"] = error or "操作失败"
        response["code"] = kwargs.get("code", 400)
    
    return response

# ==========================================
# 验证工具
# ==========================================

def is_valid_uuid(uuid_string: str) -> bool:
    """验证UUID格式"""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

def is_valid_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone: str) -> bool:
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    # 移除危险字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 限制长度
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:190] + ext
    return filename

# ==========================================
# 配置和环境工具
# ==========================================

def get_env_var(key: str, default: Any = None, var_type: type = str) -> Any:
    """获取环境变量"""
    value = os.getenv(key, default)
    if value is None:
        return default
    
    try:
        if var_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif var_type == int:
            return int(value)
        elif var_type == float:
            return float(value)
        else:
            return var_type(value)
    except (ValueError, TypeError):
        return default

def load_json_config(file_path: str) -> Dict[str, Any]:
    """加载JSON配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败 {file_path}: {e}")
        return {}

# ==========================================
# 调试和日志工具
# ==========================================

def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None, level: int = logging.DEBUG):
    """记录函数调用"""
    args_str = str(args) if args else ""
    kwargs_str = str(kwargs) if kwargs else ""
    logger.log(level, f"调用函数 {func_name}({args_str}, {kwargs_str})")

def log_execution_time(func):
    """装饰器：记录函数执行时间"""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} 执行耗时: {execution_time:.2f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败 (耗时{execution_time:.2f}秒): {e}")
            raise
    
    return wrapper

# ==========================================
# 数据处理工具
# ==========================================

def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """合并多个字典"""
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result

def filter_dict(data: Dict[str, Any], allowed_keys: List[str]) -> Dict[str, Any]:
    """过滤字典，只保留指定的键"""
    return {k: v for k, v in data.items() if k in allowed_keys}

def flatten_dict(data: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    """扁平化嵌套字典"""
    result = {}
    
    def _flatten(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}{separator}{k}" if prefix else k
                _flatten(v, new_key)
        else:
            result[prefix] = obj
    
    _flatten(data)
    return result

# ==========================================
# 缓存工具
# ==========================================

_memory_cache = {}

def simple_cache_get(key: str) -> Any:
    """简单内存缓存获取"""
    return _memory_cache.get(key)

def simple_cache_set(key: str, value: Any, ttl: int = 300):
    """简单内存缓存设置"""
    import time
    _memory_cache[key] = {
        'value': value,
        'expire_time': time.time() + ttl
    }

def simple_cache_clear():
    """清空内存缓存"""
    global _memory_cache
    _memory_cache = {}

def cache_cleanup():
    """清理过期缓存"""
    import time
    current_time = time.time()
    expired_keys = [
        key for key, data in _memory_cache.items() 
        if isinstance(data, dict) and data.get('expire_time', 0) < current_time
    ]
    for key in expired_keys:
        del _memory_cache[key]

# ==========================================
# 字符串工具
# ==========================================

def mask_sensitive_info(text: str, preserve_chars: int = 4) -> str:
    """遮罩敏感信息"""
    if len(text) <= preserve_chars * 2:
        return "*" * len(text)
    
    start = text[:preserve_chars]
    end = text[-preserve_chars:] if len(text) > preserve_chars else ""
    middle = "*" * (len(text) - len(start) - len(end))
    return start + middle + end

def generate_random_string(length: int = 8, include_special: bool = False) -> str:
    """生成随机字符串"""
    import secrets
    import string
    
    chars = string.ascii_letters + string.digits
    if include_special:
        chars += "!@#$%^&*"
    
    return ''.join(secrets.choice(chars) for _ in range(length))