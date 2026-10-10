"""Custom domain exceptions for the backend service.

These exceptions are lightweight and carry HTTP status codes and optional
payloads for uniform error responses.
"""

from __future__ import annotations

from typing import Any


class APIException(Exception):
    """Generic API exception with an attached status code and payload."""

    status_code: int = 500

    def __init__(self, message: str, *, status_code: int | None = None, payload: Any | None = None) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload


class ValidationException(APIException):
    status_code = 400


class AuthenticationException(APIException):
    status_code = 401


class AuthorizationException(APIException):
    status_code = 403


class NotFoundException(APIException):
    status_code = 404


class SimulationException(APIException):
    status_code = 500


class SecurityException(APIException):
    status_code = 401


class ResearchException(APIException):
    status_code = 500


class LedgerException(APIException):
    status_code = 500
