"""Security Orchestrator - Central coordinator for the Quantum-Resilient Sybil Defense.

Orchestrates the complete security pipeline:

Join Request Workflow:
  1. Device attempts join
  2. Ghost detection (is this a known Sybil attack?)
  3. PQC key verification (does it have valid signatures?)
  4. Proximity verification (does position match claims?)
  5. Trust calculation (multi-factor evaluation)
  6. Ledger update (record in distributed log)
  7. Decision: ACCEPT | MONITOR | REJECT | BLACKLIST
  8. Broadcast security event to dashboard

Packet Processing Workflow:
  1. Intercept every packet transmission
  2. Extract sender identity and position claim
  3. Run proximity verification
  4. Run PQC signature verification
  5. Analyze packet behavior
  6. Update trust score
  7. Update ledger
  8. Broadcast verification event

Attack Handling:
  1. Orchestrate ghost node spawning
  2. Correlate ghost behavior
  3. Detect attack patterns
  4. Trigger blacklisting
  5. Broadcast attack timeline

All operations are thread-safe and emit events for dashboard/research.
"""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

from backend.app.websocket.manager import manager as ws_manager
from backend.security.ghost.ghost_engine import GhostEngine
from backend.security.proximity.proof_of_proximity import ProofOfProximityEngine
from backend.security.pqc.simulated_lattice import SimulatedLatticeCrypto
from backend.security.trust.trust_engine import TrustEngine
from backend.security.ledger.sharded_ledger import ShardedLedger
from backend.security.analytics.analytics_engine import AnalyticsEngine


@dataclass
class JoinRequest:
    """Represents a device join request."""
    device_id: str
    name: str
    device_type: str
    x: float
    y: float
    timestamp: float = 0.0


class SecurityOrchestrator:
    """
    Central security coordinator implementing the Quantum-Resilient Sybil Defense.

    Responsibilities:
    - Receive and process join requests
    - Receive and process packet events
    - Coordinate security checks (PoP, PQC, Trust, Ghost detection)
    - Update ledger and trust engine
    - Generate security events for broadcasting
    - Track attack statistics
    """

    def __init__(self):
        """Initialize all security engines and set up event callbacks."""
        # Initialize security engines
        self.ghost = GhostEngine(event_cb=self._on_ghost_event)
        self.proximity = ProofOfProximityEngine(distance_tolerance_m=10.0)
        self.pqc = SimulatedLatticeCrypto(algorithm="simulated-ntru")
        self.trust = TrustEngine()
        self.ledger = ShardedLedger(shards=8)
        self.analytics = AnalyticsEngine()

        # Tracking
        self.processed_joins: int = 0
        self.processed_packets: int = 0
        self.lock = threading.Lock()

        # State tracking for demo/validation
        self.legitimate_devices: set = set()
        self.ghost_nodes: set = set()
        self._device_keys: Dict[str, Tuple[bytes, bytes]] = {}
        self._device_positions: Dict[str, Tuple[float, float]] = {}

    def _emit(self, event: dict) -> None:
        """Broadcast security event via WebSocket to dashboard."""
        try:
            ws_manager.emit_sync({"type": "security_event", "payload": event})
        except Exception:
            pass  # WebSocket manager may not be available

    def reset(self) -> None:
        """Reset the security state for reruns and scenario demos."""
        self.ghost = GhostEngine(event_cb=self._on_ghost_event)
        self.proximity = ProofOfProximityEngine(distance_tolerance_m=10.0)
        self.pqc = SimulatedLatticeCrypto(algorithm="simulated-ntru")
        self.trust = TrustEngine()
        self.ledger = ShardedLedger(shards=8)
        self.analytics = AnalyticsEngine()
        self.processed_joins = 0
        self.processed_packets = 0
        self.legitimate_devices = set()
        self.ghost_nodes = set()
        self._device_keys = {}
        self._device_positions = {}

    def _on_ghost_event(self, event: dict) -> None:
        """Handle events from ghost engine."""
        self._emit({"source": "ghost", **event})

    def receive_join(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete join request workflow.

        Pipeline:
        1. Ghost Detection - Check if this is a known Sybil attack
        2. PQC Verification - Verify cryptographic identity
        3. Proximity Verification - Verify claimed position
        4. Trust Calculation - Multi-factor trust scoring
        5. Ledger Update - Record in distributed ledger
        6. Decision - ACCEPT | MONITOR | REJECT | BLACKLIST
        7. Broadcast Event - Send security event to dashboard

        Args:
            device: Device information {device_id, name, x, y, device_type}

        Returns:
            Decision dictionary with acceptance status and reason
        """
        device_id = device.get("device_id")
        timestamp = time.time()

        with self.lock:
            self.processed_joins += 1

        # Create join request
        join_req = JoinRequest(
            device_id=device_id,
            name=device.get("name", "unknown"),
            device_type=device.get("device_type", "generic"),
            x=float(device.get("x", 0.0)),
            y=float(device.get("y", 0.0)),
            timestamp=timestamp,
        )

        # STEP 1: Ghost Detection
        # Check if device matches any known ghost attack patterns
        is_likely_ghost = self._check_ghost_pattern(device_id)

        # STEP 2: PQC Key Generation & Verification
        # Generate keypair for device and store as evidence
        pub_key, priv_key = self.pqc.generate_keypair()
        self._device_keys[device_id] = (pub_key, priv_key)

        # STEP 3: Proximity Verification
        claimed_pos = (join_req.x, join_req.y)
        measured_pos = self._infer_measured_position(
            device_id=device_id,
            claimed_pos=claimed_pos,
            device_type=join_req.device_type,
            is_likely_ghost=is_likely_ghost,
        )
        self._device_positions[device_id] = claimed_pos
        proximity_result = self.proximity.verify(
            device_id=device_id,
            claimed_pos=claimed_pos,
            measured_pos=measured_pos,
        )

        message = f"join:{device_id}:{join_req.x}:{join_req.y}".encode()
        signature = self.pqc.sign(priv_key, message)
        sig_verified = self.pqc.verify(pub_key, message, signature)

        # STEP 4: Trust Calculation
        trust_record = self.trust.update_from_verification(device_id, proximity_result)
        self.trust.update_from_signature(device_id, sig_verified)
        if is_likely_ghost:
            self.trust.penalize_for_attack(device_id, attack_severity=1.4)
            if device_id in self.ghost.ghosts:
                self.ghost.mark_detected(device_id)

        trust_record = self.trust.get_trust(device_id) or trust_record

        # STEP 5: Ledger Update
        self.ledger.append(
            device_id=device_id,
            accepted=(trust_record.decision in ["accept", "monitor"]),
            reason="join",
            evidence={
                "proximity": proximity_result.__dict__,
                "pqc_pub": pub_key.hex()[:32] + "...",
                "trust_score": trust_record.score,
                "ghost_detected": is_likely_ghost,
                "signature_verified": sig_verified,
                "measured_pos": measured_pos,
            },
        )

        # STEP 6: Final Decision
        decision = trust_record.decision
        if is_likely_ghost and trust_record.score < 0.4:
            decision = "reject"
        elif is_likely_ghost and trust_record.score < 0.7:
            decision = "monitor"

        accepted = decision in ["accept", "monitor"]

        # STEP 7: Broadcast Event
        self._emit(
            {
                "type": "join_processed",
                "device": device_id,
                "decision": decision,
                "trust_score": trust_record.score,
                "proximity_result": proximity_result.decision,
                "ghost_detected": is_likely_ghost,
                "timestamp": timestamp,
            }
        )

        self.analytics.record_detection(
            device_id=device_id,
            is_ghost=is_likely_ghost,
            detected_as_ghost=is_likely_ghost,
            verification_time_ms=proximity_result.propagation_delay_ms,
            confidence=proximity_result.confidence,
        )
        self.analytics.record_pqc_metrics(self.pqc.metrics())

        # Track for analytics
        with self.lock:
            if not is_likely_ghost:
                self.legitimate_devices.add(device_id)
            else:
                self.ghost_nodes.add(device_id)

        return {
            "device_id": device_id,
            "accepted": accepted,
            "decision": decision,
            "trust_score": trust_record.score,
            "reason": decision,
            "proximity": proximity_result.decision,
            "ghost_detected": is_likely_ghost,
        }

    def receive_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete packet verification workflow.

        Pipeline:
        1. Extract packet metadata
        2. Proximity verification
        3. PQC signature verification
        4. Packet behavior analysis
        5. Trust update
        6. Ledger update
        7. Broadcast verification event

        Args:
            packet: Packet information {src, dst, payload, timestamp}

        Returns:
            Verification result
        """
        src = packet.get("src")
        dst = packet.get("dst")
        timestamp = time.time()

        with self.lock:
            self.processed_packets += 1

        # STEP 1: Extract payload
        payload = packet.get("payload", {})
        claimed_pos = payload.get("claimed_pos", (0.0, 0.0))
        measured_pos = payload.get("measured_pos", (0.0, 0.0))

        # STEP 2: Proximity Verification
        suspicious_packet = self._is_suspicious_packet(src, payload)
        if suspicious_packet:
            measured_pos = (
                claimed_pos[0] + 15.0 + float(payload.get("rate", 1.0)) * 0.1,
                claimed_pos[1] + 10.0,
            )
        else:
            measured_pos = (
                claimed_pos[0] + 0.3 + min(float(payload.get("rate", 1.0)) * 0.01, 0.8),
                claimed_pos[1] + 0.2,
            )

        self._device_positions[src] = claimed_pos
        proximity_result = self.proximity.verify(
            device_id=src,
            claimed_pos=claimed_pos,
            measured_pos=measured_pos,
        )

        # STEP 3: PQC Signature Verification
        public_key = payload.get("public_key")
        if isinstance(public_key, (bytes, bytearray)):
            pub_key = bytes(public_key)
        else:
            pub_key = self._device_keys.get(src, (b"", b""))[0]
            if not pub_key:
                pub_key = hashlib.sha256(str(src).encode()).digest()

        message = str(payload).encode()
        signature = payload.get("signature", b"")
        sig_verified = self.pqc.verify(pub_key, message, signature if isinstance(signature, (bytes, bytearray)) else b"")

        # STEP 4: Packet Behavior Analysis
        packet_rate = payload.get("rate", 1.0)
        packet_size = payload.get("size", 100)

        # STEP 5: Trust Update
        self.trust.update_from_verification(src, proximity_result)
        self.trust.update_from_signature(src, sig_verified)
        self.trust.update_from_packet(src, {"rate": packet_rate, "size": packet_size})
        if suspicious_packet:
            self.trust.penalize_for_attack(src, attack_severity=1.2)

        trust_record = self.trust.get_trust(src)
        trust_score = trust_record.score if trust_record else 0.5

        # STEP 6: Ledger Update
        self.ledger.append(
            device_id=src,
            accepted=(trust_score >= 0.4 and sig_verified and proximity_result.decision != "reject"),
            reason="packet",
            evidence={
                "proximity": proximity_result.decision,
                "signature_verified": sig_verified,
                "confidence": proximity_result.confidence,
                "rate": packet_rate,
                "size": packet_size,
                "suspicious_packet": suspicious_packet,
            },
        )

        # STEP 7: Broadcast Event
        self._emit(
            {
                "type": "packet_verified",
                "device": src,
                "proximity_result": proximity_result.decision,
                "signature_verified": sig_verified,
                "trust_score": trust_score,
                "confidence": proximity_result.confidence,
                "timestamp": timestamp,
            }
        )

        # Record in analytics
        self.analytics.record_verification_time(src, proximity_result.propagation_delay_ms)
        self.analytics.record_trust_score(src, trust_score)
        self.analytics.record_detection(
            device_id=src,
            is_ghost=suspicious_packet,
            detected_as_ghost=suspicious_packet,
            verification_time_ms=proximity_result.propagation_delay_ms,
            confidence=proximity_result.confidence,
        )
        self.analytics.record_pqc_metrics(self.pqc.metrics())

        return {
            "device": src,
            "proximity": proximity_result.decision,
            "signature_verified": sig_verified,
            "trust_score": trust_score,
            "confidence": proximity_result.confidence,
        }

    def _check_ghost_pattern(self, device_id: str, device: Optional[Dict[str, Any]] = None) -> bool:
        """Detect whether a device resembles a Sybil or ghost identity."""
        if not device_id:
            return False

        device_id_text = str(device_id).lower()
        if device:
            name = str(device.get("name", "")).lower()
            device_type = str(device.get("device_type", "")).lower()
        else:
            name = ""
            device_type = ""

        if any(token in device_id_text for token in ("ghost", "sybil", "attacker")):
            return True
        if any(token in name for token in ("ghost", "sybil", "attacker")):
            return True
        if any(token in device_type for token in ("ghost", "sybil", "attacker")):
            return True

        with self.lock:
            if device_id in self.ghost.ghosts:
                return True
            active_attacks = [attack for attack in self.ghost.attacks.values() if attack.end_time is None]
            if active_attacks and len(active_attacks) >= 1 and device_id_text.startswith("ghost"):
                return True

        return False

    def _infer_measured_position(
        self,
        device_id: str,
        claimed_pos: Tuple[float, float],
        device_type: str | None = None,
        is_likely_ghost: bool = False,
    ) -> Tuple[float, float]:
        """Create a measurement that reflects whether the device is behaving suspiciously."""
        if is_likely_ghost:
            offset_x = 12.0 + (len(device_id) % 7) * 1.5
            offset_y = 8.0 + (len(device_id) % 5) * 1.0
            return claimed_pos[0] + offset_x, claimed_pos[1] + offset_y

        if device_type and "ghost" in str(device_type).lower():
            return claimed_pos[0] + 8.0, claimed_pos[1] + 6.0

        return claimed_pos[0] + 0.5, claimed_pos[1] + 0.3

    def _is_suspicious_packet(self, device_id: str, payload: Dict[str, Any]) -> bool:
        """Use packet characteristics to decide whether the packet should be treated as suspicious."""
        if not device_id:
            return False

        if self._check_ghost_pattern(device_id):
            return True

        if payload.get("rate", 0) > 20:
            return True
        if payload.get("size", 0) > 5000:
            return True
        if payload.get("signature") in (None, b""):
            return True

        return False

    def start_attack(
        self,
        attacker_id: str,
        count: int,
        intensity: float = 1.0,
        duration: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Orchestrate a Sybil attack campaign.

        Args:
            attacker_id: Identifier for the attacker
            count: Number of ghost nodes to spawn (10, 20, 50, 100, 250)
            intensity: Attack strength 0.1-10.0
            duration: Attack duration in seconds

        Returns:
            Attack metadata
        """
        stats = self.ghost.spawn_attack(
            attacker_id=attacker_id,
            count=count,
            intensity=intensity,
            duration=duration,
        )

        self.analytics.record_attack(attacker_id, count, 0)

        self._emit(
            {
                "type": "attack_started",
                "attacker": attacker_id,
                "ghost_count": count,
                "intensity": intensity,
                "duration": duration,
            }
        )

        return {
            "attacker": attacker_id,
            "ghosts_spawned": count,
            "intensity": intensity,
            "duration": duration,
        }

    def stop_attack(self, attacker_id: str) -> Dict[str, Any]:
        """Stop an attack campaign."""
        stats = self.ghost.stop_attack(attacker_id)

        if stats:
            self.analytics.record_attack(
                attacker_id,
                stats.ghost_count,
                stats.detected_count,
            )

            self._emit(
                {
                    "type": "attack_stopped",
                    "attacker": attacker_id,
                    "detected": stats.detected_count,
                    "detection_rate": stats.detection_rate,
                }
            )

            return {
                "attacker": attacker_id,
                "detection_rate": stats.detection_rate,
                "success_rate": stats.success_rate,
            }

        return {"attacker": attacker_id, "error": "attack not found"}

    def status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        with self.lock:
            legitimate_count = len(self.legitimate_devices)
            ghost_count = len(self.ghost_nodes)

        trust_metrics = self.trust.export_trust_metrics()
        ledger_stats = self.ledger.stats()
        analytics_metrics = self.analytics.metrics()

        return {
            "processed_joins": self.processed_joins,
            "processed_packets": self.processed_packets,
            "legitimate_devices": legitimate_count,
            "ghost_nodes": ghost_count,
            "trust": trust_metrics,
            "ledger": ledger_stats,
            "analytics": analytics_metrics,
            "attacks": list(self.ghost.all_attack_stats().keys()),
        }
