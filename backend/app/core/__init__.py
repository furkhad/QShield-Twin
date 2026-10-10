"""Core utilities and dependency primitives for the application."""

from backend.app.core.dependencies import (  # re-export for convenience
    get_db_session,
    get_settings_dep,
)

__all__ = ["get_db_session", "get_settings_dep"]
