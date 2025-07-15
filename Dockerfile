# Dockerfile for pdf2text
# Builds a minimal image with all system and Python requirements pre-installed.

FROM python:3.11-slim AS base

LABEL maintainer="Valery Giner <ginerv@yahoo.com)"
LABEL description="Convert scanned PDF files to searchable text using Tesseract and Poppler."

# -----------------------------------------------------------------------------
# System-level dependencies: Tesseract OCR + Poppler (for pdftoppm)
# -----------------------------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Python dependencies & project code
# -----------------------------------------------------------------------------
WORKDIR /app

COPY pyproject.toml requirements-dev.txt README.md LICENSE /app/
# Copy source to install after dep resolution
COPY pdf2text /app/pdf2text

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[dev]" || pip install --no-cache-dir .

# Optionally copy CLI entrypoints if needed (nothing extra here)

# Default command: use CLI wrapper.
ENTRYPOINT ["pdf2text"]

# Example usage:
#   docker build -t pdf2text .
#   docker run --rm -v $(pwd)/data:/data pdf2text /data/sample.pdf -v
