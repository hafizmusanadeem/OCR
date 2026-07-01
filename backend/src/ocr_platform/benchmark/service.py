"""Benchmark service orchestration.

Runs OCR benchmarks by comparing engine outputs against ground-truth
datasets, computing CER, WER, latency, and confidence scores.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime

from ocr_platform.benchmark.metrics import BenchmarkMetrics
from ocr_platform.benchmark.models import (
    BenchmarkRun,
    BenchmarkStatus,
    EngineScore,
    PageBenchmark,
)
from ocr_platform.benchmark.store import BenchmarkStore, benchmark_store
from ocr_platform.jobs.models import JobPageResult
from ocr_platform.logging_config import get_logger
from ocr_platform.providers import global_registry
from ocr_platform.providers.models import OCRResult

logger = get_logger(__name__)


class BenchmarkService:
    """Service for orchestrating OCR benchmark runs.

    Attributes:
        store: In-memory benchmark store.
    """

    def __init__(self, store: BenchmarkStore | None = None) -> None:
        self.store = store or benchmark_store

    def run_benchmark(
        self,
        benchmark_id: str,
        dataset_name: str,
        pages: list[dict],
        engines: list[str],
    ) -> None:
        """Run a benchmark comparing multiple engines against a dataset.

        This is a synchronous blocking method suitable for Celery tasks or
        direct API calls. Each page dict must contain:
        - ``page_number``: int
        - ``ground_truth``: str
        - ``image_data``: bytes (optional, for live OCR)
        - ``hypotheses``: dict[str, str] (optional, pre-computed engine outputs)

        If ``hypotheses`` is provided, the engine names in *engines* are used
        as keys into that dict. If ``image_data`` is provided, live OCR is run
        for each engine.

        Args:
            benchmark_id: Unique benchmark identifier.
            dataset_name: Name of the dataset.
            pages: List of page dicts with ground truth and optional hypotheses.
            engines: List of engine names to benchmark.
        """
        self.store.update_status(benchmark_id, BenchmarkStatus.RUNNING)
        logger.info(
            "benchmark_started",
            benchmark_id=benchmark_id,
            dataset_name=dataset_name,
            engine_count=len(engines),
            page_count=len(pages),
        )

        try:
            all_page_results: list[PageBenchmark] = []
            engine_pages: dict[str, list[PageBenchmark]] = defaultdict(list)

            for page in pages:
                page_number = page["page_number"]
                ground_truth = page["ground_truth"]

                for engine_name in engines:
                    hypothesis = self._get_hypothesis(page, engine_name)
                    confidence = page.get("hypotheses", {}).get(engine_name, {}).get("confidence")
                    latency_ms = page.get("hypotheses", {}).get(engine_name, {}).get("latency_ms")

                    score = BenchmarkMetrics.compute_page_score(
                        ground_truth=ground_truth,
                        hypothesis=hypothesis,
                        confidence=confidence,
                        latency_ms=latency_ms,
                    )

                    page_benchmark = PageBenchmark(
                        page_number=page_number,
                        ground_truth=ground_truth,
                        hypothesis=hypothesis,
                        cer=score["cer"],
                        wer=score["wer"],
                        accuracy=score["accuracy"],
                        word_accuracy=score["word_accuracy"],
                        confidence=score["confidence"],
                        latency_ms=score["latency_ms"],
                    )
                    all_page_results.append(page_benchmark)
                    engine_pages[engine_name].append(page_benchmark)

            # Compute engine scores
            engine_scores = []
            for engine_name in engines:
                scores = engine_pages[engine_name]
                if not scores:
                    continue

                total_chars = sum(len(p.ground_truth) for p in scores)
                total_words = sum(len(p.ground_truth.split()) for p in scores)

                engine_score = EngineScore(
                    engine=engine_name,
                    average_cer=round(sum(p.cer for p in scores) / len(scores), 6),
                    average_wer=round(sum(p.wer for p in scores) / len(scores), 6),
                    average_accuracy=round(sum(p.accuracy for p in scores) / len(scores), 6),
                    average_word_accuracy=round(sum(p.word_accuracy for p in scores) / len(scores), 6),
                    average_confidence=(
                        round(sum(p.confidence for p in scores if p.confidence is not None) / len([p for p in scores if p.confidence is not None]), 6)
                        if any(p.confidence is not None for p in scores)
                        else None
                    ),
                    average_latency_ms=(
                        round(sum(p.latency_ms for p in scores if p.latency_ms is not None) / len([p for p in scores if p.latency_ms is not None]), 3)
                        if any(p.latency_ms is not None for p in scores)
                        else None
                    ),
                    total_pages=len(scores),
                    total_characters=total_chars,
                    total_words=total_words,
                )
                engine_scores.append(engine_score)

            # Sort by accuracy descending
            engine_scores.sort(key=lambda s: s.average_accuracy, reverse=True)

            self.store.add_page_results(benchmark_id, all_page_results)
            self.store.set_engine_scores(benchmark_id, engine_scores)
            self.store.complete(benchmark_id)

            logger.info(
                "benchmark_finished",
                benchmark_id=benchmark_id,
                engine_count=len(engine_scores),
                page_count=len(pages),
            )

        except Exception as exc:
            logger.error("benchmark_failed", benchmark_id=benchmark_id, error=str(exc))
            self.store.fail(benchmark_id, str(exc))
            raise

    def _get_hypothesis(self, page: dict, engine_name: str) -> str:
        """Extract hypothesis text for a given engine from a page dict.

        Args:
            page: Page dict with ground truth and optional hypotheses.
            engine_name: Engine name to look up.

        Returns:
            Hypothesis text or empty string if not found.
        """
        hypotheses = page.get("hypotheses", {})
        if isinstance(hypotheses, dict):
            engine_result = hypotheses.get(engine_name)
            if isinstance(engine_result, dict):
                return engine_result.get("text", "")
            if isinstance(engine_result, str):
                return engine_result
        return ""

    def build_leaderboard(self, benchmark_id: str) -> dict:
        """Build a leaderboard from a completed benchmark run.

        Args:
            benchmark_id: Unique benchmark identifier.

        Returns:
            Dictionary with ``benchmark_id``, ``dataset_name``, ``leaderboard``,
            ``best_engine``, ``total_pages``, and ``total_engines``.

        Raises:
            ValueError: If the benchmark is not completed.
        """
        run = self.store.get(benchmark_id)
        if run is None:
            raise ValueError(f"Benchmark '{benchmark_id}' not found")
        if run.status != BenchmarkStatus.COMPLETED:
            raise ValueError(f"Benchmark '{benchmark_id}' is not completed (status: {run.status.value})")

        leaderboard = sorted(run.engine_scores, key=lambda s: s.average_accuracy, reverse=True)
        best_engine = leaderboard[0].engine if leaderboard else None

        return {
            "benchmark_id": benchmark_id,
            "dataset_name": run.dataset_name,
            "leaderboard": leaderboard,
            "best_engine": best_engine,
            "total_pages": len({p.page_number for p in run.page_results}),
            "total_engines": len(run.engine_scores),
        }


# Global singleton instance
benchmark_service = BenchmarkService()
