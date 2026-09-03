"""Integration tests for FastAPI against real Qdrant and embeddings."""

import pytest


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/health", {"status": "healthy", "indexed_items": 3}),
        ("/api/v1/stats", {"total_points": 3, "embedding_dim": 384}),
    ],
)
def test_service_info(api_client, path, expected):
    response = api_client.get(path)

    assert response.status_code == 200
    data = response.json()
    assert all(data[key] == value for key, value in expected.items())
    assert data["collection"] == "test_movies"


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "", "top_k": 5},
        {"query": "a" * 501, "top_k": 5},
    ],
)
def test_search_validation(api_client, payload):
    assert api_client.post("/api/v1/search", json=payload).status_code == 422


def test_search_and_filters(api_client):
    response = api_client.post(
        "/api/v1/search",
        json={"query": "interstellar", "top_k": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["query"] == "interstellar"
    assert data["total"] > 0
    assert data["results"]

    response = api_client.post(
        "/api/v1/search",
        json={
            "query": "drama",
            "top_k": 5,
            "filters": {
                "year": {"gte": 2010},
                "rating": {"gte": 7.0},
                "genre": ["drama"],
            },
        },
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert all(
        movie["year"] >= 2010
        and movie["rating"] >= 7.0
        and "drama" in movie["genres"]
        for movie in results
    )

    response = api_client.post(
        "/api/v1/search",
        json={
            "query": "anything",
            "top_k": 5,
            "filters": {"year": {"gte": 2030}},
        },
    )
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["total"] == 0


@pytest.mark.parametrize(
    ("movie_id", "status", "title"),
    [(1, 200, "Inception"), (999, 404, None)],
)
def test_movie_details(api_client, movie_id, status, title):
    response = api_client.get(f"/api/v1/movies/{movie_id}")

    assert response.status_code == status
    if title is not None:
        assert response.json()["title"] == title
        assert response.json()["id"] == movie_id
