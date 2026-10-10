"""Version endpoint for release tracking."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.settings import get_settings
from backend.app.schemas.response import StandardResponse

router = APIRouter(tags=["version"])


@router.get("/version", summary="Application version", response_model=StandardResponse)
def version(cfg=Depends(get_settings)) -> StandardResponse:
    """Return application version information."""

    payload = {"name": cfg.app_name, "version": cfg.app_version}
    return StandardResponse(status="ok", message="Application version", data=payload)
