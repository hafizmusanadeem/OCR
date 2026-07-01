"""SQLAlchemy ORM models for OCR job persistence.

Maps the domain :class:`~ocr_platform.jobs.models.Job` and
:class:`~ocr_platform.jobs.models.JobPageResult` objects to relational
database tables.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""


class JobDB(Base):
    """Database table for OCR jobs.

    Attributes:
        id: Primary key (UUIDv4).
        status: Lifecycle state (pending, processing, completed, failed).
        filename: Original uploaded filename.
        content_type: MIME type of the uploaded file.
        provider: OCR provider name used.
        created_at: UTC timestamp when the job was created.
        updated_at: UTC timestamp of the last status change.
        error: Error message if the job failed.
        total_processing_time_ms: Total OCR time across all pages.
        page_count: Number of pages in the document.
        pages_completed: Number of pages processed so far.
        pages: Related :class:`PageResultDB` rows.
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pages_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pages: Mapped[list[PageResultDB]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PageResultDB(Base):
    """Database table for per-page OCR results.

    Attributes:
        id: Auto-increment primary key.
        job_id: Foreign key to :class:`JobDB`.
        page_number: 1-based page index.
        text: Extracted text for this page.
        confidence: Confidence score (0.0-1.0).
        language: Detected language code.
        processing_time_ms: Processing time in milliseconds.
        job: Parent :class:`JobDB` row.
    """

    __tablename__ = "page_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    job: Mapped[JobDB] = relationship(back_populates="pages")
