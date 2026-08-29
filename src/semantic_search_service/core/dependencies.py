"""Application-level shared dependencies."""

from functools import lru_cache

from semantic_search_service.backend.services.search_service import SearchService


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Return the shared SearchService instance."""
    return SearchService()
