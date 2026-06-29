"""Structured logging configuration.

Uses ``structlog`` for structured, JSON-formatted logs in production
and human-readable console output in development.

The configuration is deterministic and idempotent: calling
:func:`configure_logging` multiple times is safe.

Example:
    >>> from ocr_platform.logging_config import get_logger
    >>> logger = get_logger("my_module")
    >>> logger.info("processing_started", page=1, total=10)
    {"event": "processing_started", "page": 1, "total": 10, ...}
"""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.stdlib import ProcessorFormatter

from ocr_platform.config import settings

# ---------------------------------------------------------------------------
# Shared processors used by both standard library and structlog
# ---------------------------------------------------------------------------

SHARED_PROCESSORS: list[structlog.types.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
]

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """Configure global logging with structlog and stdlib integration.

    Sets up:
    - Standard library logging to route through structlog.
    - JSON formatting for production (``json``) or colored console for dev
      (``console``).
    - Log level driven by :attr:`ocr_platform.config.settings.log_level`.

    This function is idempotent and safe to call multiple times.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.log_format == "json":
        _configure_json_logging(log_level)
    else:
        _configure_console_logging(log_level)

    # Suppress overly verbose third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def _configure_json_logging(level: int) -> None:
    """Set up JSON-formatted structured logging for production."""
    structlog.configure(
        processors=SHARED_PROCESSORS
        + [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _configure_stdlib_handlers(
        level,
        formatter_cls=ProcessorFormatter,
        renderer=structlog.processors.JSONRenderer(),
    )


def _configure_console_logging(level: int) -> None:
    """Set up colored, human-readable console logging for development."""
    structlog.configure(
        processors=SHARED_PROCESSORS
        + [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _configure_stdlib_handlers(
        level,
        formatter_cls=ProcessorFormatter,
        renderer=structlog.dev.ConsoleRenderer(),
    )


def _configure_stdlib_handlers(
    level: int,
    formatter_cls: type[ProcessorFormatter],
    renderer: structlog.types.Processor,
) -> None:
    """Attach a stream handler to the root stdlib logger.

    Args:
        level: Logging level to set on the root logger.
        formatter_cls: Formatter class to use for the handler.
        renderer: Final processor that returns a string for output.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates on reconfiguration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        formatter_cls(
            processors=[
                ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
            foreign_pre_chain=SHARED_PROCESSORS,
        )
    )
    root_logger.addHandler(handler)


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger bound to the given module name.

    Args:
        name: Logger name, conventionally ``__name__``.

    Returns:
        A bound structlog logger with context support.
    """
    return structlog.get_logger(name)
