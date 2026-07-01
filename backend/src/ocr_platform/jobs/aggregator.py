"""Document aggregator for merging page-level OCR results.

Provides a clean, reusable service that merges per-page OCR results into a
coherent document-level output while preserving page order and computing
document-level statistics.
"""

from __future__ import annotations

from ocr_platform.jobs.models import DocumentResult, JobPageResult
from ocr_platform.logging_config import get_logger

logger = get_logger(__name__)

PAGE_BREAK_MARKER = "\n\n--- PAGE BREAK ---\n\n"


class DocumentAggregator:
    """Merge page-level OCR results into a single document result.

    The aggregator sorts pages by page number, joins text with a page-break
    marker, and computes statistics such as average confidence, word count,
    and character count.
    """

    @staticmethod
    def aggregate(
        job_id: str,
        pages: list[JobPageResult],
        total_processing_time_ms: float,
    ) -> DocumentResult:
        """Merge page results into a single :class:`DocumentResult`.

        Pages are sorted by ``page_number`` to ensure the correct order.
        Page text is joined with a ``PAGE_BREAK_MARKER`` separator.

        Args:
            job_id: Unique job identifier.
            pages: List of per-page OCR results.
            total_processing_time_ms: Total processing time for all pages.

        Returns:
            A :class:`DocumentResult` with merged text and statistics.

        Raises:
            ValueError: If *pages* is empty.
        """
        if not pages:
            raise ValueError("Cannot aggregate an empty list of pages")

        sorted_pages = sorted(pages, key=lambda p: p.page_number)

        # Build document text with page break markers
        document_text = PAGE_BREAK_MARKER.join(
            f"[Page {p.page_number}]\n{p.text}" for p in sorted_pages
        )

        # Compute statistics
        page_count = len(sorted_pages)
        confidences = [p.confidence for p in sorted_pages if p.confidence is not None]
        average_confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
        average_processing_time = round(total_processing_time_ms / page_count, 3)
        word_count = sum(len(p.text.split()) for p in sorted_pages)
        character_count = sum(len(p.text) for p in sorted_pages)
        languages = sorted({p.language for p in sorted_pages if p.language})

        logger.info(
            "document_aggregated",
            job_id=job_id,
            page_count=page_count,
            word_count=word_count,
            character_count=character_count,
            languages=languages,
            average_confidence=average_confidence,
        )

        return DocumentResult(
            job_id=job_id,
            document_text=document_text,
            pages=sorted_pages,
            page_count=page_count,
            languages=languages,
            average_confidence=average_confidence,
            total_processing_time_ms=round(total_processing_time_ms, 3),
            average_processing_time_ms=average_processing_time,
            word_count=word_count,
            character_count=character_count,
        )
