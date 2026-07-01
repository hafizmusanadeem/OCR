"""Dataset models for benchmark datasets.

Defines Pydantic models for dataset metadata, pages, and categories.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DatasetCategory(StrEnum):
    """Built-in benchmark dataset categories."""

    ENGLISH = "english"
    URDU = "urdu"
    ARABIC = "arabic"
    HEBREW = "hebrew"
    MIXED = "mixed"
    ROTATED = "rotated"
    LOW_QUALITY = "low_quality"
    TABLES = "tables"


class DatasetPage(BaseModel):
    """A single page within a benchmark dataset.

    Attributes:
        page_number: 1-based page index.
        ground_truth: Reference text for this page.
        image_path: Optional path to the image/PDF file.
        tags: Optional tags for filtering (e.g., "rotated", "noisy").
    """

    page_number: int = Field(ge=1, description="1-based page index")
    ground_truth: str = Field(description="Reference text for this page")
    image_path: str | None = Field(default=None, description="Path to image or PDF file")
    tags: list[str] = Field(default_factory=list, description="Filter tags")


class Dataset(BaseModel):
    """A benchmark dataset with ground truth for every page.

    Attributes:
        id: Unique dataset identifier.
        name: Human-readable dataset name.
        category: Dataset category.
        description: Human-readable description.
        language: Primary language code (ISO 639-1).
        pages: List of dataset pages with ground truth.
        total_characters: Total character count across all pages.
        total_words: Total word count across all pages.
    """

    id: str = Field(description="Unique dataset identifier")
    name: str = Field(description="Human-readable dataset name")
    category: DatasetCategory = Field(description="Dataset category")
    description: str = Field(description="Human-readable description")
    language: str = Field(description="Primary language code (ISO 639-1)")
    pages: list[DatasetPage] = Field(description="Dataset pages with ground truth")
    total_characters: int = Field(ge=0, description="Total character count")
    total_words: int = Field(ge=0, description="Total word count")

    @classmethod
    def from_pages(
        cls,
        dataset_id: str,
        name: str,
        category: DatasetCategory,
        description: str,
        language: str,
        pages: list[DatasetPage],
    ) -> "Dataset":
        """Build a Dataset from pages, computing totals automatically.

        Args:
            dataset_id: Unique dataset identifier.
            name: Human-readable dataset name.
            category: Dataset category.
            description: Human-readable description.
            language: Primary language code.
            pages: List of dataset pages.

        Returns:
            A Dataset with computed totals.
        """
        total_chars = sum(len(p.ground_truth) for p in pages)
        total_words = sum(len(p.ground_truth.split()) for p in pages)
        return cls(
            id=dataset_id,
            name=name,
            category=category,
            description=description,
            language=language,
            pages=pages,
            total_characters=total_chars,
            total_words=total_words,
        )
