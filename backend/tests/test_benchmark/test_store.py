"""Tests for the benchmark store."""

from __future__ import annotations

import pytest

from ocr_platform.benchmark.models import BenchmarkStatus
from ocr_platform.benchmark.store import BenchmarkStore


class TestBenchmarkStore:
    """Tests for the in-memory benchmark store."""

    def test_create(self) -> None:
        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        assert benchmark_id is not None
        assert len(benchmark_id) == 36  # UUID length

    def test_get_existing(self) -> None:
        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        run = store.get(benchmark_id)
        assert run is not None
        assert run.id == benchmark_id
        assert run.status == BenchmarkStatus.PENDING
        assert run.dataset_name == "english-test"

    def test_get_missing(self) -> None:
        store = BenchmarkStore()
        assert store.get("nonexistent") is None

    def test_update_status(self) -> None:
        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        store.update_status(benchmark_id, BenchmarkStatus.RUNNING)
        run = store.get(benchmark_id)
        assert run.status == BenchmarkStatus.RUNNING

    def test_update_status_missing(self) -> None:
        store = BenchmarkStore()
        with pytest.raises(KeyError):
            store.update_status("nonexistent", BenchmarkStatus.RUNNING)

    def test_add_page_results(self) -> None:
        from ocr_platform.benchmark.models import PageBenchmark

        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        store.update_status(benchmark_id, BenchmarkStatus.RUNNING)

        results = [
            PageBenchmark(
                page_number=1,
                ground_truth="hello",
                hypothesis="hallo",
                cer=0.2,
                wer=0.0,
                accuracy=0.8,
                word_accuracy=1.0,
            ),
        ]
        store.add_page_results(benchmark_id, results)
        run = store.get(benchmark_id)
        assert len(run.page_results) == 1
        assert run.page_results[0].page_number == 1

    def test_set_engine_scores(self) -> None:
        from ocr_platform.benchmark.models import EngineScore

        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        scores = [
            EngineScore(
                engine="mock",
                average_cer=0.1,
                average_wer=0.05,
                average_accuracy=0.9,
                average_word_accuracy=0.95,
                total_pages=10,
                total_characters=100,
                total_words=20,
            ),
        ]
        store.set_engine_scores(benchmark_id, scores)
        run = store.get(benchmark_id)
        assert len(run.engine_scores) == 1
        assert run.engine_scores[0].engine == "mock"

    def test_complete(self) -> None:
        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        store.complete(benchmark_id)
        run = store.get(benchmark_id)
        assert run.status == BenchmarkStatus.COMPLETED

    def test_fail(self) -> None:
        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        store.fail(benchmark_id, "something went wrong")
        run = store.get(benchmark_id)
        assert run.status == BenchmarkStatus.FAILED
        assert run.error == "something went wrong"

    def test_list_runs(self) -> None:
        store = BenchmarkStore()
        id1 = store.create("dataset-a")
        id2 = store.create("dataset-b")
        runs = store.list_runs()
        assert len(runs) == 2
        # Sorted by created_at descending
        assert runs[0].id == id2
        assert runs[1].id == id1

    def test_delete(self) -> None:
        store = BenchmarkStore()
        benchmark_id = store.create("english-test")
        store.delete(benchmark_id)
        assert store.get(benchmark_id) is None
