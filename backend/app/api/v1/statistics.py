"""Statistics endpoints exposing simulation metrics."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.response import StandardResponse
from backend.digital_twin.manager import DigitalTwinManager
from backend.simulation.environment import SimConfig

router = APIRouter(tags=["statistics"])

_manager = DigitalTwinManager(config=SimConfig())


@router.get("/statistics", response_model=StandardResponse)
def get_statistics():
    devices = _manager.get_devices()
    total = len(devices)
    avg_latency = sum(d.get("latency_ms", 0) for d in devices) / (total or 1)
    packets_sent = sum(d.get("packets_sent", 0) for d in devices)
    packets_recv = sum(d.get("packets_received", 0) for d in devices)
    return StandardResponse(status="ok", message="Statistics", data={"total_devices": total, "avg_latency": avg_latency, "packets_sent": packets_sent, "packets_received": packets_recv})
