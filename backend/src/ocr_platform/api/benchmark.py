"""Benchmark API endpoints.

Provides REST endpoints for creating benchmark runs, querying status,
and retrieving results with leaderboards.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ocr_platform.benchmark.models import (
    BenchmarkCreateResponse,
    BenchmarkDetailResponse,
    BenchmarkResult,
    BenchmarkStatus,
)
from ocr_platform.benchmark.service import benchmark_service
from ocr_platform.benchmark.store import benchmark_store
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["benchmark"])


class BenchmarkSubmitRequest(BaseModel):
    """Request body for submitting a benchmark run.

    Attributes:
        dataset_name: Name of the dataset to benchmark.
        engines: List of OCR engine names to compare.
        pages: List of pages with ground truth and optional hypotheses.
    """

    dataset_name: str = Field(description="Name of the dataset to benchmark")
    engines: list[str] = Field(description="List of OCR engine names to compare")
    pages: list[dict] = Field(description="Pages with ground truth and optional hypotheses")


class BenchmarkListResponse(BaseModel):
    """Response model for listing benchmark runs.

    Attributes:
        benchmarks: List of benchmark detail responses.
        total: Total number of benchmark runs.
    """

    benchmarks: list[BenchmarkDetailResponse] = Field(description="List of benchmark runs")
    total: int = Field(description="Total number of benchmark runs")


def _run_to_response(run) -> BenchmarkDetailResponse:
    """Convert a BenchmarkRun to a BenchmarkDetailResponse.

    Args:
        run: Internal BenchmarkRun model.

    Returns:
        API-friendly response model.
    """
    return BenchmarkDetailResponse(
        benchmark_id=run.id,
        status=run.status,
        dataset_name=run.dataset_name,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
        page_results=run.page_results,
        engine_scores=run.engine_scores,
        error=run.error,
    )


@router.post(
    "/benchmarks",
    response_model=BenchmarkCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a benchmark run",
    description="Create a new benchmark run and execute it synchronously. "
    "Returns the benchmark ID immediately with the completed results.",
)
async def create_benchmark(request: BenchmarkSubmitRequest) -> BenchmarkCreateResponse:
    """Submit a benchmark run comparing multiple OCR engines.

    Args:
        request: Benchmark submission request.

    Returns:
        A BenchmarkCreateResponse with the benchmark ID and status.

    Raises:
        HTTPException: 400 for invalid request data.
    """
    if not request.engines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one engine must be specified.",
        )
    if not request.pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one page must be provided.",
        )

    benchmark_id = benchmark_store.create(request.dataset_name)
    logger.info(
        "benchmark_submitted",
        benchmark_id=benchmark_id,
        dataset_name=request.dataset_name,
        engine_count=len(request.engines),
        page_count=len(request.pages),
    )

    # Run benchmark synchronously (for now; can be made async via Celery later)
    benchmark_service.run_benchmark(
        benchmark_id=benchmark_id,
        dataset_name=request.dataset_name,
        pages=request.pages,
        engines=request.engines,
    )

    return BenchmarkCreateResponse(
        benchmark_id=benchmark_id,
        status=BenchmarkStatus.COMPLETED,
        message="Benchmark completed successfully. "
        f"GET /api/v1/benchmarks/{benchmark_id} for details.",
    )


@router.get(
    "/benchmarks",
    response_model=BenchmarkListResponse,
    status_code=status.HTTP_200_OK,
    summary="List benchmark runs",
    description="Retrieve all benchmark runs, sorted by creation time descending.",
)
async def list_benchmarks() -> BenchmarkListResponse:
    """List all benchmark runs.

    Returns:
        A BenchmarkListResponse with all benchmark runs.
    """
    runs = benchmark_store.list_runs()
    return BenchmarkListResponse(
        benchmarks=[_run_to_response(r) for r in runs],
        total=len(runs),
    )


@router.get(
    "/benchmarks/{benchmark_id}",
    response_model=BenchmarkDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get benchmark details",
    description="Retrieve the status and results of a benchmark run.",
)
async def get_benchmark(benchmark_id: str) -> BenchmarkDetailResponse:
    """Query the status and results of a benchmark run.

    Args:
        benchmark_id: Unique benchmark identifier.

    Returns:
        BenchmarkDetailResponse with status, metadata, and results.

    Raises:
        HTTPException: 404 if the benchmark ID is not found.
    """
    run = benchmark_store.get(benchmark_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark '{benchmark_id}' not found.",
        )
    return _run_to_response(run)


@router.get(
    "/benchmarks/{benchmark_id}/leaderboard",
    response_model=BenchmarkResult,
    status_code=status.HTTP_200_OK,
    summary="Get benchmark leaderboard",
    description="Retrieve the leaderboard for a completed benchmark run. "
    "Engines are ranked by average accuracy (descending).",
)
async def get_leaderboard(benchmark_id: str) -> BenchmarkResult:
    """Retrieve the leaderboard for a completed benchmark run.

    Args:
        benchmark_id: Unique benchmark identifier.

    Returns:
        BenchmarkResult with the leaderboard and best engine.

    Raises:
        HTTPException: 404 if the benchmark ID is not found.
        HTTPException: 422 if the benchmark is not completed.
    """
    run = benchmark_store.get(benchmark_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark '{benchmark_id}' not found.",
        )

    if run.status != BenchmarkStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Benchmark '{benchmark_id}' is not completed (status: {run.status.value}).",
        )

    try:
        leaderboard_data = benchmark_service.build_leaderboard(benchmark_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return BenchmarkResult(
        benchmark_id=leaderboard_data["benchmark_id"],
        dataset_name=leaderboard_data["dataset_name"],
        leaderboard=leaderboard_data["leaderboard"],
        best_engine=leaderboard_data["best_engine"],
        total_pages=leaderboard_data["total_pages"],
        total_engines=leaderboard_data["total_engines"],
    )
