# Worker health check endpoint

from __future__ import annotations

from fastapi import APIRouter, status

from ocr_platform.jobs.celery_app import celery_app
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["workers"])


@router.get(
    "/workers/health",
    status_code=status.HTTP_200_OK,
    summary="Worker health check",
    description="Returns the health status of connected Celery workers.",
)
async def workers_health() -> dict:
    """Check health of connected Celery workers.

    Returns:
        Dictionary with worker count and status.
    """
    try:
        # Inspect active workers
        inspector = celery_app.control.inspect()
        active = inspector.active() or {}
        registered = inspector.registered() or {}
        
        worker_count = len(active)
        registered_count = len(registered)
        
        logger.info(
            "workers_health_checked",
            active_workers=worker_count,
            registered_workers=registered_count,
        )
        
        return {
            "status": "ok" if worker_count > 0 else "degraded",
            "active_workers": worker_count,
            "registered_workers": registered_count,
            "workers": list(active.keys()) if active else [],
        }
    except Exception as exc:
        logger.warning("workers_health_check_failed", error=str(exc))
        return {
            "status": "error",
            "active_workers": 0,
            "registered_workers": 0,
            "workers": [],
            "error": str(exc),
        }
