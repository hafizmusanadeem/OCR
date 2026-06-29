"""Integration tests demonstrating provider swapping requires zero backend changes."""

from __future__ import annotations

from ocr_platform.providers.base import OCRProvider
from ocr_platform.providers.models import OCRResult
from ocr_platform.providers.registry import ProviderRegistry


class _FastEngine(OCRProvider):
    """Simulated fast engine."""

    def name(self) -> str:
        return "fast"

    def version(self) -> str:
        return "2.0.0"

    def is_available(self) -> bool:
        return True

    async def recognize(self, image_data: bytes) -> OCRResult:
        return OCRResult(
            text="fast result",
            engine=self.name(),
            confidence=0.95,
            processing_time_ms=5.0,
        )


class _AccurateEngine(OCRProvider):
    """Simulated accurate engine."""

    def name(self) -> str:
        return "accurate"

    def version(self) -> str:
        return "3.0.0"

    def is_available(self) -> bool:
        return True

    async def recognize(self, image_data: bytes) -> OCRResult:
        return OCRResult(
            text="accurate result",
            engine=self.name(),
            confidence=0.99,
            processing_time_ms=50.0,
        )


class TestProviderSwap:
    """End-to-end swap demonstration."""

    async def test_swap_by_registry_name(self) -> None:
        """The backend never imports engine classes directly."""
        registry = ProviderRegistry()
        registry.register("fast", _FastEngine)
        registry.register("accurate", _AccurateEngine)

        # Consumer code only knows the registry and the name string
        async def run_ocr(registry: ProviderRegistry, name: str) -> OCRResult:
            provider = registry.create_provider(name)
            return await provider.recognize(b"dummy")

        fast_result = await run_ocr(registry, "fast")
        accurate_result = await run_ocr(registry, "accurate")

        assert fast_result.engine == "fast"
        assert accurate_result.engine == "accurate"
        assert fast_result.confidence == 0.95
        assert accurate_result.confidence == 0.99
