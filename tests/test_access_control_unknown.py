"""Unknown-telemetry handling through the security orchestrator.

Security-sensitive access-control joins must not resolve to "allow" when the
detector has insufficient, stale, malformed or contradictory telemetry. Non
security-sensitive joins remain best-effort but are still surfaced and counted as
unknown rather than benign.
"""

from __future__ import annotations

from backend.security.orchestrator import SecurityOrchestrator

_GOOD_OBS = {
    "measured_pos": [0.5, 0.3],
    "signature_valid": True,
    "packet_rate": 3.0,
    "packet_size": 256,
    "credential_fingerprint": "cred-device-a",
}


def _join(orchestrator: SecurityOrchestrator, **device) -> dict:
    return orchestrator.receive_join(device)


def test_security_sensitive_join_without_telemetry_is_challenged():
    orch = SecurityOrchestrator()
    result = _join(
        orch,
        device_id="door-1",
        name="Door Controller",
        device_type="door_controller",
        x=1.0,
        y=2.0,
        security_sensitive=True,
    )
    assert result["accepted"] is False
    assert result["decision"] == "challenge"
    assert result["detection_unknown"] is True
    assert result["detection_status"] == "insufficient_data"
    assert result["ghost_detected"] is False


def test_security_sensitive_join_with_malformed_telemetry_is_challenged():
    orch = SecurityOrchestrator()
    result = _join(
        orch,
        device_id="door-2",
        name="Door Controller",
        device_type="door_controller",
        x=1.0,
        y=2.0,
        security_sensitive=True,
        observation={
            "measured_pos": [0.5, 0.3],
            "signature_valid": True,
            "packet_rate": -4.0,  # malformed
            "credential_fingerprint": "cred-door-2",
        },
    )
    assert result["accepted"] is False
    assert result["decision"] == "challenge"
    assert result["detection_status"] == "malformed"


def test_security_sensitive_join_with_contradictory_telemetry_is_challenged():
    orch = SecurityOrchestrator()
    result = _join(
        orch,
        device_id="door-3",
        name="Door Controller",
        device_type="door_controller",
        x=1.0,
        y=2.0,
        security_sensitive=True,
        observation={
            "measured_pos": [0.5, 0.3],
            "signature_valid": False,
            "packet_rate": 3.0,
            "packet_size": 256,
            "credential_fingerprint": "cred-door-3",
            "trust_score": 0.99,
        },
    )
    assert result["accepted"] is False
    assert result["decision"] in {"challenge", "reject", "blacklist"}
    assert result["detection_unknown"] is True
    assert result["detection_status"] == "contradictory"


def test_security_sensitive_join_with_sufficient_benign_telemetry_is_accepted():
    orch = SecurityOrchestrator()
    result = _join(
        orch,
        device_id="door-4",
        name="Door Controller",
        device_type="door_controller",
        x=1.0,
        y=2.0,
        security_sensitive=True,
        observation=dict(_GOOD_OBS),
    )
    assert result["accepted"] is True
    assert result["detection_unknown"] is False
    assert result["detection_status"] == "ok"
    assert result["ghost_detected"] is False


def test_non_sensitive_join_without_telemetry_is_monitored_not_benign():
    orch = SecurityOrchestrator()
    result = _join(
        orch, device_id="sensor-1", name="Sensor", device_type="sensor", x=5.0, y=5.0
    )
    # Best-effort path: still accepted, but explicitly flagged as unknown telemetry
    # rather than treated as a clean benign pass.
    assert result["accepted"] is True
    assert result["decision"] == "monitor"
    assert result["detection_unknown"] is True
    assert result["detection_status"] == "insufficient_data"


def test_unknown_join_is_not_counted_as_true_negative():
    orch = SecurityOrchestrator()
    _join(orch, device_id="sensor-1", name="Sensor", device_type="sensor", x=5.0, y=5.0)

    metrics = orch.analytics.metrics()
    assert metrics["confusion_matrix"]["true_negatives"] == 0
    assert metrics["observation_coverage"]["unknown"] == 1
    assert metrics["observation_coverage"]["observed"] == 0
    assert metrics["detector"]["unknown_detections"] == 1


def test_unknown_packet_is_not_counted_as_true_negative():
    orch = SecurityOrchestrator()
    # A packet with no observable telemetry whatsoever -> unknown, not benign.
    orch.receive_packet({"src": "pkt-1", "dst": "sink", "payload": {}})

    metrics = orch.analytics.metrics()
    assert metrics["confusion_matrix"]["true_negatives"] == 0
    assert metrics["observation_coverage"]["unknown"] >= 1
