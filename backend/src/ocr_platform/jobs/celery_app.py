"""Celery application configuration with robust failure recovery.

Sets up the Celery app with Redis broker and result backend.
Configures retry policies, dead-letter queues, and task acknowledgement
settings for worker-crash resilience.
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
    task_time_limit=300,  # 5 minutes per task (hard limit)
    task_soft_time_limit=240,  # 4 minutes (soft limit, triggers exception)
    worker_prefetch_multiplier=1,
    # Failure recovery settings
    task_acks_late=True,  # Acknowledge after task completes, allowing requeue on crash
    task_reject_on_worker_lost=True,  # Requeue if worker dies mid-task
    task_default_retry_delay=10,  # Base retry delay in seconds
    task_max_retries=5,  # Maximum retries per task
    # Dead letter queue for failed tasks
    task_routes={
        "ocr_platform.jobs.tasks.process_page": {"queue": "ocr.pages"},
        "ocr_platform.jobs.tasks.finalize_job": {"queue": "ocr.finalize"},
        "ocr_platform.jobs.tasks.process_ocr_job": {"queue": "ocr.jobs"},
    },
    broker_transport_options={
        "visibility_timeout": 600,  # 10 minutes for Redis
    },
)
