PY = python -m

.PHONY: lint test build release

lint:
	@echo "Running ruff & mypy..."
	ruff check pdf2text tests
	mypy pdf2text

test:
	pytest -q

build:
	$(PY) build

release: lint test build
	@echo "Ready to upload dist/* to PyPI"
