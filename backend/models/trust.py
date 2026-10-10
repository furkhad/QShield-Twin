"""Trust record persistence model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text

from backend.base import Base
from backend.models._common import gen_uuid, utcnow


class TrustRecord(Base):
    """Per-device trust score and evidence reference."""

    __tablename__ = "trust_records"

    id: str = Column(String(36), primary_key=True, default=gen_uuid)
    device_id: str = Column(String(36), ForeignKey("devices.id"), nullable=False)
    score: float = Column(Float, nullable=False, default=0.0)
    reason: str = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, default=utcnow, nullable=False)
