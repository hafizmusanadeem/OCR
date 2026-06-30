"""Job models for the asynchronous OCR pipeline.

Defines Pydantic models for job status, job metadata, and API responses
for the async job submission and status query endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """Lifecycle states of an OCR job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobPageResult(BaseModel):
    """OCR result for a single page within a job.

    Attributes:
        page_number: 1-based page index.
        text: Extracted text for this page.
        confidence: Confidence score (0.0-1.0) if available.
        language: Detected language code if available.
        processing_time_ms: Time taken to process this page in milliseconds.
    """

    page_number: int = Field(
        ge=1,
        description="1-based page index",
    )
    text: str = Field(description="Extracted text for this page")
    confidence: float | None = Field(default=None, description="Confidence score (0.0-1.0)")
    language: str | None = Field(default=None, description="Detected language code")
    processing_time_ms: float | None = Field(
        default=None, description="Processing time in milliseconds"
    )


class Job(BaseModel):
    """Internal representation of an OCR job.

    Attributes:
        id: Unique job identifier (UUID).
        status: Current lifecycle state.
        filename: Original uploaded filename.
        content_type: MIME type of the uploaded file.
        provider: OCR provider name used.
        created_at: UTC timestamp when the job was created.
        updated_at: UTC timestamp of the last status change.
        pages: Per-page OCR results (populated when completed).
        error: Error message if the job failed.
        total_processing_time_ms: Total OCR time across all pages.
        page_count: Number of pages in the document.
    """

    id: str = Field(description="Unique job identifier")
    status: JobStatus = Field(description="Current lifecycle state")
    filename: str = Field(description="Original uploaded filename")
    content_type: str = Field(description="MIME type of the uploaded file")
    provider: str = Field(description="OCR provider name used")
    created_at: datetime = Field(description="UTC creation timestamp")
    updated_at: datetime = Field(description="UTC last-update timestamp")
    pages: list[JobPageResult] = Field(default_factory=list, description="Per-page OCR results")
    error: str | None = Field(default=None, description="Error message if failed")
    total_processing_time_ms: float | None = Field(
        default=None, description="Total processing time in milliseconds"
    )
    page_count: int | None = Field(default=None, description="Number of pages in the document")


class JobCreateResponse(BaseModel):
    """Response model for the async job submission endpoint.

    Attributes:
        job_id: Unique identifier for the submitted job.
        status: Initial job status (always ``pending``).
        message: Human-readable confirmation message.
    """

    job_id: str = Field(description="Unique identifier for the submitted job")
    status: JobStatus = Field(description="Initial job status")
    message: str = Field(description="Human-readable confirmation message")


class JobDetailResponse(BaseModel):
    """Response model for the job status query endpoint.

    Attributes:
        job_id: Unique job identifier.
        status: Current job status.
        filename: Original uploaded filename.
        provider: OCR provider name.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        page_count: Number of pages (if known).
        pages: Per-page OCR results (if completed).
        error: Error message (if failed).
        total_processing_time_ms: Total processing time (if completed).
    """

    job_id: str = Field(description="Unique job identifier")
    status: JobStatus = Field(description="Current job status")
    filename: str = Field(description="Original uploaded filename")
    provider: str = Field(description="OCR provider name")
    created_at: str = Field(description="ISO-8601 creation timestamp")
    updated_at: str = Field(description="ISO-8601 last-update timestamp")
    page_count: int | None = Field(default=None, description="Number of pages in the document")
    pages: list[JobPageResult] = Field(default_factory=list, description="Per-page OCR results")
    error: str | None = Field(default=None, description="Error message if failed")
    total_processing_time_ms: float | None = Field(
        default=None, description="Total processing time in milliseconds"
    )
