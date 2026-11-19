FROM python:3.14-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
COPY scripts ./scripts

RUN uv sync --frozen --no-dev

ENV PYTHONPATH=/app/src



FROM base AS api
CMD ["uv", "run", "--no-sync", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS bot
CMD ["uv", "run", "--no-sync", "python", "-m", "bot.main"]

FROM base AS indexer
CMD ["uv", "run", "--no-sync", "python", "scripts/run_indexer.py"]

FROM base AS scraper
CMD ["uv", "run", "--no-sync", "python", "scripts/run_scraper.py"]
