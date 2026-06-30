"""Tests for the job API endpoints."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from ocr_platform.jobs.models import JobPageResult
from ocr_platform.jobs.store import job_store
from ocr_platform.main import create_app

client = TestClient(create_app())


class TestCreateJob:
    """POST /api/v1/jobs endpoint tests."""

    def setup_method(self) -> None:
        # Clear the global store before each test
        for job in job_store.list_jobs():
            job_store.delete(job.id)

    def test_create_job_with_mock_provider(self) -> None:
        with patch("ocr_platform.jobs.tasks.process_ocr_job.delay") as mock_delay:
            response = client.post(
                "/api/v1/jobs",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
                data={"provider": "mock"},
            )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert len(data["job_id"]) == 36
        assert data["status"] == "pending"
        assert "Poll GET" in data["message"]
        mock_delay.assert_called_once()

    def test_create_job_without_provider_uses_default(self) -> None:
        with patch("ocr_platform.jobs.tasks.process_ocr_job.delay") as mock_delay:
            response = client.post(
                "/api/v1/jobs",
                files={"file": ("test.pdf", b"x", "application/pdf")},
            )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        mock_delay.assert_called_once()

    def test_create_job_invalid_file_type(self) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.text

    def test_create_job_file_too_large(self) -> None:
        large = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("large.pdf", large, "application/pdf")},
        )
        assert response.status_code == 413
        assert "too large" in response.text.lower()

    def test_create_job_unknown_provider(self) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", b"x", "application/pdf")},
            data={"provider": "nonexistent"},
        )
        assert response.status_code == 404
        assert "not found" in response.text.lower()

    def test_create_job_unavailable_provider(self) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", b"x", "application/pdf")},
            data={"provider": "mistral"},
        )
        assert response.status_code == 503
        assert "not available" in response.text.lower()

    def test_create_job_no_file(self) -> None:
        response = client.post("/api/v1/jobs")
        assert response.status_code == 422


class TestGetJob:
    """GET /api/v1/jobs/{job_id} endpoint tests."""

    def setup_method(self) -> None:
        for job in job_store.list_jobs():
            job_store.delete(job.id)

    def test_get_pending_job(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert data["filename"] == "test.pdf"
        assert data["provider"] == "mock"
        assert data["pages"] == []
        assert data["error"] is None

    def test_get_completed_job(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        job_store.complete(
            job_id,
            pages=[JobPageResult(page_number=1, text="hello")],
            total_processing_time_ms=42.0,
            page_count=1,
        )
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["page_count"] == 1
        assert len(data["pages"]) == 1
        assert data["pages"][0]["page_number"] == 1
        assert data["pages"][0]["text"] == "hello"
        assert data["total_processing_time_ms"] == 42.0

    def test_get_failed_job(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        job_store.fail(job_id, "Provider crashed")
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Provider crashed"

    def test_get_missing_job(self) -> None:
        response = client.get("/api/v1/jobs/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.text.lower()

    def test_get_job_has_timestamps(self) -> None:
        job_id = job_store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake",
        )
        response = client.get(f"/api/v1/jobs/{job_id}")
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
