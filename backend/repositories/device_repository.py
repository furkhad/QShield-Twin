"""SQL-backed device repository implementation."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from backend.repositories.base import Repository
from backend.models import Device


class SQLDeviceRepository(Repository[Device]):
    """Simple SQLAlchemy-based repository for Device model."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, obj: Device) -> Device:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def get(self, obj_id: str) -> Device | None:
        return self.session.get(Device, obj_id)

    def list(self, limit: int = 100, offset: int = 0) -> Iterable[Device]:
        return self.session.query(Device).offset(offset).limit(limit).all()

    def delete(self, obj_id: str) -> None:
        obj = self.get(obj_id)
        if obj:
            self.session.delete(obj)
            self.session.commit()
