"""Tests for the Celery OCR task."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ocr_platform.jobs.models import JobStatus
from ocr_platform.jobs.store import job_store
from ocr_platform.jobs.tasks import process_ocr_job


class TestProcessOcrJob:
    """Celery OCR task tests (runs synchronously in eager mode)."""

    def setup_method(self) -> None:
        # Clear global store before each test
        for job in job_store.list_jobs():
            job_store.delete(job.id)

    def test_task_processes_single_page(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake pdf content",
        )

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake pdf content"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "png"

        with patch(
            "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            process_ocr_job(job_id, "application/pdf", "mock")

        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.page_count == 1
        assert len(job.pages) == 1
        assert job.pages[0].text == "Mock OCR result for 16 bytes"
        assert job.pages[0].page_number == 1
        assert job.total_processing_time_ms is not None

    def test_task_processes_multi_page(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake pdf content",
        )

        pages = []
        for i in range(1, 4):
            p = MagicMock()
            p.page_number = i
            p.image_data = f"page {i}".encode()
            p.width = 100
            p.height = 200
            p.format = "png"
            pages.append(p)

        with patch(
            "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
            return_value=pages,
        ):
            process_ocr_job(job_id, "application/pdf", "mock")

        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.page_count == 3
        assert len(job.pages) == 3
        assert job.pages[0].page_number == 1
        assert job.pages[1].page_number == 2
        assert job.pages[2].page_number == 3

    def test_task_fails_on_preprocessing_error(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )

        with (
            patch(
                "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
                side_effect=RuntimeError("PyMuPDF not installed"),
            ),
            pytest.raises(RuntimeError, match="PyMuPDF"),
        ):
            process_ocr_job(job_id, "application/pdf", "mock")

        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error is not None
        assert "PyMuPDF" in job.error

    def test_task_fails_on_missing_content(self) -> None:
        job_id = "nonexistent-job"
        with pytest.raises(RuntimeError, match="content not found"):
            process_ocr_job(job_id, "application/pdf", "mock")

    def test_task_fails_on_unavailable_provider(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mistral",
            content=b"fake",
        )

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "png"

        with (
            patch(
                "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
                return_value=[mock_page],
            ),
            pytest.raises(RuntimeError, match="not available"),
        ):
            process_ocr_job(job_id, "application/pdf", "mistral")

        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED

    def test_task_fails_on_ocr_error(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "png"

        with (
            patch(
                "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
                return_value=[mock_page],
            ),
            patch(
                "ocr_platform.providers.mock.MockProvider.recognize",
                side_effect=RuntimeError("Simulated OCR failure"),
            ),
            pytest.raises(RuntimeError, match="Simulated"),
        ):
            process_ocr_job(job_id, "application/pdf", "mock")

        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error is not None
        assert "Simulated OCR failure" in job.error

    def test_task_deletes_content_after_completion(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"content to be deleted",
        )

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "png"

        with patch(
            "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            process_ocr_job(job_id, "application/pdf", "mock")

        assert job_store.get_content(job_id) is None

    def test_task_deletes_content_after_failure(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"content to be deleted",
        )

        with (
            patch(
                "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
                side_effect=RuntimeError("fail"),
            ),
            pytest.raises(RuntimeError),
        ):
            process_ocr_job(job_id, "application/pdf", "mock")

        assert job_store.get_content(job_id) is None

    def test_task_updates_status_to_processing(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "png"

        with patch(
            "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            process_ocr_job(job_id, "application/pdf", "mock")

        job = job_store.get(job_id)
        assert job is not None
        # Status should be COMPLETED, not PROCESSING, because task finished
        assert job.status == JobStatus.COMPLETED
        assert job.updated_at >= job.created_at
