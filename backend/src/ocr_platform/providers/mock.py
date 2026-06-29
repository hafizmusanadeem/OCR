"""Mock OCR provider for testing and demonstration.

Returns deterministic, predictable results without any external
dependencies. Used to validate the plugin architecture before
integrating real OCR engines.
"""

from __future__ import annotations

from ocr_platform.providers.base import OCRProvider
from ocr_platform.providers.models import OCRResult
from ocr_platform.providers.registry import register


@register("mock")
class MockProvider(OCRProvider):
    """A mock OCR provider that returns synthetic results."""

    def name(self) -> str:
        return "mock"

    def version(self) -> str:
        return "1.0.0"

    def is_available(self) -> bool:
        return True

    async def recognize(self, image_data: bytes) -> OCRResult:
        text = f"Mock OCR result for {len(image_data)} bytes"
        return OCRResult(
            text=text,
            confidence=0.99,
            language="en",
            engine=self.name(),
            processing_time_ms=1.0,
        )
