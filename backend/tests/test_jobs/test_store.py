"""Tests for the in-memory job store."""

from __future__ import annotations

import threading

import pytest

from ocr_platform.jobs.models import JobPageResult, JobStatus
from ocr_platform.jobs.store import JobStore


class TestJobStore:
    """JobStore lifecycle and thread-safety tests."""

    def test_create_returns_uuid(self) -> None:
        store = JobStore()
        job_id = store.create(
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            content=b"fake pdf",
        )
        assert isinstance(job_id, str)
        assert len(job_id) == 36  # UUIDv4 length

    def test_get_existing_job(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        job = store.get(job_id)
        assert job is not None
        assert job.filename == "test.pdf"
        assert job.status == JobStatus.PENDING
        assert job.provider == "mock"

    def test_get_missing_job(self) -> None:
        store = JobStore()
        assert store.get("nonexistent") is None

    def test_get_content(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        assert store.get_content(job_id) == b"content"

    def test_get_content_missing(self) -> None:
        store = JobStore()
        assert store.get_content("nonexistent") is None

    def test_update_status(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.update_status(job_id, JobStatus.PROCESSING)
        job = store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.PROCESSING

    def test_update_status_missing_raises(self) -> None:
        store = JobStore()
        with pytest.raises(KeyError):
            store.update_status("nonexistent", JobStatus.PROCESSING)

    def test_complete(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.complete(
            job_id,
            pages=[JobPageResult(page_number=1, text="hello")],
            total_processing_time_ms=100.0,
            page_count=1,
        )
        job = store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert len(job.pages) == 1
        assert job.page_count == 1
        assert job.total_processing_time_ms == 100.0

    def test_complete_deletes_content(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.complete(
            job_id,
            pages=[JobPageResult(page_number=1, text="hello")],
            total_processing_time_ms=100.0,
            page_count=1,
        )
        assert store.get_content(job_id) is None

    def test_fail(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.fail(job_id, "Something went wrong")
        job = store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error == "Something went wrong"

    def test_fail_deletes_content(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.fail(job_id, "Error")
        assert store.get_content(job_id) is None

    def test_delete(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.delete(job_id)
        assert store.get(job_id) is None
        assert store.get_content(job_id) is None

    def test_list_jobs_sorted(self) -> None:
        store = JobStore()
        id1 = store.create("a.pdf", "application/pdf", "mock", b"x")
        id2 = store.create("b.pdf", "application/pdf", "mock", b"y")
        jobs = store.list_jobs()
        assert len(jobs) == 2
        assert jobs[0].id == id1
        assert jobs[1].id == id2

    def test_thread_safety_create(self) -> None:
        store = JobStore()
        ids: list[str] = []
        lock = threading.Lock()

        def create() -> None:
            job_id = store.create("t.pdf", "application/pdf", "mock", b"x")
            with lock:
                ids.append(job_id)

        threads = [threading.Thread(target=create) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(ids)) == 10
        assert len(store.list_jobs()) == 10

    def test_thread_safety_update(self) -> None:
        store = JobStore()
        job_id = store.create("t.pdf", "application/pdf", "mock", b"x")

        def update() -> None:
            store.update_status(job_id, JobStatus.PROCESSING)

        threads = [threading.Thread(target=update) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        job = store.get(job_id)
        assert job is not None
        assert job.status == JobStatus.PROCESSING
