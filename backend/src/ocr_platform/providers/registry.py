"""Provider registry for OCR engine discovery and instantiation.

The registry maps string names to :class:`OCRProvider` subclasses.
Swapping engines at runtime is a single configuration change —
no consumer code needs to be modified.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from ocr_platform.logging_config import get_logger
from ocr_platform.providers.base import OCRProvider

logger = get_logger(__name__)

T = TypeVar("T", bound=OCRProvider)


class ProviderRegistry:
    """Registry for OCR provider classes.

    Attributes:
        _providers: Internal mapping of name → provider class.
    """

    def __init__(self) -> None:
        self._providers: dict[str, type[OCRProvider]] = {}

    def register(self, name: str, provider_cls: type[OCRProvider]) -> None:
        """Register a provider class under the given name.

        Args:
            name: Unique identifier for the provider (e.g., ``"mistral"``).
            provider_cls: Concrete subclass of :class:`OCRProvider`.

        Raises:
            ValueError: If *name* is already registered.
        """
        if name in self._providers:
            raise ValueError(f"Provider '{name}' is already registered")
        self._providers[name] = provider_cls
        logger.info(
            "provider_registered",
            name=name,
            class_name=provider_cls.__name__,
        )

    def get_provider_class(self, name: str) -> type[OCRProvider]:
        """Retrieve a provider class by name.

        Args:
            name: Registered provider identifier.

        Returns:
            The provider class.

        Raises:
            KeyError: If *name* is not registered.
        """
        if name not in self._providers:
            available = ", ".join(sorted(self._providers.keys())) or "none"
            raise KeyError(f"Provider '{name}' is not registered. Available: {available}")
        return self._providers[name]

    def create_provider(self, name: str) -> OCRProvider:
        """Instantiate a provider by name.

        Args:
            name: Registered provider identifier.

        Returns:
            A new instance of the provider.

        Raises:
            KeyError: If *name* is not registered.
        """
        cls = self.get_provider_class(name)
        return cls()

    def list_providers(self) -> list[str]:
        """Return all registered provider names.

        Returns:
            Sorted list of registered provider names.
        """
        return sorted(self._providers.keys())

    def list_available(self) -> list[str]:
        """Return providers that are currently ready to use.

        Returns:
            Names of providers where :meth:`OCRProvider.is_available`
            returns ``True``.
        """
        available: list[str] = []
        for name, cls in self._providers.items():
            try:
                instance = cls()
                if instance.is_available():
                    available.append(name)
            except Exception:
                logger.warning(
                    "provider_availability_check_failed",
                    name=name,
                )
        return available

    def unregister(self, name: str) -> None:
        """Remove a provider from the registry.

        Args:
            name: Provider identifier to remove.

        Raises:
            KeyError: If *name* is not registered.
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' is not registered")
        del self._providers[name]
        logger.info("provider_unregistered", name=name)


# Global registry instance used throughout the application
global_registry = ProviderRegistry()


def register(name: str) -> Callable[[type[T]], type[T]]:
    """Decorator to register a provider class with the global registry.

    Args:
        name: Unique identifier for the provider.

    Returns:
        A decorator that registers the class with :data:`global_registry`.

    Example:
        >>> @register("my_engine")
        ... class MyEngine(OCRProvider):
        ...     ...
    """

    def decorator(cls: type[T]) -> type[T]:
        global_registry.register(name, cls)
        return cls

    return decorator
