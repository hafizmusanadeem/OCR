"""Celery tasks for asynchronous OCR processing.

The task pipeline is now split into three stages:

1. ``process_ocr_job`` — Preprocesses the document, stores page images,
   and dispatches a Celery chord for concurrent page processing.
2. ``process_page`` — Runs OCR on a single page image. Executed in
   parallel by multiple workers.
3. ``finalize_job`` — Callback that aggregates all page results and
   marks the job as completed.
"""

from __future__ import annotations

import asyncio

from celery import chord  # type: ignore[import-untyped]

from ocr_platform.jobs.celery_app import celery_app
from ocr_platform.jobs.models import JobPageResult, JobStatus
from ocr_platform.jobs.store import job_store
from ocr_platform.logging_config import get_logger
from ocr_platform.preprocessing.document import DocumentPreprocessor
from ocr_platform.providers import global_registry
from ocr_platform.providers.models import OCRResult

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_page(
    self,  # noqa: ARG001
    job_id: str,
    page_number: int,
    provider_name: str,
) -> dict:
    """Process a single page image asynchronously.

    Retrieves the page image from the job store, runs OCR, and stores
    the result. This task is designed to run concurrently with other
    page tasks for the same job.

    Args:
        job_id: Unique job identifier.
        page_number: 1-based page index to process.
        provider_name: OCR provider to use.

    Returns:
        A dictionary representation of the page result.

    Raises:
        self.retry: If a transient error occurs, the task retries up to
            3 times with a 10-second backoff.
    """
    logger.info(
        "page_task_started",
        job_id=job_id,
        page_number=page_number,
        provider=provider_name,
    )

    try:
        image_data = job_store.get_page_image(job_id, page_number)
        if image_data is None:
            raise RuntimeError(f"Page image not found for job {job_id}, page {page_number}")

        provider = global_registry.create_provider(provider_name)
        if not provider.is_available():
            raise RuntimeError(f"Provider '{provider_name}' is not available")

        result: OCRResult = asyncio.run(provider.recognize(image_data))
        page_result = JobPageResult(
            page_number=page_number,
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            processing_time_ms=result.processing_time_ms,
        )
        job_store.add_page_result(job_id, page_number, page_result)

        logger.info(
            "page_task_completed",
            job_id=job_id,
            page_number=page_number,
            text_length=len(result.text),
        )
        return page_result.model_dump()

    except Exception as exc:
        logger.error(
            "page_task_failed",
            job_id=job_id,
            page_number=page_number,
            error=str(exc),
        )
        raise self.retry(exc=exc) from None


@celery_app.task
def finalize_job(
    _results: list,
    job_id: str,
    expected_count: int,
) -> None:
    """Aggregate page results and mark the job as completed.

    This is the chord callback that runs after all ``process_page``
    tasks for a job have finished. It reads results from the job store,
    computes totals, and updates the job status.

    Args:
        _results: List of return values from the header tasks (ignored in
            favor of the job store, which is the source of truth).
        job_id: Unique job identifier.
        expected_count: Expected number of pages.
    """
    logger.info(
        "finalize_job_started",
        job_id=job_id,
        expected_count=expected_count,
    )

    try:
        page_results = job_store.get_page_results(job_id)
        if len(page_results) == expected_count:
            total_time = sum(r.processing_time_ms or 0 for r in page_results)
            job_store.complete(
                job_id,
                pages=page_results,
                total_processing_time_ms=round(total_time, 3),
                page_count=expected_count,
            )
            logger.info(
                "finalize_job_completed",
                job_id=job_id,
                page_count=expected_count,
            )
        else:
            completed = len(page_results)
            job_store.fail(
                job_id,
                f"Incomplete: {completed}/{expected_count} pages completed",
            )
            logger.warning(
                "finalize_job_incomplete",
                job_id=job_id,
                completed=completed,
                expected=expected_count,
            )

    except Exception as exc:
        logger.error("finalize_job_failed", job_id=job_id, error=str(exc))
        raise


@celery_app.task
def process_ocr_job(
    job_id: str,
    content_type: str,
    provider_name: str,
) -> None:
    """Dispatch an OCR job as a chord of concurrent page tasks.

    Retrieves the raw file, preprocesses it into page images, stores the
    page images in the job store, and launches a Celery chord so that each
    page is processed by a separate worker concurrently.

    Args:
        job_id: Unique job identifier (used to retrieve content from store).
        content_type: MIME type of the uploaded file.
        provider_name: OCR provider to use.
    """
    logger.info(
        "ocr_job_started",
        job_id=job_id,
        provider=provider_name,
        content_type=content_type,
    )

    try:
        content = job_store.get_content(job_id)
        if content is None:
            raise RuntimeError(f"Job content not found for {job_id}")
    except Exception as exc:
        logger.error("ocr_job_failed", job_id=job_id, error=str(exc))
        if job_store.get(job_id) is not None:
            job_store.fail(job_id, str(exc))
        raise

    job_store.update_status(job_id, JobStatus.PROCESSING)

    try:
        # Preprocess document into pages
        preprocessor = DocumentPreprocessor()
        page_images = preprocessor.preprocess(content, content_type)

        # Store page images so subtasks can retrieve them
        job_store.store_page_images(job_id, page_images)

        # Build chord: one process_page per page, then finalize_job
        header = [process_page.s(job_id, page.page_number, provider_name) for page in page_images]
        callback = finalize_job.s(job_id, len(page_images))

        chord(header)(callback)

        logger.info(
            "ocr_job_dispatched_pages",
            job_id=job_id,
            page_count=len(page_images),
        )

    except Exception as exc:
        logger.error("ocr_job_failed", job_id=job_id, error=str(exc))
        if job_store.get(job_id) is not None:
            job_store.fail(job_id, str(exc))
        raise
