"""Tests for the OCR upload endpoint (multi-page)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ocr_platform.main import create_app

client = TestClient(create_app())


class TestOcrUpload:
    """OCR upload endpoint tests."""

    def test_upload_pdf_with_mock_provider(self) -> None:
        # Mock the preprocessor to return a single page (as if PDF rendered)
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake pdf content"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "png"

        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
                data={"provider": "mock"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["page_count"] == 1
        assert data["document_type"] == "pdf"
        assert data["engine"] == "mock"
        assert data["filename"] == "test.pdf"
        assert data["file_size"] == 16
        assert len(data["pages"]) == 1
        assert data["pages"][0]["page_number"] == 1
        assert data["pages"][0]["text"] == "Mock OCR result for 16 bytes"

    def test_upload_multi_page_pdf(self) -> None:
        # Simulate a 3-page PDF
        pages = []
        for i in range(1, 4):
            p = MagicMock()
            p.page_number = i
            p.image_data = f"page {i}".encode()
            p.width = 100
            p.height = 200
            p.format = "png"
            pages.append(p)

        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            return_value=pages,
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
                data={"provider": "mock"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["page_count"] == 3
        assert len(data["pages"]) == 3
        assert data["pages"][0]["page_number"] == 1
        assert data["pages"][1]["page_number"] == 2
        assert data["pages"][2]["page_number"] == 3

    def test_upload_png_with_mock_provider(self) -> None:
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake image"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "png"

        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.png", b"fake image", "image/png")},
                data={"provider": "mock"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["page_count"] == 1
        assert data["document_type"] == "png"
        assert data["engine"] == "mock"
        assert len(data["pages"]) == 1

    def test_upload_jpeg_with_mock_provider(self) -> None:
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"fake image"
        mock_page.width = 100
        mock_page.height = 200
        mock_page.format = "jpeg"

        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.jpg", b"fake image", "image/jpeg")},
                data={"provider": "mock"},
            )
        assert response.status_code == 200

    def test_upload_without_provider_uses_default(self) -> None:
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"x"
        mock_page.width = 10
        mock_page.height = 10
        mock_page.format = "png"

        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.pdf", b"x", "application/pdf")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["engine"] == "mock"  # default is mock

    def test_upload_invalid_file_type(self) -> None:
        response = client.post(
            "/api/v1/ocr",
            files={"file": ("test.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.text

    def test_upload_unknown_provider(self) -> None:
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"x"
        mock_page.width = 10
        mock_page.height = 10
        mock_page.format = "png"

        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.pdf", b"x", "application/pdf")},
                data={"provider": "nonexistent"},
            )
        assert response.status_code == 404
        assert "not found" in response.text.lower()

    def test_upload_file_size_limit(self) -> None:
        large_content = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/v1/ocr",
            files={"file": ("large.pdf", large_content, "application/pdf")},
        )
        assert response.status_code == 413
        assert "too large" in response.text.lower()

    def test_upload_no_file(self) -> None:
        response = client.post("/api/v1/ocr")
        assert response.status_code == 422

    def test_upload_mistral_provider_not_available(self) -> None:
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"x"
        mock_page.width = 10
        mock_page.height = 10
        mock_page.format = "png"

        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            return_value=[mock_page],
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.pdf", b"x", "application/pdf")},
                data={"provider": "mistral"},
            )
        assert response.status_code == 503
        assert "not available" in response.text.lower()

    def test_upload_preprocessing_failure(self) -> None:
        with patch(
            "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
            side_effect=RuntimeError("PyMuPDF not installed"),
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.pdf", b"x", "application/pdf")},
            )
        assert response.status_code == 502
        assert "preprocessing failed" in response.text.lower()

    def test_upload_page_ocr_failure(self) -> None:
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"x"
        mock_page.width = 10
        mock_page.height = 10
        mock_page.format = "png"

        with (
            patch(
                "ocr_platform.api.ocr.DocumentPreprocessor.preprocess",
                return_value=[mock_page],
            ),
            patch(
                "ocr_platform.providers.mock.MockProvider.recognize",
                side_effect=RuntimeError("Simulated OCR failure"),
            ),
        ):
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.pdf", b"x", "application/pdf")},
            )
        assert response.status_code == 502
        assert "page 1" in response.text.lower()
