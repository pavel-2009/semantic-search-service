"""Fast API routers"""

import logging
from functools import lru_cache

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

# Dependency
@lru_cache
def get_search_service() -> SearchService:
    logger.info("Creating shared SearchService instance")
    return SearchService()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    search_service: SearchService = Depends(get_search_service)
) -> HealthResponse:
    """Checking App health"""

    try:
        stats = search_service.get_stats()
    except Exception as exc:
        logger.exception("Health check failed while accessing Qdrant")
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc
    return HealthResponse(
        status="healthy" if stats["total_points"] > 0 else "degraded",
        collection=stats["collection"],
        indexed_items=stats["total_points"],
    )

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    service: SearchService = Depends(get_search_service)
) -> StatsResponse:
    """Collection stats"""
    try:
        stats = service.get_stats()
    except Exception as exc:
        logger.exception("Stats request failed while accessing Qdrant")
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc
    return StatsResponse(
        collection=stats["collection"],
        total_points=stats["total_points"],
        status=stats["status"],
        model=stats["model"],
        embedding_dim=stats["embedding_dim"],
    )


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """Семантический поиск по фильмам"""
    try:
        results = service.search(request)
        return SearchResponse(
            success=True,
            query=request.query,
            total=len(results),
            results=results,
        )
    except Exception as e:
        logger.exception("Search endpoint failed")
        raise HTTPException(status_code=500, detail="Search request failed; see server logs") from e
