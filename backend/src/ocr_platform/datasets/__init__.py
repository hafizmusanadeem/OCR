"""Dataset package for OCR benchmark datasets.

Provides built-in benchmark datasets with ground truth for multiple
languages, document types, and quality levels.
"""

from __future__ import annotations

from ocr_platform.datasets.loader import DatasetLoader
from ocr_platform.datasets.models import Dataset, DatasetCategory, DatasetPage
from ocr_platform.datasets.registry import dataset_registry

__all__ = [
    "Dataset",
    "DatasetCategory",
    "DatasetLoader",
    "DatasetPage",
    "dataset_registry",
]
