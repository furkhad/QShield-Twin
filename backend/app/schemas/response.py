"""Standard API response models used across endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp factory (avoids deprecated utcnow())."""

    return datetime.now(timezone.utc)


class StandardResponse(BaseModel):
    """Uniform envelope returned by the REST API.

    ``status`` is ``"ok"`` or ``"error"``; ``data`` carries the payload and
    ``errors`` carries structured error detail. The envelope is intentionally
    stable so existing clients keep working.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "message": "Request successful",
                "data": {},
            }
        }
    )

    status: str
    message: str
    timestamp: datetime = Field(default_factory=_utcnow)
    version: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[Any] = None
    request_id: Optional[str] = None
