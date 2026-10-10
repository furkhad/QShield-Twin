"""Standard API response models used across endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class StandardResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "ok",
            "message": "Request successful",
            "data": {},
        }
    })
    status: str
    message: str
    timestamp: datetime | None = None
    version: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[Any] = None
    request_id: Optional[str] = None

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        if d.get("timestamp") is None:
            d["timestamp"] = datetime.utcnow().isoformat()
        return d
