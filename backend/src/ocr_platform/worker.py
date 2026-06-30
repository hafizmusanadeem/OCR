"""Celery worker entry point.

Starts a Celery worker that processes OCR tasks from the Redis queue.

Usage:
    python -m ocr_platform.worker

Or with Celery CLI:
    celery -A ocr_platform.jobs.celery_app worker --loglevel=info
"""

from __future__ import annotations

from ocr_platform.jobs.celery_app import celery_app
from ocr_platform.jobs.tasks import process_ocr_job  # noqa: F401
from ocr_platform.logging_config import configure_logging

# Ensure logging is configured before worker starts
configure_logging()

# This module is imported by Celery to discover tasks
# The `celery_app` variable is the application instance

if __name__ == "__main__":
    celery_app.start()
