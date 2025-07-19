"""pdf2text package.

Exposes the high-level PDFToTextConverter API and package metadata.
"""

from importlib import metadata as _metadata  # Python ≥3.8

from .converter import PDFToTextConverter

__all__ = [
    "PDFToTextConverter",
    "__version__",
]

try:
    __version__: str = _metadata.version("pdf2text-ocr")
except _metadata.PackageNotFoundError:  # running from source / editable install
    __version__ = "0.0.0.dev0"
