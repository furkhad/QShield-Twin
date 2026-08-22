"""Repository base interfaces and helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Iterable

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract repository interface describing basic data operations."""

    @abstractmethod
    def add(self, obj: T) -> T:
        raise NotImplementedError

    @abstractmethod
    def get(self, obj_id: str) -> T | None:
        raise NotImplementedError

    @abstractmethod
    def list(self, limit: int = 100, offset: int = 0) -> Iterable[T]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, obj_id: str) -> None:
        raise NotImplementedError
