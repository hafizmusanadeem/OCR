"""Document preprocessor.

Converts uploaded documents (PDF, PNG, JPEG, TIFF) into a uniform
list of :class:`PageImage` objects. PDFs are rendered to PNG per page;
images are passed through after validation.
"""

from __future__ import annotations

from io import BytesIO

from ocr_platform.logging_config import get_logger
from ocr_platform.preprocessing.types import DocumentType, PageImage

logger = get_logger(__name__)

DEFAULT_DPI = 200

try:
    from PIL import Image

    _PILLOW_AVAILABLE = True
except ImportError:
    _PILLOW_AVAILABLE = False

try:
    import fitz  # type: ignore[import-untyped]

    _FITZ_AVAILABLE = True
except ImportError:
    _FITZ_AVAILABLE = False


class DocumentPreprocessor:
    """Convert documents into page-level images.

    Attributes:
        dpi: Resolution for PDF rendering (dots per inch).
    """

    def __init__(self, dpi: int = DEFAULT_DPI) -> None:
        self.dpi = dpi

    def preprocess(self, content: bytes, content_type: str) -> list[PageImage]:
        """Convert a document into a list of page images.

        Args:
            content: Raw file bytes.
            content_type: MIME type of the uploaded file.

        Returns:
            A list of :class:`PageImage` objects, one per page.

        Raises:
            ValueError: If the content type is not supported.
            RuntimeError: If a required library (PyMuPDF or Pillow) is missing.
        """
        doc_type = self._detect_type(content_type)
        logger.info(
            "preprocessing_document",
            content_type=content_type,
            document_type=doc_type.value,
            size=len(content),
        )

        if doc_type == DocumentType.PDF:
            return self._process_pdf(content)
        if doc_type in (DocumentType.PNG, DocumentType.JPEG, DocumentType.TIFF):
            return self._process_image(content, doc_type)

        raise ValueError(
            f"Unsupported document type: {content_type}. "
            f"Supported: PDF, PNG, JPEG, TIFF."
        )

    def _detect_type(self, content_type: str) -> DocumentType:
        """Map MIME type to :class:`DocumentType`."""
        mapping = {
            "application/pdf": DocumentType.PDF,
            "image/png": DocumentType.PNG,
            "image/jpeg": DocumentType.JPEG,
            "image/jpg": DocumentType.JPEG,
            "image/tiff": DocumentType.TIFF,
        }
        return mapping.get(content_type.lower().strip(), DocumentType.UNKNOWN)

    def _process_pdf(self, content: bytes) -> list[PageImage]:
        """Render a PDF to page images using PyMuPDF.

        Args:
            content: Raw PDF bytes.

        Returns:
            One :class:`PageImage` per page, rendered as PNG.

        Raises:
            RuntimeError: If PyMuPDF is not installed.
        """
        if not _FITZ_AVAILABLE:
            raise RuntimeError(
                "PDF processing requires PyMuPDF. "
                "Install with: pip install pymupdf"
            )

        pages: list[PageImage] = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page_num, page in enumerate(doc, start=1):
                pix = page.get_pixmap(dpi=self.dpi)
                image_data = pix.tobytes("png")
                pages.append(
                    PageImage(
                        page_number=page_num,
                        image_data=image_data,
                        width=pix.width,
                        height=pix.height,
                        format="png",
                    )
                )
                logger.debug(
                    "pdf_page_rendered",
                    page_number=page_num,
                    width=pix.width,
                    height=pix.height,
                )

        logger.info(
            "pdf_preprocessed",
            page_count=len(pages),
            dpi=self.dpi,
        )
        return pages

    def _process_image(self, content: bytes, doc_type: DocumentType) -> list[PageImage]:
        """Validate an image and return it as a single-page list.

        Args:
            content: Raw image bytes.
            doc_type: Detected document type.

        Returns:
            A single-element list containing the image as a :class:`PageImage`.

        Raises:
            RuntimeError: If Pillow is not installed.
            ValueError: If the image is corrupt or unreadable.
        """
        if not _PILLOW_AVAILABLE:
            raise RuntimeError(
                "Image processing requires Pillow. "
                "Install with: pip install Pillow"
            )

        try:
            img = Image.open(BytesIO(content))
            img.verify()  # Validate without fully decoding
        except Exception as exc:
            raise ValueError(f"Invalid or corrupt image: {exc}") from exc

        # Re-open after verify() exhausts the stream
        img = Image.open(BytesIO(content))
        width, height = img.size

        logger.info(
            "image_preprocessed",
            format=doc_type.value,
            width=width,
            height=height,
        )
        return [
            PageImage(
                page_number=1,
                image_data=content,
                width=width,
                height=height,
                format=doc_type.value,
            )
        ]
