"""Application configuration via Pydantic Settings.

Provides strongly-typed, environment-variable-driven configuration
with validation, defaults, and .env file support.

Example:
    >>> from ocr_platform.config import settings
    >>> settings.app_name
    'OCR Benchmark Platform'
    >>> settings.debug
    False
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name: Human-readable application name.
        app_env: Deployment environment (development, staging, production).
        app_version: Semantic version string.
        debug: Enable debug mode with verbose output.
        log_level: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format (json, console).
        host: Bind address for the HTTP server.
        port: Bind port for the HTTP server.
        redis_url: Redis connection URL for task queues.
        database_url: PostgreSQL async connection URL.
        mistral_api_key: API key for Mistral OCR (optional, future milestone).
        frontend_url: URL of the frontend dashboard for CORS.
    """

    # Application
    app_name: str = Field(default="OCR Benchmark Platform", description="Application name")
    app_env: str = Field(default="development", description="Deployment environment")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode flag")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Logging format")

    # Server
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, description="Server bind port")

    # Infrastructure
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    database_url: str | None = Field(default=None, description="PostgreSQL async URL")

    # OCR Providers (optional until Milestone 3)
    mistral_api_key: str | None = Field(default=None, description="Mistral OCR API key")

    # Frontend
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL")

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra env vars without crashing
        case_sensitive=False,
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _validate_log_level(cls, value: str | None) -> str:
        """Normalize and validate logging level.

        Args:
            value: Raw log level string from environment.

        Returns:
            Uppercase log level string.

        Raises:
            ValueError: If the log level is not recognized.
        """
        if not value:
            return "INFO"
        level = str(value).upper().strip()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in valid_levels:
            raise ValueError(
                f"Invalid log level '{level}'. "
                f"Expected one of: {', '.join(sorted(valid_levels))}"
            )
        return level

    @field_validator("log_format", mode="before")
    @classmethod
    def _validate_log_format(cls, value: str | None) -> str:
        """Validate logging format.

        Args:
            value: Raw log format string.

        Returns:
            Lowercase format string.

        Raises:
            ValueError: If the format is not recognized.
        """
        if not value:
            return "json"
        fmt = str(value).lower().strip()
        valid_formats = {"json", "console"}
        if fmt not in valid_formats:
            raise ValueError(
                f"Invalid log format '{fmt}'. "
                f"Expected one of: {', '.join(sorted(valid_formats))}"
            )
        return fmt

    @field_validator("app_env", mode="before")
    @classmethod
    def _validate_app_env(cls, value: str | None) -> str:
        """Normalize environment name.

        Args:
            value: Raw environment string.

        Returns:
            Lowercase environment name.
        """
        if not value:
            return "development"
        return str(value).lower().strip()


# Singleton instance — imported throughout the application
settings = Settings()
