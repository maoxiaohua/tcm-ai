"""Stage-2 settings facade.

This module is a compatibility layer that re-exports existing settings
from the legacy config package, so migration can be done incrementally.
"""

from pathlib import Path
from typing import Any, Dict

from config.settings import (  # noqa: F401
    PROJECT_ROOT,
    PATHS,
    API_CONFIG,
    DATABASE_CONFIG,
    AI_CONFIG,
    SECURITY_CONFIG,
)


def get_path(name: str) -> Path:
    """Return a typed Path from the shared PATHS mapping."""
    value = PATHS[name]
    return value if isinstance(value, Path) else Path(value)


def get_config_snapshot() -> Dict[str, Any]:
    """Useful for debug endpoints and diagnostics."""
    return {
        "project_root": str(PROJECT_ROOT),
        "paths": {k: str(v) for k, v in PATHS.items()},
        "api": dict(API_CONFIG),
        "database": dict(DATABASE_CONFIG),
        "ai": dict(AI_CONFIG),
        "security": dict(SECURITY_CONFIG),
    }

