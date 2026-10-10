"""Unit tests for the observable-feature ghost detector."""

from __future__ import annotations

from backend.security.detection.detector import (
    DETECTOR_VERSION,
    DetectorConfig,
    GhostDetector,
    Observation,
)


def _obs(device_id: str, **kwargs) -> Observation:
    params = {
        "claimed_pos": (0.0, 0.0),
        "measured_pos": (0.3, 0.2),
        "signature_valid": True,
        "packet_rate": 3.0,
        "packet_size": 256,
        "credential_fingerprint": f"cred-{device_id}",
    }
    params.update(kwargs)
    return Observation(device_id=device_id, **params)


def test_benign_device_is_not_flagged():
    detector = GhostDetector()
    outcome = detector.observe(_obs("d1"))
    assert outcome.is_flagged is False
    assert outcome.score >= 0.0
    assert outcome.reasons  # always explainable
    assert outcome.detector_version == DETECTOR_VERSION


def test_spoofed_proximity_is_flagged():
    detector = GhostDetector()
    outcome = detector.observe(_obs("d1", measured_pos=(41.0, 12.0)))
    assert outcome.is_flagged is True
    assert outcome.features["proximity_error_m"] > 30
    assert any("proximity" in reason for reason in outcome.reasons)


def test_repeated_signature_failures_are_flagged():
    detector = GhostDetector()
    detector.observe(_obs("d1", signature_valid=False))
    outcome = detector.observe(_obs("d1", signature_valid=False))
    assert outcome.is_flagged is True
    assert outcome.features["signature_failure_ratio"] == 1.0


def test_single_signature_failure_is_not_enough():
    detector = GhostDetector()
    outcome = detector.observe(_obs("d1", signature_valid=False))
    # A single failure is insufficient evidence (ratio/attempts below minimum).
    assert outcome.is_flagged is False


def test_shared_credential_across_identities_is_flagged():
    detector = GhostDetector()
    detector.observe(_obs("d1", credential_fingerprint="shared"))
    detector.observe(_obs("d2", credential_fingerprint="shared"))
    outcome = detector.observe(_obs("d3", credential_fingerprint="shared"))
    assert outcome.is_flagged is True
    assert outcome.features["credential_reuse"] >= 2


def test_identity_cluster_at_one_origin_is_flagged():
    detector = GhostDetector()
    outcomes = []
    for i in range(5):
        outcomes.append(
            detector.observe(
                _obs(f"d{i}", measured_pos=(500.0 + i * 0.2, 500.0))
            )
        )
    assert outcomes[-1].is_flagged is True
    assert outcomes[-1].features["identity_cluster_size"] >= 4


def test_names_do_not_influence_the_score():
    """Two devices with identical telemetry must score identically regardless of id."""
    a = GhostDetector().observe(_obs("ghost-clone-fake", measured_pos=(0.4, 0.3)))
    b = GhostDetector().observe(_obs("innocent-node", measured_pos=(0.4, 0.3)))
    assert a.score == b.score
    assert not a.is_flagged
    assert not b.is_flagged


def test_scoring_is_deterministic():
    def run() -> float:
        detector = GhostDetector()
        for _ in range(3):
            detector.observe(_obs("d1", packet_rate=25.0, packet_size=6000))
        return detector.score("d1").score

    assert run() == run()


def test_threshold_is_configurable():
    low = GhostDetector(DetectorConfig(decision_threshold=0.2))
    high = GhostDetector(DetectorConfig(decision_threshold=0.95))
    for detector in (low, high):
        detector.observe(_obs("d1", measured_pos=(30.0, 10.0)))
    # Proximity-only evidence scores ~0.9: flagged at a 0.2 bar, not at 0.95.
    assert low.score("d1").is_flagged is True
    assert high.score("d1").is_flagged is False
    assert low.score("d1").score == high.score("d1").score


def test_reset_clears_state():
    detector = GhostDetector()
    detector.observe(_obs("d1", measured_pos=(50.0, 0.0)))
    detector.reset()
    assert detector.score("d1").score == 0.0
    assert detector.score("d1").is_flagged is False
