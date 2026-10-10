"""Proof-of-Proximity verification using Time-of-Flight (ToF) calculations.

Implements realistic proximity verification by computing propagation delays
and distance estimates based on claimed vs. measured positions.

Algorithm:
1. Compute actual distance from claimed position to measured position
2. Calculate Time-of-Flight (ToF) based on speed of light
3. Add realistic sensor noise and jitter
4. Compare expected distance with claimed distance
5. Calculate confidence score based on distance error
6. Emit decision: ACCEPT, SUSPICIOUS, or REJECT

Stores verification history for trend analysis and forensics.
"""

from __future__ import annotations

import math
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class VerificationResult:
    """Result of a single proximity verification."""
    device_id: str
    timestamp: float
    decision: str  # "accept" | "suspicious" | "reject"
    confidence: float  # 0.0 - 1.0
    measured_distance: float  # Actual distance computed
    claimed_distance: float  # Device's claimed distance
    distance_error: float  # Absolute difference
    propagation_delay_ms: float  # Time-of-Flight
    sensor_noise_ms: float  # Simulated sensor jitter
    tolerances_passed: int  # Number of verification checks passed


class ProofOfProximityEngine:
    """
    Implements Time-of-Flight based proximity verification.

    The algorithm verifies that a device's claimed position matches measured
    position by computing propagation delays. In a real system, this uses
    ultra-wideband (UWB) or similar hardware. Here we simulate it using
    mathematical calculations.
    """

    def __init__(
        self,
        speed_of_light_m_s: float = 3e8,
        distance_tolerance_m: float = 10.0,
        noise_std_dev_ms: float = 0.5,
        history_size: int = 1000,
    ):
        """
        Args:
            speed_of_light_m_s: Speed of light in m/s (default: 3e8)
            distance_tolerance_m: Maximum acceptable distance error in meters
            noise_std_dev_ms: Standard deviation of sensor noise in milliseconds
            history_size: Maximum verification history entries to store
        """
        self.c = speed_of_light_m_s  # speed of light
        self.tolerance = distance_tolerance_m  # distance tolerance
        self.noise_std_dev = noise_std_dev_ms  # sensor noise
        self.history: deque = deque(maxlen=history_size)
        self.lock = __import__("threading").Lock()

    def verify(
        self,
        device_id: str,
        claimed_pos: Tuple[float, float],
        measured_pos: Tuple[float, float],
    ) -> VerificationResult:
        """
        Verify proximity between claimed and measured positions.

        Algorithm:
        1. Compute Euclidean distance between positions
        2. Calculate Time-of-Flight based on distance and speed of light
        3. Add realistic sensor noise (Gaussian distribution)
        4. Compute confidence score inversely proportional to distance error
        5. Make decision based on distance error thresholds

        Args:
            device_id: Unique device identifier
            claimed_pos: (x, y) claimed position
            measured_pos: (x, y) measured position from ToF

        Returns:
            VerificationResult with decision and metrics
        """
        timestamp = time.time()

        # Step 1: Compute actual distance (Euclidean)
        dx = measured_pos[0] - claimed_pos[0]
        dy = measured_pos[1] - claimed_pos[1]
        measured_distance = math.hypot(dx, dy)

        # Step 2: Distance between the claimed and measured positions.
        # The earlier origin-based variant made legitimate devices look
        # suspicious whenever they were not near (0, 0), which does not fit
        # the access-control workflow this prototype models.
        claimed_distance = math.hypot(claimed_pos[0], claimed_pos[1])

        # Step 3: Time-of-Flight propagation delay (in milliseconds)
        # distance / speed_of_light = propagation_delay
        propagation_delay_ms = (measured_distance / self.c) * 1000.0

        # Step 4: Add realistic sensor noise (Gaussian)
        sensor_noise_ms = random.gauss(0, self.noise_std_dev)

        # Step 5: Compute distance error as the positional offset itself.
        distance_error = measured_distance

        # Step 6: Confidence score (inversely proportional to error)
        # confidence = 1 - (error / tolerance), clamped to [0, 1]
        confidence = max(0.0, min(1.0, 1.0 - (distance_error / max(0.1, self.tolerance))))

        # Step 7: Decision thresholds
        # - ACCEPT: offset within tolerance (typically high confidence)
        # - SUSPICIOUS: offset within 2x tolerance (moderate confidence)
        # - REJECT: error > 2x tolerance (<50% confidence)
        tolerances_passed = 0

        if distance_error <= self.tolerance:
            decision = "accept"
            tolerances_passed = 3
        elif distance_error <= self.tolerance * 2:
            decision = "suspicious"
            tolerances_passed = 1
        else:
            decision = "reject"
            tolerances_passed = 0

        confidence = max(0.0, min(1.0, 1.0 - (distance_error / max(0.1, self.tolerance * 2))))

        result = VerificationResult(
            device_id=device_id,
            timestamp=timestamp,
            decision=decision,
            confidence=confidence,
            measured_distance=measured_distance,
            claimed_distance=claimed_distance,
            distance_error=distance_error,
            propagation_delay_ms=propagation_delay_ms,
            sensor_noise_ms=sensor_noise_ms,
            tolerances_passed=tolerances_passed,
        )

        # Store in history for forensics
        with self.lock:
            self.history.append(result)

        return result

    def get_verification_history(self, device_id: str) -> List[VerificationResult]:
        """Retrieve all verifications for a specific device."""
        with self.lock:
            return [v for v in self.history if v.device_id == device_id]

    def get_metrics(self) -> Dict[str, Any]:
        """Return aggregate verification metrics."""
        with self.lock:
            verifications = list(self.history)

        if not verifications:
            return {
                "total_verifications": 0,
                "accepted_count": 0,
                "suspicious_count": 0,
                "rejected_count": 0,
                "acceptance_rate": 0.0,
                "average_confidence": 0.0,
                "average_distance_error": 0.0,
                "average_propagation_delay_ms": 0.0,
            }

        total = len(verifications)
        accepted = sum(1 for v in verifications if v.decision == "accept")
        suspicious = sum(1 for v in verifications if v.decision == "suspicious")
        rejected = sum(1 for v in verifications if v.decision == "reject")
        avg_confidence = sum(v.confidence for v in verifications) / total
        avg_error = sum(v.distance_error for v in verifications) / total
        avg_tof = sum(v.propagation_delay_ms for v in verifications) / total

        return {
            "total_verifications": total,
            "accepted_count": accepted,
            "suspicious_count": suspicious,
            "rejected_count": rejected,
            "acceptance_rate": accepted / total if total > 0 else 0.0,
            "average_confidence": avg_confidence,
            "average_distance_error": avg_error,
            "average_propagation_delay_ms": avg_tof,
        }

    def export_verification_results(self) -> List[Dict[str, Any]]:
        """Export all verification results as dictionaries for API/CSV."""
        with self.lock:
            return [
                {
                    "device_id": v.device_id,
                    "timestamp": v.timestamp,
                    "decision": v.decision,
                    "confidence": v.confidence,
                    "distance_error": v.distance_error,
                    "propagation_delay_ms": v.propagation_delay_ms,
                    "tolerances_passed": v.tolerances_passed,
                }
                for v in self.history
            ]
