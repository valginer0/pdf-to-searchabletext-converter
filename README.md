# pdf2text

Convert scanned PDF files into searchable plain-text using 100 % free and open-source software (Poppler + Tesseract).

---

## Installation

```bash
# Python ≥3.9
pip install -e .            # from repo root (editable)  
# OR install from PyPI (once published)
# pip install pdf2text

# Optional progress bar support
pip install "pdf2text[progress]"
```

System requirements:

| OS          | Poppler install command                | Tesseract install command                    |
|-------------|----------------------------------------|----------------------------------------------|
| Debian/Ubuntu | `sudo apt install poppler-utils`       | `sudo apt install tesseract-ocr`             |
| macOS       | `brew install poppler`                  | `brew install tesseract`                     |
| Windows     | [Poppler-Windows binaries](https://github.com/oschwartz10612/poppler-windows) | [UB Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki) |

## CLI Usage

```bash
# Convert a single file
pdf2text input.pdf -o output.txt

# Batch convert all PDFs inside a folder
pdf2text /path/to/folder -b -o /path/to/out_dir

# Higher resolution & progress bar
pdf2text input.pdf --dpi 300 --enhance
```

### Arguments

| Flag                | Description                                    |
|---------------------|------------------------------------------------|
| `input`             | Input PDF file **or** folder                   |
| `-o`, `--output`    | Output txt file or folder                      |
| `-b`, `--batch`     | Treat input as folder and process all PDFs     |
| `--dpi`             | DPI for rasterisation (default 200)            |
| `--enhance`         | Apply basic image enhancement before OCR       |
| `--tesseract-path`  | Path to `tesseract` executable (Windows)       |

## Python API

```python
from pdf2text import PDFToTextConverter

conv = PDFToTextConverter()
text = conv.extract_text_from_pdf("scan.pdf", enhance=True)
```

## Development

```bash
pip install -r requirements-dev.txt   # ruff, pytest, etc.
pytest -q
```
