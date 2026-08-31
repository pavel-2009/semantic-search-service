"""Movie information and service information routes."""

import logging
from functools import lru_cache
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException

from backend.schemas import MovieResult, StatsResponse
from backend.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["info"])


@lru_cache
def get_info_service() -> SearchService:
    """Return the shared search service instance."""
    logger.info("Creating shared SearchService instance for info routes")
    return SearchService()


@router.get("/movies/{movie_id}", response_model=MovieResult)
async def get_movie(
    movie_id: int,
    service: SearchService = Depends(get_info_service),
) -> MovieResult:
    """Return detailed information about a movie by its ID."""
    started_at = perf_counter()
    logger.info("Movie info request received: movie_id=%d", movie_id)
    try:
        movie = service.get_by_id(movie_id)
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
async def get_stats(
    service: SearchService = Depends(get_info_service),
) -> StatsResponse:
    """Return vector collection statistics."""
    started_at = perf_counter()
    logger.info("Stats request started")
    try:
        stats = service.get_stats()
    except Exception as exc:
        logger.exception("Stats request failed while accessing Qdrant")
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc

    response = StatsResponse(
        collection=stats["collection"],
        total_points=stats["total_points"],
        status=stats["status"],
        model=stats["model"],
        embedding_dim=stats["embedding_dim"],
    )
    logger.info(
        "Stats request completed: collection=%s points=%d duration_ms=%.1f",
        response.collection,
        response.total_points,
        (perf_counter() - started_at) * 1000,
    )
    return response
