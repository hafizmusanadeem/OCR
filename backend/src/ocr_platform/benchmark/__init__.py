"""Benchmark package for OCR evaluation metrics.

Provides CER, WER, latency, and confidence scoring for OCR benchmark runs.
"""

from __future__ import annotations

from ocr_platform.benchmark.metrics import BenchmarkMetrics
from ocr_platform.benchmark.models import (
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkStatus,
    EngineScore,
    PageBenchmark,
)
from ocr_platform.benchmark.service import BenchmarkService, benchmark_service
from ocr_platform.benchmark.store import BenchmarkStore, benchmark_store

__all__ = [
    "BenchmarkMetrics",
    "BenchmarkResult",
    "BenchmarkRun",
    "BenchmarkStatus",
    "BenchmarkService",
    "BenchmarkStore",
    "EngineScore",
    "PageBenchmark",
    "benchmark_service",
    "benchmark_store",
]
