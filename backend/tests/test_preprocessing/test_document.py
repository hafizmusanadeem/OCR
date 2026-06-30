"""Tests for the DocumentPreprocessor."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from ocr_platform.preprocessing.document import (
    DEFAULT_DPI,
    DocumentPreprocessor,
)
from ocr_platform.preprocessing.types import DocumentType


class TestDocumentPreprocessor:
    """DocumentPreprocessor unit tests."""

    def test_default_dpi(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor.dpi == DEFAULT_DPI

    def test_custom_dpi(self) -> None:
        preprocessor = DocumentPreprocessor(dpi=300)
        assert preprocessor.dpi == 300

    def test_detect_type_pdf(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor._detect_type("application/pdf") == DocumentType.PDF

    def test_detect_type_png(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor._detect_type("image/png") == DocumentType.PNG

    def test_detect_type_jpeg(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor._detect_type("image/jpeg") == DocumentType.JPEG

    def test_detect_type_jpg(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor._detect_type("image/jpg") == DocumentType.JPEG

    def test_detect_type_tiff(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor._detect_type("image/tiff") == DocumentType.TIFF

    def test_detect_type_unknown(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor._detect_type("text/plain") == DocumentType.UNKNOWN

    def test_detect_type_case_insensitive(self) -> None:
        preprocessor = DocumentPreprocessor()
        assert preprocessor._detect_type("APPLICATION/PDF") == DocumentType.PDF

    def test_preprocess_unsupported_type(self) -> None:
        preprocessor = DocumentPreprocessor()
        with pytest.raises(ValueError, match="Unsupported"):
            preprocessor.preprocess(b"x", "text/plain")

    def test_process_image_with_pillow(self) -> None:
        """Test image pass-through with a real Pillow-generated image."""
        buf = BytesIO()
        img = Image.new("RGB", (50, 30), color="red")
        img.save(buf, format="PNG")
        content = buf.getvalue()

        preprocessor = DocumentPreprocessor()
        pages = preprocessor._process_image(content, DocumentType.PNG)

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].width == 50
        assert pages[0].height == 30
        assert pages[0].format == "png"
        assert pages[0].image_data == content

    def test_process_image_corrupt(self) -> None:
        preprocessor = DocumentPreprocessor()
        with pytest.raises(ValueError, match="Invalid or corrupt"):
            preprocessor._process_image(b"not_an_image", DocumentType.PNG)

    def test_process_pdf_with_mock_fitz(self) -> None:
        """Test PDF rendering with mocked fitz."""
        mock_pix = MagicMock()
        mock_pix.width = 100
        mock_pix.height = 200
        mock_pix.tobytes.return_value = b"rendered_png"

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch("ocr_platform.preprocessing.document.fitz", mock_fitz):
            preprocessor = DocumentPreprocessor(dpi=150)
            pages = preprocessor._process_pdf(b"fake_pdf")

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].image_data == b"rendered_png"
        assert pages[0].width == 100
        assert pages[0].height == 200
        assert pages[0].format == "png"
        mock_page.get_pixmap.assert_called_once_with(dpi=150)

    def test_process_pdf_multi_page(self) -> None:
        """Test PDF rendering with multiple pages."""
        mock_pix1 = MagicMock()
        mock_pix1.width = 100
        mock_pix1.height = 200
        mock_pix1.tobytes.return_value = b"page1"

        mock_pix2 = MagicMock()
        mock_pix2.width = 100
        mock_pix2.height = 200
        mock_pix2.tobytes.return_value = b"page2"

        mock_page1 = MagicMock()
        mock_page1.get_pixmap.return_value = mock_pix1
        mock_page2 = MagicMock()
        mock_page2.get_pixmap.return_value = mock_pix2

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch("ocr_platform.preprocessing.document.fitz", mock_fitz):
            preprocessor = DocumentPreprocessor()
            pages = preprocessor._process_pdf(b"fake_pdf")

        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert pages[0].image_data == b"page1"
        assert pages[1].image_data == b"page2"

    def test_process_pdf_missing_fitz(self) -> None:
        """Test graceful error when PyMuPDF is not installed."""
        with patch(
            "ocr_platform.preprocessing.document._FITZ_AVAILABLE",
            False,
        ):
            preprocessor = DocumentPreprocessor()
            with pytest.raises(RuntimeError, match="PyMuPDF"):
                preprocessor._process_pdf(b"fake_pdf")

    def test_preprocess_pdf_integration(self) -> None:
        """Test preprocess dispatch for PDF."""
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.image_data = b"png"
        mock_page.width = 10
        mock_page.height = 10
        mock_page.format = "png"

        preprocessor = DocumentPreprocessor()
        with patch.object(preprocessor, "_process_pdf", return_value=[mock_page]) as mock_pdf:
            result = preprocessor.preprocess(b"x", "application/pdf")
            mock_pdf.assert_called_once_with(b"x")
            assert result == [mock_page]

    def test_preprocess_image_integration(self) -> None:
        """Test preprocess dispatch for image."""
        buf = BytesIO()
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(buf, format="PNG")
        content = buf.getvalue()

        preprocessor = DocumentPreprocessor()
        pages = preprocessor.preprocess(content, "image/png")

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].format == "png"
