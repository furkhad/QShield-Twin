"""Distributed sharded ledger for decentralized device records.

The ledger stores device verification history, trust records, and evidence.
Data is sharded (partitioned) by device_id for efficient distributed storage.

Ledger Entry contains:
- Device ID
- Timestamp
- Acceptance status (accepted/blacklisted)
- Reason (join, packet, attack, etc.)
- Evidence (verification results, metrics)

The ledger is append-only: records are never deleted, only marked as
blacklisted/restored for forensics and auditability.

Shard selection uses consistent hashing (SHA256 of device_id mod shard_count)
to ensure deterministic mapping and enable efficient distributed queries.
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Tuple
from collections import defaultdict


@dataclass
class LedgerEntry:
    """Immutable record in the ledger."""
    device_id: str
    accepted: bool  # True for accepted/monitored, False for rejected/blacklisted
    timestamp: float
    reason: str  # "join" | "packet" | "verification" | "attack" | "restore" | "manual"
    evidence: Dict[str, Any]  # Verification results, metrics, etc.
    blacklisted: bool = False  # Set to True if device is blacklisted
    shard_id: int = 0


class ShardedLedger:
    """
    Append-only distributed ledger with hash-based sharding.

    Stores device security records and verifications in shards.
    Each shard handles a partition of device space (determined by hash).

    Shard selection: shard_id = hash(device_id) % shard_count

    This enables:
    - Efficient device lookup (O(n) within shard, not O(n) globally)
    - Distributed storage (each shard can be on separate node)
    - Consistent hashing (device always maps to same shard)
    - Auditability (all records preserved)
    """

    def __init__(self, shards: int = 8):
        """
        Args:
            shards: Number of shards (typically power of 2: 4, 8, 16, 32)
        """
        self.shard_count = shards
        self.shards: Dict[int, List[LedgerEntry]] = {i: [] for i in range(shards)}
        self.device_index: Dict[str, List[int]] = defaultdict(list)  # device_id -> list of entry indices per shard
        self.lock = threading.Lock()

    def _shard_for(self, device_id: str) -> int:
        """
        Determine which shard a device belongs to using consistent hashing.

        Uses SHA256 for deterministic, uniform distribution.
        """
        h = hashlib.sha256(device_id.encode()).digest()
        return h[0] % self.shard_count

    def append(
        self,
        device_id: str,
        accepted: bool,
        reason: str,
        evidence: Dict[str, Any] | None = None,
    ) -> LedgerEntry:
        """
        Add a record to the ledger (append-only).

        Args:
            device_id: Device identifier
            accepted: Whether device is accepted (True) or rejected (False)
            reason: Reason for this record (join, packet, verification, attack, etc.)
            evidence: Dictionary with verification results, metrics, etc.

        Returns:
            The created LedgerEntry
        """
        shard_id = self._shard_for(device_id)
        entry = LedgerEntry(
            device_id=device_id,
            accepted=accepted,
            timestamp=time.time(),
            reason=reason,
            evidence=evidence or {},
            shard_id=shard_id,
        )

        with self.lock:
            self.shards[shard_id].append(entry)
            self.device_index[device_id].append(len(self.shards[shard_id]) - 1)

        return entry

    def query_device(self, device_id: str) -> List[LedgerEntry]:
        """
        Retrieve all ledger entries for a device.

        Searches only the device's assigned shard (O(n) within shard).

        Args:
            device_id: Device identifier

        Returns:
            List of LedgerEntry objects for this device
        """
        shard_id = self._shard_for(device_id)
        with self.lock:
            return [
                e for e in self.shards[shard_id]
                if e.device_id == device_id
            ]

    def query_recent(self, device_id: str, limit: int = 10) -> List[LedgerEntry]:
        """Retrieve most recent entries for a device."""
        entries = self.query_device(device_id)
        return entries[-limit:] if entries else []

    def blacklist(self, device_id: str, reason: str = "manual") -> LedgerEntry:
        """
        Blacklist a device (mark as untrusted).

        Creates a new ledger entry with blacklist flag set.
        Device cannot be accepted again without explicit restore.

        Args:
            device_id: Device identifier
            reason: Reason for blacklisting

        Returns:
            The blacklist LedgerEntry
        """
        entry = self.append(
            device_id=device_id,
            accepted=False,
            reason=reason,
            evidence={"blacklisted": True, "timestamp": time.time()},
        )
        # Mark the entry as blacklisted
        entry.blacklisted = True
        return entry

    def restore(self, device_id: str) -> LedgerEntry:
        """
        Restore a blacklisted device (mark as trustworthy again).

        Creates a new ledger entry indicating restoration.
        The blacklist is recorded but a new positive entry is added.

        Args:
            device_id: Device identifier

        Returns:
            The restore LedgerEntry
        """
        return self.append(
            device_id=device_id,
            accepted=True,
            reason="restored",
            evidence={"restored": True, "timestamp": time.time()},
        )

    def is_blacklisted(self, device_id: str) -> bool:
        """Check if device is currently blacklisted."""
        entries = self.query_device(device_id)
        # Find last blacklist/restore action
        for entry in reversed(entries):
            if entry.reason in ("manual", "attack", "restored"):
                return entry.blacklisted or (entry.reason == "manual" and not entry.accepted)
        return False

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current status of a device."""
        entries = self.query_device(device_id)
        if not entries:
            return {"device_id": device_id, "status": "unknown", "record_count": 0}

        latest = entries[-1]
        blacklisted = self.is_blacklisted(device_id)
        accepted_count = sum(1 for e in entries if e.accepted)
        rejected_count = sum(1 for e in entries if not e.accepted)

        return {
            "device_id": device_id,
            "status": "blacklisted" if blacklisted else ("accepted" if latest.accepted else "rejected"),
            "record_count": len(entries),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "last_updated": latest.timestamp,
            "last_reason": latest.reason,
        }

    def stats(self) -> Dict[str, Any]:
        """Return ledger statistics."""
        with self.lock:
            total = sum(len(v) for v in self.shards.values())
            blacklisted_count = sum(
                1 for shard in self.shards.values()
                for entry in shard
                if entry.blacklisted
            )
            accepted_count = sum(
                1 for shard in self.shards.values()
                for entry in shard
                if entry.accepted
            )

            shard_sizes = {i: len(self.shards[i]) for i in range(self.shard_count)}
            avg_shard_size = total / self.shard_count if self.shard_count > 0 else 0

        return {
            "shards": self.shard_count,
            "total_entries": total,
            "average_shard_size": avg_shard_size,
            "shard_sizes": shard_sizes,
            "accepted_entries": accepted_count,
            "rejected_entries": total - accepted_count,
            "blacklisted_count": blacklisted_count,
            "unique_devices": len(self.device_index),
        }

    def shard_stats(self, shard_id: int) -> Dict[str, Any]:
        """Return statistics for a specific shard."""
        with self.lock:
            if shard_id not in self.shards:
                return {"shard_id": shard_id, "error": "invalid shard"}

            entries = self.shards[shard_id]
            accepted = sum(1 for e in entries if e.accepted)
            rejected = len(entries) - accepted

            return {
                "shard_id": shard_id,
                "entries": len(entries),
                "accepted": accepted,
                "rejected": rejected,
                "blacklisted": sum(1 for e in entries if e.blacklisted),
                "unique_devices": len(set(e.device_id for e in entries)),
            }

    def export_entries(self, device_id: str | None = None) -> List[Dict[str, Any]]:
        """Export ledger entries as dictionaries (for JSON/CSV)."""
        if device_id:
            entries = self.query_device(device_id)
        else:
            with self.lock:
                entries = []
                for shard in self.shards.values():
                    entries.extend(shard)

        return [asdict(e) for e in entries]

    def export_csv(self, filepath: str | None = None) -> str:
        """Export ledger as CSV format."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "device_id", "accepted", "timestamp", "reason",
            "blacklisted", "evidence"
        ])

        with self.lock:
            for shard in self.shards.values():
                for entry in shard:
                    writer.writerow([
                        entry.device_id,
                        entry.accepted,
                        entry.timestamp,
                        entry.reason,
                        entry.blacklisted,
                        str(entry.evidence),
                    ])

        return output.getvalue()
