"""Tests for the FastAPI routes using a lightweight mock search service."""

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.schemas import MovieResult
from src.services.search_service.schemas import SearchQuery
from src.core.dependencies import get_qdrant_repository, get_search_service
from src.core.contracts import IndexerStats
from src.core.config import settings


@pytest.fixture
def api_client() -> Iterator[TestClient]:
    service = MockSearchService()
    repository = MockQdrantRepository()
    app.dependency_overrides[get_search_service] = lambda: service
    app.dependency_overrides[get_qdrant_repository] = lambda: repository
    client = TestClient(app)
    client.app.state.mock_search_service = service
    yield client
    app.dependency_overrides.clear()


class MockQdrantRepository:
    """Provide Qdrant statistics and movie data without creating a model."""

    collection_name = "movies"

    def __init__(self) -> None:
        self.client = Mock()
        self.client.retrieve.side_effect = self._retrieve

    def get_stats(self) -> IndexerStats:
        return IndexerStats(
            collection=self.collection_name,
            points_count=25,
            status="green",
        )

    @staticmethod
    def _retrieve(*, ids: list[int], **_: object) -> list[SimpleNamespace]:
        if ids != [42]:
            return []
        return [
            SimpleNamespace(
                payload={
                    "id": 42,
                    "title": "Интерстеллар",
                    "year": 2014,
                    "rating": 8.7,
                    "genres": ["фантастика", "драма"],
                    "countries": ["США", "Великобритания"],
                    "description": "Путешествие через космос и время.",
                    "poster_url": "https://example.test/interstellar.jpg",
                }
            )
        ]


class MockSearchService:
    """Return representative API data or fail selected service operations."""

    collection_name = "movies"

    def __init__(self, failing_operations: set[str] | None = None) -> None:
        self.failing_operations = failing_operations or set()
        self.last_request: SearchQuery | None = None

    def _fail_if_configured(self, operation: str) -> None:
        if operation in self.failing_operations:
            raise RuntimeError(f"{operation} failed")

    def search(self, request: SearchQuery) -> list[MovieResult]:
        self.last_request = request
        self._fail_if_configured("search")
        return [
            MovieResult(
                id=42,
                title="Интерстеллар",
                year=2014,
                rating=8.7,
                genres=["фантастика", "драма"],
                countries=["США", "Великобритания"],
                description="Путешествие через космос и время.",
                poster_url="https://example.test/interstellar.jpg",
                score=0.95,
            )
        ]

    def get_by_id(self, movie_id: int) -> MovieResult | None:
        self._fail_if_configured("get_by_id")
        if movie_id != 42:
            return None
        return self.search(SearchQuery(text="интерстеллар"))[0]


def test_root_returns_service_metadata(api_client: TestClient) -> None:
    response = api_client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Semantic Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "search": "/api/v1/search",
        "movie": "/api/v1/movies/{movie_id}",
    }


def test_search_returns_results_in_api_contract(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/search",
        json={"query": "фильмы про космос", "top_k": 5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "query": "фильмы про космос",
        "total": 1,
        "results": [
            {
                "id": 42,
                "title": "Интерстеллар",
                "year": 2014,
                "rating": 8.7,
                "genres": ["фантастика", "драма"],
                "countries": ["США", "Великобритания"],
                "description": "Путешествие через космос и время.",
                "poster_url": "https://example.test/interstellar.jpg",
                "score": 0.95,
            }
        ],
    }


def test_search_rejects_invalid_request(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/search", json={"query": "", "top_k": 5})

    assert response.status_code == 422
    assert response.json()["detail"]


def test_search_forwards_explicit_metadata_filters(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/search",
        json={
            "query": "космос",
            "top_k": 5,
            "filters": {
                "year": {"gte": 2000, "lte": 2020},
                "rating": {"gte": 7.5},
            },
        },
    )

    assert response.status_code == 200
    request = api_client.app.state.mock_search_service.last_request
    assert request is not None
    assert request.filters == {
        "year_gte": 2000,
        "year_lte": 2020,
        "rating_gte": 7.5,
    }


def test_health_returns_healthy_status(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        app.dependency_overrides,
        get_search_service,
        lambda: pytest.fail("health checks must not initialize search models"),
    )

    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "collection": "movies",
        "indexed_items": 25,
    }


def test_stats_returns_collection_statistics(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        app.dependency_overrides,
        get_search_service,
        lambda: pytest.fail("stats requests must not initialize search models"),
    )

    response = api_client.get("/api/v1/stats")

    assert response.status_code == 200
    assert response.json() == {
        "collection": "movies",
        "total_points": 25,
        "status": "green",
        "model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIM,
    }


def test_movie_route_returns_movie_and_not_found_response(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/movies/42")

    assert response.status_code == 200
    assert response.json()["id"] == 42
    assert response.json()["title"] == "Интерстеллар"

    not_found = api_client.get("/api/v1/movies/999")
    assert not_found.status_code == 404
    assert not_found.json() == {"detail": "Movie not found"}
