"""Abstract OCR provider interface.

All OCR engines must subclass :class:`OCRProvider` and implement
its abstract methods. This ensures the platform can swap engines
without changing any consumer code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ocr_platform.providers.models import OCRResult


class OCRProvider(ABC):
    """Abstract base class for OCR engine implementations.

    Implementations must override all abstract methods. The
    :class:`~ocr_platform.providers.registry.ProviderRegistry`
    is used to discover and instantiate concrete providers at runtime.

    Example:
        >>> class MyEngine(OCRProvider):
        ...     def name(self) -> str:
        ...         return "my_engine"
        ...     def version(self) -> str:
        ...         return "1.0.0"
        ...     def is_available(self) -> bool:
        ...         return True
        ...     async def recognize(self, image_data: bytes) -> OCRResult:
        ...         return OCRResult(text="hello", engine=self.name())
    """

    @abstractmethod
    def name(self) -> str:
        """Return the provider's human-readable name.

        Returns:
            A short, unique identifier (e.g., ``"mistral"``, ``"tesseract"``).
        """

    @abstractmethod
    def version(self) -> str:
        """Return the provider's version string.

        Returns:
            Semantic version or vendor-specific version string.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider is ready to use.

        Returns:
            ``True`` if the provider can accept requests (e.g., API key is
            configured, binary is installed, etc.).
        """

    @abstractmethod
    async def recognize(self, image_data: bytes) -> OCRResult:
        """Run OCR on image data.

        Args:
            image_data: Raw image bytes (PNG, JPEG, TIFF, etc.).

        Returns:
            A structured :class:`OCRResult` containing the extracted text
            and metadata.
        """
