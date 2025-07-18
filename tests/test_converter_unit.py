"""Unit tests for PDFToTextConverter using mocks only (no binaries)."""
from pathlib import Path

import pytest
from PIL import Image

from pdf2text.converter import PDFToTextConverter
import asyncio


def _fake_pdf_bytes():
    """Return minimal valid PDF bytes."""
    return b"%PDF-1.4\n%EOF"


@pytest.fixture
def dummy_pdf(tmp_path: Path) -> Path:
    """Create a dummy PDF file and return its path."""
    pdf = tmp_path / "dummy.pdf"
    pdf.write_bytes(_fake_pdf_bytes())
    return pdf


def test_extract_text_basic(monkeypatch, dummy_pdf: Path, tmp_path: Path):
    """Happy-path: convert a single PDF with patched dependencies."""

    dummy_img = Image.new("RGB", (100, 100))

    # Patch pdf2image.convert_from_path to return one dummy image
    monkeypatch.setattr(
        "pdf2text.converter.convert_from_path", lambda *a, **kw: [dummy_img]
    )
    # Patch pytesseract.image_to_string to return a known string
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.image_to_string", lambda *a, **kw: "HELLO"
    )
    # Patch pdfinfo_from_path to return fake page count
    monkeypatch.setattr(
        "pdf2text.converter.pdfinfo_from_path", lambda *a, **kw: {"Pages": 1}
    )
    # Patch pytesseract.get_tesseract_version so __init__ succeeds
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.get_tesseract_version", lambda: "5.0"
    )

    out_path = tmp_path / "out.txt"

    text = PDFToTextConverter().extract_text_from_pdf(dummy_pdf, out_path)

    assert text == "--- Page 1 ---\nHELLO\n"
    assert out_path.read_text() == text


def test_file_not_found(monkeypatch):
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.get_tesseract_version", lambda: "5.0"
    )
    with pytest.raises(FileNotFoundError):
        PDFToTextConverter().extract_text_from_pdf("not_there.pdf")


def test_missing_tesseract(monkeypatch, tmp_path):
    """Simulate missing Tesseract binary => RuntimeError in __init__."""
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.get_tesseract_version",
        lambda: (_ for _ in ()).throw(RuntimeError("missing")),
    )
    with pytest.raises(RuntimeError):
        from pdf2text import converter  # import inside to re-evaluate patch
        converter.PDFToTextConverter()


def test_batch_convert(monkeypatch, tmp_path):
    """batch_convert should produce one .txt per PDF input using mocks."""
    # Setup dummy input/output dirs
    in_dir = tmp_path / "pdfs"
    out_dir = tmp_path / "txts"
    in_dir.mkdir()

    # Create two minimal PDF files
    for name in ("a.pdf", "b.pdf"):
        (in_dir / name).write_bytes(_fake_pdf_bytes())

    dummy_img = Image.new("RGB", (50, 50))

    # Same patches as in single-file test
    monkeypatch.setattr(
        "pdf2text.converter.convert_from_path", lambda *a, **kw: [dummy_img]
    )
    monkeypatch.setattr(
        "pdf2text.converter.pdfinfo_from_path", lambda *a, **kw: {"Pages": 1}
    )
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.image_to_string", lambda *a, **kw: "HI"
    )
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.get_tesseract_version", lambda: "5.0"
    )

    PDFToTextConverter().batch_convert(in_dir, out_dir)

    txt_files = sorted(out_dir.glob("*.txt"))
    assert [f.name for f in txt_files] == ["a.txt", "b.txt"]
    for f in txt_files:
        assert f.read_text() == "--- Page 1 ---\nHI\n"


def test_iter_pages(monkeypatch, dummy_pdf: Path):
    """iter_pages should yield sequential page numbers and text."""
    dummy_img = Image.new("RGB", (10, 10))

    monkeypatch.setattr(
        "pdf2text.converter.convert_from_path", lambda *a, **kw: [dummy_img]
    )
    monkeypatch.setattr(
        "pdf2text.converter.pdfinfo_from_path", lambda *a, **kw: {"Pages": 3}
    )
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.image_to_string",
        lambda *a, **kw: "P",  # constant char -> easy check
    )
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.get_tesseract_version", lambda: "5.0"
    )

    conv = PDFToTextConverter()
    pages = list(conv.iter_pages(dummy_pdf))

    assert pages == [(1, "P"), (2, "P"), (3, "P")]


def test_extract_text_async(monkeypatch, dummy_pdf: Path):
    """Async extraction should compose pages in correct order using mocks."""
    monkeypatch.setattr(
        "pdf2text.converter.pdfinfo_from_path", lambda *a, **kw: {"Pages": 2}
    )
    # Replace the worker to avoid spawn overhead
    monkeypatch.setattr(
        "pdf2text.converter.PDFToTextConverter._process_page_worker",
        staticmethod(lambda path, idx, dpi, enhance: (idx, f"T{idx}")),
    )
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.get_tesseract_version", lambda: "5.0"
    )

    conv = PDFToTextConverter()
    out = asyncio.run(conv.extract_text_async(dummy_pdf, use_processes=False))

    assert out == "--- Page 1 ---\nT1\n\n--- Page 2 ---\nT2\n"
