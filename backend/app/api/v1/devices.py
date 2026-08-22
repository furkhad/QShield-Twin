"""Device management API for the Digital Twin."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Body

from backend.app.schemas.response import StandardResponse
from backend.digital_twin.manager import DigitalTwinManager
from backend.simulation.environment import SimConfig

router = APIRouter(tags=["devices"])

# For simplicity we use a single manager instance in memory.
_manager = DigitalTwinManager(config=SimConfig())


@router.get("/devices", response_model=StandardResponse)
def list_devices():
    devices = _manager.get_devices()
    return StandardResponse(status="ok", message="List devices", data=devices)


@router.post("/devices", response_model=StandardResponse)
def create_device(payload: dict):
    name = payload.get("name") or "device"
    x = float(payload.get("x", 0.0))
    y = float(payload.get("y", 0.0))
    dev = _manager.spawn_device(name=name, x=x, y=y)
    return StandardResponse(status="ok", message="Device created", data=dev.to_dict())


@router.delete("/devices/{device_id}", response_model=StandardResponse)
def delete_device(device_id: str):
    _manager.remove_device(device_id)
    return StandardResponse(status="ok", message="Device removed", data={"device_id": device_id})


@router.post("/devices/bulk", response_model=StandardResponse)
def bulk_create(payload: dict = Body(...)):
    count = int(payload.get("count", 10))
    prefix = payload.get("prefix", "dev")
    # use efficient bulk spawn
    created = _manager.spawn_bulk(count=count, prefix=prefix)
    return StandardResponse(status="ok", message=f"Created {len(created)} devices", data={"devices": [d.to_dict() for d in created]})
