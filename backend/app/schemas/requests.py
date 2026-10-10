"""Pydantic request models for state-changing API endpoints.

Using explicit models (instead of raw ``dict`` bodies) gives us automatic type
coercion, range/length validation, clear 422 errors, and protection against
unbounded resource use (e.g. spawning an enormous number of devices/ghosts).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Central upper bounds for user-controlled sizes. These mirror the configurable
# Settings.max_* limits but are kept static here so both the schema (422) and the
# handler can enforce them without a settings dependency at import time.
MAX_DEVICES_PER_REQUEST = 1000
MAX_GHOSTS_PER_ATTACK = 1000
MAX_STEPS_PER_REQUEST = 1000
MAX_TEXT_LEN = 128


class DeviceCreateRequest(BaseModel):
    name: str = Field(default="device", min_length=1, max_length=MAX_TEXT_LEN)
    x: float = 0.0
    y: float = 0.0


class BulkDeviceRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=MAX_DEVICES_PER_REQUEST)
    prefix: str = Field(default="dev", min_length=1, max_length=64)


class SimulationStartRequest(BaseModel):
    runtime: float | None = Field(default=None, gt=0, le=3600)


class SimulationStepRequest(BaseModel):
    steps: int = Field(default=1, ge=1, le=MAX_STEPS_PER_REQUEST)


class ScenarioRequest(BaseModel):
    device_count: int = Field(default=100, ge=1, le=MAX_DEVICES_PER_REQUEST)
    ghost_count: int | None = Field(default=None, ge=0, le=MAX_GHOSTS_PER_ATTACK)
    seed: int | None = Field(default=None, ge=0, le=2_000_000_000)


class TopologyRequest(BaseModel):
    topology: str = Field(..., min_length=1, max_length=32)
    params: dict = Field(default_factory=dict)


class ReplayRequest(BaseModel):
    action: str = Field(default="start", pattern="^(start|stop)$")
    speed: float = Field(default=1.0, gt=0, le=100)
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)


class AttackStartRequest(BaseModel):
    attacker: str = Field(default="attacker-1", min_length=1, max_length=MAX_TEXT_LEN)
    count: int = Field(default=10, ge=1, le=MAX_GHOSTS_PER_ATTACK)
    intensity: float = Field(default=1.0, gt=0, le=10)
    duration: float = Field(default=60.0, gt=0, le=3600)


class AttackStopRequest(BaseModel):
    attacker: str = Field(default="attacker-1", min_length=1, max_length=MAX_TEXT_LEN)


class AccessControlDemoRequest(BaseModel):
    legitimate_count: int = Field(default=100, ge=0, le=MAX_DEVICES_PER_REQUEST)
    ghost_count: int = Field(default=20, ge=0, le=MAX_GHOSTS_PER_ATTACK)


class BlacklistRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=MAX_TEXT_LEN)
    reason: str = Field(default="manual", min_length=1, max_length=MAX_TEXT_LEN)


class RestoreRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=MAX_TEXT_LEN)
