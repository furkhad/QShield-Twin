"""Network inspection endpoints exposing topology and stats."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.response import StandardResponse
from backend.digital_twin.manager import DigitalTwinManager
from backend.simulation.environment import SimConfig
from fastapi import Body

from typing import Any

router = APIRouter(tags=["network"])

_manager = DigitalTwinManager(config=SimConfig())


@router.get("/network", response_model=StandardResponse)
def get_network():
    # Provide a minimal network snapshot including degrees
    devices = _manager.get_devices()
    # compute degree statistics via manager.sim.network
    stats = _manager.sim.network.degree_statistics()
    return StandardResponse(status="ok", message="Network snapshot", data={"devices": devices, "degree_stats": stats})


@router.get("/network/topology", response_model=StandardResponse)
def get_topology():
    topo = getattr(_manager.config, "topology", None)
    return StandardResponse(status="ok", message="Current topology", data={"topology": topo})


@router.post("/network/topology", response_model=StandardResponse)
def set_topology(payload: dict = Body(...)):
    topology = payload.get("topology")
    params = payload.get("params", {})
    if not topology:
        return StandardResponse(status="error", message="Missing topology field", data={})
    try:
        _manager.apply_topology(topology, **params)
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to apply topology", errors={"detail": str(exc)})
    # return updated snapshot
    devices = _manager.get_devices()
    stats = _manager.sim.network.degree_statistics()
    return StandardResponse(status="ok", message="Topology applied", data={"topology": topology, "devices": devices, "degree_stats": stats})


@router.get("/network/history", response_model=StandardResponse)
def get_history(limit: int = 200):
    hist = _manager.sim.get_history(limit=limit)
    # return lightweight metadata list
    meta = []
    for i, item in enumerate(hist):
        meta.append({"index": i, "kind": item.get("kind"), "time": item.get("snapshot", {}).get("time") or item.get("event", {}).get("time")})
    return StandardResponse(status="ok", message="History metadata", data={"items": meta})


@router.post("/network/replay", response_model=StandardResponse)
def post_replay(payload: dict = Body(...)):
    speed = float(payload.get("speed", 1.0))
    start = payload.get("start")
    end = payload.get("end")
    action = payload.get("action", "start")
    try:
        if action == "start":
            _manager.sim.replay_history(speed=speed, start=start, end=end)
            return StandardResponse(status="ok", message="Replay started")
        elif action == "stop":
            _manager.sim.stop_replay()
            return StandardResponse(status="ok", message="Replay stopped")
        else:
            return StandardResponse(status="error", message="Unknown action")
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to control replay", errors={"detail": str(exc)})



@router.get("/network/history/{index}", response_model=StandardResponse)
def get_history_item(index: int):
    hist = _manager.sim.get_history(limit=1000)
    if index < 0 or index >= len(hist):
        return StandardResponse(status="error", message="Index out of range", errors={"detail": "index out of range"})
    item = hist[index]
    return StandardResponse(status="ok", message="History item", data={"index": index, "item": item})
