"""Tests for OCR provider data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ocr_platform.providers.models import OCRResult


class TestOCRResult:
    """Validation and behaviour tests for :class:`OCRResult`."""

    def test_minimal_valid_result(self) -> None:
        r = OCRResult(text="hello", engine="mock")
        assert r.text == "hello"
        assert r.engine == "mock"
        assert r.confidence is None
        assert r.language is None
        assert r.page_number is None
        assert r.processing_time_ms is None

    def test_full_result(self) -> None:
        r = OCRResult(
            text="hello world",
            engine="mistral",
            confidence=0.95,
            language="en",
            page_number=3,
            processing_time_ms=42.5,
        )
        assert r.confidence == 0.95
        assert r.language == "en"
        assert r.page_number == 3
        assert r.processing_time_ms == 42.5

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            OCRResult(text="hello", engine="mock", confidence=1.5)

    def test_confidence_below_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            OCRResult(text="hello", engine="mock", confidence=-0.1)

    def test_page_number_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            OCRResult(text="hello", engine="mock", page_number=0)

    def test_page_number_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            OCRResult(text="hello", engine="mock", page_number=-1)

    def test_processing_time_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            OCRResult(text="hello", engine="mock", processing_time_ms=-1.0)
