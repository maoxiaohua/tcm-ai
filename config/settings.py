"""
TCM AI系统 - 统一配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path("/opt/tcm-ai")

# 加载环境变量
env_file = PROJECT_ROOT / "config" / ".env"
if env_file.exists():
    load_dotenv(env_file)

# 基础路径配置
PATHS = {
    "project_root": PROJECT_ROOT,
    "data_dir": PROJECT_ROOT / "data",
    "static_dir": PROJECT_ROOT / "static", 
    "knowledge_db": PROJECT_ROOT / "knowledge_db",
    "docs_dir": PROJECT_ROOT / "all_tcm_docs",
    "logs_dir": PROJECT_ROOT / "logs",
    "backups_dir": PROJECT_ROOT / "backups",
    "cache_db": PROJECT_ROOT / "data" / "cache.sqlite",
    "user_db": PROJECT_ROOT / "data" / "user_history.sqlite",
    "herb_database": PROJECT_ROOT / "data" / "unified_herb_database.json"
}

# API配置
API_CONFIG = {
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", 8000)),
    "workers": int(os.getenv("WORKERS", 4)),
    "log_level": os.getenv("LOG_LEVEL", "INFO")
}

# 数据库配置
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "tcm_db"),
    "username": os.getenv("DB_USER", "tcm_user"),
    "password": os.getenv("DB_PASSWORD", "")
}

# AI模型配置
AI_CONFIG = {
    "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY", ""),
    "model_timeout": int(os.getenv("MODEL_TIMEOUT", 40)),
    "synthesis_timeout": int(os.getenv("SYNTHESIS_TIMEOUT", 45)),
    # 多模态模型配置
    "multimodal_model": os.getenv("MULTIMODAL_MODEL", "qwen-vl-max"),
    "multimodal_timeout": int(os.getenv("MULTIMODAL_TIMEOUT", 80))
}

# 域名和CORS配置
SECURITY_CONFIG = {
    "allowed_origins": os.getenv("ALLOWED_ORIGINS", "https://mxh0510.cn,https://www.mxh0510.cn").split(","),
    "domain": os.getenv("DOMAIN", "mxh0510.cn")
}

# 确保必要目录存在
for path in PATHS.values():
    if isinstance(path, Path) and not path.suffix:  # 是目录而不是文件
        path.mkdir(parents=True, exist_ok=True)