"""Asynchronous API client based on httpx"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from typing import Any, Dict


class APIClient:
    def __init__(self, token: str):
        self.client = httpx.AsyncClient(
            base_url="https://kinopoiskapiunofficial.tech/api/v2.2",
            headers={"X-API-KEY": token},
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def search_movies(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Films search with a key word"""
        response: httpx.Response = await self.client.get(
            "films",
            params={"query": query, "page": page, "limit": 50}
        )

        response.raise_for_status()
        return response.json()

    
