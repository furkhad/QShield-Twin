"""Ghost (Sybil) attack simulator.

Implements realistic Sybil attack behavior: ghost nodes with shared attacker origin
but different virtual identities. Ghosts attempt to join the network, broadcast
packets, influence neighbors, and participate in routing while appearing as
legitimate devices.

Supported attack scales: 10, 20, 50, 100, 250 ghost nodes.
Attack strength controls packet generation rate and neighbor influence intensity.
"""

from __future__ import annotations

import time
import threading
import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Tuple
from uuid import uuid4


@dataclass
class GhostNode:
    """Represents a single ghost node (Sybil attack identity)."""
    device_id: str
    attacker_id: str
    name: str
    x: float
    y: float
    active: bool = True
    packets_sent: int = 0
    packets_received: int = 0
    join_attempts: int = 0
    successful_joins: int = 0
    detected_at: float | None = None


@dataclass
class AttackStatistics:
    """Tracks metrics for a single attack campaign."""
    attacker_id: str
    ghost_count: int
    intensity: float
    duration: float
    start_time: float
    end_time: float | None = None
    total_packets: int = 0
    total_join_attempts: int = 0
    successful_joins: int = 0
    detected_count: int = 0
    detection_rate: float = 0.0
    success_rate: float = 0.0


class GhostEngine:
    """Orchestrates realistic Sybil attacks with configurable attack strength."""

    def __init__(self, event_cb: Callable[[dict], None] | None = None):
        self.ghosts: Dict[str, GhostNode] = {}
        self.attacks: Dict[str, AttackStatistics] = {}
        self.attack_threads: Dict[str, threading.Thread] = {}
        self.event_cb = event_cb
        self.lock = threading.Lock()

    def spawn_attack(
        self,
        attacker_id: str,
        count: int,
        intensity: float = 1.0,
        duration: float = 60.0,
        area_size: float = 500.0,
        attacker_x: float = 0.0,
        attacker_y: float = 0.0,
    ) -> AttackStatistics:
        """
        Spawn ghost nodes controlled by attacker_id.

        Args:
            attacker_id: Unique attacker identifier (shared origin)
            count: Number of ghost nodes to create (10, 20, 50, 100, 250 supported)
            intensity: Attack strength 0.1-10.0 (controls packet rate)
            duration: Attack duration in seconds
            area_size: Area where ghosts spawn (radius from origin)
            attacker_x, attacker_y: Attacker's true position (hidden origin)

        Returns:
            AttackStatistics object tracking this campaign
        """
        stats = AttackStatistics(
            attacker_id=attacker_id,
            ghost_count=count,
            intensity=intensity,
            duration=duration,
            start_time=time.time(),
        )

        with self.lock:
            self.attacks[attacker_id] = stats

        # Generate ghost nodes with spread positions but shared attacker origin
        ghost_ids = []
        for i in range(count):
            gid = str(uuid4())
            # Spread ghosts in area around origin but remember true origin
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, area_size)
            ghost_x = attacker_x + radius * math.cos(angle)
            ghost_y = attacker_y + radius * math.sin(angle)

            node = GhostNode(
                device_id=gid,
                attacker_id=attacker_id,
                name=f"ghost-{attacker_id}-{i}",
                x=ghost_x,
                y=ghost_y,
            )
            with self.lock:
                self.ghosts[gid] = node
            ghost_ids.append(gid)

            if self.event_cb:
                self.event_cb(
                    {
                        "type": "ghost_spawn",
                        "ghost": {
                            "device_id": gid,
                            "attacker": attacker_id,
                            "name": node.name,
                            "position": (ghost_x, ghost_y),
                        },
                    }
                )

        # Start attack thread with realistic packet generation and join attempts
        def attack_thread():
            start = time.time()
            while time.time() - start < duration and attacker_id in self.attacks:
                elapsed = time.time() - start
                for gid in ghost_ids:
                    with self.lock:
                        node = self.ghosts.get(gid)
                        if not node or not node.active:
                            continue

                    # Simulate join attempts early in attack
                    if elapsed < duration * 0.2:
                        node.join_attempts += 1
                        stats.total_join_attempts += 1
                        if self.event_cb:
                            self.event_cb(
                                {
                                    "type": "ghost_join_attempt",
                                    "ghost": gid,
                                    "attacker": attacker_id,
                                    "time": elapsed,
                                }
                            )

                    # Simulate packet broadcasting (main attack activity)
                    # Intensity controls packet generation rate
                    if random.random() < intensity * 0.1:
                        node.packets_sent += 1
                        stats.total_packets += 1
                        if self.event_cb:
                            self.event_cb(
                                {
                                    "type": "ghost_packet",
                                    "ghost": gid,
                                    "attacker": attacker_id,
                                    "time": elapsed,
                                    "intensity": intensity,
                                }
                            )

                # Sleep proportional to intensity (higher intensity = more frequent activity)
                sleep_time = max(0.05, 1.0 / max(1.0, intensity))
                time.sleep(sleep_time)

            # Attack finished: calculate statistics
            with self.lock:
                if attacker_id in self.attacks:
                    attack = self.attacks[attacker_id]
                    attack.end_time = time.time()
                    detected = sum(
                        1
                        for g in self.ghosts.values()
                        if g.attacker_id == attacker_id and g.detected_at is not None
                    )
                    attack.detected_count = detected
                    attack.detection_rate = (detected / count) if count > 0 else 0.0
                    attack.success_rate = (
                        (count - detected) / count
                    ) if count > 0 else 0.0

            if self.event_cb:
                self.event_cb(
                    {
                        "type": "attack_finished",
                        "attacker": attacker_id,
                        "stats": {
                            "duration": duration,
                            "ghost_count": count,
                            "total_packets": stats.total_packets,
                            "detected": stats.detected_count,
                            "detection_rate": stats.detection_rate,
                        },
                    }
                )

        th = threading.Thread(target=attack_thread, daemon=True)
        with self.lock:
            self.attack_threads[attacker_id] = th
        th.start()

        return stats

    def stop_attack(self, attacker_id: str) -> AttackStatistics | None:
        """Stop all ghosts for this attacker and finalize statistics."""
        with self.lock:
            for g in list(self.ghosts.values()):
                if g.attacker_id == attacker_id:
                    g.active = False
            stats = self.attacks.get(attacker_id)
            if stats and stats.end_time is None:
                stats.end_time = time.time()

        if self.event_cb:
            self.event_cb({"type": "attack_stopped", "attacker": attacker_id})

        return stats

    def mark_detected(self, ghost_id: str) -> bool:
        """Mark a ghost node as detected (identified as Sybil attack)."""
        with self.lock:
            node = self.ghosts.get(ghost_id)
            if node and node.detected_at is None:
                node.detected_at = time.time()
                return True
        return False

    def list_ghosts(self) -> List[GhostNode]:
        """Return all active ghost nodes."""
        with self.lock:
            return list(self.ghosts.values())

    def list_ghosts_by_attacker(self, attacker_id: str) -> List[GhostNode]:
        """Return ghost nodes for a specific attacker."""
        with self.lock:
            return [g for g in self.ghosts.values() if g.attacker_id == attacker_id]

    def get_attack_stats(self, attacker_id: str) -> AttackStatistics | None:
        """Retrieve statistics for an attack campaign."""
        with self.lock:
            return self.attacks.get(attacker_id)

    def all_attack_stats(self) -> Dict[str, AttackStatistics]:
        """Return statistics for all active and completed attacks."""
        with self.lock:
            return dict(self.attacks)

    def get_ghost_info(self, ghost_id: str) -> Dict | None:
        """Get detailed information about a single ghost node."""
        with self.lock:
            node = self.ghosts.get(ghost_id)
            if node:
                return {
                    "device_id": node.device_id,
                    "name": node.name,
                    "attacker_id": node.attacker_id,
                    "position": (node.x, node.y),
                    "active": node.active,
                    "packets_sent": node.packets_sent,
                    "packets_received": node.packets_received,
                    "join_attempts": node.join_attempts,
                    "successful_joins": node.successful_joins,
                    "detected_at": node.detected_at,
                }
        return None
