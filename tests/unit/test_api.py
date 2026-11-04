"""Tests for the FastAPI routes using a lightweight mock search service."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import MovieResult, SearchRequest, StatsResponse
from core.dependencies import get_search_service


class MockSearchService:
    """Return representative API data or fail selected service operations."""

    collection_name = "movies"

    def __init__(self, failing_operations: set[str] | None = None) -> None:
        self.failing_operations = failing_operations or set()

    def _fail_if_configured(self, operation: str) -> None:
        if operation in self.failing_operations:
            raise RuntimeError(f"{operation} failed")

    def search(self, request: SearchRequest) -> list[MovieResult]:
        self._fail_if_configured("search")
        return [
            MovieResult(
                id=42,
                title="Интерстеллар",
                year=2014,
                rating=8.7,
                genres=["фантастика", "драма"],
                countries=["США", "Великобритания"],
                director="Кристофер Нолан",
                actors=["Мэттью Макконахи"],
                description="Путешествие через космос и время.",
                poster_url="https://example.test/interstellar.jpg",
                score=0.95,
            )
        ]

    def get_by_id(self, movie_id: int) -> MovieResult | None:
        self._fail_if_configured("get_by_id")
        if movie_id != 42:
            return None
        return self.search(SearchRequest(query="интерстеллар"))[0]

    def get_stats(self) -> StatsResponse:
        self._fail_if_configured("get_stats")
        return StatsResponse(
            collection=self.collection_name,
            total_points=25,
            status="green",
            model="test-embedding-model",
            embedding_dim=384,
        )


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    service = MockSearchService()
    monkeypatch.setitem(app.dependency_overrides, get_search_service, lambda: service)
    yield TestClient(app)


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
                "director": "Кристофер Нолан",
                "actors": ["Мэттью Макконахи"],
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


def test_health_returns_healthy_status(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "collection": "movies",
        "indexed_items": 25,
    }


def test_stats_returns_collection_statistics(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/stats")

    assert response.status_code == 200
    assert response.json() == {
        "collection": "movies",
        "total_points": 25,
        "status": "green",
        "model": "test-embedding-model",
        "embedding_dim": 384,
    }


def test_movie_route_returns_movie_and_not_found_response(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/movies/42")

    assert response.status_code == 200
    assert response.json()["id"] == 42
    assert response.json()["title"] == "Интерстеллар"

    not_found = api_client.get("/api/v1/movies/999")
    assert not_found.status_code == 404
    assert not_found.json() == {"detail": "Movie not found"}


@pytest.mark.parametrize(
    ("operation", "method", "path", "expected_status", "expected_detail"),
    [
        ("search", "post", "/api/v1/search", 500, "Search request failed; see server logs"),
        ("get_stats", "get", "/api/v1/health", 503, "Vector database is unavailable"),
        ("get_stats", "get", "/api/v1/stats", 503, "Vector database is unavailable"),
        ("get_by_id", "get", "/api/v1/movies/42", 500, "Failed to load movie information"),
    ],
)
def test_routes_return_error_responses_when_service_fails(
    operation: str,
    method: str,
    path: str,
    expected_status: int,
    expected_detail: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MockSearchService({operation})
    monkeypatch.setitem(app.dependency_overrides, get_search_service, lambda: service)
    client = TestClient(app)
    if method == "post":
        response = client.post(path, json={"query": "фильмы про космос"})
    else:
        response = client.get(path)

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
