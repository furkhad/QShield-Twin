"""API authentication helpers.

A single shared token (``API_TOKEN``) protects state-changing and sensitive
endpoints as well as the WebSocket stream. The control is intentionally simple:
this is a research platform, not a multi-tenant identity system. When no token is
configured the API is open, which keeps local development frictionless; in
production a token is mandatory (validated in :mod:`backend.settings`).
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from backend.app.core.dependencies import get_settings_dep
from backend.settings import Settings


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def extract_presented_token(
    authorization: Optional[str], x_api_token: Optional[str]
) -> Optional[str]:
    """Pull a presented token from the ``X-API-Token`` header or Bearer header."""

    return x_api_token or _bearer_token(authorization)


def _token_matches(presented: Optional[str], configured: str) -> bool:
    if not presented:
        return False
    # Constant-time comparison to avoid trivial timing oracles. Encode to bytes
    # because compare_digest rejects non-ASCII str (a crafted header could
    # otherwise turn a 401 into a 500).
    return secrets.compare_digest(
        presented.encode("utf-8", "ignore"), configured.encode("utf-8")
    )


def require_api_token(
    authorization: Optional[str] = Header(default=None),
    x_api_token: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings_dep),
) -> None:
    """FastAPI dependency enforcing the shared API token when configured."""

    if not settings.auth_enabled or settings.api_token is None:
        return

    configured = settings.api_token.get_secret_value()
    presented = extract_presented_token(authorization, x_api_token)
    if not _token_matches(presented, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def websocket_token_ok(websocket, settings: Settings) -> bool:
    """Validate a WebSocket handshake token when one is configured.

    Browsers cannot set arbitrary headers on a WebSocket handshake, so the token
    may be supplied either as an ``Authorization``/``X-API-Token`` header or as a
    ``?token=`` query parameter.
    """

    if not settings.auth_enabled or settings.api_token is None:
        return True

    configured = settings.api_token.get_secret_value()
    presented = (
        websocket.query_params.get("token")
        or websocket.headers.get("x-api-token")
        or _bearer_token(websocket.headers.get("authorization"))
    )
    return _token_matches(presented, configured)
