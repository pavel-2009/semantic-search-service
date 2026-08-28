"""Fast API routers"""

import logging
from functools import lru_cache
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException

from semantic_search_service.backend.schemas import (
    HealthResponse,
    SearchRequest,
    SearchResponse,
    StatsResponse,
)
from semantic_search_service.backend.services.search_service import SearchService


router = APIRouter(prefix="/api/v1", tags=["search"])
logger = logging.getLogger(__name__)


@lru_cache
def get_search_service() -> SearchService:
    """Return the shared search service instance."""
    logger.info("Creating shared SearchService instance")
    return SearchService()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    search_service: SearchService = Depends(get_search_service)
) -> HealthResponse:
    """Checking App health"""
    started_at = perf_counter()
    logger.info("Health check started")

    try:
        stats = search_service.get_stats()
    except Exception as exc:
        logger.exception("Health check failed while accessing Qdrant")
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc

    response = HealthResponse(
        status="healthy" if stats["total_points"] > 0 else "degraded",
        collection=stats["collection"],
        indexed_items=stats["total_points"],
    )
    logger.info("Health check completed: status=%s indexed_items=%d duration_ms=%.1f", response.status, response.indexed_items, (perf_counter() - started_at) * 1000)
    return response


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    service: SearchService = Depends(get_search_service)
) -> StatsResponse:
    """Collection stats"""
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
    logger.info("Stats request completed: collection=%s points=%d duration_ms=%.1f", response.collection, response.total_points, (perf_counter() - started_at) * 1000)
    return response


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """Семантический поиск по фильмам"""
    started_at = perf_counter()
    logger.info("Search request received: query=%r top_k=%d filters=%s", request.query, request.top_k, request.filters is not None)
    try:
        results = service.search(request)
        response = SearchResponse(
            success=True,
            query=request.query,
            total=len(results),
            results=results,
        )
        logger.info("Search request completed: results=%d duration_ms=%.1f", len(results), (perf_counter() - started_at) * 1000)
        return response
    except Exception as exc:
        logger.exception("Search endpoint failed")
        raise HTTPException(status_code=500, detail="Search request failed; see server logs") from exc
