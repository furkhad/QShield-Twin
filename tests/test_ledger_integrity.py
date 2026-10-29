"""Tests for the sharded audit ledger's hash chain and tamper detection."""

from __future__ import annotations

import threading
import uuid

import pytest

from backend.security.ledger.sharded_ledger import (
    LedgerPersistenceError,
    ShardedLedger,
)


def _fresh_ledger() -> ShardedLedger:
    ledger = ShardedLedger(shards=8)
    for i in range(20):
        ledger.append(
            device_id=f"device-{i}",
            accepted=(i % 3 != 0),
            reason="join",
            evidence={"index": i, "score": 0.5 + i / 100},
        )
    return ledger


def test_fresh_ledger_is_valid():
    ledger = _fresh_ledger()
    result = ledger.verify_integrity()
    assert result["valid"] is True
    assert result["broken"] == []
    assert result["checked"] == 20


def test_tampered_entry_is_detected():
    ledger = _fresh_ledger()
    # Tamper with a stored entry's evidence without recomputing its hash.
    victim = ledger.shards[ledger._shard_for("device-5")][0]
    victim.evidence["score"] = 0.99

    result = ledger.verify_integrity()
    assert result["valid"] is False
    assert len(result["broken"]) >= 1


def test_deleted_entry_breaks_chain():
    ledger = _fresh_ledger()
    shard_id = ledger._shard_for("device-7")
    # Drop the first entry of the shard; the next entry's prev_hash no longer
    # links to the (now missing) predecessor.
    if len(ledger.shards[shard_id]) >= 2:
        del ledger.shards[shard_id][0]
        result = ledger.verify_integrity()
        assert result["valid"] is False


def test_blacklist_and_restore_status():
    ledger = ShardedLedger(shards=8)
    ledger.append("dev-1", accepted=True, reason="join")
    assert ledger.is_blacklisted("dev-1") is False

    ledger.blacklist("dev-1", reason="attack")
    assert ledger.is_blacklisted("dev-1") is True

    ledger.restore("dev-1")
    assert ledger.is_blacklisted("dev-1") is False
    # Integrity must hold across blacklist/restore transitions too.
    assert ledger.verify_integrity()["valid"] is True


def test_concurrent_writes_preserve_integrity():
    ledger = ShardedLedger(shards=8)

    def worker(offset: int) -> None:
        for i in range(50):
            ledger.append(f"dev-{offset}-{i}", accepted=True, reason="packet")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    result = ledger.verify_integrity()
    assert result["valid"] is True
    assert result["checked"] == 200


def test_default_ledger_remains_in_memory_and_isolated():
    """Standalone/default instances must not silently become persistent."""
    ledger1 = ShardedLedger(shards=8)
    ledger1.append("dev-1", accepted=True, reason="join")
    ledger1.append("dev-2", accepted=False, reason="reject")
    assert ledger1._persist is False
    assert ledger1.verify_integrity()["valid"] is True
    # A second default instance is independent and starts empty.
    ledger2 = ShardedLedger(shards=8)
    assert ledger2._persist is False
    assert ledger2.verify_integrity()["valid"] is True
    assert len([e for s in ledger2.shards.values() for e in s]) == 0


def _entry_count(ledger: ShardedLedger) -> int:
    return sum(len(entries) for entries in ledger.shards.values())


def test_persistent_ledger_restores_without_duplication_and_accepts_new_entries():
    """A real persistent ledger must restore its exact chains after a rebuild."""
    device_id = f"persist-{uuid.uuid4().hex}"
    ledger1 = ShardedLedger(shards=8, persist=True)
    baseline = _entry_count(ledger1)

    first = ledger1.append(device_id, accepted=True, reason="join")
    ledger2 = ShardedLedger(shards=8, persist=True)

    restored = ledger2.query_device(device_id)
    assert len(restored) == 1
    assert restored[0].entry_hash == first.entry_hash
    assert restored[0].prev_hash == first.prev_hash
    assert _entry_count(ledger2) == baseline + 1
    assert ledger2.verify_integrity()["valid"] is True

    second = ledger2.append(device_id, accepted=False, reason="verification")
    ledger3 = ShardedLedger(shards=8, persist=True)

    restored_after_second = ledger3.query_device(device_id)
    assert [entry.entry_hash for entry in restored_after_second] == [
        first.entry_hash,
        second.entry_hash,
    ]
    assert second.prev_hash == first.entry_hash
    assert _entry_count(ledger3) == baseline + 2
    assert ledger3.verify_integrity()["valid"] is True


def test_failed_persistent_write_does_not_advance_in_memory_chain(monkeypatch):
    """A storage failure must leave the chain and its head hash untouched."""
    ledger = ShardedLedger(shards=8, persist=True)
    device_id = f"write-failure-{uuid.uuid4().hex}"
    shard_id = ledger._shard_for(device_id)
    before_count = _entry_count(ledger)
    before_head = ledger._last_hash[shard_id]

    def fail(_entry):
        raise LedgerPersistenceError("simulated storage failure")

    monkeypatch.setattr(ledger, "_persist_entry", fail)

    with pytest.raises(LedgerPersistenceError):
        ledger.append(device_id, accepted=True, reason="join")

    assert _entry_count(ledger) == before_count
    assert ledger._last_hash[shard_id] == before_head
    assert ledger.query_device(device_id) == []
    assert ledger.verify_integrity()["valid"] is True


def test_persistent_ledger_never_silently_falls_back(monkeypatch):
    """Initialization errors must propagate as LedgerPersistenceError."""
    import backend.security.ledger.sharded_ledger as ledger_module

    def fail():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(ledger_module, "init_db", fail)

    with pytest.raises(LedgerPersistenceError, match="schema"):
        ShardedLedger(shards=8, persist=True)
