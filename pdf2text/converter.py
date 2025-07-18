"""Core OCR-to-text conversion logic.

Extracts searchable text from scanned PDF files using poppler (via
``pdf2image``) and Tesseract OCR (via ``pytesseract``).
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
import pytesseract

from .utils import enhance_image

logger = logging.getLogger(__name__)

__all__ = ["PDFToTextConverter"]


class PDFToTextConverter:
    """Convert scanned PDF files to plain text.

    This is a refactor of the original *scannedpdf_to_searchabletxt.py* script
    into a reusable object-oriented API.
    """

    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Verify dependencies early to fail fast.
        try:
            pytesseract.get_tesseract_version()
        except Exception as exc:  # pragma: no cover – system dep error
            logger.error(
                "Tesseract OCR not found. Install it first.\n"
                "Ubuntu/Debian: sudo apt install tesseract-ocr\n"
                "macOS: brew install tesseract\n"
                "Windows: https://github.com/UB-Mannheim/tesseract/wiki"
            )
            raise RuntimeError("Tesseract not available") from exc

        # poppler presence indirectly checked by attempting to access attribute.
        if not hasattr(convert_from_path, "__module__"):
            raise RuntimeError(
                "Poppler not available. Install poppler-utils (or brew install poppler)."
            )

    def _render_page(self, pdf_path: Path, page_num: int, dpi: int) -> Image.Image:
        """Return a single page image rendered via pdf2image."""
        pages = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_num, last_page=page_num)
        return pages[0]

    def _ocr_page(self, img: Image.Image, enhance: bool = False) -> str:
        """Run (optionally enhanced) OCR on *img* and return the extracted text."""
        if enhance:
            img = enhance_image(img)
        return pytesseract.image_to_string(img, lang="eng")

    def _write_output(self, text: str, output_path: Path) -> None:
        output_path.write_text(text, encoding="utf-8")
        logger.info("Wrote %s", output_path)

    # ---------------------------------------------------------------------
    # Streaming generator
    # ---------------------------------------------------------------------

    def iter_pages(
        self,
        pdf_path: str | os.PathLike[str],
        *,
        dpi: int = 200,
        enhance: bool = False,
    ):
        """Yield ``(page_num, text)`` for each page, allowing callers to stream.

        This performs the same work as :py:meth:`extract_text_from_pdf` but
        streams results instead of aggregating them, so large PDFs can be
        processed incrementally.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        info = pdfinfo_from_path(str(pdf_path))
        total_pages: int = info.get("Pages", 0)  # type: ignore[arg-type]
        if not total_pages:
            raise RuntimeError("Could not determine page count for %s" % pdf_path)

        page_iter = range(1, total_pages + 1)
        for idx in page_iter:
            img = self._render_page(pdf_path, idx, dpi)
            text = self._ocr_page(img, enhance=enhance)
            yield idx, text

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def extract_text_from_pdf(
        self,
        pdf_path: str | os.PathLike[str],
        output_path: str | os.PathLike[str] | None = None,
        dpi: int = 200,
        enhance: bool = False,
    ) -> str:
        """Extract text from a *single* PDF.

        Parameters
        ----------
        pdf_path : str | Path
        output_path : str | Path | None
            If provided, write the text to this file.
        dpi : int, default 200
            Rendering resolution for ``pdf2image``; higher == slower but clearer.
        enhance : bool, default ``False``
            If *True* run simple image-processing steps before OCR.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        logger.info("Processing %s", pdf_path)

        # Get page count first to stream individually and save memory
        info = pdfinfo_from_path(str(pdf_path))
        total_pages: int = info.get("Pages", 0)  # type: ignore[arg-type]
        if not total_pages:
            raise RuntimeError("Could not determine page count for %s" % pdf_path)

        # Optional tqdm progress bar
        try:
            from tqdm import tqdm  # type: ignore

            page_iter = tqdm(range(1, total_pages + 1), desc="OCR")
        except ImportError:  # pragma: no cover – optional
            page_iter = range(1, total_pages + 1)

        text_chunks: List[str] = []
        for idx, page_text in self.iter_pages(pdf_path, dpi=dpi, enhance=enhance):
            text_chunks.append(f"--- Page {idx} ---\n{page_text}\n")

        full_text = "\n".join(text_chunks)

        if output_path:
            self._write_output(full_text, Path(output_path))
        return full_text

    def batch_convert(
        self,
        input_folder: str | os.PathLike[str],
        output_folder: str | os.PathLike[str],
        file_extension: str = ".pdf",
        dpi: int = 200,
        enhance: bool = False,
    ) -> None:
        """Convert every PDF in *input_folder*.

        Each output file will have the same stem with ``.txt`` extension and be
        written to *output_folder*.
        """
        in_path = Path(input_folder)
        out_path = Path(output_folder)

        if not in_path.exists():
            raise FileNotFoundError(in_path)
        out_path.mkdir(parents=True, exist_ok=True)

        pdf_files = sorted(in_path.glob(f"*{file_extension}"))
        logger.info("%d files found in %s", len(pdf_files), in_path)
        if not pdf_files:
            return

        for pdf_file in pdf_files:
            try:
                dest_file = out_path / f"{pdf_file.stem}.txt"
                self.extract_text_from_pdf(
                    pdf_file, dest_file, dpi=dpi, enhance=enhance
                )
            except Exception as exc:
                logger.error("Failed processing %s: %s", pdf_file, exc)
                continue

        logger.info("Batch conversion complete → %s", out_path)
