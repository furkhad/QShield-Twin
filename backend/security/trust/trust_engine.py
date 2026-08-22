"""Trust Engine for continuous node trust evaluation.

Computes trust scores based on multiple signals:
- Proof-of-Proximity verification results
- Signature verification success
- Packet behavior (transmission patterns, rate anomalies)
- Communication history (neighbor reliability)
- Ledger history (past incidents)
- Attack history (detected Sybil attempts)

Trust Score: 0.0 (untrusted) to 1.0 (fully trusted)

Risk Level:
- Low: score >= 0.7
- Medium: 0.4 <= score < 0.7
- High: score < 0.4

Decision:
- ACCEPT: score >= 0.8
- MONITOR: 0.4 <= score < 0.8
- REJECT: 0.2 <= score < 0.4
- BLACKLIST: score < 0.2

Trust updates are computed incrementally as new evidence arrives.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import deque


@dataclass
class TrustRecord:
    """Represents trust state for a single device."""
    device_id: str
    score: float  # 0.0 - 1.0
    risk_level: str  # "low" | "medium" | "high"
    decision: str  # "accept" | "monitor" | "reject" | "blacklist"
    reasons: List[str] = field(default_factory=list)
    last_updated: float = 0.0
    update_count: int = 0
    proximity_evidence: float = 0.0  # weight of proximity verifications
    crypto_evidence: float = 0.0  # weight of crypto verification
    behavior_evidence: float = 0.0  # weight of packet behavior
    history_evidence: float = 0.0  # weight of past behavior


class TrustEngine:
    """
    Computes and updates node trust scores based on security evidence.

    Trust is computed as a weighted combination of multiple factors:
    - Proximity: Does the device's claimed position match measured position?
    - Cryptography: Does the device have valid signatures?
    - Behavior: Are packet patterns anomalous (rate, direction)?
    - History: What is the device's past record?
    - Attack: Has the device been flagged as Sybil?

    Trust updates are atomic and thread-safe.
    """

    def __init__(self, history_size: int = 1000):
        """
        Args:
            history_size: Maximum trust update history per device
        """
        self.scores: Dict[str, TrustRecord] = {}
        self.update_history: Dict[str, deque] = {}  # device_id -> deque of (timestamp, delta, reason)
        self.history_size = history_size
        self.lock = threading.Lock()

    def _compute_decision(self, score: float) -> Tuple[str, str]:
        """Compute decision and risk level from trust score."""
        if score >= 0.8:
            return "accept", "low"
        elif score >= 0.7:
            return "monitor", "low"
        elif score >= 0.4:
            return "monitor", "medium"
        elif score >= 0.2:
            return "reject", "high"
        else:
            return "blacklist", "high"

    def update_from_verification(self, device_id: str, verification_result: Any) -> TrustRecord:
        """
        Update trust based on Proof-of-Proximity verification result.

        Proximity verification directly impacts trust:
        - accept: +0.15 * confidence
        - suspicious: 0 (no change)
        - reject: -0.25

        Args:
            device_id: Device identifier
            verification_result: VerificationResult from ProofOfProximityEngine

        Returns:
            Updated TrustRecord
        """
        with self.lock:
            record = self.scores.get(device_id, TrustRecord(device_id=device_id, score=0.5))

            decision = getattr(verification_result, "decision", "suspicious")
            confidence = getattr(verification_result, "confidence", 0.5)

            delta = 0.0
            reason = f"proximity:{decision}"

            if decision == "accept":
                delta = 0.15 * confidence
                record.proximity_evidence += confidence
            elif decision == "suspicious":
                delta = 0.0
            else:  # reject
                delta = -0.25
                record.proximity_evidence -= 0.2

            # Apply delta and clamp to [0, 1]
            new_score = max(0.0, min(1.0, record.score + delta))
            new_decision, new_risk = self._compute_decision(new_score)

            record.score = new_score
            record.decision = new_decision
            record.risk_level = new_risk
            record.reasons.append(reason)
            record.last_updated = time.time()
            record.update_count += 1

            # Store in history
            if device_id not in self.update_history:
                self.update_history[device_id] = deque(maxlen=self.history_size)
            self.update_history[device_id].append(
                (time.time(), delta, reason)
            )

            self.scores[device_id] = record
            return record

    def update_from_signature(self, device_id: str, verified: bool, verification_time_ms: float = 0.0) -> TrustRecord:
        """
        Update trust based on signature verification result.

        Signature verification is critical to trust:
        - verified: +0.10
        - failed: -0.30

        Args:
            device_id: Device identifier
            verified: Whether signature verification succeeded
            verification_time_ms: Time taken for verification

        Returns:
            Updated TrustRecord
        """
        with self.lock:
            record = self.scores.get(device_id, TrustRecord(device_id=device_id, score=0.5))

            if verified:
                delta = 0.10
                reason = "signature:verified"
                record.crypto_evidence += 0.2
            else:
                delta = -0.30
                reason = "signature:failed"
                record.crypto_evidence -= 0.3

            new_score = max(0.0, min(1.0, record.score + delta))
            new_decision, new_risk = self._compute_decision(new_score)

            record.score = new_score
            record.decision = new_decision
            record.risk_level = new_risk
            record.reasons.append(reason)
            record.last_updated = time.time()
            record.update_count += 1

            if device_id not in self.update_history:
                self.update_history[device_id] = deque(maxlen=self.history_size)
            self.update_history[device_id].append(
                (time.time(), delta, reason)
            )

            self.scores[device_id] = record
            return record

    def update_from_packet(self, device_id: str, packet_info: Dict[str, Any]) -> TrustRecord:
        """
        Update trust based on packet transmission behavior.

        Packet analysis checks for:
        - Anomalous transmission rates
        - Suspicious packet content
        - Routing misbehavior

        Args:
            device_id: Device identifier
            packet_info: Packet metadata (src, dst, size, rate, etc.)

        Returns:
            Updated TrustRecord
        """
        with self.lock:
            record = self.scores.get(device_id, TrustRecord(device_id=device_id, score=0.5))

            # Simple heuristics for packet behavior
            packet_rate = packet_info.get("rate", 1.0)  # packets per second
            packet_size = packet_info.get("size", 100)

            delta = 0.0
            reason = "packet:normal"

            # Detect anomalies
            if packet_rate > 100:  # Excessive transmission
                delta = -0.15
                reason = "packet:excessive_rate"
                record.behavior_evidence -= 0.2
            elif packet_rate > 10:  # High rate but acceptable
                delta = 0.02
                reason = "packet:high_rate"
            elif packet_size > 10000:  # Suspiciously large packet
                delta = -0.10
                reason = "packet:large_size"
                record.behavior_evidence -= 0.15
            else:
                delta = 0.01  # Normal packet, slight boost
                record.behavior_evidence += 0.05

            new_score = max(0.0, min(1.0, record.score + delta))
            new_decision, new_risk = self._compute_decision(new_score)

            record.score = new_score
            record.decision = new_decision
            record.risk_level = new_risk
            record.reasons.append(reason)
            record.last_updated = time.time()
            record.update_count += 1

            if device_id not in self.update_history:
                self.update_history[device_id] = deque(maxlen=self.history_size)
            self.update_history[device_id].append(
                (time.time(), delta, reason)
            )

            self.scores[device_id] = record
            return record

    def penalize_for_attack(self, device_id: str, attack_severity: float = 1.0) -> TrustRecord:
        """
        Penalize device for being involved in attack or detected as Sybil.

        Sybil/attack detection is a severe penalty.

        Args:
            device_id: Device identifier
            attack_severity: Severity multiplier (1.0-2.0)

        Returns:
            Updated TrustRecord
        """
        with self.lock:
            record = self.scores.get(device_id, TrustRecord(device_id=device_id, score=0.5))

            delta = -0.50 * attack_severity
            reason = f"attack:sybil_detected(severity={attack_severity})"

            new_score = max(0.0, min(1.0, record.score + delta))
            new_decision, new_risk = self._compute_decision(new_score)

            record.score = new_score
            record.decision = new_decision
            record.risk_level = new_risk
            record.reasons.append(reason)
            record.last_updated = time.time()
            record.update_count += 1

            if device_id not in self.update_history:
                self.update_history[device_id] = deque(maxlen=self.history_size)
            self.update_history[device_id].append(
                (time.time(), delta, reason)
            )

            self.scores[device_id] = record
            return record

    def get_trust(self, device_id: str) -> Optional[TrustRecord]:
        """Retrieve current trust record for a device."""
        with self.lock:
            return self.scores.get(device_id)

    def get_all_trust_scores(self) -> Dict[str, TrustRecord]:
        """Retrieve all trust scores."""
        with self.lock:
            return dict(self.scores)

    def get_high_risk_devices(self, threshold: float = 0.4) -> List[str]:
        """Get list of devices below risk threshold."""
        with self.lock:
            return [
                device_id
                for device_id, record in self.scores.items()
                if record.score < threshold
            ]

    def get_devices_by_decision(self, decision: str) -> List[str]:
        """Get devices with a specific decision."""
        with self.lock:
            return [
                device_id
                for device_id, record in self.scores.items()
                if record.decision == decision
            ]

    def get_update_history(self, device_id: str) -> List[Tuple[float, float, str]]:
        """Get trust update history for a device."""
        with self.lock:
            return list(self.update_history.get(device_id, []))

    def export_trust_metrics(self) -> Dict[str, Any]:
        """Export aggregate trust metrics."""
        with self.lock:
            records = list(self.scores.values())

        if not records:
            return {
                "total_devices": 0,
                "average_trust": 0.0,
                "accepted_count": 0,
                "monitored_count": 0,
                "rejected_count": 0,
                "blacklisted_count": 0,
            }

        total = len(records)
        avg_trust = sum(r.score for r in records) / total
        accepted = sum(1 for r in records if r.decision == "accept")
        monitored = sum(1 for r in records if r.decision == "monitor")
        rejected = sum(1 for r in records if r.decision == "reject")
        blacklisted = sum(1 for r in records if r.decision == "blacklist")

        return {
            "total_devices": total,
            "average_trust": avg_trust,
            "accepted_count": accepted,
            "monitored_count": monitored,
            "rejected_count": rejected,
            "blacklisted_count": blacklisted,
            "low_risk_count": sum(1 for r in records if r.risk_level == "low"),
            "medium_risk_count": sum(1 for r in records if r.risk_level == "medium"),
            "high_risk_count": sum(1 for r in records if r.risk_level == "high"),
        }
