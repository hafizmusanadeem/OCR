"""Celery application configuration.

Sets up the Celery app with Redis broker and result backend.
"""

from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]

from ocr_platform.config import settings

celery_app = Celery(
    "ocr_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["ocr_platform.jobs.tasks"],
)

# Task serialization — JSON is safe for our simple task signatures
# (we only pass job_id, content_type, provider_name, not raw bytes)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes per task
    worker_prefetch_multiplier=1,
)
