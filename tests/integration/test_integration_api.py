"""Integration tests for FastAPI endpoints."""


def test_health_endpoint(api_client):
    """Health check reports the indexed test collection."""
    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["indexed_items"] == 3
    assert "collection" in data


def test_stats_endpoint(api_client):
    """Stats expose the indexed collection and model configuration."""
    response = api_client.get("/api/v1/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_points"] == 3
    assert "collection" in data
    assert "model" in data
    assert data["embedding_dim"] == 384


def test_search_endpoint_basic(api_client):
    """Basic semantic search returns indexed movies."""
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


def test_search_with_filters(api_client):
    """Search endpoint applies metadata filters."""
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
    data = response.json()
    assert data["success"] is True
    assert all(
        movie["year"] >= 2010
        and movie["rating"] >= 7.0
        and "drama" in movie["genres"]
        for movie in data["results"]
    )


def test_search_empty_query(api_client):
    """Empty search queries are rejected by validation."""
    response = api_client.post(
        "/api/v1/search",
        json={"query": "", "top_k": 5},
    )

    assert response.status_code == 422


def test_search_too_long_query(api_client):
    """Overlong search queries are rejected by validation."""
    response = api_client.post(
        "/api/v1/search",
        json={"query": "a" * 501, "top_k": 5},
    )

    assert response.status_code == 422


def test_movie_details(api_client):
    """Movie details are available for indexed and missing IDs."""
    response = api_client.get("/api/v1/movies/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Inception"

    response = api_client.get("/api/v1/movies/999")
    assert response.status_code == 404
