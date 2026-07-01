"""Dataset API endpoints.

Provides REST endpoints for listing and retrieving benchmark datasets.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ocr_platform.datasets.models import Dataset, DatasetCategory
from ocr_platform.datasets.registry import dataset_registry
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["datasets"])


class DatasetListResponse(BaseModel):
    """Response model for listing datasets.

    Attributes:
        datasets: List of dataset summaries.
        total: Total number of datasets.
    """

    datasets: list[dict] = Field(description="List of dataset summaries")
    total: int = Field(description="Total number of datasets")


class DatasetDetailResponse(BaseModel):
    """Response model for a single dataset.

    Attributes:
        dataset: Full dataset with all pages and ground truth.
    """

    dataset: Dataset = Field(description="Full dataset with ground truth")


class DatasetPageResponse(BaseModel):
    """Response model for a single dataset page.

    Attributes:
        dataset_id: Parent dataset identifier.
        page_number: 1-based page index.
        ground_truth: Reference text for this page.
        tags: Filter tags.
    """

    dataset_id: str = Field(description="Parent dataset identifier")
    page_number: int = Field(description="1-based page index")
    ground_truth: str = Field(description="Reference text for this page")
    tags: list[str] = Field(description="Filter tags")


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List benchmark datasets",
    description="Retrieve all available benchmark datasets with summaries. "
    "Ground truth is available for every page in every dataset.",
)
async def list_datasets() -> DatasetListResponse:
    """List all available benchmark datasets.

    Returns:
        A DatasetListResponse with dataset summaries.
    """
    datasets = dataset_registry.list_all()
    summaries = [
        {
            "id": d.id,
            "name": d.name,
            "category": d.category.value,
            "description": d.description,
            "language": d.language,
            "page_count": len(d.pages),
            "total_characters": d.total_characters,
            "total_words": d.total_words,
        }
        for d in datasets
    ]
    logger.info("datasets_listed", count=len(summaries))
    return DatasetListResponse(
        datasets=summaries,
        total=len(summaries),
    )


@router.get(
    "/datasets/categories",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List dataset categories",
    description="Retrieve all available dataset category names.",
)
async def list_categories() -> list[str]:
    """List all available dataset categories.

    Returns:
        List of category names.
    """
    categories = [c.value for c in DatasetCategory]
    return categories


@router.get(
    "/datasets/{dataset_id}",
    response_model=DatasetDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dataset details",
    description="Retrieve a full benchmark dataset including all pages and ground truth.",
)
async def get_dataset(dataset_id: str) -> DatasetDetailResponse:
    """Retrieve a benchmark dataset by ID.

    Args:
        dataset_id: Unique dataset identifier.

    Returns:
        A DatasetDetailResponse with the full dataset.

    Raises:
        HTTPException: 404 if the dataset is not found.
    """
    dataset = dataset_registry.get(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
    logger.info("dataset_retrieved", dataset_id=dataset_id, page_count=len(dataset.pages))
    return DatasetDetailResponse(dataset=dataset)


@router.get(
    "/datasets/{dataset_id}/pages/{page_number}",
    response_model=DatasetPageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dataset page ground truth",
    description="Retrieve the ground truth text for a specific page in a dataset.",
)
async def get_dataset_page(dataset_id: str, page_number: int) -> DatasetPageResponse:
    """Retrieve ground truth for a specific dataset page.

    Args:
        dataset_id: Unique dataset identifier.
        page_number: 1-based page index.

    Returns:
        A DatasetPageResponse with ground truth.

    Raises:
        HTTPException: 404 if the dataset or page is not found.
    """
    dataset = dataset_registry.get(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )

    page = next((p for p in dataset.pages if p.page_number == page_number), None)
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} not found in dataset '{dataset_id}'.",
        )

    logger.info("dataset_page_retrieved", dataset_id=dataset_id, page_number=page_number)
    return DatasetPageResponse(
        dataset_id=dataset_id,
        page_number=page_number,
        ground_truth=page.ground_truth,
        tags=page.tags,
    )
