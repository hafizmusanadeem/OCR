"""Placeholder tests to verify the test suite infrastructure.

These tests ensure pytest, coverage, and imports are wired correctly.
They will be replaced with real domain tests in subsequent milestones.
"""

from __future__ import annotations

import pytest

import ocr_platform
from src.ocr_platform import __version__
from src.ocr_platform.config import Settings, settings
from src.ocr_platform.logging_config import configure_logging, get_logger


class TestPackage:
    """Sanity checks for the top-level package."""

    def test_version_is_string(self) -> None:
        assert isinstance(__version__, str)
        assert __version__ == "0.1.0"

    def test_package_exports(self) -> None:  # noqa: D102
        assert ocr_platform.config is not None
        assert ocr_platform.logging_config is not None


class TestSettings:
    """Tests for the Pydantic-based configuration."""

    def test_default_settings(self) -> None:
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.app_name == "OCR Benchmark Platform"
        assert s.app_env == "development"
        assert s.app_version == "0.1.0"
        assert s.debug is False
        assert s.log_level == "INFO"
        assert s.log_format == "json"
        assert s.host == "0.0.0.0"
        assert s.port == 8000  # noqa: PLR2004
        assert s.redis_url == "redis://localhost:6379/0"
        assert s.database_url is None
        assert s.mistral_api_key is None
        assert s.frontend_url == "http://localhost:3000"

    def test_settings_singleton_exists(self) -> None:
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_log_level_validation(self) -> None:
        s = Settings(log_level="DEBUG")
        assert s.log_level == "DEBUG"

        s = Settings(log_level="error")
        assert s.log_level == "ERROR"

    def test_log_level_validation_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid log level"):
            Settings(log_level="VERBOSE")

    def test_log_format_validation(self) -> None:
        s = Settings(log_format="CONSOLE")
        assert s.log_format == "console"

    def test_log_format_validation_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid log format"):
            Settings(log_format="xml")

    def test_app_env_normalization(self) -> None:
        s = Settings(app_env="PRODUCTION")
        assert s.app_env == "production"

    def test_extra_env_vars_ignored(self) -> None:
        # Pydantic extra='ignore' allows unknown keys without crashing
        s = Settings(unknown_key="value")  # type: ignore[call-arg]
        assert s.app_name == "OCR Benchmark Platform"


class TestLoggingConfig:
    """Tests for the structured logging setup."""

    def test_configure_logging_idempotent(self) -> None:
        configure_logging()
        configure_logging()  # Should not raise or duplicate handlers

    def test_get_logger_returns_bound_logger(self) -> None:
        logger = get_logger("test_module")
        assert logger is not None

    def test_logger_can_log_info(self, capsys) -> None:  # noqa: D102
        configure_logging()
        logger = get_logger("test_logger")
        logger.info("test_event", key="value")
        captured = capsys.readouterr()
        assert "test_event" in captured.out
