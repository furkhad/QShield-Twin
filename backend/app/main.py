"""ASGI entrypoint for the FastAPI application.

This module exposes `app` so servers like uvicorn can import it as
`backend.app.main:app` for running.
"""

from __future__ import annotations

from backend.app import create_app

app = create_app()
