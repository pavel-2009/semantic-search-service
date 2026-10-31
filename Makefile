.PHONY: up down test test-unit test-integration test-performance test-all test-cov test-parallel test-quick clean check

up:
	docker compose up --build

down:
	docker compose down

# Tests (Docker-dependent suites run only when explicitly requested)
test: test-unit

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v

test-performance:
	uv run pytest tests/performance -v

test-all:
	uv run pytest tests -v

test-cov:
	uv run pytest tests --cov=src --cov-report=html --cov-report=term

test-parallel:
	uv run pytest tests/performance -n 0 -v

test-quick:
	uv run pytest tests/unit -m "not slow" -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov

check: test-unit
