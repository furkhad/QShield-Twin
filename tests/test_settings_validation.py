"""Tests for environment-aware configuration validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.settings import Settings

_SAFE = dict(
    environment="production",
    secret_key="a-strong-unique-secret",
    api_token="a-strong-unique-api-token",
    debug=False,
    cors_origins=["https://dashboard.example.com"],
    allowed_hosts=["dashboard.example.com"],
    database_url="postgresql://user:pass@db.internal:5432/qshield",
)


def test_development_allows_local_defaults():
    settings = Settings(environment="development")
    assert settings.is_production is False


def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError):
        Settings(**{**_SAFE, "secret_key": "change-me-in-production"})


def test_production_rejects_debug():
    with pytest.raises(ValidationError):
        Settings(**{**_SAFE, "debug": True})


def test_production_rejects_sqlite_database():
    with pytest.raises(ValidationError):
        Settings(**{**_SAFE, "database_url": "sqlite:///./qshield_twin.db"})


def test_production_rejects_missing_api_token():
    with pytest.raises(ValidationError):
        Settings(**{**_SAFE, "api_token": None})


def test_development_allows_missing_api_token():
    settings = Settings(environment="development")
    assert settings.auth_enabled is False


def test_api_token_enables_auth():
    settings = Settings(environment="test", api_token="an-api-token")
    assert settings.auth_enabled is True


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError):
        Settings(**{**_SAFE, "cors_origins": ["*"]})


def test_valid_production_configuration_passes():
    settings = Settings(**_SAFE)
    assert settings.is_production is True
    assert settings.secret_key.get_secret_value() == "a-strong-unique-secret"
