"""Database adapters and session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import the model modules for their side effect of registering every table on
# ``Base.metadata``. Without this, ``init_db`` would create no tables at all:
# ``backend.models`` is otherwise only imported by ``backend.repositories``,
# which no request path currently uses (the app keeps device state in memory).
# This is a no-op for SQLite development and a hard requirement for PostgreSQL,
# where the schema must actually exist.
import backend.models  # noqa: F401  (registers tables on Base.metadata)
from backend.base import Base
from backend.settings import get_settings

settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create database tables for the current metadata set."""

    Base.metadata.create_all(bind=engine)


__all__ = ["SessionLocal", "get_db", "init_db", "engine"]
