"""Shared helpers for SQLAlchemy models (UUID keys and UTC timestamps)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def gen_uuid() -> str:
    """Return a random UUID4 string for primary keys."""

    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp safe for use as a column default."""

    return datetime.now(timezone.utc)
