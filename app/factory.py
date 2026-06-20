"""App factory entrypoint (stage-1, zero-behavior-change wrapper)."""

from functools import lru_cache
from fastapi import FastAPI

from app.bootstrap import ensure_legacy_paths


@lru_cache(maxsize=1)
def create_app() -> FastAPI:
    """Return FastAPI app while reusing legacy app object."""
    ensure_legacy_paths()
    from api.main import app as legacy_app

    return legacy_app

