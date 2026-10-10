"""Append-only, sharded audit ledger with a per-shard hash chain.

The ledger stores device verification history, trust evidence and manual
actions. Records are partitioned ("sharded") across a fixed number of shards by
hashing the device id, and every record is linked to the previous record *in the
same shard* through a SHA-256 hash chain.

Scope and honesty note
----------------------
This is a **local, single-process, tamper-evident audit log**. It is *not* a
blockchain and provides *no* distributed consensus, replication, or Byzantine
fault tolerance:

- ``entry_hash`` detects accidental corruption and naive modification of
  historical entries: any change makes :meth:`verify_integrity` fail.
- An attacker with write access to the process memory (or who recomputes the
  whole chain) can still forge entries. Real tamper resistance requires signing
  each entry with a key the attacker does not hold, plus external anchoring.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class LedgerEntry:
    """Immutable record in the ledger."""

    device_id: str
    accepted: bool  # True for accepted/monitored, False for rejected/blacklisted
    timestamp: float
    reason: str  # "join" | "packet" | "verification" | "attack" | "restore" | "manual"
    evidence: Dict[str, Any]  # Verification results, metrics, etc.
    blacklisted: bool = False  # Set to True for blacklist records
    shard_id: int = 0
    prev_hash: str = ""  # hash of the previous entry in this shard
    entry_hash: str = ""  # hash of this entry (see ShardedLedger._compute_hash)


def _canonical_payload(entry: LedgerEntry) -> str:
    """Deterministic serialization of an entry used for hashing."""

    return json.dumps(
        {
            "device_id": entry.device_id,
            "accepted": entry.accepted,
            "timestamp": entry.timestamp,
            "reason": entry.reason,
            "evidence": entry.evidence,
            "blacklisted": entry.blacklisted,
            "shard_id": entry.shard_id,
            "prev_hash": entry.prev_hash,
        },
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )


class ShardedLedger:
    """Append-only audit ledger with hash-based sharding and chaining.

    Shard selection: ``shard_id = sha256(device_id)[0] % shard_count``.

    Every appended entry stores ``prev_hash`` (the previous entry's hash in the
    same shard) and ``entry_hash`` (SHA-256 over the canonical entry payload).
    :meth:`verify_integrity` recomputes the chain to detect tampering.
    """

    def __init__(self, shards: int = 8):
        if shards < 1:
            raise ValueError("shard count must be >= 1")
        self.shard_count = shards
        self.shards: Dict[int, List[LedgerEntry]] = {i: [] for i in range(shards)}
        self.device_index: Dict[str, int] = defaultdict(int)  # device_id -> entry count
        self._last_hash: Dict[int, str] = {i: "" for i in range(shards)}
        self.lock = threading.Lock()

    def _shard_for(self, device_id: str) -> int:
        """Determine which shard a device belongs to using consistent hashing."""

        h = hashlib.sha256(device_id.encode()).digest()
        return h[0] % self.shard_count

    @staticmethod
    def _compute_hash(entry: LedgerEntry) -> str:
        return hashlib.sha256(_canonical_payload(entry).encode()).hexdigest()

    def append(
        self,
        device_id: str,
        accepted: bool,
        reason: str,
        evidence: Dict[str, Any] | None = None,
        *,
        blacklisted: bool = False,
    ) -> LedgerEntry:
        """Add a record to the ledger (append-only) and chain it.

        Args:
            device_id: Device identifier.
            accepted: Whether the entry is an acceptance (True) or rejection.
            reason: Reason for this record (join, packet, verification, ...).
            evidence: Dictionary with verification results / metrics.
            blacklisted: Explicit blacklist marker for this record.

        Returns:
            The created :class:`LedgerEntry`.
        """

        shard_id = self._shard_for(device_id)
        entry = LedgerEntry(
            device_id=device_id,
            accepted=accepted,
            timestamp=time.time(),
            reason=reason,
            evidence=evidence or {},
            blacklisted=blacklisted,
            shard_id=shard_id,
        )

        with self.lock:
            entry.prev_hash = self._last_hash[shard_id]
            entry.entry_hash = self._compute_hash(entry)
            self.shards[shard_id].append(entry)
            self._last_hash[shard_id] = entry.entry_hash
            self.device_index[device_id] += 1

        return entry

    def query_device(self, device_id: str) -> List[LedgerEntry]:
        """Retrieve all ledger entries for a device (its shard only)."""

        shard_id = self._shard_for(device_id)
        with self.lock:
            return [e for e in self.shards[shard_id] if e.device_id == device_id]

    def query_recent(self, device_id: str, limit: int = 10) -> List[LedgerEntry]:
        """Retrieve most recent entries for a device."""

        entries = self.query_device(device_id)
        return entries[-limit:] if entries else []

    def blacklist(self, device_id: str, reason: str = "manual") -> LedgerEntry:
        """Blacklist a device (append a negative, blacklisted record)."""

        return self.append(
            device_id=device_id,
            accepted=False,
            reason=reason,
            evidence={"blacklisted": True, "timestamp": time.time()},
            blacklisted=True,
        )

    def restore(self, device_id: str) -> LedgerEntry:
        """Restore a blacklisted device (append a positive record)."""

        return self.append(
            device_id=device_id,
            accepted=True,
            reason="restored",
            evidence={"restored": True, "timestamp": time.time()},
        )

    def is_blacklisted(self, device_id: str) -> bool:
        """Check whether a device's most recent blacklist/restore state is blacklisted."""

        for entry in reversed(self.query_device(device_id)):
            if entry.reason == "restored":
                return False
            if entry.blacklisted:
                return True
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

    def verify_integrity(self) -> Dict[str, Any]:
        """Recompute every shard's hash chain and report any breakage.

        Returns a dict with ``valid`` (bool), ``checked`` (entries verified),
        ``broken`` (list of shard/index where the chain failed) and
        ``last_hashes`` (current head hash per shard).
        """

        broken: List[Tuple[int, int]] = []
        checked = 0
        with self.lock:
            last_hashes: Dict[int, str] = {}
            for shard_id, entries in self.shards.items():
                prev = ""
                for index, entry in enumerate(entries):
                    # Recompute with the stored prev_hash to detect field tampering.
                    expected = self._compute_hash(entry)
                    if entry.prev_hash != prev or entry.entry_hash != expected:
                        broken.append((shard_id, index))
                    prev = entry.entry_hash
                    checked += 1
                last_hashes[shard_id] = prev

        return {
            "valid": not broken,
            "checked": checked,
            "broken": broken,
            "last_hashes": last_hashes,
        }

    def stats(self) -> Dict[str, Any]:
        """Return ledger statistics."""

        with self.lock:
            total = sum(len(v) for v in self.shards.values())
            blacklisted_count = sum(
                1 for shard in self.shards.values() for entry in shard if entry.blacklisted
            )
            accepted_count = sum(
                1 for shard in self.shards.values() for entry in shard if entry.accepted
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
                "unique_devices": len({e.device_id for e in entries}),
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
        writer.writerow(
            ["device_id", "accepted", "timestamp", "reason", "blacklisted", "prev_hash", "entry_hash", "evidence"]
        )

        with self.lock:
            for shard in self.shards.values():
                for entry in shard:
                    writer.writerow(
                        [
                            entry.device_id,
                            entry.accepted,
                            entry.timestamp,
                            entry.reason,
                            entry.blacklisted,
                            entry.prev_hash,
                            entry.entry_hash,
                            str(entry.evidence),
                        ]
                    )

        return output.getvalue()
