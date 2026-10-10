"""Identity claim persistence model."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Text

from backend.base import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


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
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
