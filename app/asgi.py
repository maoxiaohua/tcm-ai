"""ASGI module for uvicorn/gunicorn startup."""

from app.factory import create_app


app = create_app()

