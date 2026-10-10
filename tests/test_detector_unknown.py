"""Tests for explicit *unknown* detector outcomes.

Missing, stale, malformed and contradictory telemetry must never be classified as
benign. The detector reports a data-quality ``status`` and ``is_unknown`` instead.
"""

from __future__ import annotations

from backend.security.detection.detector import (
    STATUS_CONTRADICTORY,
    STATUS_INSUFFICIENT,
    STATUS_MALFORMED,
    STATUS_OK,
    STATUS_STALE,
    GhostDetector,
    Observation,
)

_TS = 1_000_000.0


def _full(device_id: str, **kwargs) -> Observation:
    params = {
        "claimed_pos": (0.0, 0.0),
        "measured_pos": (0.3, 0.2),
        "signature_valid": True,
        "packet_rate": 3.0,
        "packet_size": 256,
        "credential_fingerprint": f"cred-{device_id}",
        "trust_score": 0.8,
        "timestamp": _TS,
    }
    params.update(kwargs)
    return Observation(device_id=device_id, **params)


def test_sufficient_benign_telemetry_is_known_ok():
    outcome = GhostDetector().observe(_full("d1"))
    assert outcome.status == STATUS_OK
    assert outcome.is_flagged is False
    assert outcome.is_unknown is False
    assert outcome.decision == "pass"


def test_missing_telemetry_is_unknown_not_benign():
    outcome = GhostDetector().observe(Observation("d1", claimed_pos=(0.0, 0.0)))
    assert outcome.status == STATUS_INSUFFICIENT
    assert outcome.is_flagged is False
    assert outcome.is_unknown is True
    assert outcome.decision == "unknown"
    assert outcome.data_quality["signal_count"] == 0


def test_partial_telemetry_below_minimum_is_unknown():
    """A single signal is not enough to conclude the device is benign."""
    outcome = GhostDetector().observe(
        Observation("d1", claimed_pos=(0.0, 0.0), packet_rate=3.0)
    )
    assert outcome.is_unknown is True
    assert outcome.status == STATUS_INSUFFICIENT


def test_malformed_telemetry_is_unknown():
    detector = GhostDetector()
    outcome = detector.observe(
        _full("d1", packet_rate=-5.0, signature_valid="yes", packet_size="big")
    )
    assert outcome.status == STATUS_MALFORMED
    assert outcome.is_unknown is True
    assert outcome.data_quality["malformed_signals"] >= 3


def test_stale_telemetry_is_unknown():
    detector = GhostDetector()
    detector.observe(_full("stale", timestamp=_TS))
    # A later event from another device advances the detector's clock, making the
    # first device's telemetry stale.
    detector.observe(_full("fresh", timestamp=_TS + 10_000.0))
    stale = detector.score("stale")
    assert stale.status == STATUS_STALE
    assert stale.is_unknown is True
    assert detector.score("fresh").is_unknown is False


def test_contradictory_signature_and_trust_is_unknown():
    detector = GhostDetector()
    # Signature verification fails but the trust engine reports very high trust.
    outcome = detector.observe(_full("d1", signature_valid=False, trust_score=0.99))
    assert outcome.status == STATUS_CONTRADICTORY
    assert outcome.is_unknown is True


def test_flapping_signature_verification_is_contradictory():
    detector = GhostDetector()
    # Three passes and one failure in four attempts: the failure ratio (0.25) is
    # below the flagging ramp, so this is a *negative* decision and the flapping
    # verification makes it contradictory (unknown), not a clean pass.
    for _ in range(3):
        detector.observe(_full("d1", signature_valid=True))
    outcome = detector.observe(_full("d1", signature_valid=False))
    assert outcome.is_flagged is False
    assert outcome.status == STATUS_CONTRADICTORY
    assert outcome.is_unknown is True


def test_strong_single_signal_still_flags_even_without_other_telemetry():
    """A positive decision is actionable on its own and is not downgraded."""
    detector = GhostDetector()
    outcome = detector.observe(
        Observation("d1", claimed_pos=(0.0, 0.0), measured_pos=(50.0, 0.0))
    )
    assert outcome.is_flagged is True
    assert outcome.is_unknown is False
    assert outcome.status == STATUS_OK


def test_never_observed_device_is_unknown():
    detector = GhostDetector()
    outcome = detector.score("never-seen")
    assert outcome.is_flagged is False
    assert outcome.is_unknown is True
    assert outcome.status == STATUS_INSUFFICIENT
