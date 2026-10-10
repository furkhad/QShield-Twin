"""Unit tests for repository implementations using in-memory SQLite."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.base import Base
from backend.models import Device
from backend.repositories.device_repository import SQLDeviceRepository


def test_device_repository_add_and_get():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        repo = SQLDeviceRepository(session)
        d = Device(name="test-device")
        saved = repo.add(d)
        assert saved.id is not None

        fetched = repo.get(saved.id)
        assert fetched is not None
        assert fetched.name == "test-device"
