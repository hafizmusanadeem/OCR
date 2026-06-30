"""Tests for job data models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ocr_platform.jobs.models import (
    Job,
    JobCreateResponse,
    JobDetailResponse,
    JobPageResult,
    JobStatus,
)


class TestJobStatus:
    """JobStatus enum tests."""

    def test_pending_value(self) -> None:
        assert JobStatus.PENDING == "pending"

    def test_processing_value(self) -> None:
        assert JobStatus.PROCESSING == "processing"

    def test_completed_value(self) -> None:
        assert JobStatus.COMPLETED == "completed"

    def test_failed_value(self) -> None:
        assert JobStatus.FAILED == "failed"

    def test_from_string(self) -> None:
        assert JobStatus("pending") == JobStatus.PENDING
        assert JobStatus("completed") == JobStatus.COMPLETED


class TestJobPageResult:
    """JobPageResult model tests."""

    def test_minimal_construction(self) -> None:
        r = JobPageResult(page_number=1, text="hello")
        assert r.page_number == 1
        assert r.text == "hello"
        assert r.confidence is None
        assert r.language is None
        assert r.processing_time_ms is None

    def test_full_construction(self) -> None:
        r = JobPageResult(
            page_number=2,
            text="world",
            confidence=0.95,
            language="en",
            processing_time_ms=42.0,
        )
        assert r.page_number == 2
        assert r.confidence == 0.95
        assert r.language == "en"
        assert r.processing_time_ms == 42.0

    def test_page_number_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            JobPageResult(page_number=0, text="x")


class TestJob:
    """Job model tests."""

    def test_default_construction(self) -> None:
        now = datetime.now(UTC)
        job = Job(
            id="test-id",
            status=JobStatus.PENDING,
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
        )
        assert job.id == "test-id"
        assert job.status == JobStatus.PENDING
        assert job.pages == []
        assert job.error is None
        assert job.total_processing_time_ms is None
        assert job.page_count is None
        assert job.pages_completed == 0

    def test_with_results(self) -> None:
        now = datetime.now(UTC)
        job = Job(
            id="test-id",
            status=JobStatus.COMPLETED,
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
            pages=[JobPageResult(page_number=1, text="hello")],
            page_count=1,
            total_processing_time_ms=100.0,
            pages_completed=1,
        )
        assert len(job.pages) == 1
        assert job.page_count == 1
        assert job.total_processing_time_ms == 100.0
        assert job.pages_completed == 1


class TestJobCreateResponse:
    """JobCreateResponse model tests."""

    def test_construction(self) -> None:
        r = JobCreateResponse(
            job_id="abc-123",
            status=JobStatus.PENDING,
            message="Job accepted",
        )
        assert r.job_id == "abc-123"
        assert r.status == JobStatus.PENDING
        assert r.message == "Job accepted"


class TestJobDetailResponse:
    """JobDetailResponse model tests."""

    def test_pending_job(self) -> None:
        now = datetime.now(UTC).isoformat()
        r = JobDetailResponse(
            job_id="abc-123",
            status=JobStatus.PENDING,
            filename="test.pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
        )
        assert r.job_id == "abc-123"
        assert r.status == JobStatus.PENDING
        assert r.pages == []
        assert r.error is None
        assert r.page_count is None
        assert r.pages_completed == 0

    def test_completed_job(self) -> None:
        now = datetime.now(UTC).isoformat()
        r = JobDetailResponse(
            job_id="abc-123",
            status=JobStatus.COMPLETED,
            filename="test.pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
            page_count=1,
            pages=[JobPageResult(page_number=1, text="hello")],
            total_processing_time_ms=50.0,
            pages_completed=1,
        )
        assert r.status == JobStatus.COMPLETED
        assert r.page_count == 1
        assert len(r.pages) == 1
        assert r.total_processing_time_ms == 50.0
        assert r.pages_completed == 1

    def test_failed_job(self) -> None:
        now = datetime.now(UTC).isoformat()
        r = JobDetailResponse(
            job_id="abc-123",
            status=JobStatus.FAILED,
            filename="test.pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
            error="Provider not available",
        )
        assert r.status == JobStatus.FAILED
        assert r.error == "Provider not available"
