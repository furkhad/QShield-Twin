"""Network inspection endpoints exposing topology and stats."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.schemas.requests import ReplayRequest, TopologyRequest
from backend.app.schemas.response import StandardResponse
from backend.digital_twin.manager import get_manager

router = APIRouter(tags=["network"])

_manager = get_manager()


@router.get("/network", response_model=StandardResponse)
def get_network():
    # Provide a minimal network snapshot including degrees
    devices = _manager.get_devices()
    stats = _manager.sim.network.degree_statistics()
    return StandardResponse(
        status="ok",
        message="Network snapshot",
        data={"devices": devices, "degree_stats": stats},
    )


@router.get("/network/topology", response_model=StandardResponse)
def get_topology():
    topo = getattr(_manager.config, "topology", None)
    return StandardResponse(status="ok", message="Current topology", data={"topology": topo})


@router.post("/network/topology", response_model=StandardResponse)
def set_topology(payload: TopologyRequest):
    try:
        _manager.apply_topology(payload.topology, **payload.params)
    except Exception as exc:  # noqa: BLE001 - report as API error envelope
        return StandardResponse(
            status="error",
            message="Failed to apply topology",
            errors={"detail": str(exc)},
        )
    devices = _manager.get_devices()
    stats = _manager.sim.network.degree_statistics()
    return StandardResponse(
        status="ok",
        message="Topology applied",
        data={"topology": payload.topology, "devices": devices, "degree_stats": stats},
    )


@router.get("/network/history", response_model=StandardResponse)
def get_history(limit: int = Query(200, ge=1, le=1000)):
    hist = _manager.sim.get_history(limit=limit)
    meta = []
    for i, item in enumerate(hist):
        meta.append(
            {
                "index": i,
                "kind": item.get("kind"),
                "time": item.get("snapshot", {}).get("time") or item.get("event", {}).get("time"),
            }
        )
    return StandardResponse(status="ok", message="History metadata", data={"items": meta})


@router.post("/network/replay", response_model=StandardResponse)
def post_replay(payload: ReplayRequest):
    try:
        if payload.action == "start":
            _manager.sim.replay_history(
                speed=payload.speed, start=payload.start, end=payload.end
            )
            return StandardResponse(status="ok", message="Replay started")
        _manager.sim.stop_replay()
        return StandardResponse(status="ok", message="Replay stopped")
    except Exception as exc:  # noqa: BLE001
        return StandardResponse(
            status="error",
            message="Failed to control replay",
            errors={"detail": str(exc)},
        )


@router.get("/network/history/{index}", response_model=StandardResponse)
def get_history_item(index: int):
    hist = _manager.sim.get_history(limit=1000)
    if index < 0 or index >= len(hist):
        return StandardResponse(
            status="error", message="Index out of range", errors={"detail": "index out of range"}
        )
    item = hist[index]
    return StandardResponse(status="ok", message="History item", data={"index": index, "item": item})
