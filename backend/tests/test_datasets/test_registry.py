"""Tests for the dataset registry."""

from __future__ import annotations

import pytest

from ocr_platform.datasets.models import Dataset, DatasetCategory, DatasetPage
from ocr_platform.datasets.registry import DatasetRegistry


class TestDatasetRegistry:
    """Tests for the dataset registry."""

    @pytest.fixture
    def sample_dataset(self) -> Dataset:
        return Dataset.from_pages(
            dataset_id="test-dataset",
            name="Test Dataset",
            category=DatasetCategory.ENGLISH,
            description="A test dataset.",
            language="en",
            pages=[
                DatasetPage(page_number=1, ground_truth="Hello world"),
            ],
        )

    def test_register_and_get(self, sample_dataset: Dataset) -> None:
        registry = DatasetRegistry()
        registry.register(sample_dataset)
        result = registry.get("test-dataset")
        assert result is not None
        assert result.id == "test-dataset"
        assert result.name == "Test Dataset"

    def test_get_missing(self) -> None:
        registry = DatasetRegistry()
        assert registry.get("missing") is None

    def test_duplicate_registration_raises(self, sample_dataset: Dataset) -> None:
        registry = DatasetRegistry()
        registry.register(sample_dataset)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(sample_dataset)

    def test_list_ids(self, sample_dataset: Dataset) -> None:
        registry = DatasetRegistry()
        registry.register(sample_dataset)
        ids = registry.list_ids()
        assert ids == ["test-dataset"]

    def test_list_all(self, sample_dataset: Dataset) -> None:
        registry = DatasetRegistry()
        registry.register(sample_dataset)
        all_datasets = registry.list_all()
        assert len(all_datasets) == 1
        assert all_datasets[0].id == "test-dataset"

    def test_load_from_directory(self, tmp_path) -> None:
        import json
        from pathlib import Path

        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()
        sample = {
            "name": "Registry Test",
            "category": "english",
            "description": "Testing registry load.",
            "language": "en",
            "pages": [
                {"page_number": 1, "ground_truth": "Registry test"},
            ],
        }
        with (datasets_dir / "registry_test.json").open("w", encoding="utf-8") as f:
            json.dump(sample, f)

        from ocr_platform.datasets.loader import DatasetLoader
        registry = DatasetRegistry()
        loader = DatasetLoader(datasets_dir=datasets_dir)
        registry.load_from_directory(loader)

        assert "registry_test" in registry.list_ids()
        dataset = registry.get("registry_test")
        assert dataset is not None
        assert dataset.name == "Registry Test"

    def test_load_from_directory_skips_duplicates(self, tmp_path) -> None:
        import json
        from pathlib import Path

        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()
        sample = {
            "name": "Dup Test",
            "category": "english",
            "description": "Testing duplicates.",
            "language": "en",
            "pages": [
                {"page_number": 1, "ground_truth": "Dup test"},
            ],
        }
        with (datasets_dir / "dup.json").open("w", encoding="utf-8") as f:
            json.dump(sample, f)

        from ocr_platform.datasets.loader import DatasetLoader
        registry = DatasetRegistry()
        loader = DatasetLoader(datasets_dir=datasets_dir)
        registry.load_from_directory(loader)
        # Second load should skip duplicates without crashing
        registry.load_from_directory(loader)
        assert len(registry.list_ids()) == 1
