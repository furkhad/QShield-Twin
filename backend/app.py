"""Compatibility wrapper for the backend application object."""

from __future__ import annotations

from backend.app import app, create_app

__all__ = ["app", "create_app"]
