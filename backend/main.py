"""Application entrypoint for ASGI servers."""

from __future__ import annotations

from backend.app import create_app

app = create_app()

__all__ = ["app"]
