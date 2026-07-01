"""Dataset loader for benchmark datasets.

Loads dataset definitions from JSON files and provides a registry
for built-in datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ocr_platform.datasets.models import Dataset, DatasetCategory, DatasetPage
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_DATASETS_DIR = Path(__file__).resolve().parents[3] / "datasets"


class DatasetLoader:
    """Loads benchmark datasets from JSON files.

    Attributes:
        datasets_dir: Directory containing dataset JSON files.
    """

    def __init__(self, datasets_dir: Path | None = None) -> None:
        self.datasets_dir = datasets_dir or DEFAULT_DATASETS_DIR

    def _load_json(self, path: Path) -> dict[str, Any]:
        """Load and parse a JSON dataset file.

        Args:
            path: Path to the JSON file.

        Returns:
            Parsed JSON dict.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def load(self, dataset_id: str) -> Dataset:
        """Load a dataset by its ID.

        Args:
            dataset_id: Unique dataset identifier (matches JSON filename).

        Returns:
            Parsed Dataset model.

        Raises:
            FileNotFoundError: If no JSON file exists for the dataset.
        """
        path = self.datasets_dir / f"{dataset_id}.json"
        data = self._load_json(path)
        pages = [
            DatasetPage(
                page_number=p["page_number"],
                ground_truth=p["ground_truth"],
                image_path=p.get("image_path"),
                tags=p.get("tags", []),
            )
            for p in data.get("pages", [])
        ]
        dataset = Dataset.from_pages(
            dataset_id=dataset_id,
            name=data["name"],
            category=DatasetCategory(data["category"]),
            description=data["description"],
            language=data["language"],
            pages=pages,
        )
        logger.info("dataset_loaded", dataset_id=dataset_id, page_count=len(pages))
        return dataset

    def list_available(self) -> list[str]:
        """List all available dataset IDs.

        Returns:
            Sorted list of dataset IDs (JSON filenames without extension).
        """
        if not self.datasets_dir.exists():
            logger.warning("datasets_dir_not_found", path=str(self.datasets_dir))
            return []
        ids = sorted(
            p.stem for p in self.datasets_dir.iterdir() if p.suffix == ".json"
        )
        return ids

    def load_all(self) -> list[Dataset]:
        """Load all available datasets.

        Returns:
            List of Dataset objects, sorted by ID.
        """
        datasets = []
        for dataset_id in self.list_available():
            try:
                datasets.append(self.load(dataset_id))
            except Exception as exc:
                logger.warning("dataset_load_failed", dataset_id=dataset_id, error=str(exc))
        return datasets
