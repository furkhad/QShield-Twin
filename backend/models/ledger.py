"""Ledger entry persistence model."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Integer, Text

from backend.base import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class LedgerEntry(Base):
    """A minimal ledger entry used for audit and evidence storage.

    The payload is stored as text (JSON) to keep the initial implementation simple.
    """

    __tablename__ = "ledger_entries"

    id: str = Column(String(36), primary_key=True, default=gen_uuid)
    shard_id: int = Column(Integer, nullable=False, default=0)
    entry_type: str = Column(String(64), nullable=False)
    payload: str = Column(Text, nullable=False)
    entry_hash: str = Column(String(128), nullable=True)
    previous_hash: str = Column(String(128), nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
