"""Dependency providers used by FastAPI endpoints and services."""

from __future__ import annotations

from typing import Generator

from fastapi import Depends

from backend.database import get_db, SessionLocal
from backend.settings import get_settings, Settings


def get_settings_dep() -> Settings:
    return get_settings()


def get_db_session() -> Generator:
    """Yield a SQLAlchemy session for request-scoped operations."""

    yield from get_db()


# Convenience FastAPI dependency wrappers
def SettingsDep() -> Settings:  # pragma: no cover - trivial wrapper
    return Depends(get_settings_dep)


def DBSessionDep():  # pragma: no cover - used as dependency marker
    return Depends(get_db_session)
