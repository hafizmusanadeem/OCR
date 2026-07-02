"""Circuit breaker pattern for resilient external calls.

Provides a simple circuit breaker that trips after a threshold of
consecutive failures, preventing cascading failures and giving
external services time to recover.
"""

from __future__ import annotations

import threading
import time
from enum import Enum

from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Simple thread-safe circuit breaker.

    Attributes:
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait before trying half-open.
        name: Human-readable identifier for logging.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        """Current breaker state (thread-safe)."""
        with self._lock:
            return self._state

    def call(self, func, *args, **kwargs):
        """Execute *func* through the circuit breaker.

        Args:
            func: Callable to protect.
            *args: Positional arguments for *func*.
            **kwargs: Keyword arguments for *func*.

        Returns:
            The result of ``func(*args, **kwargs)``.

        Raises:
            CircuitBreakerOpen: If the circuit is open.
            Exception: Any exception raised by *func* (and recorded as failure).
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and (
                    time.time() - self._last_failure_time >= self.recovery_timeout
                ):
                    self._state = CircuitState.HALF_OPEN
                    logger.info("circuit_half_open", breaker=self.name)
                else:
                    logger.warning(
                        "circuit_breaker_open", breaker=self.name, rejection=True
                    )
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{self.name}' is OPEN"
                    )

        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            self._record_failure()
            raise

        self._record_success()
        return result

    def _record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("circuit_closed", breaker=self.name)
            self._failure_count = 0

    def _record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._state = CircuitState.OPEN
                    logger.error(
                        "circuit_opened",
                        breaker=self.name,
                        failures=self._failure_count,
                    )


class CircuitBreakerOpen(Exception):
    """Raised when a circuit breaker is OPEN and rejects a call."""

    pass


# Global circuit breaker instances
_page_ocr_breaker = CircuitBreaker("page_ocr", failure_threshold=3, recovery_timeout=30.0)
_registry_breaker = CircuitBreaker("provider_registry", failure_threshold=5, recovery_timeout=60.0)
