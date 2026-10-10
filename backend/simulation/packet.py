"""Packet representation used by the simulator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class Packet:
    src: str
    dst: str | None
    payload: Dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {"src": self.src, "dst": self.dst, "payload": self.payload, "timestamp": self.timestamp.isoformat()}
