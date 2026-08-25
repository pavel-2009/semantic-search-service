"""Fast API routers"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from typing import Dict, Any

from semantic_search_service.backend.schemas import (
    SearchRequest,
    SearchResponse,
    HealthResponse,
    StatsResponse,
)
from semantic_search_service.backend.services.search_service import SearchService


router = APIRouter(prefix="/api/v1", tags=["search"])

# Dependency
def get_search_service() -> SearchService:
    return SearchService()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    search_service: SearchService = Depends(get_search_service)
) -> HealthResponse:
    """Checking App health"""

    stats = search_service.get_stats()
    return HealthResponse(
        status="healthy" if stats["total_points"] > 0 else "degraded",
        collection=stats["collection"],
        indexed_items=stats["total_points"],
    )
