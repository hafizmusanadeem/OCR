"""Tests for preprocessing data types."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ocr_platform.preprocessing.types import DocumentType, PageImage


class TestDocumentType:
    """DocumentType enum tests."""

    def test_pdf_value(self) -> None:
        assert DocumentType.PDF == "pdf"

    def test_png_value(self) -> None:
        assert DocumentType.PNG == "png"

    def test_jpeg_value(self) -> None:
        assert DocumentType.JPEG == "jpeg"

    def test_from_string(self) -> None:
        assert DocumentType("pdf") == DocumentType.PDF
        assert DocumentType("png") == DocumentType.PNG


class TestPageImage:
    """PageImage model tests."""

    def test_valid_construction(self) -> None:
        p = PageImage(
            page_number=1,
            image_data=b"fake_image",
            width=100,
            height=200,
            format="png",
        )
        assert p.page_number == 1
        assert p.image_data == b"fake_image"
        assert p.width == 100
        assert p.height == 200
        assert p.format == "png"

    def test_page_number_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            PageImage(
                page_number=0,
                image_data=b"x",
                width=1,
                height=1,
                format="png",
            )

    def test_page_number_negative(self) -> None:
        with pytest.raises(ValidationError):
            PageImage(
                page_number=-1,
                image_data=b"x",
                width=1,
                height=1,
                format="png",
            )

    def test_width_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            PageImage(
                page_number=1,
                image_data=b"x",
                width=0,
                height=1,
                format="png",
            )

    def test_height_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            PageImage(
                page_number=1,
                image_data=b"x",
                width=1,
                height=0,
                format="png",
            )
