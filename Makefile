.PHONY: up down test test-unit test-integration test-all test-cov lint type-check format clean

up:
	docker compose up --build

down:
	docker compose down

# Tests
test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v

test-e2e:
	uv run pytest tests/e2e -v

test-cov:
	uv run pytest tests/ --cov=src --cov-report=html --cov-report=term

test-parallel:
	uv run pytest tests/ -n auto -v

test-quick:
	uv run pytest tests/ -m "not slow" -v

lint:
	uv run ruff check .

type-check:
	uv run pyright

format:
	uv run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov

# All checks
check: lint type-check test-unit
	@echo "✅ All checks passed!"