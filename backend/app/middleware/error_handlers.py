"""Global API error handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.core.exceptions import (
    APIException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
)

logger = logging.getLogger(__name__)


def _error_payload(message: str, *, errors: Any | None = None) -> dict:
    payload: dict[str, Any] = {"status": "error", "message": message}
    if errors is not None:
        payload["errors"] = errors
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    """Register consistent JSON handlers for common API failures."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload("Validation error", errors=exc.errors()),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_payload(str(exc.detail)))

    @app.exception_handler(APIException)
    async def api_exception_handler(_: Request, exc: APIException) -> JSONResponse:
        logger.warning("API exception: %s", exc)
        return JSONResponse(status_code=exc.status_code, content=_error_payload(str(exc), errors=getattr(exc, "payload", None)))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error: %s", exc)
        return JSONResponse(status_code=500, content=_error_payload("Internal server error"))
