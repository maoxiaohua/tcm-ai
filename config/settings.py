"""
TCM AI系统 - 统一配置管理
"""
import os
from pathlib import Path
from urllib.parse import unquote, urlparse
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_env_files() -> None:
    """优先加载 config/.env，并兼容历史根目录 .env。"""
    env_candidates = (
        PROJECT_ROOT / "config" / ".env",
        PROJECT_ROOT / ".env",
    )
    for env_file in env_candidates:
        if env_file.exists():
            load_dotenv(env_file, override=False)


def _first_env(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            return value
    return None


def _get_env_str(name: str, default: str, *aliases: str) -> str:
    value = _first_env(name, *aliases)
    return value if value is not None else default


def _get_env_int(name: str, default: int, *aliases: str) -> int:
    value = _first_env(name, *aliases)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_env_csv(name: str, default: str, *aliases: str) -> list[str]:
    raw_value = _get_env_str(name, default, *aliases)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _parse_database_url(database_url: str) -> dict[str, str | int]:
    """
    兼容历史 DATABASE_URL。
    若 DB_HOST/DB_PORT/... 未设置，则可从 URL 自动拆分。
    """
    parsed = urlparse(database_url)
    if not parsed.scheme:
        return {}

    db_name = parsed.path.lstrip("/") or "tcm_db"
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": db_name,
        "username": unquote(parsed.username) if parsed.username else "tcm_user",
        "password": unquote(parsed.password) if parsed.password else "",
    }


_load_env_files()
_database_url_defaults = _parse_database_url(_get_env_str("DATABASE_URL", "", "DB_URL"))
_knowledge_db_path = _get_env_str(
    "KNOWLEDGE_DB_PATH",
    str(PROJECT_ROOT / "knowledge_db"),
    "KNOWLEDGE_BASE_PATH",
)
_main_model = _get_env_str("MAIN_MODEL", "qwen-turbo", "CHAT_MODEL")
_model_timeout = _get_env_int("MODEL_TIMEOUT", 40, "TIMEOUT")
_synthesis_timeout = _get_env_int("SYNTHESIS_TIMEOUT", 45)
_multimodal_timeout = _get_env_int("MULTIMODAL_TIMEOUT", 80)

# 基础路径配置
PATHS = {
    "project_root": PROJECT_ROOT,
    "data_dir": PROJECT_ROOT / "data",
    "static_dir": PROJECT_ROOT / "static", 
    "knowledge_db": Path(_knowledge_db_path),
    "docs_dir": PROJECT_ROOT / "all_tcm_docs",
    "logs_dir": PROJECT_ROOT / "logs",
    "backups_dir": PROJECT_ROOT / "backups",
    "cache_db": PROJECT_ROOT / "data" / "cache.sqlite",
    "user_db": PROJECT_ROOT / "data" / "user_history.sqlite",
    "tcm_knowledge_graph_db": PROJECT_ROOT / "data" / "tcm_knowledge_graph.sqlite",
    "herb_database": PROJECT_ROOT / "data" / "unified_herb_database.json"
}

# API配置
API_CONFIG = {
    "host": _get_env_str("HOST", "0.0.0.0", "SERVER_HOST"),
    "port": _get_env_int("PORT", 8000, "SERVER_PORT"),
    "workers": _get_env_int("WORKERS", 1, "UVICORN_WORKERS"),
    "log_level": _get_env_str("LOG_LEVEL", "INFO"),
}

# 数据库配置
DATABASE_CONFIG = {
    "host": _get_env_str("DB_HOST", str(_database_url_defaults.get("host", "localhost")), "DATABASE_HOST"),
    "port": _get_env_int("DB_PORT", int(_database_url_defaults.get("port", 5432)), "DATABASE_PORT"),
    "database": _get_env_str("DB_NAME", str(_database_url_defaults.get("database", "tcm_db")), "DATABASE_NAME"),
    "username": _get_env_str("DB_USER", str(_database_url_defaults.get("username", "tcm_user")), "DATABASE_USER"),
    "password": _get_env_str("DB_PASSWORD", str(_database_url_defaults.get("password", "")), "DATABASE_PASSWORD"),
}

# AI模型配置
AI_CONFIG = {
    "dashscope_api_key": _get_env_str("DASHSCOPE_API_KEY", "", "QWEN_API_KEY"),
    "main_model": _main_model,
    "model_timeout": _model_timeout,
    "timeout": _model_timeout,  # 兼容旧代码读取 AI_CONFIG["timeout"]
    "synthesis_timeout": _synthesis_timeout,
    # 多模态模型配置
    "multimodal_model": _get_env_str("MULTIMODAL_MODEL", "qwen-vl-max"),
    "multimodal_timeout": _multimodal_timeout,
    # 决策树生成专用模型
    "decision_tree_model": _get_env_str("DECISION_TREE_MODEL", "qwen-max"),
    # OCR服务配置（兼容旧变量名）
    "baidu_ocr_api_key": _get_env_str("BAIDU_OCR_API_KEY", "", "BAIDU_API_KEY"),
    "baidu_ocr_secret_key": _get_env_str("BAIDU_OCR_SECRET_KEY", "", "BAIDU_SECRET_KEY"),
}

# 域名和CORS配置
SECURITY_CONFIG = {
    "allowed_origins": _get_env_csv(
        "ALLOWED_ORIGINS",
        "https://mxh0510.cn,https://www.mxh0510.cn",
        "CORS_ALLOWED_ORIGINS",
    ),
    "domain": _get_env_str("DOMAIN", "mxh0510.cn", "APP_DOMAIN"),
    "secret_key": _get_env_str("SECRET_KEY", ""),
}

# 邮件配置
EMAIL_CONFIG = {
    "smtp_host": _get_env_str("SMTP_HOST", "smtp.163.com"),
    "smtp_port": _get_env_int("SMTP_PORT", 587),
    "smtp_username": _get_env_str("SMTP_USERNAME", ""),
    "smtp_password": _get_env_str("SMTP_PASSWORD", ""),
    "from_name": _get_env_str("SMTP_FROM_NAME", "TCM AI 中医智能诊疗"),
    "use_tls": _get_env_str("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
    "use_ssl": _get_env_str("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes"),
}

# 确保必要目录存在
for path in PATHS.values():
    if isinstance(path, Path) and not path.suffix:  # 是目录而不是文件
        path.mkdir(parents=True, exist_ok=True)
