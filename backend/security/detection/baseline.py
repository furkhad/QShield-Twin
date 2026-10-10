"""Name-token baseline detector, kept only for honest comparison.

The pre-upgrade detector flagged a device as a ghost if its id/name/type
contained tokens such as ``ghost`` or ``clone``, or if it appeared in the
scenario's own ghost registry. That is label leakage, not detection. This class
preserves the *mechanism* so the evaluation harness can quantify how little it
generalises once scenario names are neutral.
"""

from __future__ import annotations

from typing import Iterable

from backend.security.detection.detector import DetectionOutcome

_BASELINE_VERSION = "name-token-baseline/1.0"
_SUSPICIOUS_TOKENS = (
    "ghost",
    "sybil",
    "attacker",
    "copy",
    "clone",
    "fake",
    "rogue",
    "impostor",
)


class NameTokenBaseline:
    """Baseline that predicts from identity strings only (no real telemetry)."""

    version = _BASELINE_VERSION

    def __init__(self, tokens: Iterable[str] = _SUSPICIOUS_TOKENS) -> None:
        self.tokens = tuple(tokens)

    def predict(self, device_id: str, name: str = "", device_type: str = "") -> DetectionOutcome:
        haystack = f"{device_id} {name} {device_type}".lower()
        hit = next((token for token in self.tokens if token in haystack), None)
        return DetectionOutcome(
            device_id=device_id,
            is_flagged=hit is not None,
            score=1.0 if hit else 0.0,
            features={"name_token_hit": 1.0 if hit else 0.0},
            contributions={},
            reasons=[f"name token '{hit}'"] if hit else ["no name token"],
            detector_version=self.version,
        )

    def reset(self) -> None:  # pragma: no cover - stateless
        return None
