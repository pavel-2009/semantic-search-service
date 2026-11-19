"""Service and movie information API routes."""

from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from src.backend.schemas import HealthResponse, MovieResult, StatsResponse
from src.services.search_service.search_service import SearchService
from src.services.indexer.indexer import Indexer
from src.services.indexer.config import config
from src.core.dependencies import get_search_service
from src.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["info"])
SearchServiceDependency = Annotated[SearchService, Depends(get_search_service)]


def get_info_service() -> SearchService:
    """Return the shared search service instance."""
    return get_search_service()


@router.get("/health", response_model=HealthResponse)
async def health_check(service: SearchServiceDependency) -> HealthResponse:
    """Check API and vector database health."""
    started_at = perf_counter()
    logger.info("Health check started")
    try:
        if hasattr(service, "get_stats"):
            stats = await run_in_threadpool(service.get_stats)
        else:
            stats = await run_in_threadpool(Indexer().get_stats)
        points_count = getattr(stats, "points_count", getattr(stats, "total_points", 0))
        if points_count == 0:
            logger.warning("Qdrant collection exists but is empty")
            return HealthResponse(
                status="degraded",
                collection=service.collection_name,
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
async def get_movie(movie_id: int, service: SearchServiceDependency) -> MovieResult:
    """Return detailed information about a movie by its ID."""
    started_at = perf_counter()
    logger.info("Movie info request received: movie_id=%d", movie_id)
    try:
        if hasattr(service, "get_by_id"):
            movie = await run_in_threadpool(service.get_by_id, movie_id)
        else:
            points = await run_in_threadpool(
                service.qdrant_repo.client.retrieve,
                collection_name=service.qdrant_repo.collection_name,
                ids=[movie_id],
                with_payload=True,
                with_vectors=False,
            )
            movie = None if not points or not points[0].payload else MovieResult.model_validate(
                {**points[0].payload, "score": 0.0}
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
async def get_stats(service: SearchServiceDependency) -> StatsResponse:
    """Return vector collection statistics."""
    started_at = perf_counter()
    logger.info("Stats request started")
    try:
        if hasattr(service, "get_stats"):
            response = await run_in_threadpool(service.get_stats)
        else:
            stats = await run_in_threadpool(Indexer().get_stats)
            response = StatsResponse(
                collection=stats.collection,
                total_points=stats.points_count,
                status=stats.status,
                model=config.model_name,
                embedding_dim=config.dense_dim,
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
