"""Synchronous wrapper around the async JobRepository.

Celery tasks run in a synchronous context and cannot ``await`` async
methods directly. This wrapper uses ``asyncio.run()`` to bridge the gap.

FastAPI endpoints should use :class:`~ocr_platform.db.repository.JobRepository`
directly with ``await``.
"""

from __future__ import annotations

import asyncio

from ocr_platform.db.repository import JobRepository as AsyncJobRepository
from ocr_platform.jobs.models import Job, JobPageResult
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)


class JobRepositorySync:
    """Synchronous wrapper for :class:`~ocr_platform.db.repository.JobRepository`.

    All methods mirror the async repository but block with ``asyncio.run()``.
    Safe to call from synchronous code (Celery tasks, CLI scripts, etc.).

    Attributes:
        _repo: Underlying async repository class.
    """

    def __init__(self) -> None:
        self._repo = AsyncJobRepository

    def create_job(self, job: Job) -> None:
        """Persist a new job (sync wrapper)."""
        asyncio.run(self._repo.create_job(job))

    def update_job(self, job: Job) -> None:
        """Update an existing job (sync wrapper)."""
        asyncio.run(self._repo.update_job(job))

    def complete_job(
        self,
        job_id: str,
        pages: list[JobPageResult],
        total_processing_time_ms: float,
        page_count: int,
    ) -> None:
        """Mark a job as completed (sync wrapper)."""
        asyncio.run(
            self._repo.complete_job(
                job_id,
                pages,
                total_processing_time_ms,
                page_count,
            )
        )

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark a job as failed (sync wrapper)."""
        asyncio.run(self._repo.fail_job(job_id, error))

    def add_page_result(self, job_id: str, result: JobPageResult) -> None:
        """Persist a single page result (sync wrapper)."""
        asyncio.run(self._repo.add_page_result(job_id, result))

    def get_job(self, job_id: str) -> Job | None:
        """Retrieve a job from the database (sync wrapper)."""
        return asyncio.run(self._repo.get_job(job_id))

    def get_page_results(self, job_id: str) -> list[JobPageResult]:
        """Retrieve page results (sync wrapper)."""
        return asyncio.run(self._repo.get_page_results(job_id))
