"""Celery task for asynchronous OCR processing.

The task runs the full OCR pipeline: preprocessing, page splitting,
provider dispatch, and result aggregation. It updates the job store
in-place so the API can poll for status.
"""

from __future__ import annotations

import asyncio

from ocr_platform.jobs.celery_app import celery_app
from ocr_platform.jobs.models import JobPageResult, JobStatus
from ocr_platform.jobs.store import job_store
from ocr_platform.logging_config import get_logger
from ocr_platform.preprocessing.document import DocumentPreprocessor
from ocr_platform.providers import global_registry
from ocr_platform.providers.models import OCRResult

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr_job(
    self,  # noqa: ARG001
    job_id: str,
    content_type: str,
    provider_name: str,
) -> None:
    """Process an OCR job asynchronously.

        Retrieves the file content from the job store, preprocesses the
    document, runs OCR on each page, and updates the job store with
        results or failure information.

        Args:
            job_id: Unique job identifier (used to retrieve content from store).
            content_type: MIME type of the uploaded file.
            provider_name: OCR provider to use.

        Raises:
            self.retry: If a transient error occurs, the task retries up to
                3 times with a 60-second backoff.
    """
    logger.info(
        "ocr_task_started",
        job_id=job_id,
        provider=provider_name,
        content_type=content_type,
    )

    try:
        content = job_store.get_content(job_id)
        if content is None:
            raise RuntimeError(f"Job content not found for {job_id}")
    except Exception as exc:
        logger.error(
            "ocr_task_failed",
            job_id=job_id,
            error=str(exc),
        )
        raise

    job_store.update_status(job_id, JobStatus.PROCESSING)

    try:
        # Preprocess document into pages
        preprocessor = DocumentPreprocessor()
        page_images = preprocessor.preprocess(content, content_type)

        # Resolve provider
        provider = global_registry.create_provider(provider_name)
        if not provider.is_available():
            raise RuntimeError(f"Provider '{provider_name}' is not available")

        # OCR each page
        page_results: list[JobPageResult] = []
        total_processing_time = 0.0

        for page_image in page_images:
            result: OCRResult = asyncio.run(provider.recognize(page_image.image_data))
            page_results.append(
                JobPageResult(
                    page_number=page_image.page_number,
                    text=result.text,
                    confidence=result.confidence,
                    language=result.language,
                    processing_time_ms=result.processing_time_ms,
                )
            )
            if result.processing_time_ms:
                total_processing_time += result.processing_time_ms

        job_store.complete(
            job_id,
            pages=page_results,
            total_processing_time_ms=round(total_processing_time, 3),
            page_count=len(page_results),
        )

        logger.info(
            "ocr_task_completed",
            job_id=job_id,
            page_count=len(page_results),
            total_processing_time_ms=round(total_processing_time, 3),
        )

    except Exception as exc:
        logger.error(
            "ocr_task_failed",
            job_id=job_id,
            error=str(exc),
        )
        job_store.fail(job_id, str(exc))
        raise
