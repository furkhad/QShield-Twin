"""Digital Twin Manager: high-level orchestration for device lifecycle and statistics."""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from backend.digital_twin.access_control import (
    build_access_control_demo_devices,
    zones_as_dicts,
)
from backend.security.orchestrator import SecurityOrchestrator
from backend.settings import get_settings
from backend.simulation.device import SimDevice
from backend.simulation.environment import SimConfig
from backend.simulation.simulator import Simulator

# Upper bound on devices materialised by a single scripted scenario. Keeps a
# scenario bounded even if a caller asks for more.
MAX_SCENARIO_DEVICES = 1000


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
            self.security = SecurityOrchestrator(seed=self.config.random_seed)
            # let simulator call orchestrator for packet events
            self.sim.packet_callback = self.security.receive_packet
        except Exception:
            self.security = None

    def spawn_device(
        self,
        name: str,
        x: float = 0.0,
        y: float = 0.0,
        device_type: str = "generic",
        zone: str | None = None,
        legitimate: bool = True,
        malicious: bool = False,
        security_decision: str = "monitor",
        authentication_status: str = "pending",
        proximity_status: str = "pending",
        connection_status: str = "joining",
        trust_score: float = 0.0,
        credential_label: str | None = None,
        attacker_id: str | None = None,
        observation: dict | None = None,
    ) -> SimDevice:
        device_id = str(uuid4())
        dev = SimDevice(
            device_id=device_id,
            name=name,
            device_type=device_type,
            x=x,
            y=y,
            comms_radius=self.config.default_comms_radius,
            zone=zone,
            legitimate=legitimate,
            malicious=malicious,
            authentication_status=authentication_status,
            proximity_status=proximity_status,
            connection_status=connection_status,
            security_decision=security_decision,
            trust_score=trust_score,
            credential_label=credential_label,
            attacker_id=attacker_id,
        )
        dev.join_ts = None
        self.sim.add_device(dev)
        # inform security orchestrator of join event
        try:
            if hasattr(self, "security") and self.security:
                result = self.security.receive_join(
                    {
                        "device_id": device_id,
                        "name": name,
                        "x": x,
                        "y": y,
                        "zone": zone,
                        "device_type": device_type,
                        "legitimate": legitimate,
                        "malicious": malicious,
                        "credential_label": credential_label,
                        "attacker_id": attacker_id,
                        "observation": observation,
                    }
                )
                dev.trust_score = float(result.get("trust_score", trust_score))
                dev.authentication_status = "verified" if result.get("accepted") else "failed"
                dev.proximity_status = result.get("proximity", proximity_status)
                dev.security_decision = result.get("decision", security_decision)
                dev.connection_status = "connected" if result.get("accepted") else "quarantined"
        except Exception:
            if self.security:
                raise
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

    def spawn_access_control_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        zone: str,
        x: float,
        y: float,
        *,
        legitimate: bool = True,
        malicious: bool = False,
        security_decision: str = "monitor",
        authentication_status: str = "pending",
        proximity_status: str = "pending",
        connection_status: str = "joining",
        trust_score: float = 0.0,
        credential_label: str | None = None,
        attacker_id: str | None = None,
        observation: dict | None = None,
    ) -> SimDevice:
        device = SimDevice(
            device_id=device_id,
            name=name,
            device_type=device_type,
            x=x,
            y=y,
            comms_radius=self.config.default_comms_radius,
            zone=zone,
            legitimate=legitimate,
            malicious=malicious,
            authentication_status=authentication_status,
            proximity_status=proximity_status,
            connection_status=connection_status,
            security_decision=security_decision,
            trust_score=trust_score,
            credential_label=credential_label,
            attacker_id=attacker_id,
        )
        self.sim.add_device(device)
        if self.security:
            result = self.security.receive_join(
                {
                    "device_id": device_id,
                    "name": name,
                    "x": x,
                    "y": y,
                    "zone": zone,
                    "device_type": device_type,
                    "legitimate": legitimate,
                    "malicious": malicious,
                    "credential_label": credential_label,
                    "attacker_id": attacker_id,
                    "observation": observation,
                    # Access-control joins gate physical access, so degraded/absent
                    # telemetry must not silently resolve to "allow".
                    "security_sensitive": True,
                }
            )
            device.trust_score = float(result.get("trust_score", trust_score))
            device.authentication_status = "verified" if result.get("accepted") else "failed"
            device.proximity_status = result.get("proximity", proximity_status)
            device.security_decision = result.get("decision", security_decision)
            device.connection_status = "connected" if result.get("accepted") else "quarantined"
        return device

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
            # Re-seed so a given scenario configuration reproduces identical runs.
            self.security.reset(seed=self.config.random_seed)

    def get_devices(self) -> List[Dict]:
        return self.sim.snapshot()

    def status(self):
        simulation = self.sim.status()
        devices = self.get_devices()
        security = self.security.status() if getattr(self, "security", None) else {}

        accepted = sum(1 for device in devices if device.get("security_decision") in {"accept", "monitor"})
        trusted = sum(1 for device in devices if float(device.get("trust_score", 0.0) or 0.0) >= 0.7)
        monitoring = sum(1 for device in devices if device.get("security_decision") == "monitor")
        rejected = sum(1 for device in devices if device.get("security_decision") == "reject")
        blacklisted = sum(1 for device in devices if device.get("security_decision") == "blacklist")

        overview: Dict[str, Any] = {
            "total_devices": len(devices),
            "active_devices": sum(1 for device in devices if device.get("connection_status") == "connected"),
            "trusted_devices": trusted,
            "monitoring_devices": monitoring,
            "rejected_devices": rejected,
            "blacklisted_devices": blacklisted,
            "accepted_devices": accepted,
        }

        return {
            "simulation": simulation,
            "security": security,
            "access_control": {
                "zones": zones_as_dicts(),
                "devices": devices,
                "overview": overview,
            },
            "devices": devices,
            "overview": overview,
        }

    def run_scenario(
        self,
        scenario_name: str,
        device_count: int = 100,
        ghost_count: int | None = None,
        seed: int | None = None,
    ) -> Dict:
        """Execute a scripted access-control demonstration scenario using the existing security pipeline.

        Args:
            scenario_name: Scenario identifier.
            device_count: Number of legitimate devices to materialise.
            ghost_count: Override for the number of ghost/Sybil identities.
            seed: Optional PRNG seed for this run. Overrides the manager's
                configured seed so callers can run reproducible experiments.
        """
        scenario = scenario_name.lower().replace(" ", "_")
        if scenario not in {
            "normal",
            "light_sybil_attack",
            "medium_sybil_attack",
            "heavy_sybil_attack",
            "access_control_demo",
            "access_control_attack",
        }:
            scenario = "access_control_demo"

        if seed is not None:
            self.config.random_seed = seed

        self.reset_simulation()

        if scenario in {"normal", "access_control_demo"}:
            attack_count = 0
            intensity = 0.5
        elif scenario == "light_sybil_attack":
            attack_count = ghost_count or 10
            intensity = 1.0
        elif scenario == "medium_sybil_attack":
            attack_count = ghost_count or 20
            intensity = 1.5
        else:
            attack_count = ghost_count or 50
            intensity = 2.0

        demo_devices = build_access_control_demo_devices(
            legitimate_count=min(device_count, MAX_SCENARIO_DEVICES),
            ghost_count=attack_count,
            seed=self.config.random_seed,
            severity=min(2.0, max(0.5, intensity)),
        )

        for device in demo_devices:
            self.spawn_access_control_device(
                device_id=device["device_id"],
                name=device["name"],
                device_type=device["device_type"],
                zone=device["zone"],
                x=float(device["x"]),
                y=float(device["y"]),
                legitimate=bool(device["legitimate"]),
                malicious=bool(device["malicious"]),
                security_decision=str(device["security_decision"]),
                authentication_status=str(device["authentication_status"]),
                proximity_status=str(device["proximity_status"]),
                connection_status=str(device["connection_status"]),
                trust_score=float(device["trust_score"]),
                credential_label=device.get("credential_label"),
                attacker_id=device.get("attacker_id"),
                observation=device.get("observation"),
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

        # The ghosts above are materialised as observable, scored identities, so
        # the attack summary is derived from the detector's actual outcomes rather
        # than a separate (legacy) ghost-engine campaign. This keeps ``attack``
        # and the analytics ``attack_defense`` block consistent with the
        # confusion matrix instead of reporting a spurious 0% detection rate.
        if attack_count > 0:
            confusion = self.security.analytics.metrics().get("confusion_matrix", {})
            # TP counts scored *events* (join and, for early devices, packets),
            # so cap at the number of distinct ghost identities.
            detected_count = min(attack_count, int(confusion.get("true_positives", 0)))
            detection_rate = detected_count / attack_count
            attack_stats = {
                "ghost_count": attack_count,
                "detected_count": detected_count,
                "detection_rate": detection_rate,
                "success_rate": round(1.0 - detection_rate, 4),
            }
            self.security.analytics.record_attack(
                f"{scenario}-attacker", attack_count, detected_count
            )
        else:
            attack_stats = {
                "ghost_count": 0,
                "detected_count": 0,
                "detection_rate": 0.0,
                "success_rate": 0.0,
            }

        # Attach provenance so exported metrics can be tied to this exact run.
        effective_seed = self.config.random_seed
        detector = getattr(self.security, "detector", None)
        self.security.analytics.set_run_metadata(
            scenario=scenario,
            device_count=min(device_count, MAX_SCENARIO_DEVICES),
            ghost_count=attack_count,
            seed=effective_seed,
            software_version=get_settings().app_version,
            detector_version=getattr(detector, "version", None),
            detector_threshold=(
                detector.config.decision_threshold if detector is not None else None
            ),
        )

        status = self.status()
        return {
            "scenario": scenario,
            "device_count": min(device_count, MAX_SCENARIO_DEVICES),
            "ghost_count": attack_count,
            "seed": effective_seed,
            "software_version": get_settings().app_version,
            "processed_joins": status.get("security", {}).get("processed_joins", 0),
            "processed_packets": status.get("security", {}).get("processed_packets", 0),
            "ghost_nodes": status.get("security", {}).get("ghost_nodes", 0),
            "trust": status.get("security", {}).get("trust", {}),
            "ledger": status.get("security", {}).get("ledger", {}),
            "analytics": status.get("security", {}).get("analytics", {}),
            "overview": status.get("overview", {}),
            "devices": status.get("devices", []),
            "zones": status.get("access_control", {}).get("zones", []),
            "attack": attack_stats,
            "security_status": status,
        }

    def run_access_control_demo(self, legitimate_count: int = 100, ghost_count: int = 20) -> Dict[str, Any]:
        return self.run_scenario(
            scenario_name="access_control_attack" if ghost_count else "access_control_demo",
            device_count=legitimate_count,
            ghost_count=ghost_count,
        )
