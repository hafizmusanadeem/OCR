"""Tests for the abstract OCRProvider interface."""

from __future__ import annotations

import pytest

from ocr_platform.providers.base import OCRProvider
from ocr_platform.providers.models import OCRResult


class TestOCRProvider:
    """Interface contract tests."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            OCRProvider()  # type: ignore[abstract]

    def test_subclass_must_implement_name(self) -> None:
        class BadEngine(OCRProvider):
            def version(self) -> str:
                return "1.0"

            def is_available(self) -> bool:
                return True

            async def recognize(self, image_data: bytes) -> OCRResult:
                return OCRResult(text="", engine="bad")

        with pytest.raises(TypeError, match="abstract"):
            BadEngine()  # type: ignore[abstract]

    def test_subclass_must_implement_version(self) -> None:
        class BadEngine(OCRProvider):
            def name(self) -> str:
                return "bad"

            def is_available(self) -> bool:
                return True

            async def recognize(self, image_data: bytes) -> OCRResult:
                return OCRResult(text="", engine="bad")

        with pytest.raises(TypeError, match="abstract"):
            BadEngine()  # type: ignore[abstract]

    def test_subclass_must_implement_is_available(self) -> None:
        class BadEngine(OCRProvider):
            def name(self) -> str:
                return "bad"

            def version(self) -> str:
                return "1.0"

            async def recognize(self, image_data: bytes) -> OCRResult:
                return OCRResult(text="", engine="bad")

        with pytest.raises(TypeError, match="abstract"):
            BadEngine()  # type: ignore[abstract]

    def test_subclass_must_implement_recognize(self) -> None:
        class BadEngine(OCRProvider):
            def name(self) -> str:
                return "bad"

            def version(self) -> str:
                return "1.0"

            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError, match="abstract"):
            BadEngine()  # type: ignore[abstract]

    def test_complete_subclass_instantiates(self) -> None:
        class GoodEngine(OCRProvider):
            def name(self) -> str:
                return "good"

            def version(self) -> str:
                return "1.0.0"

            def is_available(self) -> bool:
                return True

            async def recognize(self, image_data: bytes) -> OCRResult:
                return OCRResult(text="good", engine=self.name())

        engine = GoodEngine()
        assert engine.name() == "good"
        assert engine.version() == "1.0.0"
        assert engine.is_available() is True
