"""Utilities for simulation environment configuration and seeding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimConfig:
    random_seed: Optional[int] = None
    simulation_time: float = 30.0
    default_comms_radius: float = 100.0
    topology: str = "random"
