"""Health endpoint for service monitoring."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.response import StandardResponse

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check", response_model=StandardResponse)
def health_check() -> StandardResponse:
    """Return a simple service health payload."""

    response = StandardResponse(status="ok", message="Service healthy", data={"status": "healthy"})
    response.model_dump()
    return response
