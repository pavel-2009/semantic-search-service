.PHONY: up down test lint type-check format

up:
	docker compose up --build

down:
	docker compose down

test:
	uv run pytest

lint:
	uv run ruff check .

type-check:
	uv run pyright

format:
	uv run ruff format .
