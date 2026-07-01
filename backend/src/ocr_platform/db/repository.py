"""Database repository for OCR job persistence.

Provides async CRUD operations for :class:`~ocr_platform.db.models.JobDB`
and :class:`~ocr_platform.db.models.PageResultDB`.

All methods accept and return Pydantic domain models, keeping the ORM
layer decoupled from the rest of the application.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ocr_platform.db.engine import get_session_factory
from ocr_platform.db.models import JobDB, PageResultDB
from ocr_platform.jobs.models import Job, JobPageResult, JobStatus
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)


class JobRepository:
    """Async repository for persisting and retrieving OCR jobs.

    Uses SQLAlchemy async sessions with the ``get_session_factory()``
    engine. All public methods are ``async`` and should be awaited or
    wrapped with ``asyncio.run()`` when called from synchronous code.
    """

    @staticmethod
    async def create_job(job: Job) -> None:
        """Persist a new job to the database.

        Args:
            job: Domain Job model to persist.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            db_job = JobDB(
                id=job.id,
                status=job.status.value,
                filename=job.filename,
                content_type=job.content_type,
                provider=job.provider,
                created_at=job.created_at,
                updated_at=job.updated_at,
                pages_completed=job.pages_completed,
            )
            session.add(db_job)
            await session.commit()
            logger.info("db_job_created", job_id=job.id)

    @staticmethod
    async def update_job(job: Job) -> None:
        """Update an existing job in the database.

        Args:
            job: Domain Job model with updated fields.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            db_job = await session.get(JobDB, job.id)
            if db_job is None:
                logger.warning("db_job_not_found_for_update", job_id=job.id)
                return
            db_job.status = job.status.value
            db_job.updated_at = job.updated_at
            db_job.error = job.error
            db_job.total_processing_time_ms = job.total_processing_time_ms
            db_job.page_count = job.page_count
            db_job.pages_completed = job.pages_completed
            await session.commit()
            logger.info("db_job_updated", job_id=job.id, status=job.status.value)

    @staticmethod
    async def complete_job(
        job_id: str,
        pages: list[JobPageResult],
        total_processing_time_ms: float,
        page_count: int,
    ) -> None:
        """Mark a job as completed and persist all page results.

        Args:
            job_id: Unique job identifier.
            pages: Per-page OCR results.
            total_processing_time_ms: Total processing time.
            page_count: Number of pages.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            db_job = await session.get(JobDB, job_id)
            if db_job is None:
                logger.warning("db_job_not_found_for_completion", job_id=job_id)
                return

            db_job.status = JobStatus.COMPLETED.value
            db_job.total_processing_time_ms = total_processing_time_ms
            db_job.page_count = page_count
            db_job.pages_completed = page_count
            db_job.updated_at = datetime.now(UTC)

            for page in pages:
                db_page = PageResultDB(
                    job_id=job_id,
                    page_number=page.page_number,
                    text=page.text,
                    confidence=page.confidence,
                    language=page.language,
                    processing_time_ms=page.processing_time_ms,
                )
                session.add(db_page)

            await session.commit()
            logger.info(
                "db_job_completed",
                job_id=job_id,
                page_count=page_count,
            )

    @staticmethod
    async def fail_job(job_id: str, error: str) -> None:
        """Mark a job as failed in the database.

        Args:
            job_id: Unique job identifier.
            error: Error message.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            db_job = await session.get(JobDB, job_id)
            if db_job is None:
                logger.warning("db_job_not_found_for_failure", job_id=job_id)
                return
            db_job.status = JobStatus.FAILED.value
            db_job.error = error
            db_job.updated_at = datetime.now(UTC)
            await session.commit()
            logger.info("db_job_failed", job_id=job_id)

    @staticmethod
    async def add_page_result(job_id: str, result: JobPageResult) -> None:
        """Persist a single page result.

        Args:
            job_id: Unique job identifier.
            result: Page OCR result.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            db_page = PageResultDB(
                job_id=job_id,
                page_number=result.page_number,
                text=result.text,
                confidence=result.confidence,
                language=result.language,
                processing_time_ms=result.processing_time_ms,
            )
            session.add(db_page)
            await session.commit()
            logger.info(
                "db_page_result_created",
                job_id=job_id,
                page_number=result.page_number,
            )

    @staticmethod
    async def get_job(job_id: str) -> Job | None:
        """Retrieve a job from the database.

        Args:
            job_id: Unique job identifier.

        Returns:
            Domain Job model or ``None`` if not found.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(JobDB).where(JobDB.id == job_id).options(selectinload(JobDB.pages))
            )
            db_job = result.scalar_one_or_none()
            if db_job is None:
                return None

            return Job(
                id=db_job.id,
                status=JobStatus(db_job.status),
                filename=db_job.filename,
                content_type=db_job.content_type,
                provider=db_job.provider,
                created_at=db_job.created_at,
                updated_at=db_job.updated_at,
                pages=[
                    JobPageResult(
                        page_number=p.page_number,
                        text=p.text,
                        confidence=p.confidence,
                        language=p.language,
                        processing_time_ms=p.processing_time_ms,
                    )
                    for p in db_job.pages
                ],
                error=db_job.error,
                total_processing_time_ms=db_job.total_processing_time_ms,
                page_count=db_job.page_count,
                pages_completed=db_job.pages_completed,
            )

    @staticmethod
    async def get_page_results(job_id: str) -> list[JobPageResult]:
        """Retrieve page results for a job.

        Args:
            job_id: Unique job identifier.

        Returns:
            List of page results, sorted by page number.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(PageResultDB)
                .where(PageResultDB.job_id == job_id)
                .order_by(PageResultDB.page_number)
            )
            pages = result.scalars().all()
            return [
                JobPageResult(
                    page_number=p.page_number,
                    text=p.text,
                    confidence=p.confidence,
                    language=p.language,
                    processing_time_ms=p.processing_time_ms,
                )
                for p in pages
            ]
