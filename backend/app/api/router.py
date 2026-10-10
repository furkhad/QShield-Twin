"""Aggregate router for versioned API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.v1.devices import router as devices_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.network import router as network_router
from backend.app.api.v1.research import router as research_router
from backend.app.api.v1.security import router as security_router
from backend.app.api.v1.simulation_control import router as simulation_router
from backend.app.api.v1.statistics import router as statistics_router
from backend.app.api.v1.status import router as status_router
from backend.app.api.v1.system import router as system_router
from backend.app.api.v1.version import router as version_router
from backend.app.api.v1.ws import router as ws_router
from backend.app.core.security import require_api_token

# Read-only/status routers stay open so liveness/version probes and the info
# panels work without credentials. Everything that mutates server state or
# exposes operational detail is gated behind the shared API token.
_sensitive = [Depends(require_api_token)]

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(status_router)
api_router.include_router(version_router)
api_router.include_router(system_router)
api_router.include_router(research_router)
api_router.include_router(devices_router, dependencies=_sensitive)
api_router.include_router(simulation_router, dependencies=_sensitive)
api_router.include_router(network_router, dependencies=_sensitive)
api_router.include_router(statistics_router, dependencies=_sensitive)
api_router.include_router(ws_router)
api_router.include_router(security_router, dependencies=_sensitive)


@api_router.get("/", tags=["root"], summary="API root")
def api_root():
    return {"status": "ok", "message": "QShield Twin API", "available": ["/health", "/status", "/version"]}
