"""Entry point for FastAPI application."""

import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.api.info_router import get_info_service, router as info_router
from backend.api.search_router import router as search_router
from core.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize dependencies early so startup errors include their full context."""
    logger.info(
        "Starting Semantic Search API: collection=%s qdrant=%s:%s model=%s log_level=%s",
        settings.QDRANT_COLLECTION,
        settings.QDRANT_HOST,
        settings.QDRANT_PORT,
        settings.EMBEDDING_MODEL,
        settings.LOG_LEVEL.upper(),
    )
    started_at = perf_counter()
    try:
        service = get_info_service()
        logger.info("Checking Qdrant collection during startup: %s", settings.QDRANT_COLLECTION)
        stats = service.get_stats()
        if stats["total_points"] == 0:
            logger.warning("⚠️ Collection is empty! Indexer may have failed.")
    except Exception:
        logger.critical(
            "API startup failed; see traceback below for the failing stage", exc_info=True
        )
        raise

    logger.info(
        "API startup complete: collection=%s points=%s duration_ms=%.1f",
        stats["collection"],
        stats["total_points"],
        (perf_counter() - started_at) * 1000,
    )
    try:
        yield
    finally:
        logger.info("Shutting down Semantic Search API")


app = FastAPI(
    title="Semantic Search API",
    description="Семантический поиск по фильмам с Qdrant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)


@app.middleware("http")
async def log_http_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log every request and preserve a traceback for unexpected API failures."""
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled request error: method=%s path=%s", request.method, request.url.path
        )
        raise

    logger.info(
        "HTTP request completed: method=%s path=%s status=%d duration_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        (perf_counter() - started_at) * 1000,
    )
    return response


app.include_router(search_router)
app.include_router(info_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "Semantic Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "search": "/api/v1/search",
        "movie": "/api/v1/movies/{movie_id}",
    }
