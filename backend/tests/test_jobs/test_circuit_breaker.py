"""Tests for the circuit breaker pattern."""

from __future__ import annotations

import pytest

from ocr_platform.jobs.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
)


class TestCircuitBreaker:
    """Tests for the circuit breaker utility."""

    def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_successful_call(self) -> None:
        cb = CircuitBreaker("test")
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitState.CLOSED

    def test_failure_count_increments(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60.0)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

    def test_open_rejects_calls(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60.0)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        with pytest.raises(CircuitBreakerOpen):
            cb.call(lambda: 42)

    def test_half_open_then_closes(self) -> None:
        import time

        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        # Next call should succeed in half-open state
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitState.CLOSED

    def test_half_open_then_reopens(self) -> None:
        import time

        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        # Next call fails again → should reopen
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail again")))
        assert cb.state == CircuitState.OPEN

    def test_thread_safety(self) -> None:
        import threading

        cb = CircuitBreaker("test", failure_threshold=100)
        errors = []
        successes = []

        def worker():
            for _ in range(10):
                try:
                    cb.call(lambda: 1)
                    successes.append(1)
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes) == 50
        assert len(errors) == 0
