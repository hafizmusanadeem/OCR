"""Tests for the benchmark metrics calculator."""

from __future__ import annotations

import pytest

from ocr_platform.benchmark.metrics import BenchmarkMetrics


class TestEditDistance:
    """Tests for the Levenshtein distance implementation."""

    def test_empty_sequences(self) -> None:
        assert BenchmarkMetrics._edit_distance([], []) == 0
        assert BenchmarkMetrics._edit_distance(["a"], []) == 1
        assert BenchmarkMetrics._edit_distance([], ["b"]) == 1

    def test_identical_sequences(self) -> None:
        assert BenchmarkMetrics._edit_distance(list("hello"), list("hello")) == 0

    def test_one_substitution(self) -> None:
        assert BenchmarkMetrics._edit_distance(list("hello"), list("hallo")) == 1

    def test_one_insertion(self) -> None:
        assert BenchmarkMetrics._edit_distance(list("hello"), list("helllo")) == 1

    def test_one_deletion(self) -> None:
        assert BenchmarkMetrics._edit_distance(list("hello"), list("helo")) == 1

    def test_words(self) -> None:
        assert BenchmarkMetrics._edit_distance(
            ["the", "quick", "brown"],
            ["the", "quick", "brown"],
        ) == 0
        assert BenchmarkMetrics._edit_distance(
            ["the", "quick", "brown"],
            ["the", "slow", "brown"],
        ) == 1


class TestCER:
    """Tests for Character Error Rate."""

    def test_perfect_match(self) -> None:
        assert BenchmarkMetrics.cer("hello", "hello") == 0.0

    def test_empty_both(self) -> None:
        assert BenchmarkMetrics.cer("", "") == 0.0

    def test_empty_hypothesis(self) -> None:
        assert BenchmarkMetrics.cer("hello", "") == 1.0

    def test_empty_ground_truth(self) -> None:
        assert BenchmarkMetrics.cer("", "hello") == 1.0

    def test_one_character_error(self) -> None:
        # 1 substitution out of 5 characters
        assert BenchmarkMetrics.cer("hello", "hallo") == pytest.approx(0.2)

    def test_insertion(self) -> None:
        # 1 insertion out of 5 characters
        assert BenchmarkMetrics.cer("hello", "helllo") == pytest.approx(0.2)

    def test_deletion(self) -> None:
        # 1 deletion out of 5 characters
        assert BenchmarkMetrics.cer("hello", "helo") == pytest.approx(0.2)


class TestWER:
    """Tests for Word Error Rate."""

    def test_perfect_match(self) -> None:
        assert BenchmarkMetrics.wer("the quick brown fox", "the quick brown fox") == 0.0

    def test_empty_both(self) -> None:
        assert BenchmarkMetrics.wer("", "") == 0.0

    def test_empty_hypothesis(self) -> None:
        assert BenchmarkMetrics.wer("the quick brown", "") == 1.0

    def test_one_word_error(self) -> None:
        # 1 substitution out of 4 words
        assert BenchmarkMetrics.wer(
            "the quick brown fox",
            "the slow brown fox",
        ) == pytest.approx(0.25)

    def test_whitespace_handling(self) -> None:
        # Extra whitespace should not affect WER
        assert BenchmarkMetrics.wer(
            "the quick brown fox",
            "the  quick  brown  fox",
        ) == 0.0


class TestAccuracy:
    """Tests for accuracy metrics."""

    def test_character_accuracy(self) -> None:
        assert BenchmarkMetrics.accuracy("hello", "hello") == 1.0
        assert BenchmarkMetrics.accuracy("hello", "hallo") == pytest.approx(0.8)

    def test_word_accuracy(self) -> None:
        assert BenchmarkMetrics.word_accuracy("the quick brown fox", "the quick brown fox") == 1.0
        assert BenchmarkMetrics.word_accuracy(
            "the quick brown fox",
            "the slow brown fox",
        ) == pytest.approx(0.75)


class TestComputePageScore:
    """Tests for the full page score computation."""

    def test_complete_score(self) -> None:
        score = BenchmarkMetrics.compute_page_score(
            ground_truth="the quick brown fox",
            hypothesis="the slow brown fox",
            confidence=0.95,
            latency_ms=123.4,
        )
        # "the quick brown fox" (19 chars) vs "the slow brown fox" (18 chars)
        # difference is "quick" -> "slow": 5 substitutions
        assert score["cer"] == pytest.approx(5 / 19, abs=1e-6)
        assert score["wer"] == pytest.approx(0.25)
        assert score["accuracy"] == pytest.approx(1 - 5 / 19, abs=1e-6)
        assert score["word_accuracy"] == pytest.approx(0.75)
        assert score["confidence"] == 0.95
        assert score["latency_ms"] == 123.4

    def test_no_confidence_or_latency(self) -> None:
        score = BenchmarkMetrics.compute_page_score(
            ground_truth="hello",
            hypothesis="hello",
            confidence=None,
            latency_ms=None,
        )
        assert score["cer"] == 0.0
        assert score["wer"] == 0.0
        assert score["confidence"] is None
        assert score["latency_ms"] is None

    def test_rtl_text(self) -> None:
        """CER/WER should work correctly with RTL scripts."""
        ground_truth = "مرحبا بالعالم"
        hypothesis = "مرحبا بالعالم"
        score = BenchmarkMetrics.compute_page_score(
            ground_truth=ground_truth,
            hypothesis=hypothesis,
            confidence=None,
            latency_ms=None,
        )
        assert score["cer"] == 0.0
        assert score["wer"] == 0.0
