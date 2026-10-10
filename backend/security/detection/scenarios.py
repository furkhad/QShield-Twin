"""Deterministic attack scenarios with separable ground truth.

Scenarios are generated here, independently of the running application or its
database. Each scenario produces a list of :class:`ScenarioDevice` records that
pair a short **observable** observation stream
(:class:`~backend.security.detection.detector.Observation`) with a **held-out
ground-truth** label (``is_ghost`` / ``attack_type``). The detector is never
shown the label.

Device names and ids are deliberately *neutral* (no ``ghost`` / ``clone`` /
``sybil`` vocabulary) so that a name-matching detector cannot succeed by
memorising generator wording.

Each device emits a short stream of observations (join + packets) so that
frequency- and repetition-based signals (repeated signature failures, sustained
packet rate, credential reuse over time) are genuinely observable.

A scenario-config ``severity`` scales the observable signal strength. Clear
configurations are used while developing the detector's thresholds; "subtle"
configurations are **held out** and used to check the thresholds generalise to
feature distributions they were not tuned on.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List

from backend.security.detection.detector import Observation

# Building footprint (metres) used for positions in every scenario.
_AREA_X = 800.0
_AREA_Y = 400.0

# Observations emitted per device (join + a few packets).
_OBSERVATIONS_PER_DEVICE = 5


@dataclass
class ScenarioDevice:
    device_id: str
    name: str
    is_ghost: bool
    attack_type: str  # "legit" | "clone" | "sybil_herd" | "spoof" | "traffic_abuse" | "auth_failure"
    observations: List[Observation] = field(default_factory=list)


@dataclass
class Scenario:
    name: str
    seed: int
    devices: List[ScenarioDevice] = field(default_factory=list)
    holdout: bool = False

    @property
    def ghost_count(self) -> int:
        return sum(1 for d in self.devices if d.is_ghost)

    @property
    def legitimate_count(self) -> int:
        return sum(1 for d in self.devices if not d.is_ghost)


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    legitimate_count: int = 40
    clone_count: int = 0
    herd_count: int = 0
    spoof_count: int = 0
    traffic_abuse_count: int = 0
    auth_failure_count: int = 0
    severity: float = 1.0
    holdout: bool = False


def _pos(rng: random.Random) -> tuple[float, float]:
    return (rng.uniform(0, _AREA_X), rng.uniform(0, _AREA_Y))


def _neutral(index: int) -> tuple[str, str]:
    token = f"{index:04d}"
    return f"node-{token}", f"access-node-{token}"


def _emit(
    device_id: str,
    rng: random.Random,
    *,
    claimed_pos: tuple[float, float],
    measured_origin: tuple[float, float],
    position_jitter: float,
    sig_fail_prob: float,
    rate_mean: float,
    rate_sd: float,
    size_mean: float,
    size_sd: float,
    credential_fingerprint: str,
    trust_score: float,
    count: int = _OBSERVATIONS_PER_DEVICE,
) -> List[Observation]:
    observations: List[Observation] = []
    for _ in range(count):
        measured = (
            measured_origin[0] + rng.gauss(0, position_jitter),
            measured_origin[1] + rng.gauss(0, position_jitter),
        )
        observations.append(
            Observation(
                device_id=device_id,
                claimed_pos=claimed_pos,
                measured_pos=measured,
                signature_valid=rng.random() >= sig_fail_prob,
                packet_rate=max(0.1, rng.gauss(rate_mean, rate_sd)),
                packet_size=int(max(64, rng.gauss(size_mean, size_sd))),
                credential_fingerprint=credential_fingerprint,
                trust_score=trust_score,
            )
        )
    return observations


def build_scenario(config: ScenarioConfig, seed: int) -> Scenario:
    """Generate a deterministic scenario from ``config`` and ``seed``."""

    rng = random.Random(seed)
    scenario = Scenario(name=config.name, seed=seed, holdout=config.holdout)
    sev = max(0.05, config.severity)
    next_index = 0

    def next_id() -> tuple[str, str]:
        nonlocal next_index
        pair = _neutral(next_index)
        next_index += 1
        return pair

    # -- legitimate devices -------------------------------------------------
    legit_positions: list[tuple[float, float]] = []
    for _ in range(config.legitimate_count):
        device_id, name = next_id()
        pos = _pos(rng)
        legit_positions.append(pos)
        scenario.devices.append(
            ScenarioDevice(
                device_id=device_id,
                name=name,
                is_ghost=False,
                attack_type="legit",
                observations=_emit(
                    device_id,
                    rng,
                    claimed_pos=pos,
                    measured_origin=pos,
                    position_jitter=1.0,
                    sig_fail_prob=0.0,
                    rate_mean=3.0,
                    rate_sd=1.0,
                    size_mean=256,
                    size_sd=60,
                    credential_fingerprint=f"cred-{device_id}",
                    trust_score=round(rng.uniform(0.7, 0.9), 3),
                ),
            )
        )

    # -- spoofed-position identities (large proximity deviation) -----------
    for _ in range(config.spoof_count):
        device_id, name = next_id()
        claimed = _pos(rng)
        error = sev * rng.uniform(30.0, 80.0)
        angle = rng.uniform(0, 2 * math.pi)
        measured = (
            claimed[0] + error * rng.uniform(0.6, 1.0) * math.cos(angle),
            claimed[1] + error * rng.uniform(0.6, 1.0) * math.sin(angle),
        )
        scenario.devices.append(
            ScenarioDevice(
                device_id=device_id,
                name=name,
                is_ghost=True,
                attack_type="spoof",
                observations=_emit(
                    device_id,
                    rng,
                    claimed_pos=claimed,
                    measured_origin=measured,
                    position_jitter=1.0,
                    sig_fail_prob=0.0,
                    rate_mean=5.0,
                    rate_sd=1.5,
                    size_mean=300,
                    size_sd=80,
                    credential_fingerprint=f"cred-{device_id}",
                    trust_score=round(rng.uniform(0.35, 0.6), 3),
                ),
            )
        )

    # -- cloned identities (shared forged credential + moderate offset) -----
    # All clones in a scenario present one attacker-held credential, which is
    # distinct from every legitimate device's unique fingerprint. This keeps the
    # credential-reuse signal attributable to the attacker rather than to the
    # innocent device whose behaviour is being imitated.
    for _ in range(config.clone_count):
        device_id, name = next_id()
        victim = rng.choice(legit_positions) if legit_positions else _pos(rng)
        measured = (victim[0] + rng.gauss(0, 2.0), victim[1] + rng.gauss(0, 2.0))
        claimed = (victim[0] + sev * rng.uniform(6.0, 18.0), victim[1] + rng.gauss(0, 3.0))
        scenario.devices.append(
            ScenarioDevice(
                device_id=device_id,
                name=name,
                is_ghost=True,
                attack_type="clone",
                observations=_emit(
                    device_id,
                    rng,
                    claimed_pos=claimed,
                    measured_origin=measured,
                    position_jitter=2.0,
                    sig_fail_prob=min(0.95, 0.7 * sev),
                    rate_mean=4.0 + 4.0 * sev,
                    rate_sd=1.5,
                    size_mean=320,
                    size_sd=70,
                    credential_fingerprint="cred-clone-shared",
                    trust_score=round(rng.uniform(0.35, 0.6), 3),
                ),
            )
        )

    # -- Sybil herd (many identities sharing one physical origin) -----------
    if config.herd_count > 0:
        origin = _pos(rng)
        for _ in range(config.herd_count):
            device_id, name = next_id()
            claimed = _pos(rng)  # spoofed/diverse claimed locations
            scenario.devices.append(
                ScenarioDevice(
                    device_id=device_id,
                    name=name,
                    is_ghost=True,
                    attack_type="sybil_herd",
                    observations=_emit(
                        device_id,
                        rng,
                        claimed_pos=claimed,
                        measured_origin=origin,
                        position_jitter=1.2,
                        sig_fail_prob=min(0.95, 0.8 * sev),
                        rate_mean=sev * 22.0,
                        rate_sd=4.0,
                        size_mean=400,
                        size_sd=90,
                        credential_fingerprint="cred-herd-shared",
                        trust_score=round(rng.uniform(0.3, 0.5), 3),
                    ),
                )
            )

    # -- traffic abuse (legit-looking identity, abnormal volume) -----------
    for _ in range(config.traffic_abuse_count):
        device_id, name = next_id()
        pos = _pos(rng)
        scenario.devices.append(
            ScenarioDevice(
                device_id=device_id,
                name=name,
                is_ghost=True,
                attack_type="traffic_abuse",
                observations=_emit(
                    device_id,
                    rng,
                    claimed_pos=pos,
                    measured_origin=pos,
                    position_jitter=1.0,
                    sig_fail_prob=0.0,
                    rate_mean=sev * 35.0,
                    rate_sd=sev * 6.0,
                    size_mean=sev * 4500,
                    size_sd=sev * 500,
                    credential_fingerprint=f"cred-{device_id}",
                    trust_score=round(rng.uniform(0.45, 0.65), 3),
                ),
            )
        )

    # -- authentication failures (repeated signature failures) -------------
    for _ in range(config.auth_failure_count):
        device_id, name = next_id()
        pos = _pos(rng)
        scenario.devices.append(
            ScenarioDevice(
                device_id=device_id,
                name=name,
                is_ghost=True,
                attack_type="auth_failure",
                observations=_emit(
                    device_id,
                    rng,
                    claimed_pos=pos,
                    measured_origin=pos,
                    position_jitter=1.2,
                    sig_fail_prob=1.0,
                    rate_mean=4.0,
                    rate_sd=1.5,
                    size_mean=280,
                    size_sd=70,
                    credential_fingerprint=f"cred-{device_id}",
                    trust_score=round(rng.uniform(0.35, 0.6), 3),
                ),
            )
        )

    rng.shuffle(scenario.devices)
    return scenario


# Tuning configs (clear signals) and held-out configs (subtle signals).
TUNING_CONFIGS: List[ScenarioConfig] = [
    ScenarioConfig("normal", legitimate_count=50),
    ScenarioConfig("clear_spoof", legitimate_count=40, spoof_count=10),
    ScenarioConfig("clear_clone", legitimate_count=40, clone_count=10),
    ScenarioConfig("clear_herd", legitimate_count=40, herd_count=12),
    ScenarioConfig("clear_traffic", legitimate_count=40, traffic_abuse_count=10),
    ScenarioConfig("clear_auth", legitimate_count=40, auth_failure_count=10),
]

HOLDOUT_CONFIGS: List[ScenarioConfig] = [
    ScenarioConfig("holdout_subtle_spoof", legitimate_count=45, spoof_count=8,
                   severity=0.55, holdout=True),
    ScenarioConfig("holdout_subtle_herd", legitimate_count=45, herd_count=9,
                   severity=0.55, holdout=True),
    ScenarioConfig("holdout_subtle_traffic", legitimate_count=45,
                   traffic_abuse_count=8, severity=0.5, holdout=True),
    ScenarioConfig("holdout_mixed", legitimate_count=50, clone_count=5, spoof_count=4,
                   herd_count=6, traffic_abuse_count=3, auth_failure_count=3,
                   severity=0.7, holdout=True),
]

# Deliberately hard, adversarial holdout: single-identity spoofing kept below
# every threshold, with valid signatures, a unique credential, normal traffic and
# no clustering. This is the evasion case a threshold detector is expected to
# miss; it is reported rather than hidden.
HOLDOUT_HARD_CONFIGS: List[ScenarioConfig] = [
    ScenarioConfig("holdout_stealth_spoof", legitimate_count=45, spoof_count=8,
                   severity=0.12, holdout=True),
]

DEFAULT_SEEDS: List[int] = [1, 7, 42, 1337, 9001]


def build_suite(configs: List[ScenarioConfig], seeds: List[int]) -> List[Scenario]:
    return [build_scenario(config, seed) for config in configs for seed in seeds]
