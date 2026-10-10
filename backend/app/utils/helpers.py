"""Small utility helpers used across the backend."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any


def generate_uuid() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def to_json_serializable(obj: Any) -> str:
    return json.dumps(obj, default=str)


@contextmanager
def perf_timer(label: str = "operation"):
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        # For now we just print; real implementation should use logger
        print(f"[perf] {label} took {elapsed:.6f}s")
