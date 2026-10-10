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
    orchestrator = SecurityOrchestrator()

    result = orchestrator.receive_join(
        {
            "device_id": "door-controller-001-copy",
            "name": "door-controller-001-clone",
            "device_type": "door_controller",
            "zone": "main-entrance",
            "x": 260.0,
            "y": 190.0,
            "legitimate": False,
            "malicious": True,
            "credential_label": "clone",
        }
    )

    trust_record = orchestrator.trust.get_trust("door-controller-001-copy")

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
    assert result["attack"]["detection_rate"] >= 0.0

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