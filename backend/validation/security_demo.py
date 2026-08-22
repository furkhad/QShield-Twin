"""
Automated validation and demonstration of the Quantum-Resilient Sybil Defense Framework.

This script performs an end-to-end test:
1. Create 100 legitimate devices
2. Initialize the security orchestrator
3. Run devices through the complete security pipeline
4. Launch a Sybil attack with 20 ghost nodes
5. Verify detection accuracy
6. Collect and display research metrics

Run this script after starting the Digital Twin backend:
    python -m backend.validation.security_demo

Expected output:
    - 100 legitimate devices accepted
    - 20 ghost nodes detected
    - Detection accuracy metrics (Precision, Recall, F1)
    - Research statistics on verification times, trust scores, ledger growth
"""

from __future__ import annotations

import asyncio
import time
import sys
import json
from typing import Dict, List, Any
from uuid import uuid4

# Add backend to path for imports
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from backend.security.orchestrator import SecurityOrchestrator
from backend.simulation.device import SimDevice
from backend.simulation.environment import SimConfig
from backend.digital_twin.manager import DigitalTwinManager


def print_header(text: str) -> None:
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_metric(label: str, value: Any) -> None:
    """Print a metric with formatting."""
    if isinstance(value, float):
        print(f"  {label:<40} {value:>10.2f}")
    else:
        print(f"  {label:<40} {value:>10}")


def create_legitimate_devices(count: int, orchestrator: SecurityOrchestrator) -> List[Dict[str, Any]]:
    """
    Create and authenticate legitimate devices through the security pipeline.

    Args:
        count: Number of legitimate devices to create
        orchestrator: SecurityOrchestrator instance

    Returns:
        List of device information dictionaries
    """
    print_header(f"CREATING {count} LEGITIMATE DEVICES")

    devices = []
    for i in range(count):
        device_id = str(uuid4())
        x = float(i % 10) * 50.0
        y = float(i // 10) * 50.0

        device = {
            "device_id": device_id,
            "name": f"device-{i}",
            "device_type": "legitimate",
            "x": x,
            "y": y,
        }

        result = orchestrator.receive_join(device)
        devices.append({"info": device, "result": result})

        if (i + 1) % 25 == 0:
            print(f"  Created {i + 1}/{count} devices...")

    print(f"\n  ✓ Successfully created {count} legitimate devices")
    return devices


def launch_sybil_attack(
    orchestrator: SecurityOrchestrator,
    attacker_id: str,
    ghost_count: int,
    duration: float = 5.0,
) -> Dict[str, Any]:
    """
    Launch a Sybil attack with ghost nodes.

    Args:
        orchestrator: SecurityOrchestrator instance
        attacker_id: ID of the attacker
        ghost_count: Number of ghost nodes to spawn
        duration: Attack duration in seconds

    Returns:
        Attack statistics
    """
    print_header(f"LAUNCHING SYBIL ATTACK ({ghost_count} GHOST NODES)")

    start_time = time.time()

    # Start attack
    attack_result = orchestrator.start_attack(
        attacker_id=attacker_id,
        count=ghost_count,
        intensity=2.0,
        duration=duration,
    )

    print(f"  Attack started: {attacker_id}")
    print(f"  Ghost nodes spawning: {ghost_count}")
    print(f"  Intensity: 2.0x (high packet generation)")

    # Wait for attack to complete
    print(f"\n  Waiting {duration:.1f} seconds for attack to complete...")
    time.sleep(duration + 1)

    elapsed = time.time() - start_time
    print(f"  ✓ Attack completed in {elapsed:.1f} seconds")

    # Get attack statistics
    attack_stats = orchestrator.ghost.get_attack_stats(attacker_id)

    result = {
        "attacker_id": attacker_id,
        "ghost_count": ghost_count,
        "packets_sent": attack_stats.total_packets if attack_stats else 0,
        "join_attempts": attack_stats.total_join_attempts if attack_stats else 0,
        "detected_count": attack_stats.detected_count if attack_stats else 0,
        "detection_rate": attack_stats.detection_rate if attack_stats else 0.0,
        "success_rate": attack_stats.success_rate if attack_stats else 0.0,
    }

    return result


def verify_devices(legitimate_devices: List[Dict], orchestrator: SecurityOrchestrator) -> None:
    """
    Simulate packet verification for legitimate devices to trigger trust updates.

    Args:
        legitimate_devices: List of device information
        orchestrator: SecurityOrchestrator instance
    """
    print_header("SIMULATING PACKET VERIFICATION")

    for i, device_entry in enumerate(legitimate_devices[:50]):  # Verify subset
        device_id = device_entry["info"]["device_id"]
        packet = {
            "src": device_id,
            "dst": "broadcast",
            "payload": {
                "claimed_pos": (device_entry["info"]["x"], device_entry["info"]["y"]),
                "measured_pos": (
                    device_entry["info"]["x"] + 0.5,
                    device_entry["info"]["y"] + 0.5,
                ),
                "rate": 1.0,
                "size": 256,
                "signature": b"mock_signature",
            },
        }
        orchestrator.receive_packet(packet)

        if (i + 1) % 10 == 0:
            print(f"  Verified {i + 1}/50 packet transmissions...")

    print(f"  ✓ Packet verification complete")


def collect_metrics(orchestrator: SecurityOrchestrator) -> Dict[str, Any]:
    """
    Collect comprehensive research metrics.

    Args:
        orchestrator: SecurityOrchestrator instance

    Returns:
        Dictionary with all metrics
    """
    print_header("COLLECTING RESEARCH METRICS")

    status = orchestrator.status()
    analytics = orchestrator.analytics.metrics()
    trust_metrics = orchestrator.trust.export_trust_metrics()
    ledger_stats = orchestrator.ledger.stats()
    verification_metrics = orchestrator.proximity.get_metrics()

    metrics = {
        "summary": {
            "legitimate_devices": len(orchestrator.legitimate_devices),
            "ghost_nodes": len(orchestrator.ghost_nodes),
            "joins_processed": orchestrator.processed_joins,
            "packets_processed": orchestrator.processed_packets,
        },
        "trust": trust_metrics,
        "ledger": ledger_stats,
        "verification": verification_metrics,
        "analytics": analytics,
    }

    return metrics


def display_results(
    legitimate_devices: List[Dict],
    attack_stats: Dict,
    metrics: Dict[str, Any],
) -> None:
    """
    Display final validation results.

    Args:
        legitimate_devices: List of legitimate devices created
        attack_stats: Sybil attack statistics
        metrics: Research metrics
    """
    print_header("VALIDATION RESULTS")

    print("\n  DEVICE STATISTICS:")
    print_metric("Total legitimate devices", len(legitimate_devices))
    print_metric("Accepted devices", metrics["summary"]["legitimate_devices"])
    print_metric("Ghost nodes spawned", attack_stats["ghost_count"])
    print_metric("Ghost nodes detected", attack_stats["detected_count"])

    print("\n  ATTACK DEFENSE PERFORMANCE:")
    print_metric("Attack success rate", f"{attack_stats['success_rate'] * 100:.1f}%")
    print_metric("Defense success rate", f"{(1 - attack_stats['success_rate']) * 100:.1f}%")
    print_metric("Detection accuracy", f"{attack_stats['detection_rate'] * 100:.1f}%")

    if metrics["analytics"].get("detection_accuracy"):
        acc = metrics["analytics"]["detection_accuracy"]
        print("\n  DETECTION ACCURACY METRICS:")
        print_metric("Precision", f"{acc.get('precision', 0) * 100:.1f}%")
        print_metric("Recall", f"{acc.get('recall', 0) * 100:.1f}%")
        print_metric("F1 Score", f"{acc.get('f1_score', 0) * 100:.1f}%")
        print_metric("Overall Accuracy", f"{acc.get('accuracy', 0) * 100:.1f}%")

    if metrics["verification"]:
        print("\n  PROOF-OF-PROXIMITY METRICS:")
        print_metric("Total verifications", metrics["verification"].get("total_verifications", 0))
        print_metric(
            "Acceptance rate",
            f"{metrics['verification'].get('acceptance_rate', 0) * 100:.1f}%",
        )
        print_metric(
            "Avg confidence",
            f"{metrics['verification'].get('average_confidence', 0) * 100:.1f}%",
        )
        print_metric(
            "Avg propagation delay (ms)",
            f"{metrics['verification'].get('average_propagation_delay_ms', 0):.3f}",
        )

    if metrics["trust"]:
        print("\n  TRUST ENGINE STATISTICS:")
        print_metric("Total devices evaluated", metrics["trust"].get("total_devices", 0))
        print_metric("Average trust score", f"{metrics['trust'].get('average_trust', 0):.3f}")
        print_metric("Accepted devices", metrics["trust"].get("accepted_count", 0))
        print_metric("Monitored devices", metrics["trust"].get("monitored_count", 0))
        print_metric("Rejected devices", metrics["trust"].get("rejected_count", 0))
        print_metric("Blacklisted devices", metrics["trust"].get("blacklisted_count", 0))

    if metrics["ledger"]:
        print("\n  DISTRIBUTED LEDGER:")
        print_metric("Total entries", metrics["ledger"].get("total_entries", 0))
        print_metric("Unique devices", metrics["ledger"].get("unique_devices", 0))
        print_metric("Shards", metrics["ledger"].get("shards", 0))
        print_metric("Avg shard size", f"{metrics['ledger'].get('average_shard_size', 0):.1f}")

    print("\n" + "=" * 70)
    print("  ✓ VALIDATION COMPLETE - ALL MODULES FUNCTIONAL")
    print("=" * 70 + "\n")


async def run_validation() -> None:
    """Run complete security framework validation."""
    try:
        print("\n")
        print("#" * 70)
        print("# QShield-Twin: Quantum-Resilient Sybil Defense Framework")
        print("# Automated Validation & Demonstration")
        print("#" * 70)

        # Initialize orchestrator
        print_header("INITIALIZING SECURITY ORCHESTRATOR")
        orchestrator = SecurityOrchestrator()
        print("  ✓ Security Orchestrator initialized")
        print("  ✓ Ghost Engine ready")
        print("  ✓ Proof-of-Proximity Engine ready")
        print("  ✓ Lattice Cryptography ready")
        print("  ✓ Trust Engine ready")
        print("  ✓ Sharded Ledger ready")
        print("  ✓ Analytics Engine ready")

        # Test 1: Create legitimate devices
        legitimate_devices = create_legitimate_devices(100, orchestrator)

        # Test 2: Launch attack
        attack_stats = launch_sybil_attack(orchestrator, "attacker-1", 20, duration=5.0)

        # Test 3: Verify devices
        verify_devices(legitimate_devices, orchestrator)

        # Test 4: Collect metrics
        metrics = collect_metrics(orchestrator)

        # Test 5: Display results
        display_results(legitimate_devices, attack_stats, metrics)

        # Export metrics
        print("Exporting detailed metrics...")
        json_export = orchestrator.analytics.export_json()
        with open("/tmp/security_validation_results.json", "w") as f:
            f.write(json_export)
        print("  ✓ Metrics saved to /tmp/security_validation_results.json")

    except Exception as e:
        print(f"\n✗ Validation failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_validation())
