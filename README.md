# Semantic Search Service

[![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-FF4F00?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Lint](https://img.shields.io/badge/lint-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![CI](https://img.shields.io/github/actions/workflow/status/pavel-2009/semantic-search-service/ci.yml?label=CI)](https://github.com/pavel-2009/semantic-search-service/actions)

**Semantic movie search service built with Python, Sentence Transformers, Qdrant, FastAPI and Aiogram.**

Search is based on the meaning of a query rather than exact keyword matches. The project covers the full path from data collection and indexing to a REST API and Telegram interface.

> **Status:** portfolio / learning project.

## ✨ Features

- 🔎 Semantic search over movie data
- 🧠 Multilingual text embeddings with [Sentence Transformers](https://www.sbert.net/)
- 🗄️ Vector storage and similarity search with [Qdrant](https://qdrant.tech/)
- 🎯 Metadata filtering by year, rating, genre and country
- 🌐 Versioned REST API with [FastAPI](https://fastapi.tiangolo.com/)
- 🤖 Telegram interface powered by [Aiogram 3](https://docs.aiogram.dev/)
- 🕷️ Data collection with [Scrapy](https://scrapy.org/) and [Playwright](https://playwright.dev/)
- 🐳 Reproducible local environment with Docker Compose
- 🧪 Automated tests with [pytest](https://docs.pytest.org/)
- 🔍 Static analysis and formatting with [Ruff](https://docs.astral.sh/ruff/) and [Pyright](https://microsoft.github.io/pyright/)
- 🔄 CI through GitHub Actions

## 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │      Data Source     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Scraper              │
                         │ Scrapy + Playwright  │
                         └──────────┬───────────┘
                                    │ JSON
                                    ▼
                         ┌──────────────────────┐
                         │ Indexer              │
                         │ Normalization        │
                         │ + embeddings         │
                         └──────────┬───────────┘
                                    │ vectors
                                    ▼
                         ┌──────────────────────┐
                         │ Qdrant               │
                         │ Vector database      │
                         └──────────▲───────────┘
                                    │ similarity search
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
              ▼                                           ▼
     ┌───────────────────┐                       ┌───────────────────┐
     │ FastAPI            │                       │ Telegram Bot      │
     │ REST API           │                       │ Aiogram 3         │
     └─────────┬─────────┘                       └───────────────────┘
               │
               ▼
        JSON search results
```

### Search pipeline

```text
User query
    ↓
Text normalization
    ↓
Sentence Transformer
    ↓
Query embedding (384 dimensions)
    ↓
Qdrant similarity search
    ↓
Metadata filters
    ↓
Top-K movies
```

The default embedding model is `paraphrase-multilingual-MiniLM-L12-v2` with 384-dimensional vectors.

## 🧩 Project structure

```text
semantic-search-service/
├── src/
│   └── semantic_search_service/
│       ├── backend/              # FastAPI application and API schemas
│       ├── bot/                  # Telegram bot
│       ├── core/                 # configuration and shared dependencies
│       ├── scraper/              # Scrapy project and movie spider
│       └── services/              # indexing and search services
│
├── scripts/                     # pipeline entry points
├── tests/                       # automated tests
├── docker-compose.yml            # Qdrant + scraper + indexer + API + bot
├── Dockerfile.api
├── Dockerfile.bot
├── Dockerfile.indexer
├── Dockerfile.scraper
├── pyproject.toml
├── uv.lock
├── .env.example
└── README.md
```

## 🔌 API

All application endpoints are exposed under `/api/v1`.

### `GET /api/v1/health`

Returns service health and the number of indexed objects.

```bash
curl http://localhost:8000/api/v1/health
```

Example response:

```json
{
  "status": "healthy",
  "collection": "movies",
  "indexed_items": 5000
}
```

### `GET /api/v1/stats`

Returns the Qdrant collection status, number of indexed objects, embedding model and vector dimensionality.

```bash
curl http://localhost:8000/api/v1/stats
```

### `POST /api/v1/search`

Performs semantic movie search. `top_k` accepts 1–100 results. Optional filters support year, rating, genre and country.

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "психологический триллер про человека, который теряет связь с реальностью",
    "top_k": 5,
    "filters": {
      "year": {"gte": 2015},
      "rating": {"gte": 7.0},
      "genre": ["триллер"]
    }
  }'
```

Example response shape:

```json
{
  "success": true,
  "query": "психологический триллер про человека, который теряет связь с реальностью",
  "total": 5,
  "results": [
    {
      "id": 123456,
      "title": "Example Movie",
      "year": 2020,
      "rating": 8.1,
      "genres": ["триллер", "драма"],
      "countries": ["США"],
      "director": "Director Name",
      "actors": ["Actor Name"],
      "description": "...",
      "poster_url": null,
      "score": 0.89
    }
  ]
}
```

### Interactive documentation

After starting the API:

- Swagger UI: [`http://localhost:8000/docs`](http://localhost:8000/docs)
- ReDoc: [`http://localhost:8000/redoc`](http://localhost:8000/redoc)

## 🤖 Telegram bot

The bot provides a simple interface for semantic movie search.

- `/start` — start the bot
- Send any text message — use it as a search query
- **Подробнее** — load full information about a selected movie

The bot uses the shared search service and retrieves movie details by ID.

## 📦 Data & indexing

The indexer reads movie data from JSON, builds a searchable text representation from fields such as title, description, director, country, year, rating, actors and genres, generates embeddings and upserts the resulting points into Qdrant.

Each point contains:

- numeric movie ID;
- 384-dimensional embedding;
- payload with title, year, rating, genres, countries, director, actors, description and poster URL.

The default Qdrant collection is `movies` and the default indexing batch size is `32`.

## 🚀 Quick start

### Prerequisites

For the Docker setup:

- Docker with Docker Compose
- Telegram bot token if you want to run the bot
- PoiskKino API key if you want to run the scraper

For local development, the project targets **Python 3.14+** and uses `uv` for dependency management.

### 1. Clone

```bash
git clone https://github.com/pavel-2009/semantic-search-service.git
cd semantic-search-service
```

### 2. Configure environment

```bash
cp .env.example .env
```

Set the required values in `.env`:

```dotenv
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=movies
BOT_TOKEN=your_telegram_bot_token
POISKKINO_API_KEY=your_api_key
```

### 3. Start the full pipeline

```bash
docker compose up --build
```

The Compose stack starts Qdrant, then the scraper and indexer, followed by the API and Telegram bot.

Services exposed locally:

| Service | Address |
|---|---|
| FastAPI | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| Qdrant | `http://localhost:6333` |

### 4. Check the API

```bash
curl http://localhost:8000/api/v1/health
```

## 🛠️ Local development

Install dependencies:

```bash
uv sync --dev
```

Run the API:

```bash
uv run uvicorn src.semantic_search_service.backend.main:app --reload
```

Run the bot:

```bash
uv run python -m src.semantic_search_service.bot.main
```

Run the scraper:

```bash
uv run python scripts/run_scraper.py
```

Run indexing:

```bash
uv run python scripts/run_indexer.py
```

## 🧪 Testing & quality

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run type checking:

```bash
uv run pyright
```

## 🔐 Configuration

| Variable | Default | Description |
|---|---|---|
| `QDRANT_HOST` | `localhost` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION` | `movies` | Vector collection name |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence Transformer model |
| `EMBEDDING_DIM` | `384` | Embedding dimensionality |
| `MAX_TEXT_LENGTH` | `2000` | Maximum indexed text length |
| `BATCH_SIZE` | `32` | Indexing batch size |
| `LOG_LEVEL` | `INFO` | Application log level |
| `POISKKINO_API_KEY` | empty | API key for data collection |
| `BOT_TOKEN` | empty | Telegram bot token |

## 🐳 Docker architecture

The Docker Compose environment contains five services:

1. **qdrant** — vector database;
2. **scraper** — collects source data;
3. **indexer** — creates embeddings and fills Qdrant;
4. **api** — serves the REST API;
5. **bot** — runs the Telegram interface.

Qdrant data is persisted in the `qdrant_storage` Docker volume.

## 🗺️ Roadmap

- [ ] Add production deployment configuration
- [ ] Add benchmark suite for embedding and search latency
- [ ] Add richer ranking / reranking
- [ ] Improve observability with metrics and tracing
- [ ] Expand integration-test coverage
- [ ] Add a dedicated frontend client

## 📚 Tech stack

| Area | Technology |
|---|---|
| Language | Python 3.14+ |
| API | FastAPI, Pydantic |
| Embeddings | Sentence Transformers |
| Vector DB | Qdrant |
| Scraping | Scrapy, Playwright |
| Telegram | Aiogram 3 |
| Runtime | Uvicorn |
| Containers | Docker Compose |
| Testing | pytest |
| Linting / formatting | Ruff |
| Type checking | Pyright |
| Dependency management | uv |

## 📄 License

No license file is currently included in the repository. If this project is intended for public reuse, add an appropriate open-source license.

## 👤 Author

**Pavel** — [@pavel-2009](https://github.com/pavel-2009)

[Repository](https://github.com/pavel-2009/semantic-search-service)
