"""Search API routes."""

import logging
from functools import lru_cache
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException

from backend.schemas import SearchRequest, SearchResponse
from backend.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@lru_cache
def get_search_service() -> SearchService:
    """Return the shared search service instance."""
    logger.info("Creating shared SearchService instance")
    return SearchService()


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Run semantic movie search."""
    started_at = perf_counter()
    logger.info(
        "Search request received: query=%r top_k=%d filters=%s",
        request.query,
        request.top_k,
        request.filters is not None,
    )
    try:
        results = service.search(request)
        response = SearchResponse(
            success=True,
            query=request.query,
            total=len(results),
            results=results,
        )
        logger.info(
            "Search request completed: results=%d duration_ms=%.1f",
            len(results),
            (perf_counter() - started_at) * 1000,
        )
        return response
    except Exception as exc:
        logger.exception("Search endpoint failed")
        raise HTTPException(status_code=500, detail="Search request failed; see server logs") from exc
