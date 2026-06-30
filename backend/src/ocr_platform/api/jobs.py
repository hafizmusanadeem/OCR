"""Async job submission and status query endpoints.

Provides a non-blocking API for OCR processing:
* ``POST /api/v1/jobs`` — Upload a file and receive a job ID immediately.
* ``GET /api/v1/jobs/{job_id}`` — Poll for status and results.

The actual OCR work is delegated to a Celery worker via the
:func:`~ocr_platform.jobs.tasks.process_ocr_job` task.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ocr_platform.config import settings
from ocr_platform.jobs.models import Job, JobCreateResponse, JobDetailResponse, JobStatus
from ocr_platform.jobs.store import job_store
from ocr_platform.jobs.tasks import process_ocr_job
from ocr_platform.logging_config import get_logger
from ocr_platform.providers import global_registry

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
VALID_CONTENT_TYPES = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
)


def _job_to_response(job: Job) -> JobDetailResponse:
    """Convert a Job model to a JobDetailResponse.

    For jobs that are still in progress, page results are fetched from the
    job store's partial result cache rather than the job's own ``pages``
    attribute (which is only populated on completion).

    Args:
        job: Internal Job model.

    Returns:
        API-friendly response model.
    """
    pages = job.pages if job.status == JobStatus.COMPLETED else job_store.get_page_results(job.id)
    return JobDetailResponse(
        job_id=job.id,
        status=job.status,
        filename=job.filename,
        provider=job.provider,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        page_count=job.page_count,
        pages=pages,
        pages_completed=job.pages_completed,
        error=job.error,
        total_processing_time_ms=job.total_processing_time_ms,
    )


@router.post(
    "/jobs",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit an async OCR job",
    description="Upload a PDF or image and receive a job ID. "
    "Use the returned job_id to poll for results via GET /jobs/{job_id}. "
    "Supported formats: PDF, PNG, JPEG, TIFF.",
)
async def create_job(
    file: UploadFile = File(..., description="PDF or image file to OCR"),
    provider: str | None = Form(
        None, description="OCR provider name (defaults to configured default)"
    ),
) -> JobCreateResponse:
    """Submit a file for asynchronous OCR processing.

    Args:
        file: PDF or image file to process.
        provider: Optional OCR provider name. Defaults to
            ``settings.default_ocr_provider``.

    Returns:
        A JobCreateResponse with the job ID and initial status.

    Raises:
        HTTPException: 400 for invalid file type, 413 for file too large,
            404 for unknown provider, 503 for unavailable provider.
    """
    # Validate content type
    content_type = file.content_type or ""
    if not content_type.startswith(VALID_CONTENT_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {content_type}. "
            f"Supported: {', '.join(VALID_CONTENT_TYPES)}.",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large ({len(content)} bytes). "
            f"Maximum allowed: {MAX_FILE_SIZE} bytes (10 MB).",
        )

    logger.info(
        "job_submitted",
        filename=file.filename,
        content_type=content_type,
        file_size=len(content),
    )

    # Resolve provider
    provider_name = provider or settings.default_ocr_provider
    try:
        ocr_provider = global_registry.create_provider(provider_name)
    except KeyError as exc:
        available = ", ".join(global_registry.list_providers()) or "none"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' not found. Available: {available}.",
        ) from exc

    if not ocr_provider.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider '{provider_name}' is not available. "
            "Check configuration (e.g., API key).",
        )

    # Create job in store
    job_id = job_store.create(
        filename=file.filename or "unknown",
        content_type=content_type,
        provider=provider_name,
        content=content,
    )

    # Dispatch Celery task (non-blocking)
    process_ocr_job.delay(job_id, content_type, provider_name)

    logger.info(
        "job_dispatched",
        job_id=job_id,
        provider=provider_name,
    )

    return JobCreateResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Job accepted and queued for processing. "
        f"Poll GET /api/v1/jobs/{job_id} for status.",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job status and results",
    description="Retrieve the current status and (if completed) results "
    "of an asynchronous OCR job.",
)
async def get_job(job_id: str) -> JobDetailResponse:
    """Query the status of an asynchronous OCR job.

    Args:
        job_id: Unique job identifier returned by POST /jobs.

    Returns:
        JobDetailResponse with status, metadata, and results if available.

    Raises:
        HTTPException: 404 if the job ID is not found.
    """
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    return _job_to_response(job)
