"""Independent-evaluation tests: ground-truth separation, held-out generalisation,
metric correctness and honest baseline comparison.
"""

from __future__ import annotations

from backend.security.detection.baseline import NameTokenBaseline
from backend.security.detection.detector import GhostDetector
from backend.security.detection.evaluation import (
    Metrics,
    evaluate,
    evaluate_baseline,
)
from backend.security.detection.scenarios import (
    DEFAULT_SEEDS,
    HOLDOUT_CONFIGS,
    HOLDOUT_HARD_CONFIGS,
    TUNING_CONFIGS,
    build_scenario,
    build_suite,
)

_SEEDS = [1, 42, 1337]


def test_metrics_handle_zero_denominators():
    empty = Metrics()
    assert empty.precision == 0.0
    assert empty.recall == 0.0
    assert empty.f1_score == 0.0
    assert empty.accuracy == 0.0
    assert empty.false_positive_rate == 0.0


def test_metrics_compute_expected_values():
    m = Metrics(true_positives=3, false_positives=1, true_negatives=6, false_negatives=2)
    assert m.precision == 0.75
    assert m.recall == 0.6
    assert abs(m.f1_score - 0.6667) < 0.001
    assert m.false_positive_rate == 1 / 7


def test_evaluate_on_empty_suite_is_zero_safe():
    report = evaluate(GhostDetector, [])
    assert report.scenario_count == 0
    assert report.confusion.as_dict()["precision"] == 0.0
    assert report.confusion.as_dict()["recall"] == 0.0


def test_scenarios_are_deterministic_for_a_seed():
    from backend.security.detection.scenarios import TUNING_CONFIGS

    a = build_scenario(TUNING_CONFIGS[1], 7)
    b = build_scenario(TUNING_CONFIGS[1], 7)
    assert [d.device_id for d in a.devices] == [d.device_id for d in b.devices]
    assert [d.is_ghost for d in a.devices] == [d.is_ghost for d in b.devices]


def test_scenario_names_are_neutral():
    """No attack vocabulary may appear in generated names/ids."""
    tokens = ("ghost", "sybil", "clone", "copy", "fake", "attacker", "rogue")
    for config in TUNING_CONFIGS + HOLDOUT_CONFIGS:
        scenario = build_scenario(config, 7)
        for device in scenario.devices:
            haystack = f"{device.device_id} {device.name}".lower()
            assert not any(token in haystack for token in tokens)


def test_detector_beats_name_baseline_on_holdout():
    suite = build_suite(HOLDOUT_CONFIGS, _SEEDS)
    detector = evaluate(GhostDetector, suite)
    baseline = evaluate_baseline(suite)

    assert detector.confusion.recall > baseline.confusion.recall
    assert baseline.confusion.recall == 0.0  # names carry no signal
    # The detector should achieve strong recall on separable holdout scenarios.
    assert detector.confusion.recall >= 0.8
    # And it should not spam false positives.
    assert detector.confusion.false_positive_rate <= 0.05


def test_detector_reports_per_attack_type():
    suite = build_suite(HOLDOUT_CONFIGS, _SEEDS)
    report = evaluate(GhostDetector, suite)
    assert "legit" in report.per_attack_type
    for ghost_type in ("spoof", "clone", "sybil_herd", "traffic_abuse", "auth_failure"):
        assert ghost_type in report.per_attack_type


def test_honest_reporting_of_undetectable_stealth_attacks():
    """Deliberately sub-threshold attacks must be reported as misses, not hidden."""
    suite = build_suite(HOLDOUT_HARD_CONFIGS, DEFAULT_SEEDS)
    report = evaluate(GhostDetector, suite)
    # The stealthy attacker keeps every feature below threshold, so recall is
    # (honestly) near zero. This test pins that expectation so the limitation is
    # visible rather than silently optimised away.
    assert report.confusion.recall <= 0.2


def test_baseline_is_zero_recall_without_name_tokens():
    baseline = NameTokenBaseline()
    assert baseline.predict("node-0001", name="access-node-0001").is_flagged is False
    flagged = baseline.predict("door-controller-001-copy", name="clone")
    assert flagged.is_flagged is True


def test_report_is_json_serialisable():
    import json

    suite = build_suite(TUNING_CONFIGS[:2], [1])
    report = evaluate(GhostDetector, suite)
    payload = json.dumps(report.as_dict())
    assert "overall" in json.loads(payload)


def test_unknown_outcomes_are_excluded_from_confusion_matrix():
    """A device with no telemetry is reported as unknown, not a true negative."""
    from backend.security.detection.scenarios import Scenario, ScenarioDevice

    scenario = Scenario(
        name="silent_sensor",
        seed=1,
        devices=[
            ScenarioDevice(
                device_id="node-0001",
                name="access-node-0001",
                is_ghost=False,
                attack_type="legit",
                observations=[],  # no telemetry at all
            )
        ],
    )
    report = evaluate(GhostDetector, [scenario])
    assert report.confusion.unknown == 1
    assert report.confusion.true_negatives == 0
    assert report.confusion.false_positives == 0
    assert report.confusion.as_dict()["unknown"] == 1
