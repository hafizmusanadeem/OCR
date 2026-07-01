"""Tests for the benchmark service."""

from __future__ import annotations

import pytest

from ocr_platform.benchmark.models import BenchmarkStatus
from ocr_platform.benchmark.service import BenchmarkService
from ocr_platform.benchmark.store import BenchmarkStore


class TestBenchmarkService:
    """Tests for the benchmark service orchestration."""

    def test_run_benchmark(self) -> None:
        store = BenchmarkStore()
        service = BenchmarkService(store)
        benchmark_id = store.create("english-test")

        pages = [
            {
                "page_number": 1,
                "ground_truth": "hello world",
                "hypotheses": {
                    "mock": {"text": "hallo world", "confidence": 0.9, "latency_ms": 10.0},
                    "mistral": {"text": "hello world", "confidence": 0.99, "latency_ms": 20.0},
                },
            },
            {
                "page_number": 2,
                "ground_truth": "the quick brown fox",
                "hypotheses": {
                    "mock": {"text": "the quick brown fox", "confidence": 0.95, "latency_ms": 12.0},
                    "mistral": {"text": "the slow brown fox", "confidence": 0.92, "latency_ms": 22.0},
                },
            },
        ]

        service.run_benchmark(
            benchmark_id=benchmark_id,
            dataset_name="english-test",
            pages=pages,
            engines=["mock", "mistral"],
        )

        run = store.get(benchmark_id)
        assert run.status == BenchmarkStatus.COMPLETED
        assert len(run.page_results) == 4  # 2 pages × 2 engines
        assert len(run.engine_scores) == 2

        # Verify engine scores exist
        mock_score = next(s for s in run.engine_scores if s.engine == "mock")
        mistral_score = next(s for s in run.engine_scores if s.engine == "mistral")

        assert mock_score.total_pages == 2
        assert mistral_score.total_pages == 2

        # Mock has better average accuracy (1 char error on page 1, perfect on page 2)
        # Mistral has perfect on page 1, but 5 char errors on page 2 (quick->slow)
        assert mock_score.average_accuracy > mistral_score.average_accuracy

        # Mistral has better word accuracy (0 word errors on page 1, 1 word error on page 2)
        # Mock has 1 word error on page 1 (hallo != hello), 0 on page 2
        assert mistral_score.average_word_accuracy > mock_score.average_word_accuracy

        # Leaderboard should rank mock higher by accuracy (default sort key)
        assert run.engine_scores[0].engine == "mock"

    def test_build_leaderboard(self) -> None:
        store = BenchmarkStore()
        service = BenchmarkService(store)
        benchmark_id = store.create("english-test")

        pages = [
            {
                "page_number": 1,
                "ground_truth": "hello",
                "hypotheses": {
                    "engine_a": {"text": "hello", "confidence": 0.99, "latency_ms": 10.0},
                    "engine_b": {"text": "hallo", "confidence": 0.9, "latency_ms": 15.0},
                },
            },
        ]

        service.run_benchmark(
            benchmark_id=benchmark_id,
            dataset_name="english-test",
            pages=pages,
            engines=["engine_a", "engine_b"],
        )

        leaderboard = service.build_leaderboard(benchmark_id)
        assert leaderboard["best_engine"] == "engine_a"
        assert leaderboard["total_pages"] == 1
        assert leaderboard["total_engines"] == 2
        assert leaderboard["dataset_name"] == "english-test"

    def test_build_leaderboard_not_completed(self) -> None:
        store = BenchmarkStore()
        service = BenchmarkService(store)
        benchmark_id = store.create("english-test")
        store.update_status(benchmark_id, BenchmarkStatus.RUNNING)

        with pytest.raises(ValueError, match="not completed"):
            service.build_leaderboard(benchmark_id)

    def test_build_leaderboard_not_found(self) -> None:
        store = BenchmarkStore()
        service = BenchmarkService(store)

        with pytest.raises(ValueError, match="not found"):
            service.build_leaderboard("nonexistent")

    def test_run_benchmark_no_hypotheses(self) -> None:
        """Test that missing hypotheses produce empty strings."""
        store = BenchmarkStore()
        service = BenchmarkService(store)
        benchmark_id = store.create("english-test")

        pages = [
            {
                "page_number": 1,
                "ground_truth": "hello",
                "hypotheses": {},
            },
        ]

        service.run_benchmark(
            benchmark_id=benchmark_id,
            dataset_name="english-test",
            pages=pages,
            engines=["missing_engine"],
        )

        run = store.get(benchmark_id)
        assert run.status == BenchmarkStatus.COMPLETED
        assert len(run.page_results) == 1
        assert run.page_results[0].hypothesis == ""
        assert run.page_results[0].cer == 1.0  # All characters are insertions
        assert run.page_results[0].wer == 1.0  # All words are insertions
