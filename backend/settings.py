"""Application settings backed by environment variables.

Configuration is centralized here and validated at load time. In ``production``
the application refuses to start with unsafe defaults (placeholder secrets,
debug mode, wildcard CORS/hosts, or a SQLite database), so security-critical
misconfiguration fails fast instead of silently shipping.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "change-me-in-production"
_PLACEHOLDER_SECRETS = {_DEFAULT_SECRET, "", "changeme", "secret"}


class Settings(BaseSettings):
    """Centralized, validated runtime configuration for the backend service.

    Values are read from the process environment and, when present, a local
    ``.env`` file (see ``.env.example`` for the supported keys).
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    app_name: str = "QShield Twin"
    app_version: str = "0.2.0"
    description: str = "Digital Twin cybersecurity research platform"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    # API
    api_v1_prefix: str = "/api/v1"
    # Restrict accepted Host headers. "*" is convenient for local development;
    # production must list explicit hosts (enforced below).
    allowed_hosts: List[str] = Field(default_factory=lambda: ["*"])
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Database
    database_url: str = "sqlite:///./qshield_twin.db"

    # Security
    secret_key: SecretStr = SecretStr(_DEFAULT_SECRET)
    # Optional shared token protecting state-changing/sensitive API and the
    # WebSocket stream. Unset (the default) keeps local development frictionless;
    # production requires a strong token (enforced below).
    api_token: SecretStr | None = None

    # Request / connection protection.
    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=600, ge=1, le=1_000_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=86_400)
    max_request_bytes: int = Field(default=1_000_000, ge=1024, le=100_000_000)
    max_ws_connections: int = Field(default=50, ge=1, le=10_000)

    # Logging
    log_level: str = "INFO"

    # Research / Simulation
    research_mode: bool = False
    simulation_speed: float = 1.0
    random_seed: int | None = None

    # Resource limits for user-controlled state-changing operations.
    max_devices_per_request: int = Field(default=1000, ge=1, le=100_000)
    max_ghosts_per_attack: int = Field(default=1000, ge=0, le=100_000)

    # Future integrations (unused placeholders, kept explicit and typed).
    pqc_library_path: str | None = None
    mqtt_broker_url: str | None = None
    mqtt_username: str | None = None
    mqtt_password: SecretStr | None = None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def auth_enabled(self) -> bool:
        """Whether a shared API token is configured and enforced."""
        return bool(self.api_token and self.api_token.get_secret_value())

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        """Reject dangerous configuration when running in production."""

        if not self.is_production:
            return self

        problems: list[str] = []
        if self.secret_key.get_secret_value() in _PLACEHOLDER_SECRETS:
            problems.append(
                "SECRET_KEY must be set to a strong, unique value in production."
            )
        if self.api_token is None or self.api_token.get_secret_value() in _PLACEHOLDER_SECRETS:
            problems.append(
                "API_TOKEN must be set to a strong, unique value in production."
            )
        if self.debug:
            problems.append("DEBUG must be disabled in production.")
        if "*" in self.cors_origins:
            problems.append(
                "CORS_ORIGINS must not contain '*' when credentials are allowed."
            )
        if "*" in self.allowed_hosts:
            problems.append("ALLOWED_HOSTS must list explicit hosts in production.")
        if self.database_url.startswith("sqlite"):
            problems.append(
                "DATABASE_URL must point to a networked database in production "
                "(SQLite is not supported for production deployments)."
            )

        if problems:
            raise ValueError(
                "Unsafe production configuration: " + " ".join(problems)
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
