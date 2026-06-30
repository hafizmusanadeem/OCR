"""Tests for the Celery OCR tasks (concurrent page processing)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ocr_platform.jobs.models import JobPageResult, JobStatus
from ocr_platform.jobs.store import job_store
from ocr_platform.jobs.tasks import finalize_job, process_ocr_job, process_page
from ocr_platform.providers.models import OCRResult


class TestProcessPage:
    """Tests for the single-page OCR task."""

    def setup_method(self) -> None:
        for job in job_store.list_jobs():
            job_store.delete(job.id)

    def test_process_page_runs_ocr_and_stores_result(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        job_store.store_page_images(
            job_id,
            [
                MagicMock(
                    page_number=1,
                    image_data=b"page1",
                    width=100,
                    height=200,
                    format="png",
                )
            ],
        )

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.recognize = AsyncMock(
            return_value=OCRResult(
                text="hello",
                engine="mock",
                confidence=0.95,
                language="en",
                processing_time_ms=42.0,
            )
        )

        with patch(
            "ocr_platform.jobs.tasks.global_registry.create_provider",
            return_value=mock_provider,
        ):
            process_page(job_id, 1, "mock")

        results = job_store.get_page_results(job_id)
        assert len(results) == 1
        assert results[0].page_number == 1
        assert results[0].text == "hello"
        assert results[0].confidence == 0.95
        assert results[0].processing_time_ms == 42.0

        job = job_store.get(job_id)
        assert job is not None
        assert job.pages_completed == 1

    def test_process_page_missing_image_raises(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        with pytest.raises(RuntimeError, match="Page image not found"):
            process_page(job_id, 1, "mock")

    def test_process_page_unavailable_provider_raises(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        job_store.store_page_images(
            job_id,
            [
                MagicMock(
                    page_number=1,
                    image_data=b"page1",
                    width=100,
                    height=200,
                    format="png",
                )
            ],
        )

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False

        with (
            patch(
                "ocr_platform.jobs.tasks.global_registry.create_provider",
                return_value=mock_provider,
            ),
            pytest.raises(RuntimeError, match="not available"),
        ):
            process_page(job_id, 1, "mock")


class TestFinalizeJob:
    """Tests for the chord callback that aggregates results."""

    def setup_method(self) -> None:
        for job in job_store.list_jobs():
            job_store.delete(job.id)

    def test_finalize_job_completes_when_all_pages_done(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        job_store.add_page_result(job_id, 1, JobPageResult(page_number=1, text="hello"))
        job_store.add_page_result(job_id, 2, JobPageResult(page_number=2, text="world"))

        finalize_job([{}, {}], job_id, 2)

        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.page_count == 2
        assert len(job.pages) == 2
        assert job.pages[0].text == "hello"
        assert job.pages[1].text == "world"
        assert job.pages_completed == 2

    def test_finalize_job_fails_when_incomplete(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        job_store.add_page_result(job_id, 1, JobPageResult(page_number=1, text="hello"))

        finalize_job([{}], job_id, 2)

        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error is not None
        assert "Incomplete" in job.error

    def test_finalize_job_computes_total_time(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        job_store.add_page_result(
            job_id, 1, JobPageResult(page_number=1, text="a", processing_time_ms=10.0)
        )
        job_store.add_page_result(
            job_id, 2, JobPageResult(page_number=2, text="b", processing_time_ms=20.0)
        )

        finalize_job([{}, {}], job_id, 2)

        job = job_store.get(job_id)
        assert job is not None
        assert job.total_processing_time_ms == 30.0


class TestProcessOcrJob:
    """Tests for the main OCR job dispatcher."""

    def setup_method(self) -> None:
        for job in job_store.list_jobs():
            job_store.delete(job.id)

    def test_dispatches_chord_for_concurrent_pages(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake pdf",
        )

        mock_pages = []
        for i in range(1, 4):
            p = MagicMock()
            p.page_number = i
            p.image_data = f"page{i}".encode()
            p.width = 100
            p.height = 200
            p.format = "png"
            mock_pages.append(p)

        with (
            patch(
                "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
                return_value=mock_pages,
            ),
            patch("ocr_platform.jobs.tasks.chord") as mock_chord,
        ):
            mock_chord_obj = MagicMock()
            mock_chord.return_value = mock_chord_obj

            process_ocr_job(job_id, "application/pdf", "mock")

        # Status updated to processing
        job = job_store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.PROCESSING
        assert job.page_count == 3

        # Chord was created with 3 page signatures
        mock_chord.assert_called_once()
        args = mock_chord.call_args[0]
        assert len(args[0]) == 3

        # Callback was applied
        mock_chord_obj.assert_called_once()

    def test_fails_when_content_missing(self) -> None:
        with pytest.raises(RuntimeError, match="content not found"):
            process_ocr_job("nonexistent", "application/pdf", "mock")

    def test_fails_on_preprocessing_error(self) -> None:
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

    def test_stores_page_images_in_job_store(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake pdf",
        )

        mock_pages = [
            MagicMock(
                page_number=1,
                image_data=b"img1",
                width=100,
                height=200,
                format="png",
            )
        ]

        with (
            patch(
                "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
                return_value=mock_pages,
            ),
            patch("ocr_platform.jobs.tasks.chord") as mock_chord,
        ):
            mock_chord.return_value = MagicMock()
            process_ocr_job(job_id, "application/pdf", "mock")

        assert job_store.get_page_image(job_id, 1) == b"img1"

    def test_content_deleted_from_store_after_preprocessing(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"original",
        )

        mock_pages = [
            MagicMock(
                page_number=1,
                image_data=b"img1",
                width=100,
                height=200,
                format="png",
            )
        ]

        with (
            patch(
                "ocr_platform.jobs.tasks.DocumentPreprocessor.preprocess",
                return_value=mock_pages,
            ),
            patch("ocr_platform.jobs.tasks.chord") as mock_chord,
        ):
            mock_chord.return_value = MagicMock()
            process_ocr_job(job_id, "application/pdf", "mock")

        # Original content is still there until finalize_job completes
        # (process_ocr_job doesn't delete it anymore)
        assert job_store.get_content(job_id) == b"original"
