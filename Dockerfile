FROM python:3.14-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY scripts ./scripts

RUN uv sync --no-dev

ENV PYTHONPATH=/app/src

# API
FROM ./Dockerfile.api AS api

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Bot
FROM ./Dockerfile.bot AS bot

CMD ["uv", "run", "python", "-m", "bot.main"]

# Indexer
FROM ./Dockerfile.indexer AS indexer

CMD ["uv", "run", "python", "scripts/run_indexer.py"]

# Scraper
FROM ./Dockerfile.scraper AS scraper

CMD ["uv", "run", "python", "scripts/run_scraper.py"]