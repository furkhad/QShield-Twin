"""Configuration tests to validate Pydantic settings parsing."""

from backend.settings import get_settings


def test_settings_defaults():
    cfg = get_settings()
    assert cfg.app_name == "QShield Twin"
    assert cfg.api_v1_prefix == "/api/v1"
    assert cfg.database_url is not None
