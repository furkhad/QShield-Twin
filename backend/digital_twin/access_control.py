"""Access-control device and building layout helpers for the SecureAccess demo."""

from __future__ import annotations

from dataclasses import dataclass, asdict
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
    }


def iter_legitimate_blueprints() -> Iterable[tuple[str, str, str, str]]:
    return list(LEGITIMATE_DEVICE_BLUEPRINTS)


def build_access_control_demo_devices(
    legitimate_count: int = 100,
    ghost_count: int = 20,
) -> List[Dict[str, Any]]:
    """Build a deterministic access-control scenario with legitimate and ghost identities."""

    devices: List[Dict[str, Any]] = []
    for index in range(legitimate_count):
        blueprint = LEGITIMATE_DEVICE_BLUEPRINTS[index % len(LEGITIMATE_DEVICE_BLUEPRINTS)]
        device_id, name, device_type, zone_id = blueprint
        zone = _zone_lookup()[zone_id]
        offset_x = (index % 5) * 12.0
        offset_y = (index // 5 % 4) * 10.0
        devices.append(
            build_access_control_device(
                device_id=f"{device_id}-{index // len(LEGITIMATE_DEVICE_BLUEPRINTS) + 1:02d}" if index >= len(LEGITIMATE_DEVICE_BLUEPRINTS) else device_id,
                name=name,
                device_type=device_type,
                zone_id=zone.zone_id,
                x=zone.x + 20.0 + offset_x,
                y=zone.y + 20.0 + offset_y,
                legitimate=True,
                malicious=False,
                authentication_status="pending",
                proximity_status="pending",
                connection_status="discovering",
                security_decision="monitor",
                trust_score=0.72,
            )
        )

    ghost_names = [
        "door-controller-001-copy",
        "door-controller-001-clone",
        "fake-reader-01",
        "mobile-gateway-ghost",
    ]
    for index in range(ghost_count):
        zone = zone_for_index(index)
        clone_name = ghost_names[index % len(ghost_names)]
        clone_suffix = f"-{index + 1:02d}"
        devices.append(
            build_access_control_device(
                device_id=f"{clone_name}{clone_suffix}",
                name=f"{clone_name}{clone_suffix}",
                device_type=ACCESS_CONTROL_DEVICE_TYPES[index % len(ACCESS_CONTROL_DEVICE_TYPES)],
                zone_id=zone.zone_id,
                x=zone.x + 140.0 + (index % 4) * 8.0,
                y=zone.y + 95.0 + (index % 3) * 6.0,
                legitimate=False,
                malicious=True,
                authentication_status="failed",
                proximity_status="suspicious",
                connection_status="quarantined",
                security_decision="blacklist",
                trust_score=0.15,
                credential_label="ghost",
                attacker_id="ghost-attack",
            )
        )

    return devices
