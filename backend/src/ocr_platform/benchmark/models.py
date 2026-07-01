"""Benchmark models for OCR evaluation.

Defines Pydantic models for benchmark runs, per-page scores, engine-level
aggregations, and overall benchmark results.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class BenchmarkStatus(StrEnum):
    """Lifecycle states of a benchmark run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PageBenchmark(BaseModel):
    """Benchmark score for a single page.

    Attributes:
        page_number: 1-based page index.
        ground_truth: Reference text for this page.
        hypothesis: OCR output text for this page.
        cer: Character Error Rate (0.0-1.0).
        wer: Word Error Rate (0.0-1.0).
        accuracy: Character-level accuracy (1 - CER).
        word_accuracy: Word-level accuracy (1 - WER).
        confidence: OCR confidence score (0.0-1.0), if available.
        latency_ms: Processing time in milliseconds, if available.
    """

    page_number: int = Field(ge=1, description="1-based page index")
    ground_truth: str = Field(description="Reference text for this page")
    hypothesis: str = Field(description="OCR output text for this page")
    cer: float = Field(ge=0.0, le=1.0, description="Character Error Rate")
    wer: float = Field(ge=0.0, le=1.0, description="Word Error Rate")
    accuracy: float = Field(ge=0.0, le=1.0, description="Character-level accuracy")
    word_accuracy: float = Field(ge=0.0, le=1.0, description="Word-level accuracy")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="OCR confidence")
    latency_ms: float | None = Field(default=None, ge=0.0, description="Processing time in ms")


class EngineScore(BaseModel):
    """Aggregated benchmark score for a single OCR engine.

    Attributes:
        engine: Name of the OCR engine.
        average_cer: Mean CER across all pages.
        average_wer: Mean WER across all pages.
        average_accuracy: Mean character accuracy across all pages.
        average_word_accuracy: Mean word accuracy across all pages.
        average_confidence: Mean confidence across all pages (if available).
        average_latency_ms: Mean latency across all pages (if available).
        total_pages: Total number of pages evaluated.
        total_characters: Total character count in ground truth.
        total_words: Total word count in ground truth.
    """

    engine: str = Field(description="Name of the OCR engine")
    average_cer: float = Field(ge=0.0, le=1.0, description="Mean CER across all pages")
    average_wer: float = Field(ge=0.0, le=1.0, description="Mean WER across all pages")
    average_accuracy: float = Field(ge=0.0, le=1.0, description="Mean character accuracy")
    average_word_accuracy: float = Field(ge=0.0, le=1.0, description="Mean word accuracy")
    average_confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Mean confidence")
    average_latency_ms: float | None = Field(default=None, ge=0.0, description="Mean latency in ms")
    total_pages: int = Field(ge=0, description="Total number of pages evaluated")
    total_characters: int = Field(ge=0, description="Total character count in ground truth")
    total_words: int = Field(ge=0, description="Total word count in ground truth")


class BenchmarkRun(BaseModel):
    """Internal representation of a benchmark run.

    Attributes:
        id: Unique benchmark run identifier.
        status: Current lifecycle state.
        dataset_name: Name of the dataset used for benchmarking.
        created_at: UTC creation timestamp.
        updated_at: UTC last-update timestamp.
        page_results: Per-page benchmark results.
        engine_scores: Aggregated scores per engine.
        error: Error message if the benchmark failed.
    """

    id: str = Field(description="Unique benchmark run identifier")
    status: BenchmarkStatus = Field(description="Current lifecycle state")
    dataset_name: str = Field(description="Name of the dataset used")
    created_at: datetime = Field(description="UTC creation timestamp")
    updated_at: datetime = Field(description="UTC last-update timestamp")
    page_results: list[PageBenchmark] = Field(default_factory=list, description="Per-page results")
    engine_scores: list[EngineScore] = Field(default_factory=list, description="Aggregated engine scores")
    error: str | None = Field(default=None, description="Error message if failed")


class BenchmarkCreateResponse(BaseModel):
    """Response model for benchmark submission.

    Attributes:
        benchmark_id: Unique identifier for the benchmark run.
        status: Initial benchmark status.
        message: Human-readable confirmation message.
    """

    benchmark_id: str = Field(description="Unique benchmark run identifier")
    status: BenchmarkStatus = Field(description="Initial benchmark status")
    message: str = Field(description="Human-readable confirmation message")


class BenchmarkDetailResponse(BaseModel):
    """Response model for benchmark status query.

    Attributes:
        benchmark_id: Unique benchmark run identifier.
        status: Current benchmark status.
        dataset_name: Name of the dataset used.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        page_results: Per-page benchmark results (if completed).
        engine_scores: Aggregated engine scores (if completed).
        error: Error message (if failed).
    """

    benchmark_id: str = Field(description="Unique benchmark run identifier")
    status: BenchmarkStatus = Field(description="Current benchmark status")
    dataset_name: str = Field(description="Name of the dataset used")
    created_at: str = Field(description="ISO-8601 creation timestamp")
    updated_at: str = Field(description="ISO-8601 last-update timestamp")
    page_results: list[PageBenchmark] = Field(default_factory=list, description="Per-page results")
    engine_scores: list[EngineScore] = Field(default_factory=list, description="Engine scores")
    error: str | None = Field(default=None, description="Error message if failed")


class BenchmarkResult(BaseModel):
    """Overall benchmark result with leaderboard.

    Attributes:
        benchmark_id: Unique benchmark run identifier.
        dataset_name: Name of the dataset used.
        leaderboard: Engine scores sorted by accuracy (descending).
        best_engine: Name of the best-performing engine.
        total_pages: Total number of pages evaluated.
        total_engines: Number of engines compared.
    """

    benchmark_id: str = Field(description="Unique benchmark run identifier")
    dataset_name: str = Field(description="Name of the dataset used")
    leaderboard: list[EngineScore] = Field(description="Engine scores sorted by accuracy descending")
    best_engine: str | None = Field(default=None, description="Best-performing engine name")
    total_pages: int = Field(ge=0, description="Total pages evaluated")
    total_engines: int = Field(ge=0, description="Number of engines compared")
