"""Access-control security tests for the QShield SecureAccess scenario."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.digital_twin.manager import DigitalTwinManager
from backend.security.orchestrator import SecurityOrchestrator


def test_legitimate_access_control_device_joins_and_is_trusted():
    orchestrator = SecurityOrchestrator()

    result = orchestrator.receive_join(
        {
            "device_id": "door-controller-001",
            "name": "Main Entrance Door Controller",
            "device_type": "door_controller",
            "zone": "main-entrance",
            "x": 64.0,
            "y": 58.0,
            "legitimate": True,
            "malicious": False,
        }
    )

    trust_record = orchestrator.trust.get_trust("door-controller-001")

    assert result["accepted"] is True
    assert result["ghost_detected"] is False
    assert result["decision"] in {"accept", "monitor"}
    assert trust_record is not None
    assert trust_record.score >= 0.5
    assert result["trust_score"] == trust_record.score


def test_clone_access_control_device_is_flagged_as_suspicious():
    """A cloned identity is detected from observable telemetry, not its name."""
    orchestrator = SecurityOrchestrator()

    result = orchestrator.receive_join(
        {
            "device_id": "access-node-0001",
            "name": "Access Node 0001",
            "device_type": "door_controller",
            "zone": "main-entrance",
            "x": 260.0,
            "y": 190.0,
            "legitimate": False,
            "malicious": True,
            # Observable clone signals: spoofed proximity measurement and a
            # shared/cloned credential.
            "observation": {
                "measured_pos": [300.0, 220.0],
                "signature_valid": False,
                "packet_rate": 21.0,
                "packet_size": 420,
                "credential_fingerprint": "cred-access-ghost",
            },
        }
    )

    trust_record = orchestrator.trust.get_trust("access-node-0001")

    assert result["ghost_detected"] is True
    assert result["decision"] in {"monitor", "reject", "blacklist"}
    assert trust_record is not None
    assert trust_record.score <= 0.7


def test_access_control_demo_and_api_endpoints():
    manager = DigitalTwinManager()
    result = manager.run_access_control_demo(legitimate_count=12, ghost_count=4)

    assert result["overview"]["total_devices"] == 16
    assert result["overview"]["trusted_devices"] >= 1
    assert result["security_status"]["security"]["recent_events"]
    # Every materialised ghost identity is scored through the pipeline, so the
    # attack summary must agree with the confusion matrix rather than showing a
    # hard-coded 0% detection rate.
    assert result["attack"]["ghost_count"] == 4
    assert result["attack"]["detected_count"] == 4
    assert result["attack"]["detection_rate"] == 1.0
    attack_defense = result["analytics"]["attack_defense"]
    assert attack_defense["ghosts_spawned"] == 4
    assert attack_defense["ghosts_detected"] == 4

    app = create_app()
    client = TestClient(app)

    overview_response = client.get("/api/v1/security/access-control/overview")
    devices_response = client.get("/api/v1/security/access-control/devices")
    demo_response = client.post(
        "/api/v1/security/demo/access-control",
        json={"legitimate_count": 8, "ghost_count": 2},
    )

    assert overview_response.status_code == 200
    assert devices_response.status_code == 200
    assert demo_response.status_code == 200
    assert overview_response.json()["status"] == "ok"
    assert devices_response.json()["status"] == "ok"
    assert demo_response.json()["status"] == "ok"


def test_attack_campaign_statistics_reflect_detections():
    """A started campaign is scored through the pipeline and counted once."""
    orchestrator = SecurityOrchestrator()

    spawn = orchestrator.start_attack(
        attacker_id="attacker-x", count=5, intensity=1.0, duration=0.1
    )
    assert spawn["ghosts_spawned"] == 5

    stopped = orchestrator.stop_attack("attacker-x")
    assert stopped["detection_rate"] == 1.0
    assert stopped["success_rate"] == 0.0

    attack_defense = orchestrator.analytics.metrics()["attack_defense"]
    # Counted exactly once: 5 spawned (at start) and 5 detected (at stop).
    assert attack_defense["attacks_launched"] == 1
    assert attack_defense["ghosts_spawned"] == 5
    assert attack_defense["ghosts_detected"] == 5
    assert attack_defense["defense_success_rate"] == 1.0
