"""Simulation-level Device model for the Digital Twin.

This class represents a simulated IoT device within the Digital Twin engine.
It is intentionally independent from persistence models so the simulator can
operate without database access. Persistence adapters may translate between
the two representations when needed.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class SimDevice:
    """Lightweight simulation device used by the simulator.

    Fields match the Digital Twin contract described in the project plan.
    """

    device_id: str
    name: str
    device_type: str = "generic"
    zone: str | None = None
    legitimate: bool = True
    malicious: bool = False
    authentication_status: str = "pending"
    proximity_status: str = "pending"
    connection_status: str = "joining"
    security_decision: str = "monitor"
    threat_status: str = "unknown"
    credential_label: str | None = None
    attacker_id: str | None = None
    public_key: str | None = None
    private_key: str | None = None
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    comms_radius: float = 100.0
    battery: float = 100.0
    trust_score: float = 0.0
    neighbours: List[str] = field(default_factory=list)
    packets_sent: int = 0
    packets_received: int = 0
    latency_ms: float = 0.0
    status: str = "idle"
    join_ts: datetime | None = None
    last_activity: datetime | None = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def distance_to(self, other: "SimDevice") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def move(self, dt: float) -> None:
        """Update position by applying velocity for dt seconds."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
