"""Runnable evaluation report for the ghost detector.

Usage::

    uv run python -m backend.security.detection.run_evaluation
    uv run python -m backend.security.detection.run_evaluation --out report.json

It evaluates the feature-based detector and the name-token baseline over three
scenario suites (tuning, held-out *and* deliberately hard/stealthy) and prints a
human-readable summary. Ground truth is held out and only used for scoring.

This is a **simulation** evaluation: results reflect controlled synthetic
scenarios, not field deployment. The hard suite exists specifically to show where
threshold-based detection fails.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from backend.security.detection.detector import GhostDetector
from backend.security.detection.evaluation import (
    EvaluationReport,
    evaluate,
    evaluate_baseline,
)
from backend.security.detection.scenarios import (
    DEFAULT_SEEDS,
    HOLDOUT_CONFIGS,
    HOLDOUT_HARD_CONFIGS,
    TUNING_CONFIGS,
)


def build_reports() -> Dict[str, EvaluationReport]:
    from backend.security.detection.scenarios import build_suite

    seeds = DEFAULT_SEEDS
    return {
        "tuning": evaluate(GhostDetector, build_suite(TUNING_CONFIGS, seeds)),
        "holdout": evaluate(GhostDetector, build_suite(HOLDOUT_CONFIGS, seeds)),
        "holdout_hard": evaluate(GhostDetector, build_suite(HOLDOUT_HARD_CONFIGS, seeds)),
        "baseline_holdout": evaluate_baseline(build_suite(HOLDOUT_CONFIGS, seeds)),
    }


def _format_report(name: str, report: EvaluationReport) -> str:
    overall = report.confusion.as_dict()
    lines = [
        f"== {name} ({report.detector_version}) ==",
        f"   scenarios={report.scenario_count} devices={report.device_count}",
        (
            "   overall: "
            f"TP={overall['true_positives']} FP={overall['false_positives']} "
            f"TN={overall['true_negatives']} FN={overall['false_negatives']} "
            f"UNKNOWN={overall['unknown']} | "
            f"precision={overall['precision']} recall={overall['recall']} "
            f"f1={overall['f1_score']} fpr={overall['false_positive_rate']}"
        ),
    ]
    for attack_type, metrics in sorted(report.per_attack_type.items()):
        lines.append(
            f"   - {attack_type:14s} "
            f"recall={metrics.recall:.3f} precision={metrics.precision:.3f} "
            f"fn={metrics.false_negatives} fp={metrics.false_positives}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None, help="Write JSON report to this path")
    args = parser.parse_args(argv)

    reports = build_reports()
    for name, report in reports.items():
        print(_format_report(name, report))

    print(
        "\nNOTE: synthetic simulation scenarios. Tuning/holdout use separable "
        "signals; holdout_hard uses deliberately sub-threshold stealth and is "
        "expected to score near-zero recall."
    )

    if args.out is not None:
        payload = {name: report.as_dict() for name, report in reports.items()}
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote JSON report to {args.out}")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
