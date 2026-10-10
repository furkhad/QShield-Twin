"""Identity claim persistence model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from backend.base import Base
from backend.models._common import gen_uuid, utcnow


class IdentityClaim(Base):
    """Represents a claimed identity or signature tied to a device.

    This table stores evidence used by trust decisions (signatures, raw payloads).
    """

    __tablename__ = "identity_claims"

    id: str = Column(String(36), primary_key=True, default=gen_uuid)
    device_id: str = Column(String(36), ForeignKey("devices.id"), nullable=False)
    claimed_id: str = Column(String(128), nullable=False)
    signature: str = Column(Text, nullable=True)
    payload: str = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, default=utcnow, nullable=False)
