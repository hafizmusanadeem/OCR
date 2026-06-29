"""Shared data models for OCR providers.

Standardized Pydantic models used as input/output contracts across all
OCR engine implementations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OCRResult(BaseModel):
    """Structured result from an OCR provider.

    Attributes:
        text: Extracted text content.
        confidence: Confidence score (0.0-1.0), if available.
        language: Detected or requested language code (ISO 639-1).
        page_number: Page number within a multi-page document.
        engine: Name of the OCR engine that produced this result.
        processing_time_ms: Time taken to process the image in milliseconds.
    """

    text: str = Field(description="Extracted text content")
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)",
    )
    language: str | None = Field(
        default=None,
        description="Detected or requested language code (ISO 639-1)",
    )
    page_number: int | None = Field(
        default=None,
        ge=1,
        description="Page number within a multi-page document",
    )
    engine: str = Field(description="Name of the OCR engine that produced this result")
    processing_time_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Processing time in milliseconds",
    )
