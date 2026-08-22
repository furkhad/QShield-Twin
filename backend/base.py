"""Shared SQLAlchemy base class."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base used by all database models."""

