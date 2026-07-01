"""OCR benchmark metrics calculation.

Provides Character Error Rate (CER), Word Error Rate (WER), and
auxiliary text-similarity metrics using pure-Python edit distance.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class BenchmarkMetrics:
    """Calculator for OCR benchmark metrics.

    All methods are stateless and can be called directly on the class.
    """

    @staticmethod
    def _edit_distance(seq1: list, seq2: list) -> int:
        """Compute the Levenshtein distance between two sequences.

        Uses the classic dynamic-programming algorithm with O(min(n,m))
        space optimisation.

        Args:
            seq1: First sequence (list of characters or words).
            seq2: Second sequence.

        Returns:
            The minimum number of insertions, deletions, and substitutions
            required to transform *seq1* into *seq2*.
        """
        if len(seq1) < len(seq2):
            return BenchmarkMetrics._edit_distance(seq2, seq1)

        if not seq2:
            return len(seq1)

        # Two-row DP to keep memory O(min(n,m))
        previous = list(range(len(seq2) + 1))
        current = [0] * (len(seq2) + 1)

        for i, ch1 in enumerate(seq1):
            current[0] = i + 1
            for j, ch2 in enumerate(seq2):
                # Cost is 0 if characters match, 1 otherwise
                cost = 0 if ch1 == ch2 else 1
                current[j + 1] = min(
                    current[j] + 1,       # insertion
                    previous[j + 1] + 1,  # deletion
                    previous[j] + cost,   # substitution
                )
            previous, current = current, previous

        return previous[len(seq2)]

    @classmethod
    def cer(cls, ground_truth: str, hypothesis: str) -> float:
        """Calculate Character Error Rate (CER).

        CER = (insertions + deletions + substitutions) / len(ground_truth)

        Args:
            ground_truth: The reference text.
            hypothesis: The OCR output text.

        Returns:
            CER as a float between 0.0 and 1.0 (inclusive).
            Returns 0.0 if both strings are empty.
        """
        if not ground_truth and not hypothesis:
            return 0.0

        gt_chars = list(ground_truth)
        hyp_chars = list(hypothesis)
        distance = cls._edit_distance(gt_chars, hyp_chars)
        reference_length = len(gt_chars)

        if reference_length == 0:
            # Ground truth is empty but hypothesis is not → 100% error
            return 1.0

        return round(distance / reference_length, 6)

    @classmethod
    def wer(cls, ground_truth: str, hypothesis: str) -> float:
        """Calculate Word Error Rate (WER).

        WER = (insertions + deletions + substitutions) / word_count(ground_truth)

        Words are split on whitespace after normalising the text.

        Args:
            ground_truth: The reference text.
            hypothesis: The OCR output text.

        Returns:
            WER as a float between 0.0 and 1.0 (inclusive).
            Returns 0.0 if both strings are empty or contain only whitespace.
        """
        gt_words = ground_truth.split()
        hyp_words = hypothesis.split()

        if not gt_words and not hyp_words:
            return 0.0

        distance = cls._edit_distance(gt_words, hyp_words)
        reference_length = len(gt_words)

        if reference_length == 0:
            return 1.0

        return round(distance / reference_length, 6)

    @classmethod
    def accuracy(cls, ground_truth: str, hypothesis: str) -> float:
        """Calculate character-level accuracy (1 - CER).

        Args:
            ground_truth: The reference text.
            hypothesis: The OCR output text.

        Returns:
            Accuracy as a float between 0.0 and 1.0.
        """
        return round(1.0 - cls.cer(ground_truth, hypothesis), 6)

    @classmethod
    def word_accuracy(cls, ground_truth: str, hypothesis: str) -> float:
        """Calculate word-level accuracy (1 - WER).

        Args:
            ground_truth: The reference text.
            hypothesis: The OCR output text.

        Returns:
            Word accuracy as a float between 0.0 and 1.0.
        """
        return round(1.0 - cls.wer(ground_truth, hypothesis), 6)

    @classmethod
    def compute_page_score(
        cls,
        ground_truth: str,
        hypothesis: str,
        confidence: float | None,
        latency_ms: float | None,
    ) -> dict:
        """Compute a full page-level benchmark score.

        Args:
            ground_truth: Reference text for the page.
            hypothesis: OCR output for the page.
            confidence: OCR confidence score (0.0-1.0), if available.
            latency_ms: Processing time in milliseconds, if available.

        Returns:
            Dictionary with ``cer``, ``wer``, ``accuracy``, ``word_accuracy``,
            ``confidence``, and ``latency_ms``.
        """
        return {
            "cer": cls.cer(ground_truth, hypothesis),
            "wer": cls.wer(ground_truth, hypothesis),
            "accuracy": cls.accuracy(ground_truth, hypothesis),
            "word_accuracy": cls.word_accuracy(ground_truth, hypothesis),
            "confidence": confidence,
            "latency_ms": latency_ms,
        }
