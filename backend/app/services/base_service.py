"""Generic service layer base class.

Services encapsulate business logic and orchestrate repositories. Routes
should depend on services rather than repositories directly.
"""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class BaseService(Generic[T]):
    """Base service exposing common CRUD operations.

    Concrete services receive repositories via constructor injection.
    """

    def __init__(self, repository) -> None:
        self.repository = repository

    def create(self, obj: T) -> T:
        return self.repository.create(obj)

    def get(self, obj_id: str) -> T | None:
        return self.repository.get(obj_id)

    def list(self, limit: int = 100, offset: int = 0):
        return self.repository.list(limit=limit, offset=offset)

    def update(self, obj: T) -> T:
        return self.repository.update(obj)

    def delete(self, obj_id: str) -> None:
        return self.repository.delete(obj_id)
