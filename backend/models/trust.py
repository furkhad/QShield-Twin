"""Trust record persistence model."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey

from backend.base import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class TrustRecord(Base):
    """Per-device trust score and evidence reference."""

    __tablename__ = "trust_records"

    id: str = Column(String(36), primary_key=True, default=gen_uuid)
    device_id: str = Column(String(36), ForeignKey("devices.id"), nullable=False)
    score: float = Column(Float, nullable=False, default=0.0)
    reason: str = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
