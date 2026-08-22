"""Digital Twin Manager: high-level orchestration for device lifecycle and statistics."""

from __future__ import annotations

import time
from typing import Dict, List, Optional
from uuid import uuid4

from backend.simulation.device import SimDevice
from backend.simulation.simulator import Simulator
from backend.security.orchestrator import SecurityOrchestrator
from backend.simulation.environment import SimConfig


_manager_singleton: "DigitalTwinManager | None" = None


def get_manager(config: SimConfig | None = None) -> "DigitalTwinManager":
    """Return a shared manager instance for API and UI integrations."""
    global _manager_singleton
    if _manager_singleton is None:
        _manager_singleton = DigitalTwinManager(config=config or SimConfig())
    return _manager_singleton


class DigitalTwinManager:
    """Manages simulated devices and exposes operations used by APIs.

    Responsibilities include spawning devices, removing devices, moving
    devices, and exposing simulation statistics. This manager delegates
    low-level execution to the Simulator which runs the SimPy environment.
    """

    def __init__(self, config: SimConfig | None = None) -> None:
        self.config = config or SimConfig()
        # If a WebSocket manager is present, pass its emit_sync as the
        # simulator broadcaster so snapshots are streamed to clients.
        broadcaster = None
        try:
            from backend.app.websocket.manager import manager as ws_manager

            broadcaster = ws_manager.emit_sync
        except Exception:
            broadcaster = None

        self.sim = Simulator(seed=self.config.random_seed, broadcaster=broadcaster)
        # instantiate security orchestrator and wire callbacks
        try:
            self.security = SecurityOrchestrator()
            # let simulator call orchestrator for packet events
            self.sim.packet_callback = self.security.receive_packet
        except Exception:
            self.security = None

    def spawn_device(self, name: str, x: float = 0.0, y: float = 0.0, device_type: str = "generic") -> SimDevice:
        device_id = str(uuid4())
        dev = SimDevice(device_id=device_id, name=name, device_type=device_type, x=x, y=y, comms_radius=self.config.default_comms_radius)
        dev.join_ts = None
        self.sim.add_device(dev)
        # inform security orchestrator of join event
        try:
            if hasattr(self, "security") and self.security:
                self.security.receive_join({"device_id": device_id, "name": name, "x": x, "y": y})
        except Exception:
            pass
        return dev

    def spawn_bulk(self, count: int, prefix: str = "dev") -> list:
        created = []
        # minimize per-iteration overhead
        for i in range(count):
            device_id = str(uuid4())
            name = f"{prefix}-{i}"
            dev = SimDevice(device_id=device_id, name=name, device_type="generic", x=0.0, y=0.0, comms_radius=self.config.default_comms_radius)
            dev.join_ts = None
            self.sim.add_device(dev)
            created.append(dev)
        return created

    def remove_device(self, device_id: str) -> None:
        self.sim.remove_device(device_id)

    def apply_topology(self, topology: str, **kwargs) -> None:
        """Apply a topology to all currently managed devices and persist choice in config."""
        devices = list(self.sim.devices.values())
        # Delegate to network graph
        self.sim.network.populate_topology(devices, topology=topology, **kwargs)
        # persist selection
        self.config.topology = topology


    def start_simulation(self, runtime: float | None = None) -> None:
        rt = runtime if runtime is not None else self.config.simulation_time
        self.sim.start(runtime=rt)

    def reset_simulation(self) -> None:
        self.sim.reset()
        if hasattr(self, "security") and self.security:
            self.security.reset()

    def get_devices(self) -> List[Dict]:
        return self.sim.snapshot()

    def status(self):
        return self.sim.status()

    def run_scenario(
        self,
        scenario_name: str,
        device_count: int = 100,
        ghost_count: int | None = None,
    ) -> Dict:
        """Execute a scripted demonstration scenario using the existing security pipeline."""
        scenario = scenario_name.lower().replace(" ", "_")
        if scenario not in {"normal", "light_sybil_attack", "medium_sybil_attack", "heavy_sybil_attack"}:
            scenario = "medium_sybil_attack"

        self.reset_simulation()

        if scenario == "normal":
            attack_count = 0
            intensity = 0.5
            duration = 0.2
        elif scenario == "light_sybil_attack":
            attack_count = ghost_count or 10
            intensity = 1.0
            duration = 0.8
        elif scenario == "medium_sybil_attack":
            attack_count = ghost_count or 20
            intensity = 1.5
            duration = 1.0
        else:
            attack_count = ghost_count or 50
            intensity = 2.0
            duration = 1.2

        for idx in range(min(device_count, 100)):
            self.spawn_device(
                name=f"device-{idx}",
                x=float((idx % 10) * 20),
                y=float((idx // 10) * 20),
                device_type="legitimate",
            )

        # Give the security pipeline a small amount of traffic to update the trust engine.
        for device in list(self.sim.devices.values())[:25]:
            self.security.receive_packet(
                {
                    "src": device.device_id,
                    "dst": "broadcast",
                    "payload": {
                        "claimed_pos": (device.x, device.y),
                        "measured_pos": (device.x + 0.5, device.y + 0.5),
                        "rate": 2.0,
                        "size": 256,
                        "signature": b"mock_signature",
                    },
                }
            )

        if attack_count > 0:
            attacker_id = f"{scenario}-attacker"
            self.security.start_attack(attacker_id=attacker_id, count=attack_count, intensity=intensity, duration=duration)
            time.sleep(duration + 0.2)
            attack_stats = self.security.stop_attack(attacker_id)
        else:
            attack_stats = {"ghost_count": 0, "detection_rate": 0.0, "success_rate": 0.0}

        status = self.security.status()
        return {
            "scenario": scenario,
            "device_count": min(device_count, 100),
            "ghost_count": attack_count,
            "processed_joins": status.get("processed_joins", 0),
            "processed_packets": status.get("processed_packets", 0),
            "ghost_nodes": status.get("ghost_nodes", 0),
            "trust": status.get("trust", {}),
            "ledger": status.get("ledger", {}),
            "analytics": status.get("analytics", {}),
            "attack": attack_stats,
            "security_status": status,
        }
