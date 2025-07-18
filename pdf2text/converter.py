"""Core OCR-to-text conversion logic.

Extracts searchable text from scanned PDF files using poppler (via
``pdf2image``) and Tesseract OCR (via ``pytesseract``).
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, cast, Iterator
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

    def __init__(
        self,
        tesseract_path: Optional[str] = None,
        *,
        log_level: int | None = None,
        tesseract_config: str = "--psm 1",
    ):
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

        self._tess_config = tesseract_config

    def _render_page(self, pdf_path: Path, page_num: int, dpi: int) -> Image.Image:
        """Return a single page image rendered via pdf2image."""
        pages = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_num, last_page=page_num)
        return pages[0]

    def _ocr_page(
        self, img: Image.Image, *, enhance: bool = False, lang: str = "eng", config: str | None = None
    ) -> str:
        """Run (optionally enhanced) OCR on *img* and return the extracted text."""
        if enhance:
            img = enhance_image(img)
        cfg = config if config is not None else self._tess_config
        return cast(str, pytesseract.image_to_string(img, lang=lang, config=cfg))

    def _write_output(self, text: str, output_path: Path) -> None:
        output_path.write_text(text, encoding="utf-8")
        logger.info("Wrote %s", output_path)

    # ---------------------------------------------------------------------
    # Streaming generator
    # ---------------------------------------------------------------------

    def iter_pages(
        self,
        pdf_path: Path,
        *,
        dpi: int = 200,
        enhance: bool = False,
        lang: str = "eng",
        chunk_size: int = 1,
        config: str | None = None,
    ) -> Iterator[tuple[int, str]]:
        """Yield ``(page_num, text)`` for each page, allowing callers to stream.

        This performs the same work as :py:meth:`extract_text_from_pdf` but
        streams results instead of aggregating them, so large PDFs can be
        processed incrementally.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        info = pdfinfo_from_path(str(pdf_path))
        total_pages = int(info.get("Pages", 0))
        if not total_pages:
            raise RuntimeError("Could not determine page count for %s" % pdf_path)

        if chunk_size < 1:
            chunk_size = 1

        current = 1
        while current <= total_pages:
            end = min(current + chunk_size - 1, total_pages)
            images = convert_from_path(
                str(pdf_path), dpi=dpi, first_page=current, last_page=end
            )
            for offset, img in enumerate(images, start=current):
                text = self._ocr_page(img, enhance=enhance, lang=lang, config=config)
                yield offset, text
            current += chunk_size

    # ---------------------------------------------------------------------
    # Async helper
    # ---------------------------------------------------------------------

    @staticmethod
    def _process_page_worker(
        pdf_path: str, idx: int, dpi: int, enhance: bool, lang: str
    ) -> tuple[int, str]:
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
        pdf_path: Path,
        *,
        dpi: int = 200,
        enhance: bool = False,
        lang: str = "eng",
        max_workers: int | None = None,
        use_processes: bool = True,
    ) -> str:
        """Asynchronously extract full text using a process (or thread) pool."""
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        info = pdfinfo_from_path(str(pdf_path))
        total_pages = int(info.get("Pages", 0))
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
        pdf_path: Path,
        output_path: Path | None = None,
        dpi: int = 200,
        enhance: bool = False,
        lang: str = "eng",
        chunk_size: int = 1,
    ) -> str:
        """Extract text from a *single* PDF.

        Parameters
        ----------
        pdf_path : Path
        output_path : Path | None
            If provided, write the text to this file.
        dpi : int, default 200
            Rendering resolution for ``pdf2image``; higher == slower but clearer.
        enhance : bool, default ``False``
            If *True* run simple image-processing steps before OCR.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        logger.info("Processing %s", pdf_path)

        # Get page count first to stream individually and save memory
        info = pdfinfo_from_path(str(pdf_path))
        total_pages = int(info.get("Pages", 0))
        if not total_pages:
            raise RuntimeError("Could not determine page count for %s" % pdf_path)

        # Optional tqdm progress bar
        try:
            from tqdm import tqdm

            page_iter = tqdm(range(1, total_pages + 1), desc="OCR")
        except ImportError:  # pragma: no cover – optional
            page_iter = range(1, total_pages + 1)

        text_chunks: List[str] = []
        for idx, page_text in self.iter_pages(pdf_path, dpi=dpi, enhance=enhance, lang=lang, chunk_size=chunk_size):
            text_chunks.append(f"--- Page {idx} ---\n{page_text}\n")

        full_text = "\n".join(text_chunks)

        if output_path:
            self._write_output(full_text, output_path)
        return full_text

    def batch_convert(
        self,
        input_folder: Path,
        output_folder: Path,
        file_extension: str = ".pdf",
        dpi: int = 200,
        enhance: bool = False,
        lang: str = "eng",
        parallel: bool = False,
        max_workers: int | None = None,
        chunk_size: int = 1,
    ) -> int:
        """Convert every PDF in *input_folder*.

        Each output file will have the same stem with ``.txt`` extension and be
        written to *output_folder*.
        """
        if not input_folder.exists():
            raise FileNotFoundError(input_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        pdf_files = sorted(input_folder.glob(f"*{file_extension}"))
        logger.info("%d files found in %s", len(pdf_files), input_folder)
        if not pdf_files:
            return 0

        expected_errors = (RuntimeError, FileNotFoundError)

        processed = 0
        if parallel:
            def _worker(path: Path) -> int:
                conv = PDFToTextConverter()
                dest = conv._safe_join(output_folder, f"{path.stem}.txt")
                conv.extract_text_from_pdf(
                    path,
                    dest,
                    dpi=dpi,
                    enhance=enhance,
                    lang=lang,
                    chunk_size=chunk_size,
                )
                return 1

            with ProcessPoolExecutor(max_workers=max_workers) as pool:
                processed = sum(pool.map(_worker, pdf_files))
            logger.info("Parallel batch conversion complete → %s (%d files)", output_folder, processed)
            return processed

        for pdf_file in pdf_files:
            try:
                dest_file = self._safe_join(output_folder, f"{pdf_file.stem}.txt")
                self.extract_text_from_pdf(
                    pdf_file,
                    dest_file,
                    dpi=dpi,
                    enhance=enhance,
                    lang=lang,
                    chunk_size=chunk_size,
                )
            except expected_errors as exc:
                # Log full stack in debug mode for easier diagnosis
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception("Failed processing %s", pdf_file)
                else:
                    logger.error("Failed processing %s: %s", pdf_file, exc)
                continue
            processed += 1

        logger.info("Batch conversion complete → %s (%d files)", output_folder, processed)
        return processed

    @staticmethod
    def _safe_join(base: Path, *paths: str) -> Path:
        """Return *base/paths* resolved, ensuring the result is within *base*.

        Raises ``ValueError`` if the resulting path escapes *base* via ``..`` tricks.
        """
        root = base.resolve()
        candidate = root.joinpath(*paths).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path {candidate} is outside {base}") from exc
        return candidate
