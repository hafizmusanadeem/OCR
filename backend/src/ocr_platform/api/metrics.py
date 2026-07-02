"""Prometheus metrics endpoint and custom business metrics.

Exposes application and process metrics in Prometheus text format,
plus custom OCR-platform metrics for jobs, benchmarks, and workers.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
    PlatformCollector,
    ProcessCollector,
    generate_latest,
)

from ocr_platform.benchmark.store import benchmark_store
from ocr_platform.jobs.store import job_store
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["metrics"])

# Dedicated registry to avoid global state pollution in tests
REGISTRY = CollectorRegistry()
PlatformCollector(registry=REGISTRY)
ProcessCollector(registry=REGISTRY)

# Custom business metrics
_jobs_pending = Gauge(
    "ocr_jobs_pending", "Number of pending OCR jobs", registry=REGISTRY
)
_jobs_processing = Gauge(
    "ocr_jobs_processing", "Number of processing OCR jobs", registry=REGISTRY
)
_jobs_completed = Gauge(
    "ocr_jobs_completed", "Number of completed OCR jobs", registry=REGISTRY
)
_jobs_failed = Gauge(
    "ocr_jobs_failed", "Number of failed OCR jobs", registry=REGISTRY
)

_benchmark_cer = Gauge(
    "benchmark_average_cer",
    "Average CER by dataset and engine",
    ["dataset", "engine"],
    registry=REGISTRY,
)
_benchmark_latency = Gauge(
    "benchmark_average_latency_ms",
    "Average latency in ms by engine and dataset",
    ["dataset", "engine"],
    registry=REGISTRY,
)


def _update_job_metrics() -> None:
    """Refresh job gauges from the in-memory job store."""
    counts = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    for job in job_store.list_jobs():
        counts[job.status.value] = counts.get(job.status.value, 0) + 1
    _jobs_pending.set(counts.get("pending", 0))
    _jobs_processing.set(counts.get("processing", 0))
    _jobs_completed.set(counts.get("completed", 0))
    _jobs_failed.set(counts.get("failed", 0))


def _update_benchmark_metrics() -> None:
    """Refresh benchmark gauges from the in-memory benchmark store."""
    for run in benchmark_store.list_runs():
        if run.status.value != "completed" or not run.engine_scores:
            continue
        for score in run.engine_scores:
            _benchmark_cer.labels(
                dataset=run.dataset_name, engine=score.engine
            ).set(score.average_cer)
            if score.average_latency_ms is not None:
                _benchmark_latency.labels(
                    dataset=run.dataset_name, engine=score.engine
                ).set(score.average_latency_ms)


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
    try:
        _update_job_metrics()
        _update_benchmark_metrics()
    except Exception as exc:
        logger.warning("custom_metrics_update_failed", error=str(exc))
    data = generate_latest(REGISTRY)
    return Response(
        content=data,
        media_type=CONTENT_TYPE_LATEST,
    )
