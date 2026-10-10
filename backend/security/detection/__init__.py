"""Observable-feature Sybil/ghost detection.

This package replaces the earlier name-token heuristic with a transparent,
feature-based detector that consumes only signals a real deployment could
observe. See :mod:`backend.security.detection.detector` for the algorithm and
:mod:`backend.security.detection.evaluation` for the independent evaluation
harness.
"""

from backend.security.detection.detector import (
    DETECTOR_VERSION,
    DetectionOutcome,
    DetectorConfig,
    GhostDetector,
    Observation,
)

__all__ = [
    "DETECTOR_VERSION",
    "DetectionOutcome",
    "DetectorConfig",
    "GhostDetector",
    "Observation",
]
