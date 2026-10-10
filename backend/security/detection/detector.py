"""Feature-based Sybil / ghost detector.

Design goals
------------
* **No label leakage.** The detector never reads scenario ground truth
  (``malicious`` / ``legitimate``), device names, ``credential_label``,
  ``attacker_id`` or the ghost-engine registry. Those fields are not even part
  of the :class:`Observation` contract.
* **Observable only.** Every feature is derived from telemetry a deployment can
  legitimately collect at prediction time: measured-vs-claimed position
  (proof-of-proximity), signature/credential verification outcome, packet rate
  and size, physical co-location of distinct identities, credential reuse, and
  sustained low trust.
* **Transparent and deterministic.** The score is a weighted sum of normalised
  sub-scores in ``[0, 1]``. Each contribution is reported so a decision can be
  explained and audited. There is no randomness in scoring.

The detector is intentionally rule/feature based rather than an ML model: it is
cheap, dependency-free, auditable and reproducible, which is the right trade-off
for a research prototype at this stage.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

DETECTOR_VERSION = "ghost-detector/2.0"

Position = Tuple[float, float]

# Data-quality statuses. Only :data:`STATUS_OK` means the detector had enough
# valid, fresh and self-consistent telemetry to conclude that a device is benign.
# Every other status is *unknown*: the absence of evidence is reported as such
# rather than silently treated as a clean pass.
STATUS_OK = "ok"
STATUS_INSUFFICIENT = "insufficient_data"
STATUS_STALE = "stale"
STATUS_MALFORMED = "malformed"
STATUS_CONTRADICTORY = "contradictory"

#: Statuses that represent degraded/absent telemetry (i.e. not a benign pass).
UNKNOWN_STATUSES = (
    STATUS_INSUFFICIENT,
    STATUS_STALE,
    STATUS_MALFORMED,
    STATUS_CONTRADICTORY,
)


@dataclass(frozen=True)
class DetectorConfig:
    """Thresholds and weights for the detector.

    The ``benign_*`` / ``flag_*`` pairs define a linear ramp for each feature:
    values at or below ``benign`` score 0, values at or above ``flag`` score 1.
    Defaults were chosen from the domain (metre-scale access-control positioning,
    packet rates of a small IoT device) and are *not* fitted to the evaluation
    scenarios; the evaluation harness reports performance on held-out
    distributions to check they generalise.
    """

    # Proof-of-proximity distance error (metres).
    benign_proximity_error_m: float = 4.0
    flag_proximity_error_m: float = 25.0
    # Packet rate (packets/second) and size (bytes).
    benign_packet_rate: float = 6.0
    flag_packet_rate: float = 20.0
    benign_packet_size: int = 512
    flag_packet_size: int = 4096
    # Identity clustering: distinct identities sharing one physical origin.
    cluster_radius_m: float = 6.0
    benign_cluster_size: int = 1
    flag_cluster_size: int = 4
    # Signature / credential verification failures.
    benign_signature_failure_ratio: float = 0.2
    flag_signature_failure_ratio: float = 0.6
    # Credentials shared across distinct identities (0 = unique).
    benign_credential_reuse: float = 0.0
    flag_credential_reuse: float = 2.0
    # Sustained low trust (only used when a trust score is supplied).
    trust_flag_threshold: float = 0.4
    # Per-feature reliability α∈(0,1): the probability-like weight that a fully
    # present indicator is diagnostic. Evidence is combined with a noisy-OR
    # (see ``_score_locked``), so one strong indicator (α close to 1) can flag on
    # its own while several weak indicators must corroborate each other.
    reliability: Dict[str, float] = field(
        default_factory=lambda: {
            "proximity": 0.9,
            "signature": 0.85,
            "packet_rate": 0.5,
            "packet_size": 0.45,
            "cluster": 0.9,
            "credential_reuse": 0.6,
            "trust": 0.3,
        }
    )
    decision_threshold: float = 0.5
    # Minimum signature observations before the failure ratio is trusted.
    min_signature_attempts: int = 2
    max_history: int = 200
    # Data-quality controls -------------------------------------------------
    # Minimum number of independent, valid signal families (of: proximity,
    # signature, packet_rate, packet_size, credential, trust) required before a
    # *negative* (benign) decision is trusted. With fewer, the outcome is
    # reported as ``insufficient_data`` instead of silently benign.
    min_observable_signals: int = 2
    # Observations whose newest sample is older than this many seconds are
    # treated as stale when timestamps are supplied. ``0`` disables the check.
    max_observation_age_seconds: float = 300.0
    # A failed signature alongside a trust score at/above this value is treated
    # as contradictory telemetry (the trust engine and the crypto check disagree).
    high_trust_threshold: float = 0.9


@dataclass
class Observation:
    """A single observable event for a device.

    All fields except ``device_id`` and ``claimed_pos`` are optional so callers
    can provide whatever telemetry is available. A *missing* field contributes no
    evidence; a *present but invalid* field (wrong type, negative volume,
    out-of-range trust, non-finite number) is recorded as malformed telemetry.
    Neither case is treated as a benign pass: with too little valid, fresh,
    self-consistent evidence the outcome is an explicit ``unknown`` status.
    """

    device_id: str
    claimed_pos: Position
    measured_pos: Optional[Position] = None
    signature_valid: Optional[bool] = None
    packet_rate: Optional[float] = None
    packet_size: Optional[int] = None
    credential_fingerprint: Optional[str] = None
    trust_score: Optional[float] = None
    timestamp: float = 0.0


@dataclass
class DetectionOutcome:
    """Result of scoring one device.

    ``is_flagged`` is the positive (malicious) decision. ``status`` describes the
    *data quality* behind a negative decision; when it is anything other than
    ``"ok"`` and the device was not flagged, :attr:`is_unknown` is ``True`` — the
    detector explicitly could not conclude the device is benign.
    """

    device_id: str
    is_flagged: bool
    score: float
    features: Dict[str, float]
    contributions: Dict[str, float]
    reasons: List[str]
    detector_version: str = DETECTOR_VERSION
    status: str = STATUS_OK
    data_quality: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_unknown(self) -> bool:
        return (not self.is_flagged) and self.status != STATUS_OK

    @property
    def decision(self) -> str:
        if self.is_flagged:
            return "flag"
        return "unknown" if self.is_unknown else "pass"


@dataclass
class _DeviceState:
    proximity_errors: List[float] = field(default_factory=list)
    signature_attempts: int = 0
    signature_failures: int = 0
    signature_outcomes: set = field(default_factory=set)
    packet_rates: List[float] = field(default_factory=list)
    packet_sizes: List[int] = field(default_factory=list)
    credential_fingerprint: Optional[str] = None
    trust_score: Optional[float] = None
    measured_origin: Optional[Tuple[int, int]] = None
    observations: int = 0
    malformed_signals: int = 0
    contradictory: bool = False
    newest_timestamp: float = 0.0
    valid_signals: set = field(default_factory=set)


def _is_number(value: Any) -> bool:
    """True for a finite real number (and not for ``bool``)."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _is_position(value: Any) -> bool:
    """True for a 2-element sequence of finite numbers (an (x, y) position)."""

    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(_is_number(component) for component in value)
    )


def _ramp(value: float, benign: float, flag: float) -> float:
    """Linear ramp from 0 at ``benign`` to 1 at ``flag`` (order-agnostic)."""

    if flag == benign:
        return 0.0 if value <= benign else 1.0
    if flag > benign:
        if value <= benign:
            return 0.0
        if value >= flag:
            return 1.0
        return (value - benign) / (flag - benign)
    # Decreasing ramp (higher value is more benign).
    if value >= benign:
        return 0.0
    if value <= flag:
        return 1.0
    return (benign - value) / (benign - flag)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


class GhostDetector:
    """Accumulates per-device observations and scores Sybil/ghost likelihood."""

    version = DETECTOR_VERSION

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self.config = config or DetectorConfig()
        self._devices: Dict[str, _DeviceState] = {}
        # Physical-origin clusters: rounded measured position -> set of identities.
        self._origin_clusters: Dict[Tuple[int, int], set] = {}
        # Credential fingerprint -> set of identities presenting it.
        self._credential_identities: Dict[str, set] = {}
        # Newest event timestamp seen, used to evaluate staleness.
        self._now = 0.0
        self._lock = threading.Lock()

    # -- ingestion ---------------------------------------------------------

    def observe(self, obs: Observation) -> DetectionOutcome:
        """Record one observation and return the device's current score.

        Each field is validated independently. Valid signals are accumulated;
        missing fields contribute no evidence; present-but-invalid fields are
        counted as malformed telemetry rather than being silently dropped.
        """

        with self._lock:
            state = self._devices.setdefault(obs.device_id, _DeviceState())
            state.observations += 1

            # Freshness signal.
            if obs.timestamp is None:
                pass
            elif _is_number(obs.timestamp):
                ts = float(obs.timestamp)
                if ts > 0:
                    state.newest_timestamp = max(state.newest_timestamp, ts)
                    self._now = max(self._now, ts)
            else:
                state.malformed_signals += 1

            # Proximity (proof-of-proximity deviation).
            if not _is_position(obs.claimed_pos):
                state.malformed_signals += 1
            elif obs.measured_pos is not None:
                if _is_position(obs.measured_pos):
                    error = math.hypot(
                        float(obs.measured_pos[0]) - float(obs.claimed_pos[0]),
                        float(obs.measured_pos[1]) - float(obs.claimed_pos[1]),
                    )
                    self._append_bounded(state.proximity_errors, error)
                    origin = self._quantise_origin(
                        (float(obs.measured_pos[0]), float(obs.measured_pos[1]))
                    )
                    state.measured_origin = origin
                    self._origin_clusters.setdefault(origin, set()).add(obs.device_id)
                    state.valid_signals.add("proximity")
                else:
                    state.malformed_signals += 1

            # Signature / credential verification outcome.
            if obs.signature_valid is not None:
                if isinstance(obs.signature_valid, bool):
                    state.signature_attempts += 1
                    if not obs.signature_valid:
                        state.signature_failures += 1
                    state.signature_outcomes.add(bool(obs.signature_valid))
                    state.valid_signals.add("signature")
                else:
                    state.malformed_signals += 1

            # Packet rate.
            if obs.packet_rate is not None:
                if _is_number(obs.packet_rate) and float(obs.packet_rate) >= 0.0:
                    self._append_bounded(state.packet_rates, float(obs.packet_rate))
                    state.valid_signals.add("packet_rate")
                else:
                    state.malformed_signals += 1

            # Packet size.
            if obs.packet_size is not None:
                if _is_number(obs.packet_size) and float(obs.packet_size) >= 0.0:
                    self._append_bounded(state.packet_sizes, int(obs.packet_size))
                    state.valid_signals.add("packet_size")
                else:
                    state.malformed_signals += 1

            # Credential fingerprint.
            if obs.credential_fingerprint is not None:
                if (
                    isinstance(obs.credential_fingerprint, str)
                    and obs.credential_fingerprint.strip()
                ):
                    state.credential_fingerprint = obs.credential_fingerprint
                    self._credential_identities.setdefault(
                        obs.credential_fingerprint, set()
                    ).add(obs.device_id)
                    state.valid_signals.add("credential")
                else:
                    state.malformed_signals += 1

            # Trust score.
            if obs.trust_score is not None:
                if _is_number(obs.trust_score) and 0.0 <= float(obs.trust_score) <= 1.0:
                    state.trust_score = float(obs.trust_score)
                    state.valid_signals.add("trust")
                else:
                    state.malformed_signals += 1

            # Contradictory telemetry: signature verification flapping for the
            # same identity, or a failed signature alongside a high trust score.
            if len(state.signature_outcomes) > 1:
                state.contradictory = True
            if (
                obs.signature_valid is False
                and state.trust_score is not None
                and state.trust_score >= self.config.high_trust_threshold
            ):
                state.contradictory = True

            return self._score_locked(obs.device_id)

    def _append_bounded(self, values: List, value: float) -> None:
        values.append(value)
        if len(values) > self.config.max_history:
            del values[0]

    def _quantise_origin(self, pos: Position) -> Tuple[int, int]:
        radius = max(0.1, self.config.cluster_radius_m)
        return (int(round(pos[0] / radius)), int(round(pos[1] / radius)))

    # -- scoring -----------------------------------------------------------

    def score(self, device_id: str) -> DetectionOutcome:
        with self._lock:
            return self._score_locked(device_id)

    def all_scores(self) -> Dict[str, DetectionOutcome]:
        with self._lock:
            return {device_id: self._score_locked(device_id) for device_id in self._devices}

    def _score_locked(self, device_id: str) -> DetectionOutcome:
        state = self._devices.get(device_id)
        if state is None:
            return DetectionOutcome(
                device_id=device_id,
                is_flagged=False,
                score=0.0,
                features={},
                contributions={},
                reasons=["no observations"],
                status=STATUS_INSUFFICIENT,
                data_quality={"observations": 0, "valid_signals": [], "signal_count": 0},
            )

        cfg = self.config
        features: Dict[str, float] = {}

        # Proximity: worst observed deviation in the window.
        max_error = max(state.proximity_errors) if state.proximity_errors else 0.0
        features["proximity_error_m"] = round(max_error, 3)

        # Signature failure ratio.
        if state.signature_attempts >= cfg.min_signature_attempts:
            features["signature_failure_ratio"] = round(
                state.signature_failures / state.signature_attempts, 4
            )
        else:
            features["signature_failure_ratio"] = 0.0

        # Packet rate / size: use the high percentile to resist single spikes.
        features["packet_rate_p95"] = round(self._percentile(state.packet_rates, 0.95), 3)
        features["packet_size_max"] = float(max(state.packet_sizes)) if state.packet_sizes else 0.0

        # Cluster size around the device's measured origin.
        cluster_size = 0
        if state.measured_origin is not None:
            cluster_size = len(self._origin_clusters.get(state.measured_origin, ()))
        features["identity_cluster_size"] = float(cluster_size)

        # Credential reuse: extra identities sharing this credential.
        credential_reuse = 0.0
        if state.credential_fingerprint is not None:
            shared = self._credential_identities.get(state.credential_fingerprint, set())
            credential_reuse = float(max(0, len(shared) - 1))
        features["credential_reuse"] = credential_reuse

        features["trust_score"] = (
            float(state.trust_score) if state.trust_score is not None else -1.0
        )

        sub: Dict[str, float] = {
            "proximity": _ramp(
                features["proximity_error_m"],
                cfg.benign_proximity_error_m,
                cfg.flag_proximity_error_m,
            ),
            "signature": _ramp(
                features["signature_failure_ratio"],
                cfg.benign_signature_failure_ratio,
                cfg.flag_signature_failure_ratio,
            ),
            "packet_rate": _ramp(
                features["packet_rate_p95"],
                cfg.benign_packet_rate,
                cfg.flag_packet_rate,
            ),
            "packet_size": _ramp(
                features["packet_size_max"],
                cfg.benign_packet_size,
                cfg.flag_packet_size,
            ),
            "cluster": _ramp(
                features["identity_cluster_size"],
                cfg.benign_cluster_size,
                cfg.flag_cluster_size,
            ),
            "credential_reuse": _ramp(
                credential_reuse,
                cfg.benign_credential_reuse,
                cfg.flag_credential_reuse,
            ),
            "trust": (
                _ramp(
                    features["trust_score"],
                    cfg.trust_flag_threshold,
                    max(0.0, cfg.trust_flag_threshold - 0.25),
                )
                if state.trust_score is not None
                else 0.0
            ),
        }

        reliability = cfg.reliability
        contributions = {
            name: round(reliability.get(name, 0.0) * value, 4)
            for name, value in sub.items()
        }
        # Noisy-OR evidence combination: indicators are treated as (roughly)
        # independent pieces of evidence, so one highly diagnostic indicator can
        # flag on its own while several weak ones must corroborate.
        no_hit = 1.0
        for name, value in sub.items():
            no_hit *= (1.0 - _clamp01(reliability.get(name, 0.0) * value))
        score = _clamp01(1.0 - no_hit)
        is_flagged = score >= cfg.decision_threshold

        # Data quality. A positive (flagged) decision is actionable on its own, so
        # it is always reported as "ok". For a *negative* decision the telemetry
        # must be valid, fresh, self-consistent and plentiful enough to conclude
        # "benign"; otherwise the outcome is explicitly unknown.
        valid_signal_count = len(state.valid_signals)
        stale = (
            cfg.max_observation_age_seconds > 0
            and state.newest_timestamp > 0
            and (self._now - state.newest_timestamp) > cfg.max_observation_age_seconds
        )
        if is_flagged:
            status = STATUS_OK
        elif state.malformed_signals > 0:
            status = STATUS_MALFORMED
        elif state.contradictory:
            status = STATUS_CONTRADICTORY
        elif stale:
            status = STATUS_STALE
        elif valid_signal_count < cfg.min_observable_signals:
            status = STATUS_INSUFFICIENT
        else:
            status = STATUS_OK

        data_quality: Dict[str, Any] = {
            "observations": state.observations,
            "valid_signals": sorted(state.valid_signals),
            "signal_count": valid_signal_count,
            "malformed_signals": state.malformed_signals,
            "contradictory": state.contradictory,
            "stale": stale,
        }

        reasons = self._explain(features, sub, is_flagged, status, valid_signal_count)
        return DetectionOutcome(
            device_id=device_id,
            is_flagged=is_flagged,
            score=round(score, 4),
            features=features,
            contributions=contributions,
            reasons=reasons,
            status=status,
            data_quality=data_quality,
        )

    def _explain(
        self,
        features: Dict[str, float],
        sub: Dict[str, float],
        is_flagged: bool,
        status: str,
        valid_signal_count: int,
    ) -> List[str]:
        reasons: List[str] = []
        if sub.get("proximity", 0) > 0:
            reasons.append(f"proximity deviation {features['proximity_error_m']}m")
        if sub.get("signature", 0) > 0:
            reasons.append(
                f"signature failure ratio {features['signature_failure_ratio']}"
            )
        if sub.get("packet_rate", 0) > 0:
            reasons.append(f"high packet rate {features['packet_rate_p95']}/s")
        if sub.get("packet_size", 0) > 0:
            reasons.append(f"large packets {features['packet_size_max']:.0f}B")
        if sub.get("cluster", 0) > 0:
            reasons.append(
                f"{int(features['identity_cluster_size'])} identities at one origin"
            )
        if sub.get("credential_reuse", 0) > 0:
            reasons.append(
                f"credential shared by {int(features['credential_reuse']) + 1} identities"
            )
        if sub.get("trust", 0) > 0:
            reasons.append(f"low trust {features['trust_score']}")
        if not reasons:
            if status == STATUS_OK and not is_flagged:
                reasons.append("no anomaly")
            else:
                reasons.append(
                    f"{status}: {valid_signal_count} valid signal(s) observed"
                )
        return reasons

    @staticmethod
    def _percentile(values: Iterable[float], q: float) -> float:
        data = sorted(values)
        if not data:
            return 0.0
        if len(data) == 1:
            return data[0]
        index = min(len(data) - 1, max(0, int(round(q * (len(data) - 1)))))
        return data[index]

    # -- lifecycle ---------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._devices.clear()
            self._origin_clusters.clear()
            self._credential_identities.clear()
            self._now = 0.0
