PY=python3

.PHONY: install fmt lint test build

install:
	pip install -e .

fmt:
	black .

lint:
	ruff check .

test:
	pytest -q

build:
	$(PY) -m build
