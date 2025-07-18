# pdf2text

Convert scanned PDF files into searchable plain-text using 100 % free and open-source software (Poppler + Tesseract).

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## Installation

### Via Docker

```bash
# Option A – build the image locally
docker build -t pdf2text .

# Option B – pull the latest pre-built image from GHCR
docker pull ghcr.io/valginer0/pdf2text:latest

# convert a single PDF (mount a host folder) and write the text next to it
# The -o flag ensures the output ends up in the mounted folder.
docker run --rm -v $(pwd)/data:/data ghcr.io/valginer0/pdf2text:latest /data/sample.pdf -o /data/sample.txt -v

# Alternatively mount the project root as the working directory so the default
# output path works (the default WORKDIR inside the image is /app).
docker run --rm -v $(pwd):/app -w /app ghcr.io/valginer0/pdf2text:latest data/sample.pdf -v
```

### From source

```bash
# End-users (from PyPI)
pip install pdf2text

# From source (editable)
pip install -e .

# Optional extras
pip install -e .[progress,rich]    # progress bar + rich logging
**Why are these extras optional?**  `tqdm` (progress) and `rich` are great in
  interactive terminals, but they add extra dependencies and ANSI control
  sequences that can clutter plain log files.  Keeping them optional keeps the
  core install lightweight, and lets you skip them in headless environments
  (CI, Docker, systemd services) or when embedding `pdf2text` in another
  application that provides its own UI.

### Conda quick-start

```bash
# Everything in one go: Python, Poppler, Tesseract, pdf2text
conda env create -f environment.yaml
conda activate pdf2text

# Optional editable/dev install for contributors
pip install -e .[dev]
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

# Multi-language OCR (English + Spanish)
pdf2text input.pdf --lang eng+spa -o output.txt

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
| `--lang`            | Tesseract language codes (`eng`, `eng+deu`, …) |
| `--tesseract-path`  | Path to `tesseract` executable (Windows)       |
| `--version`         | Print program version and exit                |

## Python API

```python
from pdf2text import PDFToTextConverter

conv = PDFToTextConverter()
# Traditional full-extract
# Tip: pass `log_level=logging.DEBUG` to the constructor to enable verbose logging from library code (same as `-v` flag in the CLI).
text = conv.extract_text_from_pdf("scan.pdf", enhance=True, lang="eng+spa")

# Stream pages one-by-one (memory-efficient for large PDFs)
for page_num, page_text in conv.iter_pages("scan.pdf", enhance=True):
    print(page_num, len(page_text))

# Asynchronous multi-core extraction
import asyncio
full_text = asyncio.run(conv.extract_text_async("scan.pdf"))
```

## Development

```bash
# using pip / venv
pip install -e .[dev]
# or, if you used the Conda env above, just run:
pytest -q
