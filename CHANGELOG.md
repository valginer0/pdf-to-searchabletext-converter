# Changelog

All notable changes to this project will be documented in this file.

## Unreleased
### Added
- Streaming generator `PDFToTextConverter.iter_pages()` to process PDFs page-by-page.
- Asynchronous helper `PDFToTextConverter.extract_text_async()` which off-loads page OCR to a process or thread pool for multi-core utilisation.
- Internal helpers `_render_page`, `_ocr_page`, `_write_output` for cleaner codebase.
- Comprehensive unit-test suite covering utils, converter edge-cases, streaming and async paths, batch conversion, and CLI help.
