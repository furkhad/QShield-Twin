"""Application settings backed by environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration for the backend service.

    Read values from a `.env` file when present. These settings are strongly
    typed so downstream components receive correct values.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "QShield Twin"
    app_version: str = "0.1.0"
    description: str = "Digital Twin cybersecurity research platform"
    environment: str = "development"
    debug: bool = False

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_hosts: List[str] = Field(default_factory=lambda: ["localhost"])
    cors_origins: List[AnyHttpUrl] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Database
    database_url: str = "sqlite:///./qshield_twin.db"

    # Security
    secret_key: SecretStr = SecretStr("change-me-in-production")

    # Logging
    log_level: str = "INFO"

    # Research / Simulation
    research_mode: bool = False
    simulation_speed: float = 1.0

    # Future integrations
    pqc_library_path: Optional[str] = None
    mqtt_broker_url: Optional[str] = None
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
