"""Research-related endpoints and metadata."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.response import StandardResponse

router = APIRouter(tags=["research"])


@router.get("/research/info", summary="Research metadata", response_model=StandardResponse)
def research_info() -> StandardResponse:
    payload = {
        "project": "QShield Twin",
        "description": "Digital twin platform for quantum-resilient Sybil defense research",
    }
    return StandardResponse(status="ok", message="Research metadata", data=payload)
