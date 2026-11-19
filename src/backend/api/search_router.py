"""Search API routes."""

from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from src.backend.schemas import SearchRequest, SearchResponse
from src.services.search_service.search_service import SearchService
from src.services.search_service.schemas import SearchQuery
from src.core.dependencies import get_search_service
from src.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])
SearchServiceDependency = Annotated[SearchService, Depends(get_search_service)]


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    service: SearchServiceDependency,
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
        results = await run_in_threadpool(
            service.search,
            SearchQuery(text=request.query, top_k=request.top_k),
        )
        if hasattr(results, "documents"):
            results = results.documents
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
