"""Jobs package."""

from __future__ import annotations

from ocr_platform.jobs.models import (
    Job,
    JobCreateResponse,
    JobDetailResponse,
    JobPageResult,
    JobStatus,
)
from ocr_platform.jobs.store import JobStore, job_store

__all__ = [
    "Job",
    "JobCreateResponse",
    "JobDetailResponse",
    "JobPageResult",
    "JobStatus",
    "JobStore",
    "job_store",
]
