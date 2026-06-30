"""Tests for the in-memory job store."""

from __future__ import annotations

import threading

import pytest

from ocr_platform.jobs.models import JobPageResult, JobStatus
from ocr_platform.jobs.store import JobStore
from ocr_platform.preprocessing.types import PageImage


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


class TestJobStorePageStorage:
    """Page-level storage tests."""

    def test_store_and_get_page_images(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        pages = [
            PageImage(page_number=1, image_data=b"img1", width=100, height=200, format="png"),
            PageImage(page_number=2, image_data=b"img2", width=100, height=200, format="png"),
        ]
        store.store_page_images(job_id, pages)
        assert store.get_page_image(job_id, 1) == b"img1"
        assert store.get_page_image(job_id, 2) == b"img2"
        assert store.get_page_image(job_id, 3) is None

    def test_store_page_images_updates_job_count(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        pages = [
            PageImage(page_number=1, image_data=b"img1", width=100, height=200, format="png"),
            PageImage(page_number=2, image_data=b"img2", width=100, height=200, format="png"),
        ]
        store.store_page_images(job_id, pages)
        job = store.get(job_id)
        assert job is not None
        assert job.page_count == 2

    def test_add_and_get_page_results(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.add_page_result(job_id, 2, JobPageResult(page_number=2, text="world"))
        store.add_page_result(job_id, 1, JobPageResult(page_number=1, text="hello"))
        results = store.get_page_results(job_id)
        assert len(results) == 2
        assert results[0].page_number == 1
        assert results[1].page_number == 2

    def test_add_page_result_updates_pages_completed(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        store.add_page_result(job_id, 1, JobPageResult(page_number=1, text="hello"))
        job = store.get(job_id)
        assert job is not None
        assert job.pages_completed == 1
        store.add_page_result(job_id, 2, JobPageResult(page_number=2, text="world"))
        job = store.get(job_id)
        assert job is not None
        assert job.pages_completed == 2

    def test_all_pages_done(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        assert not store.all_pages_done(job_id, 2)
        store.add_page_result(job_id, 1, JobPageResult(page_number=1, text="hello"))
        assert not store.all_pages_done(job_id, 2)
        store.add_page_result(job_id, 2, JobPageResult(page_number=2, text="world"))
        assert store.all_pages_done(job_id, 2)

    def test_complete_clears_page_data(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        pages = [
            PageImage(page_number=1, image_data=b"img1", width=100, height=200, format="png"),
        ]
        store.store_page_images(job_id, pages)
        store.add_page_result(job_id, 1, JobPageResult(page_number=1, text="hello"))
        store.complete(job_id, [JobPageResult(page_number=1, text="hello")], 10.0, 1)
        assert store.get_page_image(job_id, 1) is None
        assert store.get_page_results(job_id) == []

    def test_fail_clears_page_data(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")
        pages = [
            PageImage(page_number=1, image_data=b"img1", width=100, height=200, format="png"),
        ]
        store.store_page_images(job_id, pages)
        store.fail(job_id, "Error")
        assert store.get_page_image(job_id, 1) is None

    def test_thread_safety_page_results(self) -> None:
        store = JobStore()
        job_id = store.create("test.pdf", "application/pdf", "mock", b"content")

        def add_result(page_num: int) -> None:
            store.add_page_result(
                job_id, page_num, JobPageResult(page_number=page_num, text=f"page{page_num}")
            )

        threads = [threading.Thread(target=add_result, args=(i,)) for i in range(1, 11)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert store.all_pages_done(job_id, 10)
        results = store.get_page_results(job_id)
        assert len(results) == 10
        assert results[0].page_number == 1
        assert results[9].page_number == 10
