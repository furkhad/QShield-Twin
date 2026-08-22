"""Core utilities and dependency primitives for the application."""

from backend.app.core.dependencies import get_db_session, get_settings_dep  # re-export for convenience

__all__ = ["get_db_session", "get_settings_dep"]
