"""Document preprocessing types.

Models for representing pages extracted from uploaded documents.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    """Supported document formats."""

    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"
    UNKNOWN = "unknown"


class PageImage(BaseModel):
    """A single page rendered as an image.

    Attributes:
        page_number: 1-based page index within the document.
        image_data: Raw image bytes (PNG for PDF pages, original format for images).
        width: Image width in pixels.
        height: Image height in pixels.
        format: Image format string (e.g., ``"png"``, ``"jpeg"``).
    """

    page_number: int = Field(
        ge=1,
        description="1-based page index within the document",
    )
    image_data: bytes = Field(description="Raw image bytes")
    width: int = Field(ge=1, description="Image width in pixels")
    height: int = Field(ge=1, description="Image height in pixels")
    format: str = Field(description="Image format string")

    model_config = ConfigDict(arbitrary_types_allowed=True)
