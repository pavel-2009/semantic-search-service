# Semantic Search Service

[![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-FF4F00?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/pavel-2009/semantic-search-service/ci.yml?label=CI)](https://github.com/pavel-2009/semantic-search-service/actions)

**Semantic movie search service built with Python, Sentence Transformers, Qdrant, FastAPI and Aiogram.**

Search is based on the meaning of a query rather than exact keyword matches. The project covers the full path from data collection and indexing to a REST API and Telegram interface.

> **Status:** portfolio / learning project.

## ✨ Features

- 🔎 Semantic search over movie data
- 🧠 Multilingual text embeddings with [Sentence Transformers](https://www.sbert.net/)
- 🗄️ Vector storage and similarity search with [Qdrant](https://qdrant.tech/)
- 🎯 Metadata filtering by year, rating, genres and countries
- 🌐 Versioned REST API with [FastAPI](https://fastapi.tiangolo.com/)
- 🤖 Telegram interface powered by [Aiogram 3](https://docs.aiogram.dev/)
- 🕷️ Data collection with [Scrapy](https://scrapy.org/) and [Playwright](https://playwright.dev/)
- 🐳 Reproducible local environment with Docker Compose
- 🧪 Automated tests with [pytest](https://docs.pytest.org/)
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
Dense + sparse BGE-M3 encoding
    ↓
Hybrid Qdrant retrieval
    ↓
Metadata filters and BGE reranking
    ↓
Top-K movies
```

The search/indexing pipeline uses the local BGE-M3 model for 1024-dimensional
dense vectors and sparse lexical vectors, followed by the BGE reranker.

## 🧩 Project structure

```text
semantic-search-service/
├── src/
│   ├── backend/                # FastAPI application and API schemas
│   ├── bot/                    # Telegram bot
│   ├── core/                   # configuration and shared dependencies
│   ├── scraper/                # Scrapy project and movie spider
│   └── services/               # indexing and search services
│
├── scripts/                    # pipeline entry points
├── tests/                      # automated tests
├── docker-compose.yml           # Qdrant + scraper + indexer + API + bot
├── Dockerfile.api
├── Dockerfile.bot
├── Dockerfile.indexer
├── Dockerfile.scraper
├── pyproject.toml
├── uv.lock
├── .env.example
└── README.md
```

The `src/` directory intentionally contains the application modules directly. There is no additional `semantic_search_service/` package layer.

## 🔌 API

All application endpoints are exposed under `/api/v1`.

### `GET /api/v1/health`

Returns service health and the number of indexed objects.

```bash
curl http://localhost:8000/api/v1/health
```

### `GET /api/v1/stats`

Returns the Qdrant collection status, number of indexed objects, embedding model and vector dimensionality.

```bash
curl http://localhost:8000/api/v1/stats
```

### `POST /api/v1/search`

Performs semantic movie search. `top_k` accepts 1–100 results. Optional filters support year, rating, genres and countries.

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

The scraper writes raw movie records to `movies.jsonl`. Indexing uses the prepared `movies_enriched.jsonl` dataset, whose records follow the `EnrichedMovie` contract and include prebuilt plot, vibe and entity text. The indexer validates those records line by line, generates vectors and upserts the canonical movie payloads into Qdrant. Invalid lines are logged and skipped.

Each point contains:

- numeric movie ID;
- 1024-dimensional dense plot and vibe embeddings plus a sparse lexical vector;
- payload with title, year, rating, genres, countries, description and poster URL.

The default Qdrant collection is `movies` and the default indexing batch size is `32`.

## 🚀 Quick start

### Prerequisites

For the Docker setup:

- Docker with Docker Compose
- Telegram bot token if you want to run the bot
- PoiskKino API key if you want to run the scraper

The project targets **Python 3.14+** and uses `uv` for dependency management. On
Apple Silicon, run the API, bot and indexer directly on macOS to use the MPS GPU;
Docker Desktop's Linux containers cannot access Apple's MPS device.

Embedding and reranking automatically select PyTorch MPS when it is available.
Verify the backend with `make mps-check`. The indexer uses a smaller batch on
MPS and disables FP16 by default.

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
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=movies
BOT_TOKEN=your_telegram_bot_token
POISKKINO_API_KEY=your_api_key
API_BASE_URL=http://127.0.0.1:8000
```

The `.env` file is read at runtime and is not copied into Docker images.

Install the project dependencies:

```bash
uv sync
```

### Download the reranker model once

The first search uses the `BAAI/bge-reranker-v2-m3` model. Download it before
starting the API so offline model loading can find it:

```bash
make download-reranker
```

### 3. Start Qdrant

```bash
make up
```

This starts only Qdrant in Docker. The API, bot, scraper and indexer run on
macOS, so model inference can use MPS. Indexing is an explicit step rather than
being repeated every time the database starts.

On the first setup, run the scraper if needed, then create the collection and
index the prepared dataset:

```bash
make scraper
make indexer
```

Start the API and bot in separate terminals:

```bash
make api
make bot
```

The bot sends searches to the API instead of loading another copy of both
neural models. The API loads the models on the first search; health and
statistics endpoints use Qdrant directly and do not load them.

Services exposed locally:

| Service | Address |
|---|---|
| FastAPI | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| Qdrant | `http://localhost:6333` |

To run the complete application in Docker instead, use the optional
`container-app` profile. This is a CPU path on macOS; it does not use MPS:

```bash
docker compose build reranker-downloader
docker compose --profile model-download run --rm --no-deps reranker-downloader
docker compose --profile container-app up --build
```

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
make api
```

Run the bot:

```bash
make bot
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

The test suite is split into unit, integration and performance tests. Integration and performance tests require Docker and start an isolated Qdrant instance automatically through the project's Docker Compose definition. Integration tests use a single real embedding model for the whole test session; the API and indexer run in-process.

The default test command runs only unit tests and does not require Docker:

```bash
make test
```

Run all tests, including integration and performance:

```bash
make test-all
```

Unit tests only (same as `make test`):

```bash
make test-unit
```

Integration tests only:

```bash
make test-integration
```

Performance tests only:

```bash
make test-performance
```

Coverage:

```bash
make test-cov
```

Run the unit-test checks:

```bash
make check
```

Integration tests are intentionally not run with pytest-xdist because they share one isolated Qdrant collection and real model session.

## 🔐 Configuration

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://127.0.0.1:8000` | API URL used by the Telegram bot |
| `QDRANT_HOST` | `localhost` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION` | `movies` | Vector collection name |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Legacy Sentence Transformer loader setting |
| `EMBEDDING_DIM` | `384` | Legacy Sentence Transformer loader setting |
| `MAX_TEXT_LENGTH` | `2000` | Maximum indexed text length |
| `BATCH_SIZE` | `32` | Indexing batch size |
| `LOG_LEVEL` | `INFO` | Application log level |
| `POISKKINO_API_KEY` | empty | API key for data collection |
| `BOT_TOKEN` | empty | Telegram bot token |

## 🐳 Docker architecture

The default Docker Compose environment contains only Qdrant. This keeps model
inference on the macOS host, where PyTorch can use MPS. The optional
`container-app` profile contains the full CPU-based Docker pipeline:

1. **qdrant** — vector database;
2. **scraper** — collects source data;
3. **indexer** — creates embeddings and fills Qdrant;
4. **api** — serves the REST API;
5. **bot** — runs the Telegram interface.

Qdrant data is persisted in the `qdrant_storage` Docker volume. The host-native
bot shares the API process's model instances instead of allocating duplicates.

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
| Dependency management | uv |

## 📄 License

No license file is currently included in the repository. If this project is intended for public reuse, add an appropriate open-source license.

## 👤 Author

**Pavel** — [@pavel-2009](https://github.com/pavel-2009)

[Repository](https://github.com/pavel-2009/semantic-search-service)