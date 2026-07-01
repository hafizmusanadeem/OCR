"""Tests for the database layer (SQLAlchemy models and repository)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ocr_platform.db.models import Base, JobDB, PageResultDB
from ocr_platform.db.repository import JobRepository
from ocr_platform.jobs.models import Job, JobPageResult, JobStatus

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_engine():
    """Create an in-memory async SQLite engine with tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Yield an async session bound to the test engine."""
    async with async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        yield session


class TestJobDBModel:
    """Tests for the JobDB SQLAlchemy model."""

    @pytest.mark.asyncio
    async def test_create_job_db(self, db_session: AsyncSession) -> None:
        job = JobDB(
            id="test-job-1",
            status="pending",
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.get(JobDB, "test-job-1")
        assert result is not None
        assert result.status == "pending"
        assert result.filename == "test.pdf"
        assert result.provider == "mock"

    @pytest.mark.asyncio
    async def test_job_db_defaults(self, db_session: AsyncSession) -> None:
        job = JobDB(
            id="test-job-2",
            filename="test.png",
            content_type="image/png",
            provider="mistral",
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.get(JobDB, "test-job-2")
        assert result is not None
        assert result.status == "pending"
        assert result.pages_completed == 0


class TestPageResultDBModel:
    """Tests for the PageResultDB SQLAlchemy model."""

    @pytest.mark.asyncio
    async def test_create_page_result(self, db_session: AsyncSession) -> None:
        job = JobDB(
            id="test-job-3",
            status="completed",
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
        )
        db_session.add(job)
        await db_session.commit()

        page = PageResultDB(
            job_id="test-job-3",
            page_number=1,
            text="hello world",
            confidence=0.95,
            language="en",
            processing_time_ms=42.0,
        )
        db_session.add(page)
        await db_session.commit()

        assert page.id is not None
        assert page.job_id == "test-job-3"
        assert page.text == "hello world"
        assert page.confidence == 0.95

    @pytest.mark.asyncio
    async def test_page_result_relationship(self, db_session: AsyncSession) -> None:
        job = JobDB(
            id="test-job-4",
            status="completed",
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
        )
        db_session.add(job)
        await db_session.commit()

        page1 = PageResultDB(job_id="test-job-4", page_number=1, text="page one")
        page2 = PageResultDB(job_id="test-job-4", page_number=2, text="page two")
        db_session.add_all([page1, page2])
        await db_session.commit()

        # Use selectinload to avoid lazy loading issues in async context
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(JobDB).where(JobDB.id == "test-job-4").options(selectinload(JobDB.pages))
        )
        db_job = result.scalar_one()
        assert db_job is not None
        assert len(db_job.pages) == 2
        assert db_job.pages[0].text == "page one"
        assert db_job.pages[1].text == "page two"


class TestJobRepository:
    """Tests for the async JobRepository."""

    @pytest.fixture
    async def repo(self, db_engine):  # noqa: PLC0415
        """Create a repository that uses the test engine."""
        from ocr_platform.db import engine as db_engine_mod

        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        original = db_engine_mod._session_factory
        db_engine_mod._session_factory = session_factory
        yield JobRepository
        db_engine_mod._session_factory = original

    @pytest.mark.asyncio
    async def test_create_and_get_job(self, repo) -> None:
        now = datetime.now(UTC)
        job = Job(
            id="repo-test-1",
            status=JobStatus.PENDING,
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
        )
        await repo.create_job(job)

        fetched = await repo.get_job("repo-test-1")
        assert fetched is not None
        assert fetched.id == "repo-test-1"
        assert fetched.status == JobStatus.PENDING
        assert fetched.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_complete_job(self, repo) -> None:
        now = datetime.now(UTC)
        job = Job(
            id="repo-test-2",
            status=JobStatus.PROCESSING,
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
        )
        await repo.create_job(job)

        pages = [
            JobPageResult(page_number=1, text="hello", confidence=0.9),
            JobPageResult(page_number=2, text="world", confidence=0.8),
        ]
        await repo.complete_job("repo-test-2", pages, 100.0, 2)

        fetched = await repo.get_job("repo-test-2")
        assert fetched is not None
        assert fetched.status == JobStatus.COMPLETED
        assert fetched.page_count == 2
        assert len(fetched.pages) == 2
        assert fetched.pages[0].text == "hello"
        assert fetched.pages[1].text == "world"

    @pytest.mark.asyncio
    async def test_fail_job(self, repo) -> None:
        now = datetime.now(UTC)
        job = Job(
            id="repo-test-3",
            status=JobStatus.PROCESSING,
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
        )
        await repo.create_job(job)

        await repo.fail_job("repo-test-3", "Provider crashed")

        fetched = await repo.get_job("repo-test-3")
        assert fetched is not None
        assert fetched.status == JobStatus.FAILED
        assert fetched.error == "Provider crashed"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, repo) -> None:
        fetched = await repo.get_job("nonexistent")
        assert fetched is None

    @pytest.mark.asyncio
    async def test_add_page_result(self, repo) -> None:
        now = datetime.now(UTC)
        job = Job(
            id="repo-test-4",
            status=JobStatus.PROCESSING,
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
        )
        await repo.create_job(job)

        result = JobPageResult(page_number=1, text="hello", confidence=0.9)
        await repo.add_page_result("repo-test-4", result)

        pages = await repo.get_page_results("repo-test-4")
        assert len(pages) == 1
        assert pages[0].text == "hello"
        assert pages[0].page_number == 1

    @pytest.mark.asyncio
    async def test_get_page_results_empty(self, repo) -> None:
        now = datetime.now(UTC)
        job = Job(
            id="repo-test-5",
            status=JobStatus.PENDING,
            filename="test.pdf",
            content_type="application/pdf",
            provider="mock",
            created_at=now,
            updated_at=now,
        )
        await repo.create_job(job)

        pages = await repo.get_page_results("repo-test-5")
        assert pages == []
