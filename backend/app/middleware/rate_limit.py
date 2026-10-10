"""In-process rate limiting middleware.

A fixed-window counter keyed by client address protects the API from accidental
or malicious request floods. It is intentionally lightweight and dependency-free
and is *not* a substitute for an edge/gateway rate limiter in production; see the
security notes in ``docs/ENGINEERING_AUDIT.md``.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Iterable, List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        limit: int = 600,
        window_seconds: int = 60,
        exempt_paths: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.limit = max(1, int(limit))
        self.window = max(1, int(window_seconds))
        self.exempt_paths = set(exempt_paths or ())
        self._lock = threading.Lock()
        self._hits: Dict[str, List[float]] = {}

    def _client_key(self, request: Request) -> str:
        client = request.client
        return client.host if client else "unknown"

    def _is_limited(self, key: str, now: float) -> bool:
        window_start = now - self.window
        with self._lock:
            hits = [t for t in self._hits.get(key, ()) if t > window_start]
            if len(hits) >= self.limit:
                self._hits[key] = hits
                return True
            hits.append(now)
            self._hits[key] = hits
            return False

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if path in self.exempt_paths or path.endswith("/health"):
            return await call_next(request)

        if self._is_limited(self._client_key(request), time.monotonic()):
            return JSONResponse(
                status_code=429,
                content={"status": "error", "message": "Too many requests"},
                headers={"Retry-After": str(self.window)},
            )

        return await call_next(request)
