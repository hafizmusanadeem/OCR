"""Tests for the Mock OCR provider."""

from __future__ import annotations

import pytest

from ocr_platform.providers.mock import MockProvider
from ocr_platform.providers.models import OCRResult


class TestMockProvider:
    """Mock provider implementation tests."""

    @pytest.fixture
    def provider(self) -> MockProvider:
        return MockProvider()

    def test_name(self, provider: MockProvider) -> None:
        assert provider.name() == "mock"

    def test_version(self, provider: MockProvider) -> None:
        assert provider.version() == "1.0.0"

    def test_is_available(self, provider: MockProvider) -> None:
        assert provider.is_available() is True

    async def test_recognize_returns_result(self, provider: MockProvider) -> None:
        result = await provider.recognize(b"fake_image_data")
        assert isinstance(result, OCRResult)
        assert result.text == "Mock OCR result for 15 bytes"
        assert result.engine == "mock"
        assert result.confidence == 0.99
        assert result.language == "en"
        assert result.processing_time_ms == 1.0

    async def test_recognize_text_length_matches_input(self, provider: MockProvider) -> None:
        result = await provider.recognize(b"")
        assert result.text == "Mock OCR result for 0 bytes"

    async def test_recognize_engine_is_self_name(self, provider: MockProvider) -> None:
        result = await provider.recognize(b"x")
        assert result.engine == provider.name()
