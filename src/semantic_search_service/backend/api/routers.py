"""Fast API routers"""

from fastapi import APIRouter, HTTPException, Depends

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

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    service: SearchService = Depends(get_search_service)
) -> StatsResponse:
    """Collection stats"""
    stats = service.get_stats()
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
        raise HTTPException(status_code=500, detail=str(e))
