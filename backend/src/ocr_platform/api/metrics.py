"""Prometheus metrics endpoint.

Exposes application and process metrics in Prometheus text format.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    PlatformCollector,
    ProcessCollector,
    generate_latest,
)

router = APIRouter(tags=["metrics"])

# Dedicated registry to avoid global state pollution in tests
REGISTRY = CollectorRegistry()
PlatformCollector(registry=REGISTRY)
ProcessCollector(registry=REGISTRY)


@router.get(
    "/metrics",
    response_class=Response,
    summary="Prometheus metrics",
    description="Returns Prometheus-compatible metrics for monitoring. "
    "Scrape this endpoint with Prometheus or Grafana Agent.",
)
async def metrics() -> Response:
    """Return Prometheus metrics in text format.

    Returns:
        A Response with Content-Type set to Prometheus text format.
    """
    data = generate_latest(REGISTRY)
    return Response(
        content=data,
        media_type=CONTENT_TYPE_LATEST,
    )
