"""Lightweight CLI smoke tests using subprocess and monkeypatched internals."""
import sys
import subprocess
from pathlib import Path
import pytest


@pytest.fixture
def dummy_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "dummy.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%EOF")
    return pdf


@pytest.mark.skipif(sys.platform.startswith("win"), reason="WSL path hackery on Windows shells")
def test_cli_help_runs(monkeypatch):
    """`pdf2text --help` should exit 0 and print usage with mocks injected."""
    # Patch internals so CLI doesn't touch binaries when parser instantiates converter
    monkeypatch.setattr(
        "pdf2text.converter.pytesseract.get_tesseract_version", lambda: "5.0"
    )
    monkeypatch.setattr(
        "pdf2text.converter.convert_from_path", lambda *a, **kw: []
    )

    res = subprocess.run(
        [sys.executable, "-m", "pdf2text.cli", "--help"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "Convert scanned PDF files" in res.stdout
