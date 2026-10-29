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
import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from backend.app.websocket.manager import manager as ws_manager
from backend.security.analytics.analytics_engine import AnalyticsEngine
from backend.security.detection.detector import GhostDetector, Observation
from backend.security.ghost.ghost_engine import GhostEngine
from backend.security.ledger.sharded_ledger import ShardedLedger
from backend.security.pqc.simulated_lattice import SimulatedLatticeCrypto
from backend.security.proximity.proof_of_proximity import ProofOfProximityEngine
from backend.security.trust.trust_engine import TrustEngine

logger = logging.getLogger(__name__)


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

    def __init__(self, seed: Optional[int] = None):
        """Initialize all security engines and set up event callbacks.

        Args:
            seed: Optional PRNG seed. When provided, all stochastic components
                (ghost behavior, proximity noise) become reproducible so a
                scenario can be re-run and audited. The seed is also exposed in
                analytics exports.
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        # Initialize security engines
        self.ghost = GhostEngine(event_cb=self._on_ghost_event)
        self.proximity = ProofOfProximityEngine(distance_tolerance_m=10.0)
        self.pqc = SimulatedLatticeCrypto(algorithm="simulated-ntru")
        self.trust = TrustEngine()
        # The operational orchestrator always uses durable storage. A storage
        # failure must surface (LedgerPersistenceError) instead of silently
        # downgrading to an in-memory ledger.
        self.ledger = ShardedLedger(shards=8, persist=True)
        self.analytics = AnalyticsEngine()
        # Feature-based Sybil/ghost detector (replaces the former name-token
        # heuristic). It consumes only observable telemetry, never scenario labels.
        self.detector = GhostDetector()

        # Tracking
        self.processed_joins: int = 0
        self.processed_packets: int = 0
        self.lock = threading.Lock()

        # State tracking for demo/validation
        self.legitimate_devices: set = set()
        self.ghost_nodes: set = set()
        self._device_keys: Dict[str, Tuple[bytes, bytes]] = {}
        self._device_positions: Dict[str, Tuple[float, float]] = {}
        self._device_metadata: Dict[str, Dict[str, Any]] = {}
        self._recent_events: deque[Dict[str, Any]] = deque(maxlen=200)

    def _emit(self, event: dict) -> None:
        """Broadcast security event via WebSocket to dashboard."""
        try:
            ws_manager.emit_sync({"type": "security_event", "payload": event})
        except Exception:
            logger.exception("Failed to broadcast security event")

    def _record_event(self, event: Dict[str, Any]) -> None:
        with self.lock:
            self._recent_events.append(event)
        self._emit(event)

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset the security state for reruns and scenario demos.

        Args:
            seed: Optional new PRNG seed. When omitted the previously set seed
                (if any) is reused so reruns remain reproducible.
        """
        if seed is not None:
            self.seed = seed
        if self.seed is not None:
            random.seed(self.seed)

        self.ghost = GhostEngine(event_cb=self._on_ghost_event)
        self.proximity = ProofOfProximityEngine(distance_tolerance_m=10.0)
        self.pqc = SimulatedLatticeCrypto(algorithm="simulated-ntru")
        self.trust = TrustEngine()
        self.ledger = ShardedLedger(shards=8, persist=True)
        self.analytics = AnalyticsEngine()
        self.detector = GhostDetector()
        self.processed_joins = 0
        self.processed_packets = 0
        self.legitimate_devices = set()
        self.ghost_nodes = set()
        self._device_keys = {}
        self._device_positions = {}
        self._device_metadata = {}
        self._recent_events = deque(maxlen=200)

    def _on_ghost_event(self, event: dict) -> None:
        """Handle events from ghost engine."""
        self._record_event({"source": "ghost", **event})

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
        self._device_metadata[device_id] = dict(device)

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

        # STEP 1: Observable feature extraction.
        # The observation is derived only from telemetry a deployment can measure
        # (proof-of-proximity measurement, signature outcome, traffic volume and
        # credentials). Scenario ground-truth labels (malicious/legitimate/
        # credential_label/attacker_id) are deliberately NOT read here; they are
        # consumed only when recording metrics below.
        claimed_pos = (join_req.x, join_req.y)
        observation = self._extract_observation(device_id, claimed_pos, device=device)

        # STEP 2: PQC Key Generation & Verification (retained as ledger evidence).
        pub_key, priv_key = self.pqc.generate_keypair()
        self._device_keys[device_id] = (pub_key, priv_key)

        # STEP 3: Proximity Verification against the observed measurement.
        measured_pos = observation.measured_pos or claimed_pos
        self._device_positions[device_id] = claimed_pos
        proximity_result = self.proximity.verify(
            device_id=device_id,
            claimed_pos=claimed_pos,
            measured_pos=measured_pos,
        )

        message = f"join:{device_id}:{join_req.x}:{join_req.y}".encode()
        signature = self.pqc.sign(priv_key, message)
        sig_verified = self.pqc.verify(pub_key, message, signature)
        # The observable signature outcome overrides the (always-valid) local
        # self-signature when the scenario supplies one.
        authentication_valid = (
            sig_verified if observation.signature_valid is None else observation.signature_valid
        )

        # STEP 3b: Feature-based ghost detection (explainable, no label leakage).
        detection = self.detector.observe(observation)
        is_likely_ghost = detection.is_flagged
        detection_unknown = detection.is_unknown
        security_sensitive = bool(device.get("security_sensitive", False))

        # STEP 4: Trust Calculation
        trust_record = self.trust.update_from_verification(device_id, proximity_result)
        self.trust.update_from_signature(device_id, authentication_valid)
        if is_likely_ghost:
            self.trust.penalize_for_attack(device_id, attack_severity=1.4)
            if device_id in self.ghost.ghosts:
                self.ghost.mark_detected(device_id)

        trust_record = self.trust.get_trust(device_id) or trust_record

        # STEP 5: Ledger Update
        # A security-sensitive join whose telemetry is unknown must not be
        # recorded as accepted, even if the trust engine would otherwise allow it.
        ledger_accepted = (
            trust_record.decision in ["accept", "monitor"]
            and not (detection_unknown and security_sensitive)
        )
        self.ledger.append(
            device_id=device_id,
            accepted=ledger_accepted,
            reason="join",
            evidence={
                "proximity": proximity_result.__dict__,
                "pqc_pub": pub_key.hex()[:32] + "...",
                "trust_score": trust_record.score,
                "ghost_detected": is_likely_ghost,
                "signature_verified": authentication_valid,
                "measured_pos": measured_pos,
                "detector": {
                    "version": detection.detector_version,
                    "score": detection.score,
                    "status": detection.status,
                    "unknown": detection_unknown,
                    "reasons": detection.reasons,
                },
            },
        )

        # STEP 6: Final Decision
        decision = trust_record.decision
        if is_likely_ghost and trust_record.score < 0.4:
            decision = "reject"
        elif is_likely_ghost and trust_record.score < 0.7:
            decision = "monitor"

        # Missing, stale, malformed or contradictory telemetry must never be
        # silently treated as benign. Only a would-be *allow* is reclassified;
        # an already-denying decision (reject/blacklist) is left untouched so the
        # unknown status can never weaken it.
        if detection_unknown and decision in ("accept", "monitor"):
            decision = "challenge" if security_sensitive else "monitor"

        accepted = decision in ["accept", "monitor"]
        security_status = (
            "trusted" if decision == "accept" else
            "monitoring" if decision == "monitor" else
            "challenge_required" if decision == "challenge" else
            "rejected" if decision == "reject" else
            "blacklisted"
        )

        # STEP 7: Broadcast Event
        self._record_event(
            {
                "timestamp": timestamp,
                "device_id": device_id,
                "device_type": join_req.device_type,
                "zone": device.get("zone"),
                "event_type": "device_join",
                "security_status": security_status,
                "trust_score": trust_record.score,
                "decision": decision,
                "message": "Ghost identity detected" if is_likely_ghost else "New access-control device detected",
                "authentication_status": "verified" if authentication_valid else "failed",
                "proximity_status": proximity_result.decision,
                "ghost_detected": is_likely_ghost,
                "detection_score": detection.score,
                "detection_status": detection.status,
                "detection_unknown": detection_unknown,
                "detection_reasons": detection.reasons,
            }
        )

        # Ground truth is the scenario's own label, kept strictly separate from
        # the detector output (is_likely_ghost) so the confusion matrix reflects
        # real misses/false alarms rather than label leakage. Unknown telemetry is
        # recorded as *unobserved* so it is never miscounted as a true negative.
        ground_truth_ghost = bool(device.get("malicious", False)) or device.get("legitimate") is False
        self.analytics.record_detection(
            device_id=device_id,
            is_ghost=ground_truth_ghost,
            detected_as_ghost=is_likely_ghost,
            verification_time_ms=proximity_result.propagation_delay_ms,
            confidence=proximity_result.confidence,
            score=detection.score,
            detector_version=detection.detector_version,
            reasons=detection.reasons,
            observed=not detection_unknown,
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
            "detection_status": detection.status,
            "detection_unknown": detection_unknown,
            "security_status": security_status,
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

        # STEP 1: Extract observable features (never scenario labels).
        payload = packet.get("payload", {})
        claimed_pos = tuple(payload.get("claimed_pos", (0.0, 0.0)))
        observation = self._extract_observation(src, claimed_pos, payload=payload)
        measured_pos = observation.measured_pos or claimed_pos

        # STEP 2: Proximity Verification against the observed measurement.
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
        pqc_verified = self.pqc.verify(pub_key, message, signature if isinstance(signature, (bytes, bytearray)) else b"")
        authentication_valid = (
            pqc_verified if observation.signature_valid is None else observation.signature_valid
        )

        # STEP 4: Feature-based packet anomaly detection (no label leakage).
        packet_rate = payload.get("rate", 1.0)
        packet_size = payload.get("size", 100)
        detection = self.detector.observe(observation)
        suspicious_packet = detection.is_flagged
        detection_unknown = detection.is_unknown

        # STEP 5: Trust Update
        self.trust.update_from_verification(src, proximity_result)
        self.trust.update_from_signature(src, authentication_valid)
        self.trust.update_from_packet(src, {"rate": packet_rate, "size": packet_size})
        if suspicious_packet:
            self.trust.penalize_for_attack(src, attack_severity=1.2)

        trust_record = self.trust.get_trust(src)
        trust_score = trust_record.score if trust_record else 0.5

        # STEP 6: Ledger Update
        self.ledger.append(
            device_id=src,
            accepted=(trust_score >= 0.4 and authentication_valid and proximity_result.decision != "reject"),
            reason="packet",
            evidence={
                "proximity": proximity_result.decision,
                "signature_verified": authentication_valid,
                "confidence": proximity_result.confidence,
                "rate": packet_rate,
                "size": packet_size,
                "suspicious_packet": suspicious_packet,
                "detector": {
                    "version": detection.detector_version,
                    "score": detection.score,
                    "status": detection.status,
                    "unknown": detection_unknown,
                    "reasons": detection.reasons,
                },
            },
        )

        # STEP 7: Broadcast Event
        self._emit(
            {
                "type": "packet_verified",
                "device": src,
                "destination": dst,
                "proximity_result": proximity_result.decision,
                "signature_verified": authentication_valid,
                "trust_score": trust_score,
                "confidence": proximity_result.confidence,
                "detection_status": detection.status,
                "detection_unknown": detection_unknown,
                "timestamp": timestamp,
            }
        )

        # Record in analytics
        self.analytics.record_verification_time(src, proximity_result.propagation_delay_ms)
        self.analytics.record_trust_score(src, trust_score)
        # Ground truth (scenario label) vs. detector output (suspicious_packet),
        # recorded separately so precision/recall reflect the actual detector.
        ground_truth_ghost = bool(
            self._device_metadata.get(src, {}).get("malicious", False)
        )
        self.analytics.record_detection(
            device_id=src,
            is_ghost=ground_truth_ghost,
            detected_as_ghost=suspicious_packet,
            verification_time_ms=proximity_result.propagation_delay_ms,
            confidence=proximity_result.confidence,
            score=detection.score,
            detector_version=detection.detector_version,
            reasons=detection.reasons,
            observed=not detection_unknown,
        )
        self.analytics.record_pqc_metrics(self.pqc.metrics())

        self._record_event(
            {
                "timestamp": timestamp,
                "device_id": src,
                "device_type": self._device_metadata.get(src, {}).get("device_type", "access_control_device"),
                "zone": self._device_metadata.get(src, {}).get("zone"),
                "event_type": "packet_verified",
                "security_status": "trusted" if trust_score >= 0.8 else "monitoring" if trust_score >= 0.4 else "rejected",
                "trust_score": trust_score,
                "decision": trust_record.decision if trust_record else "monitor",
                "message": "Physical proximity verified" if proximity_result.decision == "accept" else "Suspicious packet behavior detected",
                "authentication_status": "verified" if authentication_valid else "failed",
                "proximity_status": proximity_result.decision,
            }
        )

        return {
            "device": src,
            "proximity": proximity_result.decision,
            "signature_verified": authentication_valid,
            "trust_score": trust_score,
            "confidence": proximity_result.confidence,
        }

    def _extract_observation(
        self,
        device_id: str,
        claimed_pos: Tuple[float, float],
        device: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        """Build an observable-only :class:`Observation` from a join or packet.

        Only telemetry a deployment can legitimately measure is read:
        ``measured_pos`` (proof-of-proximity), ``signature_valid``, ``rate`` /
        ``size`` (traffic), and ``credential_fingerprint``. Device names, ids,
        ``device_type`` and scenario labels are never consulted, so the detector
        cannot exploit generator vocabulary or ground truth.

        Missing telemetry is passed through as *missing* rather than being
        fabricated into a benign default. Field values are forwarded unchanged so
        the detector can distinguish an absent signal from a *malformed* one; the
        resulting outcome is then an explicit ``unknown`` status instead of an
        implicit clean pass.
        """

        source: Dict[str, Any] = device if device is not None else (payload or {})
        raw: Any = source.get("observation") if isinstance(source, dict) else None
        if raw is None and isinstance(source, dict):
            # Packets may carry their observable fields inline.
            raw = source
        raw = raw if isinstance(raw, dict) else {}

        measured = raw.get("measured_pos")
        signature_valid = raw.get("signature_valid")
        packet_rate = raw.get("rate", raw.get("packet_rate"))
        packet_size = raw.get("size", raw.get("packet_size"))
        credential = raw.get("credential_fingerprint")
        timestamp = raw.get("timestamp")
        if timestamp is None:
            timestamp = time.time()

        # Prefer a trust score supplied with the observation; otherwise fall back
        # to the trust engine's current history for this identity.
        supplied_trust = raw.get("trust_score")
        trust = self.trust.get_trust(device_id)
        trust_score = (
            supplied_trust
            if supplied_trust is not None
            else (trust.score if trust else None)
        )

        return Observation(
            device_id=device_id,
            claimed_pos=claimed_pos,
            measured_pos=measured,
            signature_valid=signature_valid,
            packet_rate=packet_rate,
            packet_size=packet_size,
            credential_fingerprint=credential,
            trust_score=trust_score,
            timestamp=timestamp,
        )

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

        # Score each spawned identity through the normal join pipeline using
        # telemetry a deployment can observe: a shared credential, spoofed
        # co-located proof-of-proximity measurements, failing signatures and an
        # elevated packet rate. The feature-based detector still decides whether
        # each is a ghost; this only ensures the campaign statistics reflect
        # real detections instead of a hard-coded zero.
        for node in self.ghost.list_ghosts_by_attacker(attacker_id):
            self.receive_join(
                {
                    "device_id": node.device_id,
                    "name": node.name,
                    "device_type": "access_control_device",
                    "x": node.x,
                    "y": node.y,
                    "legitimate": False,
                    "malicious": True,
                    "attacker_id": attacker_id,
                    "credential_label": f"cred-{attacker_id}",
                    "observation": {
                        # Identities claim different spots, but the measured
                        # proof-of-proximity resolves back to a single origin.
                        "measured_pos": [0.0, 0.0],
                        "signature_valid": False,
                        "packet_rate": 20.0 * intensity,
                        "packet_size": 420,
                        "credential_fingerprint": f"cred-{attacker_id}",
                    },
                }
            )

        self._record_event(
            {
                "timestamp": time.time(),
                "event_type": "attack_started",
                "attacker": attacker_id,
                "ghost_count": count,
                "intensity": intensity,
                "duration": duration,
                "message": "Ghost/Sybil attack simulation started",
                "security_status": "critical",
            }
        )

        return {
            "attacker": attacker_id,
            "ghosts_spawned": count,
            "intensity": intensity,
            "duration": duration,
            "spawn_stats": stats,
        }

    def stop_attack(self, attacker_id: str) -> Dict[str, Any]:
        """Stop an attack campaign."""
        stats = self.ghost.stop_attack(attacker_id)

        if stats:
            # The campaign was already counted by ``record_attack`` at start;
            # here we only add the detections observed during the campaign so a
            # single attack is never double-counted.
            self.analytics.record_detections(stats.detected_count)

            self._record_event(
                {
                    "timestamp": time.time(),
                    "event_type": "attack_stopped",
                    "attacker": attacker_id,
                    "detected": stats.detected_count,
                    "detection_rate": stats.detection_rate,
                    "message": "Ghost/Sybil attack simulation stopped",
                    "security_status": "monitoring",
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
            "recent_events": list(self._recent_events)[-50:],
        }
