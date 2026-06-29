"""OCR upload endpoint.

Accepts PDF or image files, preprocesses them into page-level images,
dispatches each page to the configured OCR provider, and returns
structured JSON results.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from ocr_platform.config import settings
from ocr_platform.logging_config import get_logger
from ocr_platform.preprocessing.document import DocumentPreprocessor
from ocr_platform.providers import global_registry
from ocr_platform.providers.models import OCRResult

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ocr"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
VALID_CONTENT_TYPES = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
)


class OCRPageResult(BaseModel):
    """OCR result for a single page.

    Attributes:
        page_number: 1-based page index.
        text: Extracted text for this page.
        confidence: Confidence score (0.0-1.0) if available.
        language: Detected language code if available.
        processing_time_ms: Time taken to process this page in milliseconds.
    """

    page_number: int = Field(description="1-based page index")
    text: str = Field(description="Extracted text for this page")
    confidence: float | None = Field(default=None, description="Confidence score (0.0-1.0)")
    language: str | None = Field(default=None, description="Detected language code")
    processing_time_ms: float | None = Field(
        default=None, description="Processing time in milliseconds"
    )


class OCRUploadResponse(BaseModel):
    """Response model for the OCR upload endpoint.

    Attributes:
        filename: Original uploaded filename.
        file_size: Size of the uploaded file in bytes.
        page_count: Number of pages extracted.
        document_type: Detected document type (pdf, png, jpeg, tiff).
        engine: Name of the OCR engine used.
        pages: List of OCR results per page.
        total_processing_time_ms: Total time across all pages.
    """

    filename: str = Field(description="Original uploaded filename")
    file_size: int = Field(description="Size of the uploaded file in bytes")
    page_count: int = Field(description="Number of pages extracted")
    document_type: str = Field(description="Detected document type")
    engine: str = Field(description="Name of the OCR engine used")
    pages: list[OCRPageResult] = Field(description="OCR results per page")
    total_processing_time_ms: float | None = Field(
        default=None, description="Total processing time in milliseconds"
    )


@router.post(
    "/ocr",
    response_model=OCRUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and OCR a document",
    description="Upload a PDF or image file and receive OCR results. "
    "PDFs are split into pages; each page is processed individually. "
    "Supported formats: PDF, PNG, JPEG, TIFF.",
)
async def ocr_upload(
    file: UploadFile = File(..., description="PDF or image file to OCR"),
    provider: str | None = Form(
        None, description="OCR provider name (defaults to configured default)"
    ),
) -> OCRUploadResponse:
    """Upload a file, preprocess it into pages, and run OCR on each page.

    Args:
        file: PDF or image file to process.
        provider: Optional OCR provider name. Defaults to
            ``settings.default_ocr_provider``.

    Returns:
        Structured OCR result with per-page detail and file metadata.

    Raises:
        HTTPException: 400 for invalid file type, 413 for file too large,
            404 for unknown provider, 503 for unavailable provider,
            502 for OCR processing or preprocessing failure.
    """
    # Validate content type
    content_type = file.content_type or ""
    if not content_type.startswith(VALID_CONTENT_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {content_type}. "
            f"Supported: {', '.join(VALID_CONTENT_TYPES)}.",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large ({len(content)} bytes). "
            f"Maximum allowed: {MAX_FILE_SIZE} bytes (10 MB).",
        )

    logger.info(
        "ocr_upload_received",
        filename=file.filename,
        content_type=content_type,
        file_size=len(content),
    )

    # Resolve provider
    provider_name = provider or settings.default_ocr_provider
    try:
        ocr_provider = global_registry.create_provider(provider_name)
    except KeyError as exc:
        available = ", ".join(global_registry.list_providers()) or "none"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' not found. Available: {available}.",
        ) from exc

    if not ocr_provider.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider '{provider_name}' is not available. "
            "Check configuration (e.g., API key).",
        )

    # Preprocess document into pages
    preprocessor = DocumentPreprocessor()
    try:
        page_images = preprocessor.preprocess(content, content_type)
    except Exception as exc:
        logger.error(
            "preprocessing_failed",
            error=str(exc),
            content_type=content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Document preprocessing failed: {exc}",
        ) from exc

    document_type = preprocessor._detect_type(content_type).value

    # OCR each page
    page_results: list[OCRPageResult] = []
    total_processing_time = 0.0

    for page_image in page_images:
        try:
            result: OCRResult = await ocr_provider.recognize(page_image.image_data)
        except Exception as exc:
            logger.error(
                "ocr_page_failed",
                provider=provider_name,
                page_number=page_image.page_number,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OCR failed on page {page_image.page_number}: {exc}",
            ) from exc

        page_results.append(
            OCRPageResult(
                page_number=page_image.page_number,
                text=result.text,
                confidence=result.confidence,
                language=result.language,
                processing_time_ms=result.processing_time_ms,
            )
        )
        if result.processing_time_ms:
            total_processing_time += result.processing_time_ms

    logger.info(
        "ocr_upload_complete",
        filename=file.filename,
        page_count=len(page_results),
        provider=provider_name,
        total_processing_time_ms=round(total_processing_time, 3),
    )

    return OCRUploadResponse(
        filename=file.filename or "unknown",
        file_size=len(content),
        page_count=len(page_results),
        document_type=document_type,
        engine=ocr_provider.name(),
        pages=page_results,
        total_processing_time_ms=(
            round(total_processing_time, 3) if total_processing_time > 0 else None
        ),
    )
