"""Device persistence models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, String

from backend.base import Base
from backend.models._common import gen_uuid, utcnow


class Device(Base):
    """Represents a virtual IoT device in the digital twin.

    Fields are intentionally minimal and designed to be extended.
    """

    __tablename__ = "devices"

    id: str = Column(String(36), primary_key=True, default=gen_uuid)
    name: str = Column(String(128), nullable=False)
    model: str = Column(String(64), nullable=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(DateTime, default=utcnow, nullable=False)
    last_seen: datetime = Column(DateTime, default=utcnow, nullable=False)

    # Simulated physical coordinates (meters). Optional for initial models.
    pos_x: float = Column(Float, default=0.0, nullable=False)
    pos_y: float = Column(Float, default=0.0, nullable=False)
