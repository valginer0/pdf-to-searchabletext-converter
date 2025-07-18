# Changelog

All notable changes to this project will be documented in this file.

## Unreleased
### Added
- Streaming generator `PDFToTextConverter.iter_pages()` to process PDFs page-by-page.
- Asynchronous helper `PDFToTextConverter.extract_text_async()` which off-loads page OCR to a process or thread pool for multi-core utilisation.
- Internal helpers `_render_page`, `_ocr_page`, `_write_output` for cleaner codebase.
- Comprehensive unit-test suite covering utils, converter edge-cases, streaming and async paths, batch conversion, and CLI help.
- `log_level` parameter in `PDFToTextConverter.__init__` for programmatic control of verbosity.
- CLI flags `--lang` (multi-language OCR) and `--version`; converter APIs accept `lang`.
- Exit codes: 0 success, 2 no files converted, ≥1 unexpected error.

### Changed
- `batch_convert` now logs full stack traces in debug mode and only catches specific expected errors, preventing silent failure of unrelated bugs.

### Performance
- new `tesseract_config` (reuse engine), `chunk_size` for multi-page rendering/OCR, and parallel `batch_convert`.
