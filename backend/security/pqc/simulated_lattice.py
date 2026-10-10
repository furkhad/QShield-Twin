"""Simulated lattice-based post-quantum cryptography (PQC).

Implements the IPostQuantumCrypto interface with simulated operations.
This is NOT a real cryptographic implementation—it's a simulation that:
- Generates synthetic keypairs
- Measures realistic operation timings (keygen, sign, verify)
- Collects metrics for performance analysis
- Maintains interface compatibility for future replacement with liboqs-python

Real PQC (CRYSTALS-Kyber, CRYSTALS-Dilithium) can replace this module
without changing orchestrator or other dependent code.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Tuple, Dict, List, Any
from collections import deque

from backend.security.interfaces import IPostQuantumCrypto


@dataclass
class KeyPair:
    """Represents a simulated lattice-based keypair."""
    public_key: bytes
    private_key: bytes
    algorithm: str = "simulated-ntru"
    key_size_bits: int = 2048
    generation_time_ms: float = 0.0
    created_at: float = 0.0


@dataclass
class Signature:
    """Represents a simulated lattice signature."""
    signature: bytes
    device_id: str
    message_hash: bytes
    signed_at: float
    sign_time_ms: float = 0.0
    signature_size_bytes: int = 0


class SimulatedLatticeCrypto:
    """
    Simulated lattice-based post-quantum cryptography implementation.

    This module provides:
    1. Keypair generation with synthetic cost
    2. Message signing with realistic timing
    3. Signature verification
    4. Key rotation
    5. Performance metrics collection

    The interface matches IPostQuantumCrypto so it can be replaced
    with real PQC (e.g., via liboqs-python) without changing dependent code.
    """

    def __init__(self, algorithm: str = "simulated-ntru", history_size: int = 1000):
        """
        Args:
            algorithm: PQC algorithm name (for identification)
            history_size: Keep history of last N operations for metrics
        """
        self.algorithm = algorithm
        self.last_keypair: Tuple[bytes, bytes] | None = None
        self.device_id: str | None = None

        # Metrics tracking
        self.keygen_times_ms: deque = deque(maxlen=history_size)
        self.sign_times_ms: deque = deque(maxlen=history_size)
        self.verify_times_ms: deque = deque(maxlen=history_size)
        self.signature_sizes_bytes: deque = deque(maxlen=history_size)
        self.verify_results: deque = deque(maxlen=history_size)

        # For tracking signing and verification operations
        self.signatures_generated: int = 0
        self.signatures_verified: int = 0
        self.verification_failures: int = 0

        self.lock = __import__("threading").Lock()

    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate a lattice-based keypair.

        Simulates the cost of keygen with synthetic timing.
        Real lattice-based schemes (CRYSTALS-Kyber, NTRU) take 0.1-1.0ms.

        Returns:
            (public_key, private_key) as byte tuples
        """
        start = time.time()

        # Simulate keygen cost (~10ms for lattice schemes)
        # This is realistic for CRYSTALS-Kyber or similar
        time.sleep(0.01)

        # Generate deterministic but unpredictable key material.
        # The first 32 bytes act as a shared simulation seed so the
        # signer/verifier can agree on the derived authenticity check.
        key_material = os.urandom(256)
        shared_seed = hashlib.sha256(key_material).digest()
        public = shared_seed + hashlib.sha256(shared_seed + b"public").digest()
        private = shared_seed + hashlib.sha256(shared_seed + b"private").digest() + os.urandom(64)

        elapsed_ms = (time.time() - start) * 1000

        with self.lock:
            self.last_keypair = (public, private)
            self.keygen_times_ms.append(elapsed_ms)

        return public, private

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """
        Sign a message with the private key.

        In a real lattice scheme, this computes a lattice-based signature.
        Here we simulate the operation and timing.

        Args:
            private_key: Private key bytes
            message: Message to sign

        Returns:
            Signature bytes
        """
        start = time.time()

        # Simulate signing cost (~2ms for CRYSTALS-Dilithium)
        time.sleep(0.002)

        # Deterministic signature (hash-based simulation)
        # In reality: lattice signature computation.
        message_hash = hashlib.sha256(message).digest()
        sig_material = hashlib.sha256(private_key[:32] + message_hash).digest()
        signature = sig_material + os.urandom(96)  # Typical sig size ~2400 bytes

        elapsed_ms = (time.time() - start) * 1000
        sig_size = len(signature)

        with self.lock:
            self.sign_times_ms.append(elapsed_ms)
            self.signature_sizes_bytes.append(sig_size)
            self.signatures_generated += 1

        return signature

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """
        Verify a message signature.

        In a real lattice scheme, this performs lattice arithmetic to verify
        the signature against the public key and message.

        Args:
            public_key: Public key bytes
            message: Original message
            signature: Signature bytes to verify

        Returns:
            True if signature is valid, False otherwise
        """
        start = time.time()

        # Simulate verification cost (~1ms for CRYSTALS-Dilithium)
        time.sleep(0.001)

        # Simulated verification: check if signature derives from the shared
        # simulation seed embedded in the public key and message.
        message_hash = hashlib.sha256(message).digest()
        expected_sig_prefix = hashlib.sha256(public_key[:32] + message_hash).digest()

        # Check if signature starts with expected prefix (simple simulation)
        # Real verification would use lattice arithmetic
        result = signature[:len(expected_sig_prefix)] == expected_sig_prefix

        elapsed_ms = (time.time() - start) * 1000

        with self.lock:
            self.verify_times_ms.append(elapsed_ms)
            self.signatures_verified += 1
            self.verify_results.append(result)
            if not result:
                self.verification_failures += 1

        return result

    def export_public_key(self, public_key: bytes) -> bytes:
        """Export public key in serializable form (already bytes)."""
        return public_key

    def rotate_keys(self) -> Tuple[bytes, bytes]:
        """
        Rotate keys (generate new keypair and discard old one).

        Useful for regular key rotation to limit exposure.
        """
        return self.generate_keypair()

    def metrics(self) -> Dict[str, Any]:
        """
        Return performance and operation metrics.

        Useful for analyzing PQC overhead and research.

        Returns:
            Dictionary with statistics on keygen, sign, verify operations
        """
        with self.lock:
            keygen_times = list(self.keygen_times_ms)
            sign_times = list(self.sign_times_ms)
            verify_times = list(self.verify_times_ms)
            sig_sizes = list(self.signature_sizes_bytes)

            def avg_if_populated(lst):
                return (sum(lst) / len(lst)) if lst else 0.0

            return {
                "algorithm": self.algorithm,
                "keypair_generation_ms": {
                    "count": len(keygen_times),
                    "avg": avg_if_populated(keygen_times),
                    "min": min(keygen_times) if keygen_times else 0,
                    "max": max(keygen_times) if keygen_times else 0,
                },
                "signature_generation_ms": {
                    "count": self.signatures_generated,
                    "avg": avg_if_populated(sign_times),
                    "min": min(sign_times) if sign_times else 0,
                    "max": max(sign_times) if sign_times else 0,
                },
                "signature_verification_ms": {
                    "count": self.signatures_verified,
                    "avg": avg_if_populated(verify_times),
                    "min": min(verify_times) if verify_times else 0,
                    "max": max(verify_times) if verify_times else 0,
                    "failures": self.verification_failures,
                    "failure_rate": (
                        self.verification_failures / self.signatures_verified
                        if self.signatures_verified > 0
                        else 0.0
                    ),
                },
                "signature_size_bytes": {
                    "avg": avg_if_populated(sig_sizes),
                    "min": min(sig_sizes) if sig_sizes else 0,
                    "max": max(sig_sizes) if sig_sizes else 0,
                },
                "total_operations": self.signatures_generated + self.signatures_verified,
            }
