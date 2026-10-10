"""Tests for the sharded audit ledger's hash chain and tamper detection."""

from __future__ import annotations

import threading

from backend.security.ledger.sharded_ledger import ShardedLedger


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
