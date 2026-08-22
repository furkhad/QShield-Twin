"""Analytics engine for research metrics collection and export.

Tracks security framework performance:
- Detection accuracy (true positives, false positives, false negatives)
- Precision, Recall, F1 Score
- Average verification time
- Average trust scores
- Attack success/defense success rates
- Ledger growth
- PQC operation timings

Exports as JSON, CSV, or raw metrics dictionary.
"""

from __future__ import annotations

import csv
import io
import json
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any
from collections import defaultdict


@dataclass
class DetectionResult:
    """Record of a single detection event."""
    timestamp: float
    device_id: str
    is_ghost: bool  # True if device is actually a ghost node
    detected_as_ghost: bool  # True if flagged as ghost
    verification_time_ms: float
    confidence: float


class AnalyticsEngine:
    """
    Collects comprehensive research metrics on the Sybil defense framework.

    Metrics tracked:
    - Detection accuracy (TP, FP, FN, TN)
    - Precision = TP / (TP + FP)
    - Recall = TP / (TP + FN)
    - F1 = 2 * (Precision * Recall) / (Precision + Recall)
    - Average verification time (ms)
    - Average trust score
    - Ledger growth (entries per time unit)
    - PQC metrics (keygen, sign, verify times)
    - Attack statistics (ghosts spawned, detected, success rate)
    """

    def __init__(self, history_size: int = 10000):
        """
        Args:
            history_size: Maximum number of detection records to store
        """
        self.detections: List[DetectionResult] = []
        self.max_history = history_size

        # Aggregate statistics
        self.stats: Dict[str, Any] = {
            "detections": 0,
            "true_positives": 0,
            "false_positives": 0,
            "true_negatives": 0,
            "false_negatives": 0,
        }

        # PQC metrics (updated by orchestrator)
        self.pqc_metrics: Dict[str, Any] = {}

        # Verification metrics
        self.verification_times_ms: List[float] = []
        self.average_confidence: float = 0.0

        # Trust metrics
        self.trust_scores_collected: List[float] = []

        # Attack statistics
        self.attacks_launched: int = 0
        self.ghosts_spawned: int = 0
        self.ghosts_detected: int = 0

        # Ledger growth
        self.ledger_entries_collected: List[tuple] = []  # (timestamp, count)

        self.lock = threading.Lock()
        self.start_time = time.time()

    def record_detection(
        self,
        device_id: str,
        is_ghost: bool,
        detected_as_ghost: bool,
        verification_time_ms: float = 0.0,
        confidence: float = 0.5,
    ) -> None:
        """
        Record a detection event.

        Args:
            device_id: Device being evaluated
            is_ghost: True if device is actually a ghost/Sybil node
            detected_as_ghost: True if system flagged it as ghost
            verification_time_ms: Time taken for verification
            confidence: Confidence in detection (0.0-1.0)
        """
        with self.lock:
            result = DetectionResult(
                timestamp=time.time(),
                device_id=device_id,
                is_ghost=is_ghost,
                detected_as_ghost=detected_as_ghost,
                verification_time_ms=verification_time_ms,
                confidence=confidence,
            )
            self.detections.append(result)
            if len(self.detections) > self.max_history:
                self.detections.pop(0)

            self.stats["detections"] += 1

            # Update confusion matrix
            if is_ghost and detected_as_ghost:
                self.stats["true_positives"] += 1
            elif is_ghost and not detected_as_ghost:
                self.stats["false_negatives"] += 1
            elif not is_ghost and detected_as_ghost:
                self.stats["false_positives"] += 1
            else:
                self.stats["true_negatives"] += 1

            # Track verification time
            self.verification_times_ms.append(verification_time_ms)

    def record_verification_time(self, device_id: str, time_ms: float) -> None:
        """Record time taken for a verification."""
        with self.lock:
            self.verification_times_ms.append(time_ms)

    def record_trust_score(self, device_id: str, score: float) -> None:
        """Record a device's trust score."""
        with self.lock:
            self.trust_scores_collected.append(score)

    def record_attack(
        self,
        attacker_id: str,
        ghosts_count: int,
        detected_count: int,
    ) -> None:
        """Record attack statistics."""
        with self.lock:
            self.attacks_launched += 1
            self.ghosts_spawned += ghosts_count
            self.ghosts_detected += detected_count

    def record_pqc_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record PQC performance metrics."""
        with self.lock:
            self.pqc_metrics = dict(metrics)

    def record_ledger_snapshot(self, entry_count: int) -> None:
        """Record ledger size at this point in time."""
        with self.lock:
            self.ledger_entries_collected.append((time.time(), entry_count))

    def metrics(self) -> Dict[str, Any]:
        """
        Compute and return comprehensive research metrics.

        Returns:
            Dictionary with precision, recall, F1, detection accuracy, etc.
        """
        with self.lock:
            tp = self.stats.get("true_positives", 0)
            fp = self.stats.get("false_positives", 0)
            fn = self.stats.get("false_negatives", 0)
            tn = self.stats.get("true_negatives", 0)

            # Precision = TP / (TP + FP)
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

            # Recall = TP / (TP + FN)
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

            # F1 = 2 * (Precision * Recall) / (Precision + Recall)
            f1 = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            # Accuracy = (TP + TN) / (TP + TN + FP + FN)
            accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

            # Average times and scores
            avg_verification_time = (
                sum(self.verification_times_ms) / len(self.verification_times_ms)
                if self.verification_times_ms
                else 0.0
            )
            avg_trust = (
                sum(self.trust_scores_collected) / len(self.trust_scores_collected)
                if self.trust_scores_collected
                else 0.0
            )

            # Attack success rate
            attack_success_rate = (
                (self.ghosts_spawned - self.ghosts_detected) / self.ghosts_spawned
                if self.ghosts_spawned > 0
                else 0.0
            )
            defense_success_rate = 1.0 - attack_success_rate

            # Ledger growth rate
            ledger_growth_rate = 0.0
            if len(self.ledger_entries_collected) >= 2:
                first_ts, first_count = self.ledger_entries_collected[0]
                last_ts, last_count = self.ledger_entries_collected[-1]
                elapsed = last_ts - first_ts
                if elapsed > 0:
                    ledger_growth_rate = (last_count - first_count) / elapsed

            return {
                "summary": {
                    "total_detections": self.stats["detections"],
                    "duration_seconds": time.time() - self.start_time,
                },
                "confusion_matrix": {
                    "true_positives": tp,
                    "false_positives": fp,
                    "true_negatives": tn,
                    "false_negatives": fn,
                },
                "detection_accuracy": {
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1_score": round(f1, 4),
                    "accuracy": round(accuracy, 4),
                },
                "performance": {
                    "average_verification_time_ms": round(avg_verification_time, 2),
                    "average_trust_score": round(avg_trust, 4),
                },
                "attack_defense": {
                    "attacks_launched": self.attacks_launched,
                    "ghosts_spawned": self.ghosts_spawned,
                    "ghosts_detected": self.ghosts_detected,
                    "attack_success_rate": round(attack_success_rate, 4),
                    "defense_success_rate": round(defense_success_rate, 4),
                },
                "ledger": {
                    "entries_collected": len(self.ledger_entries_collected),
                    "growth_rate_per_second": round(ledger_growth_rate, 2),
                },
                "pqc": self.pqc_metrics,
            }

    def export_csv(self) -> str:
        """Export detection results as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "timestamp", "device_id", "is_ghost", "detected_as_ghost",
            "verification_time_ms", "confidence"
        ])

        with self.lock:
            for detection in self.detections:
                writer.writerow([
                    detection.timestamp,
                    detection.device_id,
                    detection.is_ghost,
                    detection.detected_as_ghost,
                    detection.verification_time_ms,
                    detection.confidence,
                ])

        return output.getvalue()

    def export_json(self) -> str:
        """Export metrics as JSON."""
        with self.lock:
            data = {
                "metrics": self.metrics(),
                "detections": [asdict(d) for d in self.detections],
            }
        return json.dumps(data, indent=2)

    def export_metrics_only_json(self) -> str:
        """Export only the computed metrics as JSON."""
        return json.dumps(self.metrics(), indent=2)
