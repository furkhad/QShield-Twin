"""Ledger entry persistence model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.base import Base
from backend.models._common import gen_uuid, utcnow


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
    created_at: datetime = Column(DateTime, default=utcnow, nullable=False)
