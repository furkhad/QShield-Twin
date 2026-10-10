"""Compatibility wrapper for the backend application object."""

from __future__ import annotations

from backend.app import create_app
from backend.main import app

__all__ = ["app", "create_app"]
