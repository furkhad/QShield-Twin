"""Operational status endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from backend.app.schemas.response import StandardResponse
from backend.settings import get_settings

router = APIRouter(tags=["status"])
settings = get_settings()


@router.get("/status", summary="Runtime status", response_model=StandardResponse)
def status(cfg=Depends(get_settings)) -> StandardResponse:
    """Expose the current runtime state of the platform."""

    payload = {
        "status": "operational",
        "environment": cfg.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return StandardResponse(status="ok", message="Runtime status", data=payload)
