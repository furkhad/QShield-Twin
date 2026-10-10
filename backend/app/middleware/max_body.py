"""Request body-size limiting middleware.

Rejects requests whose ``Content-Length`` exceeds the configured maximum before
the body is read, bounding memory use for user-controlled payloads. Requests
without a ``Content-Length`` (e.g. chunked transfer encoding) are not measured
here; the application-level Pydantic bounds still apply to their parsed contents.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max(1, int(max_bytes))

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "message": "Invalid Content-Length"},
                )
            if declared > self.max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"status": "error", "message": "Request body too large"},
                )
        return await call_next(request)
