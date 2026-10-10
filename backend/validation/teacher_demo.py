"""Teacher-friendly terminal demonstration of the QShield security pipeline."""

from __future__ import annotations

import sys
from typing import Any, Callable

from backend.security.orchestrator import SecurityOrchestrator

LEGITIMATE_DEVICE_COUNT = 8
GHOST_DEVICE_COUNT = 6
ATTACKER_ID = "teacher-demo-attacker"


class DemonstrationError(RuntimeError):
    """Raised when a demonstration stage cannot complete."""


def header(title: str) -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


def subsection(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def status(label: str, passed: bool) -> None:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")


def metric(label: str, value: Any) -> None:
    print(f"  {label:<38} {value}")


def percentage(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.2f}%"


def run_stage(name: str, action: Callable[[], Any]) -> Any:
    try:
        return action()
    except Exception as exc:
        raise DemonstrationError(
            f"{name} failed: {type(exc).__name__}: {exc}"
        ) from exc


def wait_for_attack_completion(
    orchestrator: SecurityOrchestrator, attacker_id: str, timeout: float = 1.0
) -> None:
    """Wait briefly for the existing attack worker to calculate final stats."""
    thread = orchestrator.ghost.attack_threads.get(attacker_id)
    if thread is not None:
        thread.join(timeout=timeout)

    stats = orchestrator.ghost.get_attack_stats(attacker_id)
    if stats is None or stats.end_time is None:
        raise DemonstrationError("Sybil attack failed: worker did not finalize")


def initialize(orchestrator: SecurityOrchestrator) -> None:
    header("[1] INITIALIZING SECURITY FRAMEWORK")
    components = (
        ("Security Orchestrator", orchestrator),
        ("Ghost Node / Sybil Attack Engine", orchestrator.ghost),
        ("Proof-of-Proximity Engine", orchestrator.proximity),
        ("Post-Quantum / Lattice Cryptography", orchestrator.pqc),
        ("Multi-Factor Trust Engine", orchestrator.trust),
        ("Sharded Audit Ledger", orchestrator.ledger),
        ("Analytics Engine", orchestrator.analytics),
    )
    for label, component in components:
        status(label, component is not None)


def register_legitimate_devices(orchestrator: SecurityOrchestrator) -> list[dict[str, Any]]:
    header("[2] LEGITIMATE DEVICE REGISTRATION")
    results = []
    for index in range(LEGITIMATE_DEVICE_COUNT):
        result = orchestrator.receive_join(
            {
                "device_id": f"teacher-sensor-{index + 1}",
                "name": f"Temperature Sensor {index + 1}",
                "device_type": "sensor",
                "x": float(index * 3),
                "y": float(index * 2),
                "zone": "evaluation-lab",
            }
        )
        results.append(result)

    metric("Join requests processed", orchestrator.processed_joins)
    metric("Legitimate devices recorded", len(orchestrator.legitimate_devices))
    metric("Accepted or monitored joins", sum(item["accepted"] for item in results))
    return results


def verify_normal_devices(
    orchestrator: SecurityOrchestrator, results: list[dict[str, Any]]
) -> None:
    header("[3] NORMAL DEVICE VERIFICATION")
    subsection("Existing join pipeline exercised")
    print("  IoT device -> identity -> proximity -> PQC -> trust -> ledger")
    metric("Devices evaluated", len(results))
    metric("Identity/join results", len(results))
    metric("Valid cryptographic joins", sum(item["accepted"] for item in results))
    metric("Proximity results", len(orchestrator.proximity.history))
    metric("Ledger records", orchestrator.ledger.stats()["total_entries"])


def simulate_attack(orchestrator: SecurityOrchestrator) -> dict[str, Any]:
    header("[4] SYBIL ATTACK SIMULATION")
    attack = orchestrator.start_attack(
        attacker_id=ATTACKER_ID,
        count=GHOST_DEVICE_COUNT,
        intensity=2.0,
        duration=0.2,
    )
    metric("Attacker ID", attack["attacker"])
    metric("Ghost nodes spawned", attack["ghosts_spawned"])
    metric("Attack intensity", attack["intensity"])
    metric("Attack start", "recorded by GhostEngine")

    # ``start_attack`` already scores every spawned identity through the join
    # pipeline using observable Sybil telemetry (shared credential, co-located
    # spoofed proximity, failing signatures, elevated packet rate), so no manual
    # re-join is needed here.
    orchestrator.stop_attack(ATTACKER_ID)
    wait_for_attack_completion(orchestrator, ATTACKER_ID)
    stats = orchestrator.ghost.get_attack_stats(ATTACKER_ID)
    if stats is None:
        raise DemonstrationError("Sybil attack failed: no final statistics")
    metric("Attack completion", "recorded by GhostEngine")
    metric("Ghost nodes detected", stats.detected_count)
    return {
        "ghost_count": stats.ghost_count,
        "detected_count": stats.detected_count,
        "detection_rate": stats.detection_rate,
        "attack_success_rate": stats.success_rate,
    }


def display_pipeline() -> None:
    header("[5] SECURITY PIPELINE")
    print("  IoT Device")
    print("      |")
    print("  Join / Identity Verification")
    print("      |")
    print("  Proof-of-Proximity")
    print("      |")
    print("  Lattice-Based Cryptographic Verification")
    print("      |")
    print("  Behavioral Analysis")
    print("      |")
    print("  Multi-Factor Trust Engine")
    print("      |")
    print("  ACCEPT / MONITOR / REJECT / BLACKLIST")
    print("      |")
    print("  Sharded Audit Ledger")


def display_metrics(
    orchestrator: SecurityOrchestrator, attack: dict[str, Any]
) -> dict[str, bool]:
    analytics = orchestrator.analytics.metrics()
    detection = analytics["detection_accuracy"]
    confusion = analytics["confusion_matrix"]
    proximity = orchestrator.proximity.get_metrics()
    trust = orchestrator.trust.export_trust_metrics()
    pqc = orchestrator.pqc.metrics()
    ledger = orchestrator.ledger.stats()

    header("[6] DETECTION RESULTS")
    metric("Legitimate devices", len(orchestrator.legitimate_devices))
    metric("Ghost nodes", attack["ghost_count"])
    metric("Detected ghost nodes", attack["detected_count"])
    metric("Attack success rate", percentage(attack["attack_success_rate"]))
    metric("Defense success rate", percentage(attack["detection_rate"]))
    metric("Detection rate", percentage(detection["recall"]))
    metric("Precision", percentage(detection["precision"]))
    metric("True positives / false negatives", f"{confusion['true_positives']} / {confusion['false_negatives']}")

    header("[7] PROOF-OF-PROXIMITY RESULTS")
    metric("Total verifications", proximity["total_verifications"])
    metric("Acceptance rate", percentage(proximity["acceptance_rate"]))
    metric("Average confidence", percentage(proximity["average_confidence"]))
    metric("Average propagation delay", f"{proximity['average_propagation_delay_ms']:.6f} ms")

    header("[8] TRUST ENGINE RESULTS")
    metric("Total devices evaluated", trust["total_devices"])
    metric("Average trust score", f"{trust['average_trust']:.4f}")
    metric("Accepted", trust["accepted_count"])
    metric("Monitored", trust["monitored_count"])
    metric("Rejected", trust["rejected_count"])
    metric("Blacklisted", trust["blacklisted_count"])

    header("[9] LATTICE / POST-QUANTUM CRYPTOGRAPHY")
    print("  This project uses SimulatedLatticeCrypto, an abstraction for PQC integration.")
    metric("Algorithm", pqc["algorithm"])
    metric("Key generation operations", pqc["keypair_generation_ms"]["count"])
    metric("Signing operations", pqc["signature_generation_ms"]["count"])
    metric("Verification operations", pqc["signature_verification_ms"]["count"])
    metric("Average key generation", f"{pqc['keypair_generation_ms']['avg']:.2f} ms")
    metric("Average signing", f"{pqc['signature_generation_ms']['avg']:.2f} ms")
    metric("Average verification", f"{pqc['signature_verification_ms']['avg']:.2f} ms")
    metric("Verification failures", pqc["signature_verification_ms"]["failures"])

    header("[10] SHARDED LEDGER")
    metric("Total entries", ledger["total_entries"])
    metric("Unique devices", ledger["unique_devices"])
    metric("Shard count", ledger["shards"])
    metric("Average shard size", f"{ledger['average_shard_size']:.2f}")
    metric("Accepted entries", ledger["accepted_entries"])
    metric("Rejected entries", ledger["rejected_entries"])

    return {
        "Ghost Node Detection": attack["detected_count"] == attack["ghost_count"] > 0,
        "Proof-of-Proximity": proximity["total_verifications"] > 0,
        "Lattice PQC": (
            pqc["keypair_generation_ms"]["count"] > 0
            and pqc["signature_generation_ms"]["count"] > 0
            and pqc["signature_verification_ms"]["count"] > 0
            and pqc["signature_verification_ms"]["failures"] == 0
        ),
        "Trust Engine": trust["total_devices"] > 0,
        "Sharded Ledger": ledger["total_entries"] > 0 and ledger["shards"] > 0,
        "End-to-End Pipeline": (
            len(orchestrator.legitimate_devices) > 0
            and len(orchestrator.ghost_nodes) > 0
            and ledger["total_entries"] > 0
        ),
    }


def display_summary(module_status: dict[str, bool]) -> None:
    header("[11] FINAL SECURITY SUMMARY")
    print(f"{'Module':<32} Status")
    print("-" * 48)
    for name, passed in module_status.items():
        print(f"{name:<32} {'PASS' if passed else 'FAIL'}")
    end_to_end = all(module_status.values())
    print("-" * 48)
    print(f"Final Result: {'PASS' if end_to_end else 'FAIL'}")
    print("-" * 48)
    if not end_to_end:
        raise DemonstrationError("one or more security modules did not complete successfully")


def main() -> int:
    stage = "initialization"
    try:
        orchestrator = run_stage(stage, SecurityOrchestrator)
        run_stage(stage, lambda: initialize(orchestrator))
        stage = "legitimate registration"
        legitimate = run_stage(stage, lambda: register_legitimate_devices(orchestrator))
        stage = "normal verification"
        run_stage(stage, lambda: verify_normal_devices(orchestrator, legitimate))
        stage = "Sybil attack simulation"
        attack = run_stage(stage, lambda: simulate_attack(orchestrator))
        stage = "security pipeline display"
        run_stage(stage, display_pipeline)
        stage = "metric collection"
        module_status = run_stage(stage, lambda: display_metrics(orchestrator, attack))
        stage = "summary"
        run_stage(stage, lambda: display_summary(module_status))
        return 0
    except Exception as exc:
        print("\n[FAIL] TEACHER DEMONSTRATION FAILED")
        print(f"  Stage: {stage}")
        print(f"  Error: {type(exc).__name__}: {exc}")
        print("  Fix: install the project dependencies and rerun the command.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
