"""Health check endpoint.

Provides a simple liveness/readiness probe for orchestrators
and load balancers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ocr_platform.config import settings

router = APIRouter(tags=["health"])

STARTUP_TIME = datetime.now(UTC)


class HealthResponse(BaseModel):
    """Health check response model.

    Attributes:
        status: Human-readable service status.
        version: Application semantic version.
        environment: Current deployment environment.
        uptime_seconds: Seconds since service startup.
    """

    status: str = Field(default="ok", examples=["ok"])
    version: str = Field(default="0.1.0", examples=["0.1.0"])
    environment: str = Field(default="development", examples=["development"])
    uptime_seconds: float = Field(default=0.0, examples=[42.5])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns service status, version, and uptime. "
    "Use this endpoint for liveness and readiness probes.",
)
async def health_check() -> HealthResponse:
    """Return the current health status of the OCR Platform API.

    Returns:
        A HealthResponse with status, version, environment, and uptime.
    """
    uptime = (datetime.now(UTC) - STARTUP_TIME).total_seconds()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env,
        uptime_seconds=uptime,
    )
