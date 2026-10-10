"""Research-integrity tests: ground-truth separation and reproducibility."""

from __future__ import annotations

from backend.security.orchestrator import SecurityOrchestrator


def _join(orchestrator: SecurityOrchestrator, **device) -> None:
    orchestrator.receive_join(device)


def test_ground_truth_is_separate_from_detector_output():
    """The confusion matrix must reflect real misses/false alarms.

    Ground truth is supplied by the caller and never read by the detector. This
    scenario contains one of each outcome:

    * a benign device with benign telemetry (true negative),
    * a benign device whose *measurement* is anomalous, e.g. a sensor fault or
      relay (false alarm / false positive),
    * a malicious device whose observable behaviour is deliberately stealthy
      (missed / false negative),
    * a malicious device with a spoofed position (true positive).

    None of the device names carry attack vocabulary, and the malicious device
    is labelled only via the ground-truth field (never seen by the detector).
    """
    orch = SecurityOrchestrator(seed=1)

    _join(orch, device_id="clean-1", name="Clean Sensor", device_type="sensor",
          x=0.0, y=0.0, legitimate=True, malicious=False,
          observation={"measured_pos": [0.3, 0.2], "signature_valid": True,
                       "credential_fingerprint": "cred-clean-1"})
    _join(orch, device_id="glitch-2", name="Relay Node", device_type="sensor",
          x=100.0, y=0.0, legitimate=True, malicious=False,
          observation={"measured_pos": [140.0, 5.0], "signature_valid": True,
                       "credential_fingerprint": "cred-glitch-2"})
    _join(orch, device_id="stealth-3", name="Access Node", device_type="access_sensor",
          x=200.0, y=0.0, legitimate=False, malicious=True,
          observation={"measured_pos": [200.2, 0.1], "signature_valid": True,
                       "credential_fingerprint": "cred-stealth-3"})
    _join(orch, device_id="obvious-4", name="Access Node", device_type="sensor",
          x=300.0, y=0.0, legitimate=False, malicious=True,
          observation={"measured_pos": [335.0, 8.0], "signature_valid": True,
                       "credential_fingerprint": "cred-obvious-4"})

    cm = orch.analytics.metrics()["confusion_matrix"]
    assert cm == {
        "true_positives": 1,
        "false_positives": 1,
        "true_negatives": 1,
        "false_negatives": 1,
    }
    acc = orch.analytics.metrics()["detection_accuracy"]
    assert acc["precision"] == 0.5
    assert acc["recall"] == 0.5


def _run_seeded_sequence(seed: int) -> dict:
    orch = SecurityOrchestrator(seed=seed)
    for i in range(10):
        _join(
            orch,
            device_id=f"sen-{i}",
            name=f"Sensor {i}",
            device_type="sensor",
            x=float(i),
            y=float(i * 2),
            legitimate=True,
            malicious=(i % 5 == 0),
        )
    return orch.analytics.metrics()["confusion_matrix"]


def test_seeded_runs_are_reproducible():
    first = _run_seeded_sequence(20260101)
    second = _run_seeded_sequence(20260101)
    assert first == second


def test_metrics_report_simulation_source():
    orch = SecurityOrchestrator(seed=5)
    _join(orch, device_id="d1", name="Smoke Sensor", device_type="sensor",
          x=0.0, y=0.0, legitimate=True, malicious=False)
    metrics = orch.analytics.metrics()
    assert metrics["metric_source"] == "simulation"
