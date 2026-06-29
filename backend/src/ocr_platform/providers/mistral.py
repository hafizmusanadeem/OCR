"""Mistral OCR provider.

Sends PDF or image files to the Mistral OCR API and returns structured
:class:`OCRResult` objects.

Requires a ``MISTRAL_API_KEY`` environment variable or a manually
passed ``api_key``.
"""

from __future__ import annotations

import time

import httpx

from ocr_platform.config import settings
from ocr_platform.logging_config import get_logger
from ocr_platform.providers.base import OCRProvider
from ocr_platform.providers.models import OCRResult
from ocr_platform.providers.registry import register

logger = get_logger(__name__)

DEFAULT_BASE_URL = "https://api.mistral.ai/v1"
DEFAULT_OCR_PATH = "/ocr"


@register("mistral")
class MistralProvider(OCRProvider):
    """OCR provider backed by the Mistral API.

    Attributes:
        _api_key: Mistral API key (Bearer token).
        _base_url: Mistral API base URL (no trailing slash).
        _ocr_path: API path for OCR requests.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        ocr_path: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.mistral_api_key
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._ocr_path = ocr_path or DEFAULT_OCR_PATH

    def name(self) -> str:
        return "mistral"

    def version(self) -> str:
        return "1.0.0"

    def is_available(self) -> bool:
        return self._api_key is not None and len(self._api_key) > 0

    async def recognize(self, image_data: bytes) -> OCRResult:
        """Run OCR by sending bytes to the Mistral API.

        Args:
            image_data: Raw PDF or image bytes.

        Returns:
            Structured OCR result.

        Raises:
            RuntimeError: If the API key is not configured.
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        if not self._api_key:
            raise RuntimeError("Mistral API key is not configured")

        start = time.perf_counter()
        url = f"{self._base_url}{self._ocr_path}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        logger.info(
            "mistral_ocr_request",
            url=url,
            data_size=len(image_data),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                files={"file": ("document", image_data, "application/octet-stream")},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        elapsed = (time.perf_counter() - start) * 1000

        text = self._extract_text(data)
        confidence = self._extract_confidence(data)
        language = data.get("language")

        logger.info(
            "mistral_ocr_response",
            text_length=len(text),
            confidence=confidence,
            elapsed_ms=round(elapsed, 3),
        )

        return OCRResult(
            text=text,
            engine=self.name(),
            confidence=confidence,
            language=language,
            processing_time_ms=round(elapsed, 3),
        )

    def _extract_text(self, data: dict) -> str:
        """Extract text from Mistral API response.

        Tries multiple known response shapes for resilience.

        Args:
            data: Parsed JSON response body.

        Returns:
            Extracted text or empty string if no text field is found.
        """
        # Direct text field
        if "text" in data:
            return str(data["text"])

        # Pages array (common in multi-page PDF responses)
        if "pages" in data:
            return "\n\n".join(str(page.get("text", "")) for page in data["pages"])

        # Nested result object
        if "result" in data and isinstance(data["result"], dict):
            return self._extract_text(data["result"])

        # No recognizable text structure
        return ""

    def _extract_confidence(self, data: dict) -> float | None:
        """Extract confidence from API response.

        Args:
            data: Parsed JSON response body.

        Returns:
            Confidence score or ``None`` if not present.
        """
        raw = data.get("confidence")
        if raw is None and "pages" in data:
            # Average confidence across pages
            scores = [
                page.get("confidence")
                for page in data["pages"]
                if page.get("confidence") is not None
            ]
            if scores:
                raw = sum(scores) / len(scores)
        if isinstance(raw, (int, float)):
            return float(raw)
        return None
