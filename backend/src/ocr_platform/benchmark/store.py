"""Thread-safe in-memory store for benchmark runs.

Stores benchmark metadata, per-page results, and engine scores.
Optionally mirrors to the database when configured.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

from ocr_platform.benchmark.models import BenchmarkRun, BenchmarkStatus, PageBenchmark, EngineScore
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)


class BenchmarkStore:
    """Thread-safe in-memory storage for benchmark runs.

    Attributes:
        _runs: Mapping of benchmark_id → BenchmarkRun.
        _lock: Reentrant lock for thread-safe operations.
    """

    def __init__(self) -> None:
        self._runs: dict[str, BenchmarkRun] = {}
        self._lock = threading.RLock()

    def create(self, dataset_name: str) -> str:
        """Create a new benchmark run.

        Args:
            dataset_name: Name of the dataset to benchmark.

        Returns:
            The generated benchmark ID (UUIDv4).
        """
        benchmark_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        run = BenchmarkRun(
            id=benchmark_id,
            status=BenchmarkStatus.PENDING,
            dataset_name=dataset_name,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._runs[benchmark_id] = run
        logger.info("benchmark_created", benchmark_id=benchmark_id, dataset_name=dataset_name)
        return benchmark_id

    def get(self, benchmark_id: str) -> BenchmarkRun | None:
        """Retrieve a benchmark run by ID.

        Args:
            benchmark_id: Unique benchmark identifier.

        Returns:
            The BenchmarkRun or ``None`` if not found.
        """
        with self._lock:
            return self._runs.get(benchmark_id)

    def update_status(self, benchmark_id: str, status: BenchmarkStatus) -> None:
        """Update the status of a benchmark run.

        Args:
            benchmark_id: Unique benchmark identifier.
            status: New lifecycle state.

        Raises:
            KeyError: If the benchmark run does not exist.
        """
        with self._lock:
            run = self._runs[benchmark_id]
            run.status = status
            run.updated_at = datetime.now(UTC)
        logger.info("benchmark_status_updated", benchmark_id=benchmark_id, status=status.value)

    def add_page_results(self, benchmark_id: str, results: list[PageBenchmark]) -> None:
        """Add per-page benchmark results to a run.

        Args:
            benchmark_id: Unique benchmark identifier.
            results: List of page benchmark results.

        Raises:
            KeyError: If the benchmark run does not exist.
        """
        with self._lock:
            run = self._runs[benchmark_id]
            run.page_results.extend(results)
            run.updated_at = datetime.now(UTC)
        logger.info(
            "benchmark_page_results_added",
            benchmark_id=benchmark_id,
            count=len(results),
        )

    def set_engine_scores(self, benchmark_id: str, scores: list[EngineScore]) -> None:
        """Set aggregated engine scores for a benchmark run.

        Args:
            benchmark_id: Unique benchmark identifier.
            scores: List of engine scores.

        Raises:
            KeyError: If the benchmark run does not exist.
        """
        with self._lock:
            run = self._runs[benchmark_id]
            run.engine_scores = scores
            run.updated_at = datetime.now(UTC)
        logger.info(
            "benchmark_engine_scores_set",
            benchmark_id=benchmark_id,
            engine_count=len(scores),
        )

    def complete(self, benchmark_id: str) -> None:
        """Mark a benchmark run as completed.

        Args:
            benchmark_id: Unique benchmark identifier.

        Raises:
            KeyError: If the benchmark run does not exist.
        """
        with self._lock:
            run = self._runs[benchmark_id]
            run.status = BenchmarkStatus.COMPLETED
            run.updated_at = datetime.now(UTC)
        logger.info("benchmark_completed", benchmark_id=benchmark_id)

    def fail(self, benchmark_id: str, error: str) -> None:
        """Mark a benchmark run as failed.

        Args:
            benchmark_id: Unique benchmark identifier.
            error: Error message.

        Raises:
            KeyError: If the benchmark run does not exist.
        """
        with self._lock:
            run = self._runs[benchmark_id]
            run.status = BenchmarkStatus.FAILED
            run.error = error
            run.updated_at = datetime.now(UTC)
        logger.info("benchmark_failed", benchmark_id=benchmark_id, error=error)

    def list_runs(self) -> list[BenchmarkRun]:
        """Return all benchmark runs, sorted by creation time.

        Returns:
            List of BenchmarkRun objects.
        """
        with self._lock:
            return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    def delete(self, benchmark_id: str) -> None:
        """Remove a benchmark run from the store.

        Args:
            benchmark_id: Unique benchmark identifier.
        """
        with self._lock:
            self._runs.pop(benchmark_id, None)
        logger.info("benchmark_deleted", benchmark_id=benchmark_id)


# Global singleton instance
benchmark_store = BenchmarkStore()
