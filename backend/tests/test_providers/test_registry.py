"""Tests for the ProviderRegistry."""

from __future__ import annotations

import pytest

from ocr_platform.providers.base import OCRProvider
from ocr_platform.providers.models import OCRResult
from ocr_platform.providers.registry import ProviderRegistry, global_registry, register


class _DummyProvider(OCRProvider):
    """Minimal concrete provider for registry tests."""

    def name(self) -> str:
        return "dummy"

    def version(self) -> str:
        return "0.0.1"

    def is_available(self) -> bool:
        return True

    async def recognize(self, image_data: bytes) -> OCRResult:
        return OCRResult(text="dummy", engine=self.name())


class _UnavailableProvider(OCRProvider):
    """Provider that reports itself as unavailable."""

    def name(self) -> str:
        return "unavailable"

    def version(self) -> str:
        return "0.0.1"

    def is_available(self) -> bool:
        return False

    async def recognize(self, image_data: bytes) -> OCRResult:
        return OCRResult(text="unavailable", engine=self.name())


class TestProviderRegistry:
    """Registry lifecycle and discovery tests."""

    def test_register_and_create(self) -> None:
        registry = ProviderRegistry()
        registry.register("dummy", _DummyProvider)
        provider = registry.create_provider("dummy")
        assert provider.name() == "dummy"
        assert isinstance(provider, _DummyProvider)

    def test_duplicate_registration_raises(self) -> None:
        registry = ProviderRegistry()
        registry.register("dummy", _DummyProvider)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("dummy", _DummyProvider)

    def test_unregistered_provider_raises(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.create_provider("unknown")

    def test_list_providers(self) -> None:
        registry = ProviderRegistry()
        registry.register("dummy", _DummyProvider)
        assert registry.list_providers() == ["dummy"]

    def test_list_providers_sorted(self) -> None:
        registry = ProviderRegistry()
        registry.register("beta", _DummyProvider)
        registry.register("alpha", _DummyProvider)
        assert registry.list_providers() == ["alpha", "beta"]

    def test_unregister(self) -> None:
        registry = ProviderRegistry()
        registry.register("dummy", _DummyProvider)
        registry.unregister("dummy")
        assert registry.list_providers() == []

    def test_unregister_unknown_raises(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.unregister("missing")

    def test_list_available_only_ready(self) -> None:
        registry = ProviderRegistry()
        registry.register("dummy", _DummyProvider)
        registry.register("offline", _UnavailableProvider)
        available = registry.list_available()
        assert available == ["dummy"]

    def test_get_provider_class(self) -> None:
        registry = ProviderRegistry()
        registry.register("dummy", _DummyProvider)
        cls = registry.get_provider_class("dummy")
        assert cls is _DummyProvider

    def test_provider_swap_no_code_change(self) -> None:
        """Prove that swapping providers is a registry operation only."""
        registry = ProviderRegistry()
        registry.register("engine_a", _DummyProvider)
        registry.register("engine_b", _UnavailableProvider)

        # Consumer code never hard-codes a class
        provider_a = registry.create_provider("engine_a")
        provider_b = registry.create_provider("engine_b")

        assert provider_a.is_available() is True
        assert provider_b.is_available() is False


class TestGlobalRegistry:
    """Tests for the application-wide :data:`global_registry`."""

    def test_mock_is_auto_registered(self) -> None:
        assert "mock" in global_registry.list_providers()

    def test_mock_is_available(self) -> None:
        available = global_registry.list_available()
        assert "mock" in available


class TestRegisterDecorator:
    """Tests for the :func:`register` decorator."""

    def test_decorator_registers_to_global(self) -> None:
        @register("decorated_test")
        class DecoratedProvider(OCRProvider):
            def name(self) -> str:
                return "decorated_test"

            def version(self) -> str:
                return "0.0.1"

            def is_available(self) -> bool:
                return True

            async def recognize(self, image_data: bytes) -> OCRResult:
                return OCRResult(text="decorated", engine=self.name())

        assert "decorated_test" in global_registry.list_providers()
        # Clean up to avoid polluting other tests
        global_registry.unregister("decorated_test")
