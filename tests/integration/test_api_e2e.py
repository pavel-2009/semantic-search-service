"""End-to-end tests for the FastAPI routes."""

from fastapi.testclient import TestClient

from src.core.config import settings
from src.core.contracts import Movie


def test_health_stats_search_and_movie_endpoints(
    api_client: TestClient,
    seeded_movie: Movie,
) -> None:
    health = api_client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "healthy",
        "collection": "test_movies",
        "indexed_items": 1,
    }

    stats = api_client.get("/api/v1/stats")
    assert stats.status_code == 200
    assert stats.json() == {
        "collection": "test_movies",
        "total_points": 1,
        "status": "green",
        "model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIM,
    }

    search = api_client.post(
        "/api/v1/search",
        json={"query": "фильм про космос", "top_k": 5},
    )
    assert search.status_code == 200
    search_body = search.json()
    assert search_body["success"] is True
    assert search_body["query"] == "фильм про космос"
    assert search_body["total"] == 1
    assert search_body["results"][0]["id"] == seeded_movie.id
    assert search_body["results"][0]["title"] == seeded_movie.title
    assert search_body["results"][0]["score"] == 1.0

    movie_response = api_client.get(f"/api/v1/movies/{seeded_movie.id}")
    assert movie_response.status_code == 200
    assert movie_response.json()["id"] == seeded_movie.id
    assert movie_response.json()["title"] == seeded_movie.title
    assert movie_response.json()["score"] == 0.0
