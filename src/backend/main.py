"""Entry point for FastAPI application."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from opentelemetry import Fast

from src.backend.api.info_router import router as info_router
from src.backend.api.search_router import router as search_router
from src.core.config import settings
from src.core.dependencies import get_qdrant_repository
from src.core.logger import get_logger, setup_logging
from src.core.telemetry import (
    http_request_duration_ms,
    http_requests_total,
    init_telemetry,
    shutdown_telemetry,
)


setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize dependencies early so startup errors include their full context."""
    init_telemetry(
        service_name=settings.OTEL_SERVICE_NAME,
        service_version=settings.OTEL_SERVICE_VERSION,
        otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT or None,
        console_export=settings.OTEL_CONSOLE_EXPORT,
    )
    logger.info(
        "Starting Semantic Search API: collection=%s qdrant=%s:%s model=%s device=%s log_level=%s",
        settings.QDRANT_COLLECTION,
        settings.QDRANT_HOST,
        settings.QDRANT_PORT,
        settings.EMBEDDING_MODEL,
        settings.COMPUTE_DEVICE,
        settings.LOG_LEVEL.upper(),
    )
    started_at = perf_counter()
    try:
        repository = get_qdrant_repository()
        logger.info("Checking Qdrant collection during startup: %s", settings.QDRANT_COLLECTION)
        stats = repository.get_stats()
        points_count = stats.points_count
        if points_count == 0:
            logger.warning("Collection is empty! Indexer may have failed.")
    except Exception:
        logger.critical(
            "API startup failed; see traceback below for the failing stage", exc_info=True
        )
        raise

    logger.info(
        "API startup complete: collection=%s points=%s duration_ms=%.1f",
        stats.collection,
        points_count,
        (perf_counter() - started_at) * 1000,
    )
    try:
        yield
    finally:
        logger.info("Shutting down Semantic Search API")
        shutdown_telemetry()


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
    """Log every request, record HTTP metrics, and preserve tracebacks on failures."""
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        logger.exception(
            "Unhandled request error: method=%s path=%s", request.method, request.url.path
        )
        raise
    finally:
        duration_ms = (perf_counter() - started_at) * 1000
        attrs = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
        }
        http_requests_total.add(1, attrs)
        http_request_duration_ms.record(duration_ms, attrs)

    logger.info(
        "HTTP request completed: method=%s path=%s status=%d duration_ms=%.1f",
        request.method,
        request.url.path,
        status_code,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe JSON response for unexpected exceptions."""
    logger.exception("Unhandled exception: path=%s", request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(search_router)
app.include_router(info_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Return service metadata and main API routes."""
    return {
        "service": "Semantic Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "search": "/api/v1/search",
        "movie": "/api/v1/movies/{movie_id}",
    }
