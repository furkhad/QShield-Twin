"""Access-control device and building layout helpers for the SecureAccess demo."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class AccessControlZone:
    zone_id: str
    name: str
    x: float
    y: float
    width: float
    height: float


ACCESS_CONTROL_ZONES: List[AccessControlZone] = [
    AccessControlZone("main-entrance", "Main Entrance", 40.0, 40.0, 220.0, 140.0),
    AccessControlZone("reception", "Reception", 300.0, 40.0, 220.0, 140.0),
    AccessControlZone("office-area", "Office Area", 40.0, 220.0, 220.0, 150.0),
    AccessControlZone("restricted-area", "Restricted Area", 300.0, 220.0, 220.0, 150.0),
    AccessControlZone("server-room", "Server Room", 560.0, 220.0, 180.0, 150.0),
    AccessControlZone("emergency-exit", "Emergency Exit", 560.0, 40.0, 180.0, 140.0),
]

ACCESS_CONTROL_DEVICE_TYPES = [
    "door_controller",
    "smart_lock",
    "rfid_reader",
    "mobile_credential_gateway",
    "security_gateway",
    "access_sensor",
    "emergency_exit_controller",
]

LEGITIMATE_DEVICE_BLUEPRINTS = [
    ("door-controller-001", "Main Entrance Door Controller", "door_controller", "main-entrance"),
    ("door-controller-002", "Reception Door Controller", "door_controller", "reception"),
    ("door-controller-003", "Office Area Door Controller", "door_controller", "office-area"),
    ("door-controller-004", "Restricted Area Door Controller", "door_controller", "restricted-area"),
    ("smart-lock-001", "Office Door Smart Lock", "smart_lock", "office-area"),
    ("rfid-reader-001", "RFID Access Reader", "rfid_reader", "main-entrance"),
    ("mobile-gateway-001", "Mobile Credential Gateway", "mobile_credential_gateway", "reception"),
    ("security-gateway-001", "Security Floor Gateway", "security_gateway", "restricted-area"),
    ("emergency-exit-001", "Emergency Exit Controller", "emergency_exit_controller", "emergency-exit"),
    ("sensor-001", "Access-Control Sensor", "access_sensor", "server-room"),
]


def zones_as_dicts() -> List[Dict[str, Any]]:
    return [asdict(zone) for zone in ACCESS_CONTROL_ZONES]


def _zone_lookup() -> Dict[str, AccessControlZone]:
    return {zone.zone_id: zone for zone in ACCESS_CONTROL_ZONES}


def zone_for_index(index: int) -> AccessControlZone:
    return ACCESS_CONTROL_ZONES[index % len(ACCESS_CONTROL_ZONES)]


def build_access_control_device(
    device_id: str,
    name: str,
    device_type: str,
    zone_id: str,
    x: float,
    y: float,
    *,
    legitimate: bool = True,
    malicious: bool = False,
    authentication_status: str = "pending",
    proximity_status: str = "unknown",
    connection_status: str = "joining",
    security_decision: str = "monitor",
    trust_score: float = 0.5,
    credential_label: str | None = None,
    attacker_id: str | None = None,
    observation: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "device_id": device_id,
        "name": name,
        "device_type": device_type,
        "zone": zone_id,
        "x": x,
        "y": y,
        "legitimate": legitimate,
        "malicious": malicious,
        "authentication_status": authentication_status,
        "proximity_status": proximity_status,
        "connection_status": connection_status,
        "security_decision": security_decision,
        "trust_score": trust_score,
        "credential_label": credential_label,
        "attacker_id": attacker_id,
        # Observable telemetry only. Scenario labels above are never read by the
        # detector; they exist purely for reporting/ground truth.
        "observation": observation,
    }


def iter_legitimate_blueprints() -> Iterable[tuple[str, str, str, str]]:
    return list(LEGITIMATE_DEVICE_BLUEPRINTS)


def build_access_control_demo_devices(
    legitimate_count: int = 100,
    ghost_count: int = 20,
    *,
    seed: int | None = None,
    severity: float = 1.0,
) -> List[Dict[str, Any]]:
    """Build a deterministic access-control scenario with legitimate and ghost identities.

    Ghost identities use **neutral names** (no ``ghost`` / ``copy`` / ``clone``
    vocabulary) and are distinguished only by observable telemetry: a spoofed
    proof-of-proximity measurement, a shared (cloned) credential, elevated packet
    volume and repeated signature failures. This mirrors the scenarios used by
    the independent evaluation harness and prevents name-based leakage.
    """

    rng = random.Random(seed) if seed is not None else random.Random(0)
    sev = max(0.05, severity)
    devices: List[Dict[str, Any]] = []

    # Legitimate devices are spread on a unique >=8 m grid inside each zone (slot
    # 0 is reserved for the ghost herd below). Real deployments have spatially
    # distinct devices; placing many legitimate devices on the same few
    # coordinates would create legitimate false-positive Sybil clusters.
    zone_slot: Dict[str, int] = {}
    for index in range(legitimate_count):
        blueprint = LEGITIMATE_DEVICE_BLUEPRINTS[index % len(LEGITIMATE_DEVICE_BLUEPRINTS)]
        device_id, name, device_type, zone_id = blueprint
        zone = _zone_lookup()[zone_id]
        slot = zone_slot.get(zone.zone_id, 1)
        zone_slot[zone.zone_id] = slot + 1
        cols = max(1, int((zone.width - 12) // 8))
        rows = max(1, int((zone.height - 12) // 8))
        col = slot % cols
        row = (slot // cols) % rows
        x = zone.x + 6.0 + col * 8.0
        y = zone.y + 6.0 + row * 8.0
        resolved_id = (
            f"{device_id}-{index // len(LEGITIMATE_DEVICE_BLUEPRINTS) + 1:02d}"
            if index >= len(LEGITIMATE_DEVICE_BLUEPRINTS)
            else device_id
        )
        measured = (
            x + 0.5 + rng.gauss(0, 0.3),
            y + 0.3 + rng.gauss(0, 0.3),
        )
        devices.append(
            build_access_control_device(
                device_id=resolved_id,
                name=name,
                device_type=device_type,
                zone_id=zone.zone_id,
                x=x,
                y=y,
                legitimate=True,
                malicious=False,
                authentication_status="pending",
                proximity_status="pending",
                connection_status="discovering",
                security_decision="monitor",
                trust_score=0.72,
                credential_label=None,
                observation={
                    "measured_pos": [measured[0], measured[1]],
                    "signature_valid": True,
                    "packet_rate": max(0.5, rng.gauss(3.0, 0.8)),
                    "packet_size": int(max(64, rng.gauss(256, 40))),
                    "credential_fingerprint": f"cred-{resolved_id}",
                },
            )
        )

    # Ghost identities are grouped per physical origin so that co-located
    # identities form an observable cluster, and all share one cloned credential.
    # Their *measured* position is a single spoofed herd origin per zone (slot 0
    # of the grid above, distinct from every legitimate device cell).
    ghost_origin_by_zone: Dict[str, tuple[float, float]] = {}
    for index in range(ghost_count):
        zone = zone_for_index(index)
        x = zone.x + 120.0 + (index % 4) * 8.0
        y = zone.y + 80.0 + (index % 3) * 6.0
        origin = ghost_origin_by_zone.setdefault(
            zone.zone_id, (zone.x + 6.0, zone.y + 6.0)
        )
        resolved_id = f"access-node-{index + 1:04d}"
        devices.append(
            build_access_control_device(
                device_id=resolved_id,
                name=f"Access Node {index + 1:04d}",
                device_type=ACCESS_CONTROL_DEVICE_TYPES[index % len(ACCESS_CONTROL_DEVICE_TYPES)],
                zone_id=zone.zone_id,
                x=x,
                y=y,
                legitimate=False,
                malicious=True,
                authentication_status="failed",
                proximity_status="suspicious",
                connection_status="quarantined",
                security_decision="blacklist",
                trust_score=0.15,
                credential_label=None,
                attacker_id=None,
                observation={
                    # Identical spoofed measurement for the whole herd → the
                    # co-location cluster feature fires deterministically.
                    "measured_pos": [origin[0], origin[1]],
                    "signature_valid": rng.random() > (0.6 * sev),
                    "packet_rate": max(1.0, sev * rng.uniform(16.0, 30.0)),
                    "packet_size": int(max(64, rng.gauss(420, 80))),
                    "credential_fingerprint": "cred-access-ghost",
                },
            )
        )

    return devices
