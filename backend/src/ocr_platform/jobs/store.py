"""Thread-safe in-memory job store with optional database write-through.

Stores job metadata, file content, per-page image data, and aggregated
document results in memory. When a database URL is configured, writes are
mirrored to PostgreSQL for persistence across restarts.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

from ocr_platform.jobs.models import DocumentResult, Job, JobPageResult, JobStatus
from ocr_platform.logging_config import get_logger
from ocr_platform.preprocessing.types import PageImage

logger = get_logger(__name__)

# Lazy import guard for db.sync to avoid circular imports
_JobRepositorySync = None


def _get_db_sync():  # noqa: PLC0415
    """Lazy import of JobRepositorySync to avoid circular imports."""
    global _JobRepositorySync  # noqa: PLW0603
    if _JobRepositorySync is None:
        from ocr_platform.db.sync import JobRepositorySync

        _JobRepositorySync = JobRepositorySync
    return _JobRepositorySync


class JobStore:
    """Thread-safe in-memory storage for OCR jobs with optional DB persistence.

    Attributes:
        _jobs: Mapping of job_id → Job metadata.
        _contents: Mapping of job_id → raw file bytes.
        _page_images: Mapping of job_id → {page_number → image bytes}.
        _page_results: Mapping of job_id → {page_number → JobPageResult}.
        _document_results: Mapping of job_id → DocumentResult.
        _lock: Reentrant lock for thread-safe operations.
        _db: Optional synchronous database repository.
    """

    def __init__(self, db=None) -> None:  # type: ignore[no-untyped-def]
        self._jobs: dict[str, Job] = {}
        self._contents: dict[str, bytes] = {}
        self._page_images: dict[str, dict[int, bytes]] = {}
        self._page_results: dict[str, dict[int, JobPageResult]] = {}
        self._document_results: dict[str, DocumentResult] = {}
        self._lock = threading.RLock()
        self._db = db

    def _db_enabled(self) -> bool:
        return self._db is not None

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

        if self._db_enabled():
            try:
                self._db.create_job(job)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning("db_create_job_failed", job_id=job_id, error=str(exc))

        return job_id

    def get(self, job_id: str) -> Job | None:
        """Retrieve a job by ID.

        Checks in-memory first, then falls back to the database if the
        job is not found in memory.

        Args:
            job_id: Unique job identifier.

        Returns:
            The Job object or ``None`` if not found.
        """
        with self._lock:
            job = self._jobs.get(job_id)

        if job is not None:
            return job

        if self._db_enabled():
            try:
                db_job = self._db.get_job(job_id)  # type: ignore[union-attr]
                if db_job is not None:
                    with self._lock:
                        self._jobs[job_id] = db_job
                    return db_job
            except Exception as exc:
                logger.warning("db_get_job_failed", job_id=job_id, error=str(exc))

        return None

    def get_content(self, job_id: str) -> bytes | None:
        """Retrieve the raw file content for a job.

        Args:
            job_id: Unique job identifier.

        Returns:
            Raw file bytes or ``None`` if not found.
        """
        with self._lock:
            return self._contents.get(job_id)

    def store_page_images(self, job_id: str, page_images: list[PageImage]) -> None:
        """Store preprocessed page images for a job.

        Args:
            job_id: Unique job identifier.
            page_images: List of page images extracted from the document.

        Raises:
            KeyError: If the job does not exist.
        """
        with self._lock:
            job = self._jobs[job_id]
            self._page_images[job_id] = {page.page_number: page.image_data for page in page_images}
            job.page_count = len(page_images)
            job.updated_at = datetime.now(UTC)

    def get_page_image(self, job_id: str, page_number: int) -> bytes | None:
        """Retrieve a single page's image data.

        Args:
            job_id: Unique job identifier.
            page_number: 1-based page index.

        Returns:
            Raw image bytes or ``None`` if not found.
        """
        with self._lock:
            return self._page_images.get(job_id, {}).get(page_number)

    def add_page_result(self, job_id: str, page_number: int, result: JobPageResult) -> None:
        """Store a single page's OCR result.

        Args:
            job_id: Unique job identifier.
            page_number: 1-based page index.
            result: OCR result for this page.

        Raises:
            KeyError: If the job does not exist.
        """
        with self._lock:
            if job_id not in self._page_results:
                self._page_results[job_id] = {}
            self._page_results[job_id][page_number] = result
            job = self._jobs[job_id]
            job.pages_completed = len(self._page_results[job_id])
            job.updated_at = datetime.now(UTC)

        if self._db_enabled():
            try:
                self._db.add_page_result(job_id, result)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning(
                    "db_add_page_result_failed",
                    job_id=job_id,
                    page_number=page_number,
                    error=str(exc),
                )

    def get_page_results(self, job_id: str) -> list[JobPageResult]:
        """Retrieve all page results for a job, sorted by page number.

        Args:
            job_id: Unique job identifier.

        Returns:
            Sorted list of JobPageResult objects.
        """
        with self._lock:
            results = self._page_results.get(job_id, {})
            if results:
                return [results[page_num] for page_num in sorted(results.keys())]

        if self._db_enabled():
            try:
                db_results = self._db.get_page_results(job_id)  # type: ignore[union-attr]
                if db_results:
                    with self._lock:
                        self._page_results[job_id] = {r.page_number: r for r in db_results}
                    return db_results
            except Exception as exc:
                logger.warning("db_get_page_results_failed", job_id=job_id, error=str(exc))

        return []

    def all_pages_done(self, job_id: str, expected_count: int) -> bool:
        """Check whether all pages have been processed.

        Args:
            job_id: Unique job identifier.
            expected_count: Expected number of pages.

        Returns:
            ``True`` if the number of stored results is at least
            *expected_count*.
        """
        with self._lock:
            return len(self._page_results.get(job_id, {})) >= expected_count

    def store_document(self, job_id: str, document: DocumentResult) -> None:
        """Store the aggregated document result for a job.

        Args:
            job_id: Unique job identifier.
            document: Aggregated document result.

        Raises:
            KeyError: If the job does not exist.
        """
        with self._lock:
            _job = self._jobs[job_id]  # noqa: F841
            self._document_results[job_id] = document

    def get_document(self, job_id: str) -> DocumentResult | None:
        """Retrieve the aggregated document result for a job.

        Args:
            job_id: Unique job identifier.

        Returns:
            The DocumentResult or ``None`` if not found.
        """
        with self._lock:
            return self._document_results.get(job_id)

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

        if self._db_enabled():
            try:
                job = self._jobs[job_id]
                self._db.update_job(job)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning("db_update_job_failed", job_id=job_id, error=str(exc))

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
            job.pages_completed = page_count
            job.updated_at = datetime.now(UTC)
            # Free memory: delete content after processing
            self._contents.pop(job_id, None)
            self._clear_page_data(job_id)

        if self._db_enabled():
            try:
                self._db.complete_job(  # type: ignore[union-attr]
                    job_id, pages, total_processing_time_ms, page_count
                )
            except Exception as exc:
                logger.warning("db_complete_job_failed", job_id=job_id, error=str(exc))

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
            self._clear_page_data(job_id)

        if self._db_enabled():
            try:
                self._db.fail_job(job_id, error)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning("db_fail_job_failed", job_id=job_id, error=str(exc))

    def delete(self, job_id: str) -> None:
        """Remove a job and all associated data from the store.

        Args:
            job_id: Unique job identifier.
        """
        with self._lock:
            self._jobs.pop(job_id, None)
            self._contents.pop(job_id, None)
            self._clear_page_data(job_id)
            self._document_results.pop(job_id, None)

    def _clear_page_data(self, job_id: str) -> None:
        """Remove page images and results for a job.

        Args:
            job_id: Unique job identifier.
        """
        self._page_images.pop(job_id, None)
        self._page_results.pop(job_id, None)

    def list_jobs(self) -> list[Job]:
        """Return all stored jobs, sorted by creation time.

        Returns:
            List of Job objects.
        """
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at)


# Global singleton instance — initialized with DB if DATABASE_URL is available
from ocr_platform.db.engine import DATABASE_URL  # noqa: E402

if DATABASE_URL is not None:
    try:
        job_store = JobStore(db=_get_db_sync()())
        logger.info("job_store_initialized_with_db")
    except Exception as exc:
        logger.warning("job_store_db_init_failed", error=str(exc))
        job_store = JobStore()
else:
    job_store = JobStore()
