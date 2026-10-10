"""Regression guard: the browser bundle must not carry the backend API token.

Vite inlines every ``VITE_``-prefixed environment variable into the client
bundle, so a ``VITE_API_TOKEN`` would be public to every visitor. The token is
instead injected server-side by the Vite dev proxy (development) or a reverse
proxy (production). These static checks catch a regression that reintroduces a
client-side token, without paying for a full frontend build.

The build-level check lives in ``frontend/scripts/check-bundle-secrets.mjs``
(``npm run check:secrets``) and is run in CI.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_SRC = _ROOT / "frontend" / "src"
_VITE_CONFIG = _ROOT / "frontend" / "vite.config.ts"


def _src_files() -> list[Path]:
    return [p for p in _FRONTEND_SRC.rglob("*") if p.is_file()]


def test_client_source_has_no_vite_token_reference():
    """No ``import.meta.env.VITE_*TOKEN`` access (which Vite would inline)."""
    pattern = re.compile(r"import\.meta\.env\.VITE_[A-Z0-9_]*TOKEN")
    offenders = [
        p for p in _src_files() if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"client source accesses a VITE_ token: {offenders}"


def test_client_source_has_no_api_token_header_literal():
    """The browser code must not set an API-token header itself."""
    pattern = re.compile(r"""["']X-API-Token["']""")
    offenders = [
        p
        for p in _src_files()
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"client source sets an API-token header: {offenders}"


def test_vite_config_injects_token_server_side_only():
    config = _VITE_CONFIG.read_text(encoding="utf-8")
    # The proxy reads a non-VITE token variable (server-side) ...
    assert "QSHIELD_API_TOKEN" in config
    assert "X-API-Token" in config
    # ... and must not reference a VITE_-prefixed token.
    assert "VITE_API_TOKEN" not in config


def test_frontend_env_example_documents_server_side_token_only():
    env_example = (_ROOT / "frontend" / ".env.example").read_text(encoding="utf-8")
    assert "VITE_API_TOKEN" not in env_example
    assert "QSHIELD_API_TOKEN" in env_example
