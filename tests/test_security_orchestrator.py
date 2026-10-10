"""Detector behaviour through the public join API.

These tests exercise the *observable-feature* detector. They deliberately use
adversarial names (``ghost-123``) to prove that naming has no influence: only
measured telemetry decides the outcome.
"""

from backend.security.orchestrator import SecurityOrchestrator


def _benign_observation(x: float, y: float) -> dict:
    return {
        "measured_pos": [x + 0.5, y + 0.3],
        "signature_valid": True,
        "packet_rate": 3.0,
        "packet_size": 256,
        "credential_fingerprint": "cred-benign-unique",
    }


def test_receive_join_detects_spoofed_proximity_and_rejects():
    """A device whose measured position is far from its claim is flagged."""
    orchestrator = SecurityOrchestrator()

    result = orchestrator.receive_join(
        {
            "device_id": "node-0001",
            "name": "Access Node",
            "x": 1.0,
            "y": 2.0,
            "device_type": "sensor",
            # Spoofed position: physically measured ~41 m away from the claim.
            "observation": {
                "measured_pos": [41.0, 12.0],
                "signature_valid": True,
                "packet_rate": 4.0,
                "packet_size": 300,
                "credential_fingerprint": "cred-spoof",
            },
        }
    )

    assert result["ghost_detected"] is True
    assert result["decision"] in {"monitor", "reject", "blacklist"}


def test_adversarial_name_alone_is_not_flagged():
    """Naming must not drive detection: a 'ghost'-named benign device passes."""
    orchestrator = SecurityOrchestrator()

    result = orchestrator.receive_join(
        {
            "device_id": "ghost-123",
            "name": "ghost-123",
            "device_type": "ghost",
            "x": 1.0,
            "y": 2.0,
            "observation": _benign_observation(1.0, 2.0),
        }
    )

    assert result["ghost_detected"] is False
    assert result["decision"] in {"accept", "monitor"}


def test_benign_device_without_observation_is_accepted():
    """With no telemetry supplied, a device is treated as benign by default."""
    orchestrator = SecurityOrchestrator()

    result = orchestrator.receive_join(
        {
            "device_id": "sensor-1",
            "name": "Smoke Sensor",
            "device_type": "sensor",
            "x": 5.0,
            "y": 5.0,
        }
    )

    assert result["ghost_detected"] is False
    assert result["accepted"] is True
    assert result["trust_score"] >= 0.5
