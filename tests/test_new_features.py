"""Unit tests for newly added perf features (chunked pages + parallel batch)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf2text.converter import PDFToTextConverter


@pytest.fixture()
def dummy_imgs(monkeypatch):
    """Patch pdf2image.convert_from_path to return N dummy images."""

    class DummyImg:  # minimal Pillow-like object
        size = (100, 100)

    def _fake_convert(path, dpi, first_page, last_page):  # noqa: D401
        count = last_page - first_page + 1
        return [DummyImg() for _ in range(count)]

    monkeypatch.setattr("pdf2text.converter.convert_from_path", _fake_convert)
    return DummyImg


def test_iter_pages_chunked(monkeypatch, tmp_path, dummy_imgs):
    # patch pytesseract to avoid OCR
    monkeypatch.setattr("pdf2text.converter.pytesseract.image_to_string", lambda *a, **k: "TXT")

    conv = PDFToTextConverter()

    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.touch()

    # patch pdfinfo_from_path to pretend 5 pages
    monkeypatch.setattr("pdf2text.converter.pdfinfo_from_path", lambda _: {"Pages": 5})

    pages = list(conv.iter_pages(dummy_pdf, chunk_size=3))
    assert [n for n, _ in pages] == [1, 2, 3, 4, 5]


def test_batch_convert_parallel(monkeypatch, tmp_path):
    # create fake PDF files
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    for i in range(4):
        (in_dir / f"f{i}.pdf").touch()

    out_dir = tmp_path / "out"

    # patch internal worker to skip heavy work
    monkeypatch.setattr(
        "pdf2text.converter.PDFToTextConverter._process_page_worker",
        staticmethod(lambda *a, **k: (1, "TXT")),
    )

    # avoid OCR inside worker path
    monkeypatch.setattr("pdf2text.converter.pytesseract.image_to_string", lambda *a, **k: "TXT")

    # patch pdf2image & pdfinfo to avoid external binaries inside worker too
    monkeypatch.setattr(
        "pdf2text.converter.convert_from_path",
        lambda *a, **k: [SimpleNamespace(size=(100, 100))],
    )
    monkeypatch.setattr("pdf2text.converter.pdfinfo_from_path", lambda _: {"Pages": 1})

    # replace ProcessPoolExecutor with serial dummy to avoid fork issues in test runners
    class DummyPool:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, func, iterable):
            return [func(x) for x in iterable]

    monkeypatch.setattr("pdf2text.converter.ProcessPoolExecutor", DummyPool)

    conv = PDFToTextConverter()
    processed = conv.batch_convert(in_dir, out_dir, parallel=True, max_workers=2)
    assert processed == 4
    # txt files created
    assert len(list(out_dir.glob("*.txt"))) == 4
