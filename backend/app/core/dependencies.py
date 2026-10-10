"""Dependency providers used by FastAPI endpoints and services."""

from __future__ import annotations

from typing import Generator

from fastapi import Depends, Request

from backend.database import get_db
from backend.settings import Settings, get_settings


def get_settings_dep(request: Request) -> Settings:
    """Return the settings bound to the running application.

    The application stores its resolved :class:`Settings` on ``app.state`` so that
    tests (and multi-app processes) can supply a custom configuration without
    mutating the process-wide cache. Falls back to the cached global settings.
    """

    return getattr(request.app.state, "settings", None) or get_settings()


def get_db_session() -> Generator:
    """Yield a SQLAlchemy session for request-scoped operations."""

    yield from get_db()


# Convenience FastAPI dependency wrappers
def SettingsDep() -> Settings:  # pragma: no cover - trivial wrapper
    return Depends(get_settings_dep)


def DBSessionDep():  # pragma: no cover - used as dependency marker
    return Depends(get_db_session)
