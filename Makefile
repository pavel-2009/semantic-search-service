.PHONY: up down test test-unit test-integration test-all test-cov test-parallel test-quick lint type-check format clean check

up:
	docker compose up --build

down:
	docker compose down

# Tests
test:
	uv run pytest tests -v

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v

test-all: test-unit test-integration

test-cov:
	uv run pytest tests --cov=src --cov-report=html --cov-report=term

test-parallel:
	uv run pytest tests/performance -n 0 -v

test-quick:
	uv run pytest tests -m "not slow" -v

lint:
	uv run ruff check src scripts

type-check:
	uv run pyright

format:
	uv run ruff format src scripts

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov

check: lint type-check test-unit
	@echo "All checks passed!"
