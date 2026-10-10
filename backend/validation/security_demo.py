"""Automated SecureAccess demonstration for the access-control cyber-physical demo."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict


backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from backend.digital_twin.manager import DigitalTwinManager


def print_header(text: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_metric(label: str, value: Any) -> None:
    if isinstance(value, float):
        print(f"  {label:<36} {value:>10.2f}")
    else:
        print(f"  {label:<36} {value:>10}")


def collect_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    security_status = result.get("security_status", {})
    security = security_status.get("security", {})
    analytics = security.get("analytics", {})
    trust = security.get("trust", {})
    ledger = security.get("ledger", {})
    attack = result.get("attack", {})

    return {
        "overview": result.get("overview", {}),
        "analytics": analytics,
        "trust": trust,
        "ledger": ledger,
        "verification": analytics.get("performance", {}),
        "attack": attack,
        "summary": {
            "legitimate_devices": result.get("overview", {}).get("trusted_devices", 0),
            "ghost_nodes": result.get("ghost_count", 0),
            "joins_processed": result.get("processed_joins", 0),
            "packets_processed": result.get("processed_packets", 0),
        },
    }


def display_results(result: Dict[str, Any], metrics: Dict[str, Any]) -> None:
    print_header("QSHIELD SECUREACCESS DEMONSTRATION RESULTS")

    overview = metrics.get("overview", {})
    trust = metrics.get("trust", {})
    verification = metrics.get("verification", {})
    analytics = metrics.get("analytics", {})
    attack = metrics.get("attack", {})
    ledger = metrics.get("ledger", {})

    print("\n  ACCESS-CONTROL NETWORK OVERVIEW")
    print_metric("Total devices", overview.get("total_devices", 0))
    print_metric("Active devices", overview.get("active_devices", 0))
    print_metric("Trusted devices", overview.get("trusted_devices", 0))
    print_metric("Devices under monitoring", overview.get("monitoring_devices", 0))
    print_metric("Accepted devices", overview.get("accepted_devices", 0))
    print_metric("Rejected devices", overview.get("rejected_devices", 0))
    print_metric("Blacklisted devices", overview.get("blacklisted_devices", 0))

    print("\n  SIMULATION RESULTS")
    print_metric("Legitimate devices", metrics.get("summary", {}).get("legitimate_devices", 0))
    print_metric("Ghost/Sybil devices", metrics.get("summary", {}).get("ghost_nodes", 0))
    ghost_total = max(1, metrics.get("summary", {}).get("ghost_nodes", 1))
    scenario_detection_rate = metrics.get("overview", {}).get("rejected_devices", 0) / ghost_total
    print_metric("Ghost detection rate", f"{scenario_detection_rate * 100:.1f}%")
    print_metric("Attack success rate", f"{(1.0 - scenario_detection_rate) * 100:.1f}%")
    print_metric("Average trust score", f"{trust.get('average_trust', 0.0) * 100:.1f}/100")
    print_metric("Rejected device count", trust.get("rejected_count", 0))
    print_metric("Blacklisted device count", trust.get("blacklisted_count", 0))

    detection = analytics.get("detection_accuracy", {})
    print("\n  DETECTION METRICS")
    print_metric("Precision", f"{detection.get('precision', 0.0) * 100:.1f}%")
    print_metric("Recall", f"{detection.get('recall', 0.0) * 100:.1f}%")
    print_metric("F1 score", f"{detection.get('f1_score', 0.0) * 100:.1f}%")
    legitimate_count = max(1, metrics.get("summary", {}).get("legitimate_devices", 1))
    print_metric("Legitimate acceptance rate", f"{(overview.get('accepted_devices', 0) / legitimate_count) * 100:.1f}%")

    print("\n  PROXIMITY / PQC / AUDIT")
    print_metric("PQC verification events", analytics.get("summary", {}).get("total_detections", 0))
    print_metric("Average verification time (ms)", verification.get("average_verification_time_ms", 0.0))
    print_metric("Ledger entries", ledger.get("total_entries", 0))
    print_metric("8-shard ledger", ledger.get("shards", 0))

    print("\n  NOTES")
    print("  - Simulated lattice-based PQC interface")
    print("  - Software-simulated ToF proximity verification")
    print("  - 8-shard hash-based audit ledger")
    print("  - Ghost/Sybil detection is one threat modeled in the demo")

    print("\n" + "=" * 80)
    print("  SecureAccess demo completed")
    print("=" * 80 + "\n")


async def run_validation() -> None:
    try:
        print("\n#" * 40)
        print("# QShield SecureAccess automated demonstration")
        print("#" * 40)

        manager = DigitalTwinManager()
        print_header("RUNNING ACCESS-CONTROL DEMO")
        result = manager.run_access_control_demo(legitimate_count=100, ghost_count=20)

        metrics = collect_metrics(result)
        display_results(result, metrics)

        output_path = Path("logs") / "secureaccess_demo_results.json"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Saved demo results to {output_path}")

    except Exception as exc:
        print("\nX SecureAccess demonstration failed")
        print(f"  {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(run_validation())
