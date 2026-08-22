"""Generic repository base class for SQLAlchemy models.

Provides basic CRUD operations and a consistent API for concrete
repositories to extend.
"""

from __future__ import annotations

from typing import Generic, TypeVar, Type, Iterable

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """A minimal generic repository for SQLAlchemy models.

    Concrete repositories should pass a model class to the constructor.
    """

    def __init__(self, model: Type[T], session: Session) -> None:
        self.model = model
        self.session = session

    def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def get(self, obj_id: str) -> T | None:
        return self.session.get(self.model, obj_id)

    def list(self, limit: int = 100, offset: int = 0) -> Iterable[T]:
        return self.session.query(self.model).offset(offset).limit(limit).all()

    def update(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, obj_id: str) -> None:
        obj = self.get(obj_id)
        if obj:
            self.session.delete(obj)
            self.session.commit()
