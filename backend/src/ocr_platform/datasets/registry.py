"""Dataset registry for built-in benchmark datasets.

Provides a global registry of pre-loaded benchmark datasets that can be
referenced by ID throughout the application.
"""

from __future__ import annotations

from ocr_platform.datasets.loader import DatasetLoader
from ocr_platform.datasets.models import Dataset
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)


class DatasetRegistry:
    """In-memory registry of loaded benchmark datasets.

    Attributes:
        _datasets: Mapping of dataset_id → Dataset.
    """

    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}

    def register(self, dataset: Dataset) -> None:
        """Register a dataset in the registry.

        Args:
            dataset: Dataset to register.

        Raises:
            ValueError: If a dataset with the same ID is already registered.
        """
        if dataset.id in self._datasets:
            raise ValueError(f"Dataset '{dataset.id}' is already registered")
        self._datasets[dataset.id] = dataset
        logger.info("dataset_registered", dataset_id=dataset.id, name=dataset.name)

    def get(self, dataset_id: str) -> Dataset | None:
        """Retrieve a dataset by ID.

        Args:
            dataset_id: Unique dataset identifier.

        Returns:
            The Dataset or ``None`` if not found.
        """
        return self._datasets.get(dataset_id)

    def list_ids(self) -> list[str]:
        """Return all registered dataset IDs.

        Returns:
            Sorted list of dataset IDs.
        """
        return sorted(self._datasets.keys())

    def list_all(self) -> list[Dataset]:
        """Return all registered datasets.

        Returns:
            List of datasets sorted by ID.
        """
        return [self._datasets[did] for did in self.list_ids()]

    def load_from_directory(self, loader: DatasetLoader | None = None) -> None:
        """Load all datasets from the loader and register them.

        Args:
            loader: DatasetLoader instance. Defaults to a new DatasetLoader.
        """
        if loader is None:
            loader = DatasetLoader()
        for dataset in loader.load_all():
            try:
                self.register(dataset)
            except ValueError:
                logger.warning(
                    "dataset_register_skipped",
                    dataset_id=dataset.id,
                    reason="already_registered",
                )


# Global singleton instance — populated on first import
dataset_registry = DatasetRegistry()
try:
    dataset_registry.load_from_directory()
except Exception as exc:
    logger.warning("dataset_registry_auto_load_failed", error=str(exc))
