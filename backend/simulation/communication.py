"""Communication engine: models latency and packet delivery between devices."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Callable

from backend.simulation.packet import Packet


def default_latency(distance_m: float) -> float:
    """Simple latency model: base + distance-proportional (ms).

    This is intentionally simplistic but parameterizable for later research.
    """
    base_ms = 1.0
    per_meter_ms = 0.001  # 1 microsecond per meter
    jitter = random.gauss(0, 0.5)
    return max(0.1, base_ms + per_meter_ms * distance_m + jitter)


class CommunicationEngine:
    """Handles packet transmission between devices using a pluggable latency model."""

    def __init__(self, latency_fn: Callable[[float], float] = default_latency):
        self.latency_fn = latency_fn

    def transmit(self, src_device, dst_device, payload: dict) -> Packet:
        distance = src_device.distance_to(dst_device)
        latency_ms = self.latency_fn(distance)
        pkt = Packet(src=src_device.device_id, dst=dst_device.device_id, payload=payload, timestamp=datetime.utcnow())
        # Update device statistics
        src_device.packets_sent += 1
        dst_device.packets_received += 1
        dst_device.latency_ms = latency_ms
        src_device.last_activity = datetime.utcnow()
        dst_device.last_activity = datetime.utcnow()
        return pkt
