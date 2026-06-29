"""OCR provider plugin system.

The provider architecture is built around three components:

1. :class:`OCRProvider` — Abstract base class that every engine must implement.
2. :class:`ProviderRegistry` — Maps names to provider classes; enables swapping.
3. :class:`OCRResult` — Standardized data model for OCR output.

Example:
    >>> from ocr_platform.providers import global_registry
    >>> registry = global_registry
    >>> registry.list_providers()
    ['mock']
    >>> provider = registry.create_provider("mock")
    >>> # result = await provider.recognize(b"fake_image")
"""

from __future__ import annotations

from ocr_platform.providers.base import OCRProvider
from ocr_platform.providers.models import OCRResult
from ocr_platform.providers.registry import ProviderRegistry, global_registry, register

__all__ = [
    "OCRProvider",
    "OCRResult",
    "ProviderRegistry",
    "global_registry",
    "register",
]

# Ensure built-in providers are loaded and registered
import ocr_platform.providers.mistral  # noqa: F401, E402
import ocr_platform.providers.mock  # noqa: F401, E402
