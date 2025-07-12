from pathlib import Path

import pytest

from pdf2text import PDFToTextConverter


@pytest.mark.skip("Requires sample PDF + external deps")
def test_basic_extract(tmp_path: Path):
    conv = PDFToTextConverter()
    sample_pdf = Path(__file__).parent / "data" / "sample.pdf"
    if not sample_pdf.exists():
        pytest.skip("Sample PDF missing")
    out = tmp_path / "out.txt"
    text = conv.extract_text_from_pdf(sample_pdf, out, dpi=72)
    assert out.exists()
    assert len(text) > 0
