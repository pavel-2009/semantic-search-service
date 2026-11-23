.PHONY: up down up-containers observability api bot scraper indexer download-reranker otel grafana jaeger prometheus locust mps-check test test-unit test-integration test-performance test-all test-cov test-parallel test-quick clean check

test: test-unit

recall:
	uv run python -m test_recall

precision:
	uv run python -m test_precision

indexer:
	QDRANT_HOST=localhost uv run python -m scripts.run_indexer

scraper:
	uv run python -m scripts.run_scraper

api:
	QDRANT_HOST=localhost \
	OTEL_EXPORTER_OTLP_ENDPOINT=$${OTEL_EXPORTER_OTLP_ENDPOINT:-http://127.0.0.1:4318/v1/metrics} \
	OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=$${OTEL_EXPORTER_OTLP_TRACES_ENDPOINT:-http://127.0.0.1:4318/v1/traces} \
	uv run uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

bot:
	QDRANT_HOST=localhost uv run python -m src.bot.main

download-reranker:
	uv run python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-reranker-v2-m3')"

otel:
	docker compose up otel-collector

observability:
	docker compose up -d jaeger otel-collector prometheus grafana

grafana:
	docker compose up grafana

jaeger:
	docker compose up jaeger

prometheus:
	docker compose up prometheus

locust:
	docker compose --profile load-test up locust

mps-check:
	uv run python -c "import torch; print(f'PyTorch {torch.__version__}; MPS available={torch.backends.mps.is_available()}'); assert torch.backends.mps.is_available(), 'PyTorch MPS is unavailable'; print((torch.ones(1, device='mps') + 1).cpu().item())"

m ?= auto commit

commit:
	git add .
	git commit -m "$(m)"

push:
	git push

up:
	docker compose up -d

up-containers:
	docker compose --profile container-app up --build

down:
	docker compose down

# Tests (Docker-dependent suites run only when explicitly requested)
tests: test-unit

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v

test-performance:
	uv run pytest tests/performance -v

test-all:
	uv run pytest tests -v

test-cov:
	uv run pytest tests --cov=src --cov-report=term-missing

test-parallel:
	uv run pytest tests/performance -n 0 -v

test-quick:
	uv run pytest tests/unit -m "not slow" -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov

check: test-unit
