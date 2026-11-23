# Semantic Search Service

[![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-FF4F00?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)

**Semantic movie search built with Python, BGE-M3, Qdrant, FastAPI and Aiogram.**

The service collects movie data, indexes dense and sparse representations, retrieves candidates with hybrid search and reranks them. It exposes the same search API to HTTP clients and a Telegram bot.

> Portfolio / learning project.

## Features

- Multilingual semantic and lexical retrieval with BGE-M3.
- Hybrid dense + sparse search in Qdrant.
- Cross-encoder reranking with BGE Reranker v2 M3.
- Metadata filters by year and rating.
- FastAPI REST API and Aiogram Telegram bot.
- Scrapy data collection with JSONL export.
- Shared configuration for API, bot, scraper and indexer.
- Unit tests in GitHub Actions; integration tests run separately.

## Architecture

```text
PoiskKino API
     |
     v
 Scrapy scraper -----> movies.jsonl
                              |
                              v
                         Indexer
                    BGE-M3 embeddings
                              |
                              v
                           Qdrant
                              ^
                              |
                Hybrid retrieval + filters
                              |
                         Reranker
                              |
                 +------------+------------+
                 |                         |
              FastAPI                 Telegram bot
```

The bot delegates requests to FastAPI; it does not load a second copy of the embedding and reranking models.

## Project layout

```text
src/
  backend/       FastAPI routes and API schemas
  bot/           Telegram bot and HTTP API client
  core/          shared settings, contracts and dependencies
  repositories/  Qdrant access
  scraper/       Scrapy project and JSONL pipeline
  services/
    indexer/     BGE-M3 document embeddings and indexing
    search_service/
                   query parsing, embeddings and reranking
scripts/         scraper and indexer entry points
tests/
  unit/
  integration/
  performance/
eval_dataset/    retrieval and precision evaluation queries
Dockerfile       multi-stage application image
docker-compose.yml
Makefile
pyproject.toml
uv.lock
.env.example
```

## Data and indexing

The scraper writes canonical movie records to `src/scraper/data/movies.jsonl`. The indexer consumes this exact file; there is no separate, manually prepared `movies_enriched.jsonl` dataset.

Precomputed indexing text is optional. When it is absent, the indexer builds its representations from the movie description, moods, title and genres. Invalid JSONL records are logged and skipped. The stored Qdrant payload follows the shared `Movie` contract.

The default collection is `movies`. It contains 1024-dimensional plot and vibe vectors, a sparse lexical vector, and movie metadata fields including year, rating, genres and countries.

## Quick start

### Requirements

- Python 3.14+
- `uv`
- Docker and Docker Compose
- A PoiskKino API key to scrape data
- A Telegram bot token to run the bot

On Apple Silicon, run Python services on macOS to use PyTorch MPS. Docker containers use CPU inference.

### 1. Configure

```bash
git clone https://github.com/pavel-2009/semantic-search-service.git
cd semantic-search-service
cp .env.example .env
uv sync
```

Set the required values in `.env`:

```dotenv
POISKKINO_API_KEY=your_api_key
BOT_TOKEN=your_telegram_bot_token
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=movies
API_BASE_URL=http://127.0.0.1:8000
```

The bot token is read from the environment at runtime. It is not stored in source code or committed to Git. Unit tests do not require a real token.

### 2. Start Qdrant

```bash
make up
```

### 3. Collect and index movies

Run the scraper when you need to refresh the local dataset:

```bash
make scraper
```

Then create the collection and index the same `movies.jsonl` file:

```bash
make indexer
```

The indexer recreates the collection on a full indexing run.

### 4. Start the API and bot

Run each command in a separate terminal:

```bash
make api
make bot
```

The API is available at:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

Download the reranker model before the first search if it is not already cached:

```bash
make download-reranker
```

### Docker

The default Compose setup starts Qdrant only:

```bash
make up
```

To run the full scraper → indexer → API → bot pipeline in containers, download the reranker model into the shared cache once, then start the profile:

```bash
docker compose build reranker-downloader
docker compose --profile model-download run --rm --no-deps reranker-downloader
docker compose --profile container-app up --build
```

The full container profile runs model inference on CPU. Set `POISKKINO_API_KEY` and `BOT_TOKEN` in the host environment or `.env` before starting it.
Traces from the API are available in Jaeger at [http://localhost:16686](http://localhost:16686).

### Search load test

Start the API on the host with `make api`, then start Locust:

```bash
docker compose --profile load-test up locust
```

Open [http://localhost:8089](http://localhost:8089) and set the number of users and spawn rate. The default target is `http://host.docker.internal:8000`; override it with `LOCUST_HOST` if the API runs elsewhere. The Locust scenario sends only `POST /api/v1/search` requests.

## API

All application endpoints use the `/api/v1` prefix.

### `POST /api/v1/search`

```json
{
  "query": "психологический триллер про человека, который теряет связь с реальностью",
  "top_k": 5,
  "filters": {
    "year": {"gte": 2015},
    "rating": {"gte": 7.0}
  }
}
```

Year and rating bounds are combined with AND when both are supplied.

### Other endpoints

- `GET /api/v1/health` — API and Qdrant health.
- `GET /api/v1/stats` — collection size and embedding information.
- `GET /api/v1/movies/{movie_id}` — movie details by ID.

## Telegram bot

- `/start` — show the welcome message.
- Send a text message — search for movies.
- Select a result — load its details.

The bot calls the FastAPI service through `API_BASE_URL`.

## Configuration

All application components read the same settings object from `src.core.config`.

| Variable | Default | Purpose |
|---|---|---|
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION` | `movies` | Collection name |
| `QDRANT_API_KEY` | empty | Optional Qdrant API key |
| `EMBEDDING_MODEL` | `./bge-m3` | Local BGE-M3 model directory |
| `EMBEDDING_DIM` | `1024` | Dense vector dimension |
| `INDEX_BATCH_SIZE` | device-dependent | Indexing batch size |
| `SPARSE_MIN_WEIGHT` | `0.08` | Minimum sparse token weight |
| `MIN_PLOT_LENGTH` | `15` | Minimum plot text length |
| `DATA_PATH` | `src/scraper/data/movies.jsonl` | Shared scraper output and indexer input |
| `POISKKINO_API_KEY` | empty | Scraper API key |
| `BOT_TOKEN` | empty | Telegram bot token |
| `API_BASE_URL` | `http://127.0.0.1:8000` | API URL used by bot |
| `LOG_LEVEL` | `INFO` | Logging level |

## Tests and quality

The default test command and CI run unit tests only; they do not require Docker, external services, or a Telegram token.

```bash
make test
# or
make test-unit
```

Integration and performance suites are opt-in:

```bash
make test-integration
make test-performance
make test-all
make test-cov
```

## Evaluation

The query set in `eval_dataset/recall_dataset.json` contains 65 Russian-language queries over the canonical movie corpus. Run the evaluation scripts separately:

```bash
make recall
make precision
```

## Tech stack

| Area | Technology |
|---|---|
| Language | Python 3.14 |
| API | FastAPI, Pydantic |
| Embeddings | FlagEmbedding, BGE-M3 |
| Reranking | BGE Reranker v2 M3 |
| Vector database | Qdrant |
| Scraping | Scrapy |
| Telegram | Aiogram 3 |
| Runtime | Uvicorn |
| Containers | Docker Compose |
| Tests | pytest |
| Dependency management | uv |

## License

No license file is currently included. Add an open-source license before redistributing the project.

## Author

**Pavel** — [@pavel-2009](https://github.com/pavel-2009)
