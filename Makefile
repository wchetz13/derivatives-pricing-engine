.PHONY: install test lint format typecheck check serve docker

install:
	pip install -e ".[dev]"

test:
	pytest --cov

lint:
	ruff format --check src tests
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

typecheck:
	mypy

check: lint typecheck test

serve:
	uvicorn pricing_engine.api:app --reload

docker:
	docker build -t pricing-engine .
	docker run --rm -p 8000:8000 pricing-engine
