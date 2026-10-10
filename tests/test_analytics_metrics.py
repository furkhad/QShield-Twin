"""Tests for analytics metrics correctness, including zero-denominator handling."""

from __future__ import annotations

from backend.security.analytics.analytics_engine import AnalyticsEngine


def _record(engine: AnalyticsEngine, *, is_ghost: bool, detected: bool) -> None:
    engine.record_detection(
        device_id="d",
        is_ghost=is_ghost,
        detected_as_ghost=detected,
        verification_time_ms=1.0,
        confidence=0.9,
    )


def test_confusion_matrix_and_scores():
    engine = AnalyticsEngine()
    # 2 TP, 1 FP, 1 FN, 6 TN
    _record(engine, is_ghost=True, detected=True)
    _record(engine, is_ghost=True, detected=True)
    _record(engine, is_ghost=False, detected=True)
    _record(engine, is_ghost=True, detected=False)
    for _ in range(6):
        _record(engine, is_ghost=False, detected=False)

    metrics = engine.metrics()
    cm = metrics["confusion_matrix"]
    assert cm == {
        "true_positives": 2,
        "false_positives": 1,
        "true_negatives": 6,
        "false_negatives": 1,
    }

    acc = metrics["detection_accuracy"]
    # precision = 2/3, recall = 2/3, f1 = 2/3, accuracy = 8/10, fpr = 1/7
    assert acc["precision"] == round(2 / 3, 4)
    assert acc["recall"] == round(2 / 3, 4)
    assert acc["f1_score"] == round(2 / 3, 4)
    assert acc["accuracy"] == 0.8
    assert acc["false_positive_rate"] == round(1 / 7, 4)


def test_empty_engine_has_zeroed_metrics_without_error():
    metrics = AnalyticsEngine().metrics()
    acc = metrics["detection_accuracy"]
    assert acc["precision"] == 0.0
    assert acc["recall"] == 0.0
    assert acc["f1_score"] == 0.0
    assert acc["false_positive_rate"] == 0.0
    assert metrics["metric_source"] == "simulation"


def test_run_metadata_is_exported():
    engine = AnalyticsEngine()
    engine.set_run_metadata(seed=42, scenario="light_sybil_attack", software_version="0.2.0")
    metrics = engine.metrics()
    assert metrics["run_metadata"]["seed"] == 42
    assert metrics["run_metadata"]["scenario"] == "light_sybil_attack"


def test_unknown_detections_are_not_counted_as_true_negatives():
    engine = AnalyticsEngine()
    # A benign device the detector could not decide (unknown telemetry).
    engine.record_detection(
        device_id="d",
        is_ghost=False,
        detected_as_ghost=False,
        observed=False,
    )
    metrics = engine.metrics()
    assert metrics["confusion_matrix"]["true_negatives"] == 0
    assert metrics["observation_coverage"] == {
        "observed": 0,
        "unknown": 1,
        "total": 1,
        "coverage_rate": 0.0,
    }
    assert metrics["detector"]["unknown_detections"] == 1


def test_observation_coverage_reports_observed_ratio():
    engine = AnalyticsEngine()
    _record(engine, is_ghost=False, detected=False)  # observed by default
    engine.record_detection(
        device_id="d", is_ghost=True, detected_as_ghost=False, observed=False
    )
    coverage = engine.metrics()["observation_coverage"]
    assert coverage["observed"] == 1
    assert coverage["unknown"] == 1
    assert coverage["total"] == 2
    assert coverage["coverage_rate"] == 0.5


def test_csv_export_includes_observed_column():
    engine = AnalyticsEngine()
    engine.record_detection(
        device_id="d", is_ghost=False, detected_as_ghost=False, observed=False
    )
    header = engine.export_csv().splitlines()[0]
    assert "observed" in header
