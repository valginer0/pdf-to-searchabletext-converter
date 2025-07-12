"""Command-line interface wrapping :class:`pdf2text.converter.PDFToTextConverter`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .converter import PDFToTextConverter

_LOG_FORMAT = "% (levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pdf2text",
        description="Convert scanned PDF files to searchable text using free OSS",
    )
    p.add_argument("input", help="Input PDF file or folder")
    p.add_argument("-o", "--output", help="Output .txt file or folder")
    p.add_argument("-b", "--batch", action="store_true", help="Treat input as folder")
    p.add_argument("--tesseract-path", help="Path to tesseract executable")
    p.add_argument("--dpi", type=int, default=200, help="Image DPI (default: 200)")
    p.add_argument("--enhance", action="store_true", help="Enhance images before OCR")
    return p


def main(argv: list[str] | None = None) -> None:  # noqa: D401
    """Program entry point (console-script)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    converter = PDFToTextConverter(tesseract_path=args.tesseract_path)

    try:
        if args.batch:
            out_dir = args.output or f"{args.input}_converted"
            converter.batch_convert(
                args.input, out_dir, dpi=args.dpi, enhance=args.enhance
            )
        else:
            output = (
                args.output
                or f"{Path(args.input).with_suffix('').name}.txt"  # derive if missing
            )
            converter.extract_text_from_pdf(
                args.input, output, dpi=args.dpi, enhance=args.enhance
            )
    except Exception as exc:
        logging.error("Error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
