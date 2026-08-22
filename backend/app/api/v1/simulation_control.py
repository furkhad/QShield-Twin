"""API endpoints to control the simulator lifecycle."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.response import StandardResponse
from backend.digital_twin.manager import DigitalTwinManager, get_manager
from backend.simulation.environment import SimConfig

router = APIRouter(tags=["simulation"])

_manager = get_manager(config=SimConfig())


@router.post("/simulation/start", response_model=StandardResponse)
def start_simulation(payload: dict | None = None):
    runtime = None
    if payload:
        runtime = float(payload.get("runtime", 0)) or None
    _manager.start_simulation(runtime=runtime)
    return StandardResponse(status="ok", message="Simulation started")


@router.post("/simulation/reset", response_model=StandardResponse)
def reset_simulation():
    _manager.reset_simulation()
    return StandardResponse(status="ok", message="Simulation reset")


@router.get("/simulation/status", response_model=StandardResponse)
def simulation_status():
    st = _manager.status()
    return StandardResponse(status="ok", message="Simulation status", data=st)


@router.post("/simulation/pause", response_model=StandardResponse)
def pause_simulation():
    try:
        _manager.sim.pause()
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to pause simulation", errors={"detail": str(exc)})
    return StandardResponse(status="ok", message="Simulation paused")


@router.post("/simulation/resume", response_model=StandardResponse)
def resume_simulation():
    try:
        _manager.sim.resume()
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to resume simulation", errors={"detail": str(exc)})
    return StandardResponse(status="ok", message="Simulation resumed")


@router.post("/simulation/step", response_model=StandardResponse)
def step_simulation(payload: dict | None = None):
    steps = 1
    if payload:
        steps = int(payload.get("steps", 1))
    try:
        _manager.sim.step(steps=steps)
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to step simulation", errors={"detail": str(exc)})
    return StandardResponse(status="ok", message=f"Advanced simulation by {steps} step(s)")


@router.get("/simulation/scenarios", response_model=StandardResponse)
def list_scenarios():
    return StandardResponse(
        status="ok",
        message="Available scenarios",
        data={
            "scenarios": [
                {"id": "normal", "name": "Normal Network"},
                {"id": "light_sybil_attack", "name": "Light Sybil Attack"},
                {"id": "medium_sybil_attack", "name": "Medium Sybil Attack"},
                {"id": "heavy_sybil_attack", "name": "Heavy Sybil Attack"},
            ]
        },
    )


@router.post("/simulation/scenario/{scenario_name}", response_model=StandardResponse)
def run_scenario(scenario_name: str, payload: dict | None = None):
    try:
        device_count = 100
        ghost_count = None
        if payload:
            device_count = int(payload.get("device_count", 100))
            ghost_count = payload.get("ghost_count")
            if ghost_count is not None:
                ghost_count = int(ghost_count)
        result = _manager.run_scenario(scenario_name=scenario_name, device_count=device_count, ghost_count=ghost_count)
        return StandardResponse(status="ok", message="Scenario completed", data=result)
    except Exception as exc:
        return StandardResponse(status="error", message="Scenario execution failed", errors={"detail": str(exc)})
