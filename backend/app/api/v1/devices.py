"""Device management API for the Digital Twin."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.requests import BulkDeviceRequest, DeviceCreateRequest
from backend.app.schemas.response import StandardResponse
from backend.digital_twin.manager import get_manager

router = APIRouter(tags=["devices"])

# Use the shared manager so device state is consistent with the security,
# network, statistics, and simulation endpoints.
_manager = get_manager()


@router.get("/devices", response_model=StandardResponse)
def list_devices(limit: int = Query(500, ge=1, le=1000)):
    devices = _manager.get_devices()
    total = len(devices)
    return StandardResponse(
        status="ok",
        message="List devices",
        data={"devices": devices[:limit], "count": min(total, limit), "total": total},
    )


@router.post("/devices", response_model=StandardResponse)
def create_device(payload: DeviceCreateRequest):
    dev = _manager.spawn_device(name=payload.name, x=payload.x, y=payload.y)
    return StandardResponse(status="ok", message="Device created", data=dev.to_dict())


@router.delete("/devices/{device_id}", response_model=StandardResponse)
def delete_device(device_id: str):
    if device_id not in _manager.sim.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    _manager.remove_device(device_id)
    return StandardResponse(status="ok", message="Device removed", data={"device_id": device_id})


@router.post("/devices/bulk", response_model=StandardResponse)
def bulk_create(payload: BulkDeviceRequest):
    created = _manager.spawn_bulk(count=payload.count, prefix=payload.prefix)
    return StandardResponse(
        status="ok",
        message=f"Created {len(created)} devices",
        data={"devices": [d.to_dict() for d in created], "count": len(created)},
    )
