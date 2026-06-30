"""Thread-safe in-memory job store.

Stores job metadata and file content in memory. Will be replaced by a
proper database backend in Milestone 8.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

from ocr_platform.jobs.models import Job, JobPageResult, JobStatus


class JobStore:
    """Thread-safe in-memory storage for OCR jobs and their file contents.

    Attributes:
        _jobs: Mapping of job_id → Job metadata.
        _contents: Mapping of job_id → raw file bytes.
        _lock: Reentrant lock for thread-safe operations.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._contents: dict[str, bytes] = {}
        self._lock = threading.RLock()

    def create(
        self,
        filename: str,
        content_type: str,
        provider: str,
        content: bytes,
    ) -> str:
        """Create a new job and store its file content.

        Args:
            filename: Original uploaded filename.
            content_type: MIME type of the file.
            provider: OCR provider name.
            content: Raw file bytes.

        Returns:
            The generated job ID (UUIDv4).
        """
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        job = Job(
            id=job_id,
            status=JobStatus.PENDING,
            filename=filename,
            content_type=content_type,
            provider=provider,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job_id] = job
            self._contents[job_id] = content
        return job_id

    def get(self, job_id: str) -> Job | None:
        """Retrieve a job by ID.

        Args:
            job_id: Unique job identifier.

        Returns:
            The Job object or ``None`` if not found.
        """
        with self._lock:
            return self._jobs.get(job_id)

    def get_content(self, job_id: str) -> bytes | None:
        """Retrieve the raw file content for a job.

        Args:
            job_id: Unique job identifier.

        Returns:
            Raw file bytes or ``None`` if not found.
        """
        with self._lock:
            return self._contents.get(job_id)

    def update_status(self, job_id: str, status: JobStatus) -> None:
        """Update the status of a job.

        Args:
            job_id: Unique job identifier.
            status: New lifecycle state.

        Raises:
            KeyError: If the job does not exist.
        """
        with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.updated_at = datetime.now(UTC)

    def complete(
        self,
        job_id: str,
        pages: list[JobPageResult],
        total_processing_time_ms: float,
        page_count: int,
    ) -> None:
        """Mark a job as completed with results.

        Args:
            job_id: Unique job identifier.
            pages: Per-page OCR results.
            total_processing_time_ms: Total processing time.
            page_count: Number of pages processed.

        Raises:
            KeyError: If the job does not exist.
        """
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.pages = pages
            job.total_processing_time_ms = total_processing_time_ms
            job.page_count = page_count
            job.updated_at = datetime.now(UTC)
            # Free memory: delete content after processing
            self._contents.pop(job_id, None)

    def fail(self, job_id: str, error: str) -> None:
        """Mark a job as failed.

        Args:
            job_id: Unique job identifier.
            error: Error message.

        Raises:
            KeyError: If the job does not exist.
        """
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.FAILED
            job.error = error
            job.updated_at = datetime.now(UTC)
            # Free memory: delete content after failure
            self._contents.pop(job_id, None)

    def delete(self, job_id: str) -> None:
        """Remove a job and its content from the store.

        Args:
            job_id: Unique job identifier.
        """
        with self._lock:
            self._jobs.pop(job_id, None)
            self._contents.pop(job_id, None)

    def list_jobs(self) -> list[Job]:
        """Return all stored jobs, sorted by creation time.

        Returns:
            List of Job objects.
        """
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at)


# Global singleton instance used throughout the application
job_store = JobStore()
