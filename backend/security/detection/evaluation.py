"""Independent evaluation harness for the ghost detector.

The harness runs a detector over generated scenarios and compares its
predictions with held-out ground truth. It is intentionally decoupled from the
FastAPI app and the database so it can be run quickly, deterministically and in
tests. Ground truth is only read here, never inside the detector.

Reported metrics (with correct zero-denominator handling):
    * confusion matrix: TP / FP / TN / FN
    * precision, recall, F1, accuracy, false-positive rate
    * per-attack-type recall/precision
    * per-scenario breakdown and per-seed stability
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Protocol

from backend.security.detection.baseline import NameTokenBaseline
from backend.security.detection.detector import GhostDetector
from backend.security.detection.scenarios import Scenario


class _Predictor(Protocol):
    version: str

    def reset(self) -> None: ...


@dataclass
class Metrics:
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    # Devices/events the detector could not decide (unknown/insufficient data).
    # Excluded from TP/FP/TN/FN and reported separately so a lack of telemetry is
    # never scored as a true negative.
    unknown: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        total = (
            self.true_positives
            + self.false_positives
            + self.true_negatives
            + self.false_negatives
        )
        return (self.true_positives + self.true_negatives) / total if total else 0.0

    @property
    def false_positive_rate(self) -> float:
        denom = self.false_positives + self.true_negatives
        return self.false_positives / denom if denom else 0.0

    def add(self, other: "Metrics") -> None:
        self.true_positives += other.true_positives
        self.false_positives += other.false_positives
        self.true_negatives += other.true_negatives
        self.false_negatives += other.false_negatives
        self.unknown += other.unknown

    def as_dict(self) -> Dict[str, float]:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "unknown": self.unknown,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "accuracy": round(self.accuracy, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
        }


@dataclass
class EvaluationReport:
    detector_version: str
    scenario_count: int
    device_count: int
    confusion: Metrics
    per_attack_type: Dict[str, Metrics] = field(default_factory=dict)
    per_scenario: List[Dict[str, object]] = field(default_factory=list)
    thresholds: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {
            "detector_version": self.detector_version,
            "scenario_count": self.scenario_count,
            "device_count": self.device_count,
            "overall": self.confusion.as_dict(),
            "per_attack_type": {
                name: metrics.as_dict() for name, metrics in self.per_attack_type.items()
            },
            "per_scenario": self.per_scenario,
            "thresholds": self.thresholds,
        }


def _score_scenario_with_detector(detector: GhostDetector, scenario: Scenario):
    detector.reset()
    # Feed observations in the order they occurred; the detector is streaming.
    for device in scenario.devices:
        for observation in device.observations:
            detector.observe(observation)

    pairs = []  # (is_ghost, flagged, attack_type, unknown)
    for device in scenario.devices:
        outcome = detector.score(device.device_id)
        pairs.append(
            (
                device.is_ghost,
                outcome.is_flagged,
                device.attack_type,
                outcome.is_unknown,
            )
        )
    return pairs


def _score_scenario_with_baseline(baseline: NameTokenBaseline, scenario: Scenario):
    pairs = []
    for device in scenario.devices:
        outcome = baseline.predict(device.device_id, name=device.name)
        pairs.append((device.is_ghost, outcome.is_flagged, device.attack_type, False))
    return pairs


def _aggregate(pairs) -> Metrics:
    metrics = Metrics()
    for is_ghost, flagged, _attack_type, unknown in pairs:
        if unknown:
            metrics.unknown += 1
        elif is_ghost and flagged:
            metrics.true_positives += 1
        elif is_ghost and not flagged:
            metrics.false_negatives += 1
        elif not is_ghost and flagged:
            metrics.false_positives += 1
        else:
            metrics.true_negatives += 1
    return metrics


def evaluate(
    detector_factory: Callable[[], GhostDetector],
    scenarios: List[Scenario],
) -> EvaluationReport:
    """Evaluate a detector factory over ``scenarios``."""

    overall = Metrics()
    per_attack: Dict[str, Metrics] = {}
    per_scenario: List[Dict[str, object]] = []
    device_count = 0
    version = "unknown"

    for scenario in scenarios:
        detector = detector_factory()
        version = getattr(detector, "version", detector.__class__.__name__)
        pairs = _score_scenario_with_detector(detector, scenario)
        scenario_metrics = _aggregate(pairs)
        overall.add(scenario_metrics)
        device_count += len(scenario.devices)

        for is_ghost, flagged, attack_type, unknown in pairs:
            bucket = per_attack.setdefault(attack_type, Metrics())
            if unknown:
                bucket.unknown += 1
            elif is_ghost and flagged:
                bucket.true_positives += 1
            elif is_ghost and not flagged:
                bucket.false_negatives += 1
            elif not is_ghost and flagged:
                bucket.false_positives += 1
            else:
                bucket.true_negatives += 1

        per_scenario.append(
            {
                "name": scenario.name,
                "seed": scenario.seed,
                "holdout": scenario.holdout,
                "ghost_count": scenario.ghost_count,
                "legitimate_count": scenario.legitimate_count,
                **scenario_metrics.as_dict(),
            }
        )

    return EvaluationReport(
        detector_version=version,
        scenario_count=len(scenarios),
        device_count=device_count,
        confusion=overall,
        per_attack_type=per_attack,
        per_scenario=per_scenario,
        thresholds=_threshold_dict(detector_factory),
    )


def evaluate_baseline(scenarios: List[Scenario]) -> EvaluationReport:
    """Evaluate the name-token baseline on the same (neutral-named) scenarios."""

    baseline = NameTokenBaseline()
    overall = Metrics()
    per_attack: Dict[str, Metrics] = {}
    per_scenario: List[Dict[str, object]] = []
    device_count = 0

    for scenario in scenarios:
        pairs = _score_scenario_with_baseline(baseline, scenario)
        scenario_metrics = _aggregate(pairs)
        overall.add(scenario_metrics)
        device_count += len(scenario.devices)

        for is_ghost, flagged, attack_type, unknown in pairs:
            bucket = per_attack.setdefault(attack_type, Metrics())
            if unknown:
                bucket.unknown += 1
            elif is_ghost and flagged:
                bucket.true_positives += 1
            elif is_ghost and not flagged:
                bucket.false_negatives += 1
            elif not is_ghost and flagged:
                bucket.false_positives += 1
            else:
                bucket.true_negatives += 1

        per_scenario.append(
            {
                "name": scenario.name,
                "seed": scenario.seed,
                "holdout": scenario.holdout,
                **scenario_metrics.as_dict(),
            }
        )

    return EvaluationReport(
        detector_version=baseline.version,
        scenario_count=len(scenarios),
        device_count=device_count,
        confusion=overall,
        per_attack_type=per_attack,
        per_scenario=per_scenario,
        thresholds={},
    )


def _threshold_dict(detector_factory: Callable[[], GhostDetector]) -> Dict[str, float]:
    try:
        config = detector_factory().config
    except Exception:  # pragma: no cover - defensive
        return {}
    return {
        "decision_threshold": config.decision_threshold,
        "benign_proximity_error_m": config.benign_proximity_error_m,
        "flag_proximity_error_m": config.flag_proximity_error_m,
        "flag_packet_rate": config.flag_packet_rate,
        "flag_cluster_size": config.flag_cluster_size,
    }
