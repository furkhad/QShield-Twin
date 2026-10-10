"""Top-level API router."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.router import api_router
from backend.settings import get_settings

settings = get_settings()
router = APIRouter(prefix=settings.api_v1_prefix)
router.include_router(api_router)
