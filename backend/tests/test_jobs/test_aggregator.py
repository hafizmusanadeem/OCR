"""Tests for the DocumentAggregator."""

from __future__ import annotations

import pytest

from ocr_platform.jobs.aggregator import PAGE_BREAK_MARKER, DocumentAggregator
from ocr_platform.jobs.models import DocumentResult, JobPageResult


class TestDocumentAggregator:
    """DocumentAggregator unit tests."""

    def test_single_page(self) -> None:
        pages = [JobPageResult(page_number=1, text="Hello world")]
        result = DocumentAggregator.aggregate("job-1", pages, 100.0)
        assert result.job_id == "job-1"
        assert result.page_count == 1
        assert "Hello world" in result.document_text
        assert result.word_count == 2
        assert result.character_count == 11
        assert result.total_processing_time_ms == 100.0
        assert result.average_processing_time_ms == 100.0

    def test_multi_page_preserves_order(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="First page"),
            JobPageResult(page_number=2, text="Second page"),
            JobPageResult(page_number=3, text="Third page"),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 300.0)
        assert result.page_count == 3
        # Pages should be in order
        assert "[Page 1]\nFirst page" in result.document_text
        assert "[Page 2]\nSecond page" in result.document_text
        assert "[Page 3]\nThird page" in result.document_text
        # Page break markers should be present between pages
        assert PAGE_BREAK_MARKER in result.document_text
        assert result.word_count == 6
        assert result.character_count == 31

    def test_unsorted_pages_get_sorted(self) -> None:
        pages = [
            JobPageResult(page_number=3, text="Third page"),
            JobPageResult(page_number=1, text="First page"),
            JobPageResult(page_number=2, text="Second page"),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 300.0)
        # Text should be in page order, not input order
        parts = result.document_text.split(PAGE_BREAK_MARKER)
        assert parts[0] == "[Page 1]\nFirst page"
        assert parts[1] == "[Page 2]\nSecond page"
        assert parts[2] == "[Page 3]\nThird page"

    def test_average_confidence_computed(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="a", confidence=0.8),
            JobPageResult(page_number=2, text="b", confidence=0.9),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 50.0)
        assert result.average_confidence == 0.85

    def test_confidence_none_ignored(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="a", confidence=0.8),
            JobPageResult(page_number=2, text="b", confidence=None),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 50.0)
        assert result.average_confidence == 0.8

    def test_all_confidence_none_returns_none(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="a", confidence=None),
            JobPageResult(page_number=2, text="b", confidence=None),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 50.0)
        assert result.average_confidence is None

    def test_languages_extracted(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="hello", language="en"),
            JobPageResult(page_number=2, text="world", language="en"),
            JobPageResult(page_number=3, text="bonjour", language="fr"),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 150.0)
        assert result.languages == ["en", "fr"]

    def test_languages_none_ignored(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="hello", language="en"),
            JobPageResult(page_number=2, text="world", language=None),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 100.0)
        assert result.languages == ["en"]

    def test_empty_pages_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot aggregate"):
            DocumentAggregator.aggregate("job-1", [], 0.0)

    def test_average_processing_time(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="a", processing_time_ms=10.0),
            JobPageResult(page_number=2, text="b", processing_time_ms=20.0),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 30.0)
        assert result.average_processing_time_ms == 15.0

    def test_document_text_contains_page_headers(self) -> None:
        pages = [
            JobPageResult(page_number=5, text="page five"),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 10.0)
        assert result.document_text == "[Page 5]\npage five"

    def test_multi_page_no_gaps(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="one"),
            JobPageResult(page_number=2, text="two"),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 20.0)
        parts = result.document_text.split(PAGE_BREAK_MARKER)
        assert len(parts) == 2
        assert parts[0] == "[Page 1]\none"
        assert parts[1] == "[Page 2]\ntwo"

    def test_returns_document_result_type(self) -> None:
        pages = [JobPageResult(page_number=1, text="hello")]
        result = DocumentAggregator.aggregate("job-1", pages, 5.0)
        assert isinstance(result, DocumentResult)

    def test_word_count_with_punctuation(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="Hello, world! How are you?"),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 10.0)
        # split() splits on whitespace, so punctuation stays attached to words
        assert result.word_count == 5

    def test_character_count_includes_all_chars(self) -> None:
        pages = [
            JobPageResult(page_number=1, text="Hi!"),
        ]
        result = DocumentAggregator.aggregate("job-1", pages, 10.0)
        assert result.character_count == 3
