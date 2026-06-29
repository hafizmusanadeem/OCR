"""Tests for the Mistral OCR provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ocr_platform.config import Settings
from ocr_platform.providers.mistral import DEFAULT_BASE_URL, MistralProvider
from ocr_platform.providers.models import OCRResult


class TestMistralProvider:
    """Mistral provider unit tests (HTTP mocked)."""

    def test_name(self) -> None:
        provider = MistralProvider(api_key="test-key")
        assert provider.name() == "mistral"

    def test_version(self) -> None:
        provider = MistralProvider(api_key="test-key")
        assert provider.version() == "1.0.0"

    def test_is_available_with_key(self) -> None:
        provider = MistralProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_is_available_without_key(self) -> None:
        provider = MistralProvider(api_key=None)
        assert provider.is_available() is False

    def test_is_available_with_empty_key(self) -> None:
        provider = MistralProvider(api_key="")
        assert provider.is_available() is False

    def test_default_base_url(self) -> None:
        provider = MistralProvider(api_key="test-key")
        assert provider._base_url == DEFAULT_BASE_URL  # noqa: SLF001

    def test_custom_base_url(self) -> None:
        provider = MistralProvider(api_key="test-key", base_url="https://custom.ai/api/")
        assert provider._base_url == "https://custom.ai/api"  # noqa: SLF001

    async def test_recognize_returns_text(self) -> None:
        provider = MistralProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Hello World", "confidence": 0.95}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.recognize(b"fake_pdf_bytes")

        assert isinstance(result, OCRResult)
        assert result.text == "Hello World"
        assert result.engine == "mistral"
        assert result.confidence == 0.95
        assert result.processing_time_ms is not None

    async def test_recognize_extracts_pages(self) -> None:
        provider = MistralProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pages": [
                {"text": "Page one", "confidence": 0.9},
                {"text": "Page two", "confidence": 0.8},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.recognize(b"fake_pdf_bytes")

        assert result.text == "Page one\n\nPage two"
        assert result.confidence == pytest.approx(0.85)  # average of 0.9 and 0.8

    async def test_recognize_extracts_nested_result(self) -> None:
        provider = MistralProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"text": "Nested text"}}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.recognize(b"fake_pdf_bytes")

        assert result.text == "Nested text"

    async def test_recognize_no_api_key_raises(self) -> None:
        provider = MistralProvider(api_key=None)
        with pytest.raises(RuntimeError, match="API key"):
            await provider.recognize(b"fake")

    async def test_recognize_http_error_raises(self) -> None:
        provider = MistralProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status = MagicMock(side_effect=Exception("Unauthorized"))

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.raises(Exception, match="Unauthorized"),
        ):
            await provider.recognize(b"fake_pdf_bytes")

    async def test_recognize_empty_response(self) -> None:
        provider = MistralProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.recognize(b"fake")

        assert result.text == ""
        assert result.confidence is None

    def test_reads_key_from_settings(self) -> None:
        s = Settings(mistral_api_key="from_settings")
        assert s.mistral_api_key == "from_settings"

    async def test_recognize_uses_authorization_header(self) -> None:
        provider = MistralProvider(api_key="secret-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "OK"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await provider.recognize(b"fake")

        call_kwargs = mock_client.post.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer secret-token"
