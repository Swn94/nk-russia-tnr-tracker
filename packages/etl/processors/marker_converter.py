"""PDF to Markdown converter using marker-pdf."""

import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

import structlog

from packages.core.utils.config import get_settings

logger = structlog.get_logger()


class MarkerConverter:
    """Convert PDF documents to Markdown using marker-pdf."""

    def __init__(self, output_dir: Optional[str] = None):
        self.settings = get_settings()
        self.output_dir = Path(output_dir or self.settings.pdf_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _check_cached(self, file_path: Path, file_hash: str) -> Optional[Path]:
        """Check if converted file exists in cache."""
        cache_path = self.output_dir / f"{file_path.stem}_{file_hash[:8]}.md"
        if cache_path.exists():
            return cache_path
        return None

    async def convert_pdf(
        self,
        pdf_path: str,
        use_cache: bool = True,
        disable_image_extraction: bool = True,
        page_range: Optional[str] = None,
    ) -> dict:
        """
        Convert a PDF file to Markdown.

        Args:
            pdf_path: Path to the PDF file
            use_cache: Whether to use cached conversion if available
            disable_image_extraction: Skip image extraction to save memory
            page_range: Optional page range (e.g., "0-49")

        Returns:
            Dictionary with conversion results
        """
        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            return {
                "status": "error",
                "error": f"PDF file not found: {pdf_path}",
            }

        file_hash = self._get_file_hash(pdf_file)

        # Check cache
        if use_cache:
            cached = self._check_cached(pdf_file, file_hash)
            if cached:
                logger.info("Using cached conversion", file=str(pdf_file))
                return {
                    "status": "cached",
                    "source_file": str(pdf_file),
                    "output_file": str(cached),
                    "file_hash": file_hash,
                    "content": cached.read_text(encoding="utf-8"),
                }

        # Try fast PyMuPDF extraction first for digital PDFs
        try:
            content = await self._try_pymupdf_extraction(pdf_file)
            if content and len(content.strip()) > 100:
                output_path = self.output_dir / f"{pdf_file.stem}_{file_hash[:8]}.md"
                output_path.write_text(content, encoding="utf-8")

                logger.info(
                    "PDF converted using PyMuPDF",
                    file=str(pdf_file),
                    output=str(output_path),
                    chars=len(content),
                )

                return {
                    "status": "success",
                    "method": "pymupdf",
                    "source_file": str(pdf_file),
                    "output_file": str(output_path),
                    "file_hash": file_hash,
                    "content": content,
                    "char_count": len(content),
                }
        except Exception as e:
            logger.debug("PyMuPDF extraction failed, trying marker", error=str(e))

        # Fall back to marker-pdf for scanned PDFs
        try:
            content = await self._marker_conversion(
                pdf_file,
                disable_image_extraction=disable_image_extraction,
                page_range=page_range,
            )

            output_path = self.output_dir / f"{pdf_file.stem}_{file_hash[:8]}.md"
            output_path.write_text(content, encoding="utf-8")

            logger.info(
                "PDF converted using marker",
                file=str(pdf_file),
                output=str(output_path),
                chars=len(content),
            )

            return {
                "status": "success",
                "method": "marker",
                "source_file": str(pdf_file),
                "output_file": str(output_path),
                "file_hash": file_hash,
                "content": content,
                "char_count": len(content),
            }

        except Exception as e:
            logger.error("PDF conversion failed", file=str(pdf_file), error=str(e))
            return {
                "status": "error",
                "source_file": str(pdf_file),
                "error": str(e),
            }

    async def _try_pymupdf_extraction(self, pdf_path: Path) -> Optional[str]:
        """Try to extract text using PyMuPDF (fast, for digital PDFs)."""
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        text_parts = []

        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"## Page {page_num + 1}\n\n{text}")

        doc.close()

        if text_parts:
            return "\n\n".join(text_parts)
        return None

    async def _marker_conversion(
        self,
        pdf_path: Path,
        disable_image_extraction: bool = True,
        page_range: Optional[str] = None,
    ) -> str:
        """Convert using marker-pdf (slower, for scanned PDFs with OCR)."""
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict

            # Initialize models (this can be slow on first run)
            models = create_model_dict()

            # Configure converter
            converter = PdfConverter(
                artifact_dict=models,
            )

            # Convert
            rendered = converter(str(pdf_path))

            # Extract markdown content
            if hasattr(rendered, "markdown"):
                return rendered.markdown
            elif isinstance(rendered, str):
                return rendered
            else:
                return str(rendered)

        except ImportError:
            # Fallback if marker not available - use PyMuPDF only
            logger.warning("marker-pdf not available, using PyMuPDF only")
            raise

    async def batch_convert(
        self,
        pdf_paths: list[str],
        use_cache: bool = True,
    ) -> list[dict]:
        """Convert multiple PDF files."""
        results = []
        for pdf_path in pdf_paths:
            result = await self.convert_pdf(pdf_path, use_cache=use_cache)
            results.append(result)
        return results
