"""Simple performance measurement middleware for long-running requests."""

from __future__ import annotations

from time import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time()
        response = await call_next(request)
        elapsed = time() - start
        # Attach header for basic measurement; consumers can read X-Process-Time
        response.headers["X-Process-Time"] = f"{elapsed:.6f}"
        return response
