"""System information endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.schemas.response import StandardResponse
from backend.settings import get_settings

router = APIRouter(tags=["system"])


@router.get("/system/info", summary="System information", response_model=StandardResponse)
def system_info(cfg=Depends(get_settings)) -> StandardResponse:
    payload = {
        "app_name": cfg.app_name,
        "version": cfg.app_version,
        "environment": cfg.environment,
    }
    return StandardResponse(status="ok", message="System information", data=payload)
