"""HTTP client for delegating bot searches to the API process."""

import httpx

from src.backend.schemas import MovieResult
from src.core.config import settings


class SearchApiClient:
    """Call the API without loading duplicate models in the bot process."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.API_BASE_URL.rstrip("/"),
                timeout=60,
            )
        return self._client

    async def search(self, query: str, top_k: int = 10) -> list[MovieResult]:
        """Search through the API and parse its results."""
        response = await self.client.post(
            "/api/v1/search",
            json={"query": query, "top_k": top_k},
        )
        response.raise_for_status()
        return [
            MovieResult.model_validate(result)
            for result in response.json()["results"]
        ]

    async def get_movie(self, movie_id: int) -> MovieResult | None:
        """Fetch a movie through the API, returning None when it is absent."""
        response = await self.client.get(f"/api/v1/movies/{movie_id}")
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        response.raise_for_status()
        return MovieResult.model_validate(response.json())

    async def close(self) -> None:
        """Close the pooled HTTP connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


api_client = SearchApiClient()
