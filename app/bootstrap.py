"""Bootstrap helpers for compatibility during staged refactor."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def ensure_legacy_paths() -> None:
    """Keep legacy import paths working until modules are migrated."""
    legacy_paths = [
        PROJECT_ROOT,
        PROJECT_ROOT / "core",
        PROJECT_ROOT / "services",
        PROJECT_ROOT / "database",
    ]
    for path in legacy_paths:
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

