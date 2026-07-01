"""Tests for the dataset loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ocr_platform.datasets.loader import DatasetLoader
from ocr_platform.datasets.models import DatasetCategory


class TestDatasetLoader:
    """Tests for loading datasets from JSON files."""

    @pytest.fixture
    def temp_datasets_dir(self, tmp_path: Path):
        """Create a temporary datasets directory with a sample dataset."""
        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()
        sample = {
            "name": "Test Dataset",
            "category": "english",
            "description": "A test dataset.",
            "language": "en",
            "pages": [
                {
                    "page_number": 1,
                    "ground_truth": "Hello world",
                    "tags": ["simple"],
                },
                {
                    "page_number": 2,
                    "ground_truth": "The quick brown fox",
                    "tags": ["pangram"],
                },
            ],
        }
        with (datasets_dir / "test.json").open("w", encoding="utf-8") as f:
            json.dump(sample, f)

        # Another dataset
        sample2 = {
            "name": "RTL Test",
            "category": "arabic",
            "description": "RTL test.",
            "language": "ar",
            "pages": [
                {
                    "page_number": 1,
                    "ground_truth": "مرحبا بالعالم",
                },
            ],
        }
        with (datasets_dir / "arabic_test.json").open("w", encoding="utf-8") as f:
            json.dump(sample2, f)

        return datasets_dir

    def test_load_dataset(self, temp_datasets_dir: Path) -> None:
        loader = DatasetLoader(datasets_dir=temp_datasets_dir)
        dataset = loader.load("test")
        assert dataset.id == "test"
        assert dataset.name == "Test Dataset"
        assert dataset.category == DatasetCategory.ENGLISH
        assert dataset.language == "en"
        assert len(dataset.pages) == 2
        assert dataset.pages[0].page_number == 1
        assert dataset.pages[0].ground_truth == "Hello world"
        assert dataset.pages[1].ground_truth == "The quick brown fox"

    def test_load_missing_dataset(self, temp_datasets_dir: Path) -> None:
        loader = DatasetLoader(datasets_dir=temp_datasets_dir)
        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent")

    def test_load_rtl_dataset(self, temp_datasets_dir: Path) -> None:
        loader = DatasetLoader(datasets_dir=temp_datasets_dir)
        dataset = loader.load("arabic_test")
        assert dataset.category == DatasetCategory.ARABIC
        assert dataset.language == "ar"
        assert dataset.pages[0].ground_truth == "مرحبا بالعالم"

    def test_list_available(self, temp_datasets_dir: Path) -> None:
        loader = DatasetLoader(datasets_dir=temp_datasets_dir)
        available = loader.list_available()
        assert available == ["arabic_test", "test"]

    def test_load_all(self, temp_datasets_dir: Path) -> None:
        loader = DatasetLoader(datasets_dir=temp_datasets_dir)
        datasets = loader.load_all()
        assert len(datasets) == 2
        ids = {d.id for d in datasets}
        assert ids == {"arabic_test", "test"}

    def test_computed_totals(self, temp_datasets_dir: Path) -> None:
        loader = DatasetLoader(datasets_dir=temp_datasets_dir)
        dataset = loader.load("test")
        # "Hello world" = 11 chars, 2 words
        # "The quick brown fox" = 19 chars, 4 words
        assert dataset.total_characters == 11 + 19
        assert dataset.total_words == 2 + 4

    def test_empty_datasets_dir(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        loader = DatasetLoader(datasets_dir=empty_dir)
        assert loader.list_available() == []
        assert loader.load_all() == []


class TestDatasetLoaderBuiltIn:
    """Tests for the built-in datasets shipped with the platform."""

    def test_all_builtin_datasets_load(self) -> None:
        loader = DatasetLoader()
        available = loader.list_available()
        assert len(available) >= 8
        expected = {"english", "urdu", "arabic", "hebrew", "mixed", "rotated", "low_quality", "tables"}
        assert expected.issubset(set(available))

    def test_english_dataset_has_ground_truth(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("english")
        assert dataset.category == DatasetCategory.ENGLISH
        assert len(dataset.pages) > 0
        for page in dataset.pages:
            assert page.ground_truth is not None
            assert len(page.ground_truth) > 0

    def test_urdu_dataset_rtl(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("urdu")
        assert dataset.category == DatasetCategory.URDU
        assert dataset.language == "ur"
        for page in dataset.pages:
            assert page.ground_truth is not None

    def test_arabic_dataset_rtl(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("arabic")
        assert dataset.category == DatasetCategory.ARABIC
        assert dataset.language == "ar"
        for page in dataset.pages:
            assert page.ground_truth is not None

    def test_hebrew_dataset_rtl(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("hebrew")
        assert dataset.category == DatasetCategory.HEBREW
        assert dataset.language == "he"
        for page in dataset.pages:
            assert page.ground_truth is not None

    def test_mixed_dataset_has_multiple_scripts(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("mixed")
        assert dataset.category == DatasetCategory.MIXED
        assert len(dataset.pages) > 0

    def test_rotated_dataset(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("rotated")
        assert dataset.category == DatasetCategory.ROTATED
        assert len(dataset.pages) > 0

    def test_low_quality_dataset(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("low_quality")
        assert dataset.category == DatasetCategory.LOW_QUALITY
        assert len(dataset.pages) > 0

    def test_tables_dataset(self) -> None:
        loader = DatasetLoader()
        dataset = loader.load("tables")
        assert dataset.category == DatasetCategory.TABLES
        assert len(dataset.pages) > 0

    def test_ground_truth_exists_for_all_pages(self) -> None:
        """Every built-in dataset page must have non-empty ground truth."""
        loader = DatasetLoader()
        for dataset_id in loader.list_available():
            dataset = loader.load(dataset_id)
            assert len(dataset.pages) > 0, f"Dataset '{dataset_id}' has no pages"
            for page in dataset.pages:
                assert page.ground_truth is not None, f"Page {page.page_number} in '{dataset_id}' has no ground truth"
                assert len(page.ground_truth) > 0, f"Page {page.page_number} in '{dataset_id}' has empty ground truth"
