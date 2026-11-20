"""Service and movie information API routes."""

from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from src.backend.schemas import HealthResponse, MovieResult, StatsResponse
from src.core.config import settings
from src.core.dependencies import get_qdrant_repository
from src.core.logger import get_logger
from src.repositories.qdrant_repository import QdrantRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["info"])
QdrantRepositoryDependency = Annotated[
    QdrantRepository,
    Depends(get_qdrant_repository),
]


@router.get("/health", response_model=HealthResponse)
async def health_check(repository: QdrantRepositoryDependency) -> HealthResponse:
    """Check API and vector database health."""
    started_at = perf_counter()
    logger.info("Health check started")
    try:
        stats = await run_in_threadpool(repository.get_stats)
        points_count = stats.points_count
        if points_count == 0:
            logger.warning("Qdrant collection exists but is empty")
            return HealthResponse(
                status="degraded",
                collection=stats.collection,
                indexed_items=0,
            )

        response = HealthResponse(
            status="healthy",
            collection=stats.collection,
            indexed_items=points_count,
        )
        logger.info(
            "Health check completed: status=%s indexed_items=%d duration_ms=%.1f",
            response.status,
            response.indexed_items,
            (perf_counter() - started_at) * 1000,
        )
        return response

    except Exception as exc:
        logger.exception("Health check failed while accessing Qdrant")
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc


@router.get("/movies/{movie_id}", response_model=MovieResult)
async def get_movie(
    movie_id: int,
    repository: QdrantRepositoryDependency,
) -> MovieResult:
    """Return detailed information about a movie by its ID."""
    started_at = perf_counter()
    logger.info("Movie info request received: movie_id=%d", movie_id)
    try:
        points = await run_in_threadpool(
            repository.client.retrieve,
            collection_name=repository.collection_name,
            ids=[movie_id],
            with_payload=True,
            with_vectors=False,
        )
        movie = (
            None
            if not points or not points[0].payload
            else MovieResult.model_validate({**points[0].payload, "score": 0.0})
        )
    except Exception as exc:
        logger.exception("Movie info endpoint failed: movie_id=%d", movie_id)
        raise HTTPException(status_code=500, detail="Failed to load movie information") from exc

    if movie is None:
        logger.info("Movie not found: movie_id=%d", movie_id)
        raise HTTPException(status_code=404, detail="Movie not found")

    logger.info(
        "Movie info request completed: movie_id=%d duration_ms=%.1f",
        movie_id,
        (perf_counter() - started_at) * 1000,
    )
    return movie


@router.get("/stats", response_model=StatsResponse)
async def get_stats(repository: QdrantRepositoryDependency) -> StatsResponse:
    """Return vector collection statistics."""
    started_at = perf_counter()
    logger.info("Stats request started")
    try:
        stats = await run_in_threadpool(repository.get_stats)
        response = StatsResponse(
            collection=stats.collection,
            total_points=stats.points_count,
            status=stats.status,
            model=settings.EMBEDDING_MODEL,
            embedding_dim=settings.EMBEDDING_DIM,
        )
    except Exception as exc:
        logger.exception("Stats request failed while accessing Qdrant")
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc

    logger.info(
        "Stats request completed: collection=%s points=%d duration_ms=%.1f",
        response.collection,
        response.total_points,
        (perf_counter() - started_at) * 1000,
    )
    return response
