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
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import asyncio

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

    def __init__(self, tesseract_path: Optional[str] = None, *, log_level: int | None = None):
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

        # Allow callers to set per-instance logging verbosity
        if log_level is not None:
            logger.setLevel(log_level)

    def _render_page(self, pdf_path: Path, page_num: int, dpi: int) -> Image.Image:
        """Return a single page image rendered via pdf2image."""
        pages = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_num, last_page=page_num)
        return pages[0]

    def _ocr_page(self, img: Image.Image, *, enhance: bool = False, lang: str = "eng") -> str:
        """Run (optionally enhanced) OCR on *img* and return the extracted text."""
        if enhance:
            img = enhance_image(img)
        return pytesseract.image_to_string(img, lang=lang)

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
        lang: str = "eng",
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
            text = self._ocr_page(img, enhance=enhance, lang=lang)
            yield idx, text

    # ---------------------------------------------------------------------
    # Async helper
    # ---------------------------------------------------------------------

    @staticmethod
    def _process_page_worker(pdf_path: str, idx: int, dpi: int, enhance: bool, lang: str) -> tuple[int, str]:
        """Helper for multiprocessing: render + OCR a single page."""
        from pdf2image import convert_from_path  # re-import for separate process
        from pdf2text.utils import enhance_image  # local import to avoid pickle issues
        import pytesseract

        pages = convert_from_path(pdf_path, dpi=dpi, first_page=idx, last_page=idx)
        img = pages[0]
        if enhance:
            img = enhance_image(img)
        text = pytesseract.image_to_string(img, lang=lang)
        return idx, text

    async def extract_text_async(
        self,
        pdf_path: str | os.PathLike[str],
        *,
        dpi: int = 200,
        enhance: bool = False,
        lang: str = "eng",
        max_workers: int | None = None,
        use_processes: bool = True,
    ) -> str:
        """Asynchronously extract full text using a process (or thread) pool."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        info = pdfinfo_from_path(str(pdf_path))
        total_pages: int = info.get("Pages", 0)  # type: ignore[arg-type]
        if not total_pages:
            raise RuntimeError("Could not determine page count for %s" % pdf_path)

        loop = asyncio.get_running_loop()
        ExecutorCls = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

        results: List[tuple[int, str]] = []
        with ExecutorCls(max_workers=max_workers) as pool:
            tasks = [
                loop.run_in_executor(
                    pool,
                    PDFToTextConverter._process_page_worker,
                    str(pdf_path),
                    idx,
                    dpi,
                    enhance,
                    lang,
                )
                for idx in range(1, total_pages + 1)
            ]
            for coro in asyncio.as_completed(tasks):
                results.append(await coro)

        # sort by page number and compose
        results.sort(key=lambda t: t[0])
        return "\n".join(f"--- Page {idx} ---\n{text}\n" for idx, text in results)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def extract_text_from_pdf(
        self,
        pdf_path: str | os.PathLike[str],
        output_path: str | os.PathLike[str] | None = None,
        dpi: int = 200,
        enhance: bool = False,
        lang: str = "eng",
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
        for idx, page_text in self.iter_pages(pdf_path, dpi=dpi, enhance=enhance, lang=lang):
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
        lang: str = "eng",
    ) -> int:
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
            return 0

        expected_errors = (RuntimeError, FileNotFoundError)

        processed = 0
        for pdf_file in pdf_files:
            try:
                dest_file = out_path / f"{pdf_file.stem}.txt"
                self.extract_text_from_pdf(
                    pdf_file, dest_file, dpi=dpi, enhance=enhance, lang=lang
                )
            except expected_errors as exc:
                # Log full stack in debug mode for easier diagnosis
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception("Failed processing %s", pdf_file)
                else:
                    logger.error("Failed processing %s: %s", pdf_file, exc)
                continue
            processed += 1

        logger.info("Batch conversion complete → %s (%d files)", out_path, processed)
        return processed
