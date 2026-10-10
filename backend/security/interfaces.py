"""Interfaces for pluggable security modules."""

from __future__ import annotations

from typing import Protocol, Tuple


class IPostQuantumCrypto(Protocol):
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        ...

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        ...

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        ...

    def export_public_key(self, public_key: bytes) -> bytes:
        ...

    def rotate_keys(self) -> None:
        ...

    def metrics(self) -> dict:
        ...
