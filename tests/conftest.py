"""Common pytest fixtures for all tests."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import docker
import numpy as np
import pytest
import requests
from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastapi.testclient import TestClient

from backend.main import app
from core.config import settings
from core.dependencies import get_search_service
from core.model_loader import ModelLoader
from core.qdrant_client import QdrantClientSingleton
from services.indexer import Indexer


@pytest.fixture
def sample_movie_data():
    """Sample movie data for testing."""
    return [
        {
            "id": 1,
            "title": "Inception",
            "description": "A thief who steals corporate secrets",
            "year": 2010,
            "rating": 8.8,
            "genres": ["sci-fi", "thriller"],
            "country": "USA",
            "director": "Christopher Nolan",
            "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
            "poster_url": "https://example.com/poster.jpg",
        },
        {
            "id": 2,
            "title": "The Dark Knight",
            "description": "Batman faces the Joker",
            "year": 2008,
            "rating": 9.0,
            "genres": ["action", "crime"],
            "country": "USA",
            "director": "Christopher Nolan",
            "actors": ["Christian Bale", "Heath Ledger"],
            "poster_url": None,
        },
    ]


@pytest.fixture
def temp_json_file(sample_movie_data):
    """Create a temporary JSON file with movie data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
        json.dump(sample_movie_data, file, ensure_ascii=False, indent=2)
        file.flush()
        path = Path(file.name)

    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for unit tests."""
    with patch("core.qdrant_client.QdrantClientSingleton.get_client") as mock:
        client = Mock()

        collection_info = Mock()
        collection_info.points_count = 100
        collection_info.status = "green"
        client.get_collection.return_value = collection_info

        point = Mock()
        point.id = 1
        point.score = 0.95
        point.payload = {
            "id": 1,
            "title": "Inception",
            "year": 2010,
            "rating": 8.8,
            "genres": ["sci-fi", "thriller"],
            "countries": ["USA"],
            "director": "Christopher Nolan",
            "actors": ["Leonardo DiCaprio"],
            "description": "A thief who steals corporate secrets",
            "poster_url": "https://example.com/poster.jpg",
        }
        result = Mock()
        result.points = [point]
        client.query_points.return_value = result
        client.retrieve.return_value = [point]

        collection_obj = Mock()
        collection_obj.name = "movies"
        collections_response = Mock()
        collections_response.collections = [collection_obj]
        client.get_collections.return_value = collections_response

        mock.return_value = client
        yield client


@pytest.fixture
def mock_embedding_model():
    """Mock SentenceTransformer model."""
    with patch("core.model_loader.ModelLoader.get_model") as mock:
        model = Mock()
        model.encode.return_value = np.array([0.0] * 384)
        mock.return_value = model
        yield model


@pytest.fixture
def test_collection_name():
    """Return a unique collection name for tests."""
    return "test_movies"


@pytest.fixture(scope="session")
def qdrant_container():
    """Run Qdrant in Docker for integration tests."""
    client = docker.from_env()

    try:
        container = client.containers.get("test-qdrant")
        if container.status == "running":
            yield container
            return
    except docker.errors.NotFound:
        pass

    container = client.containers.run(
        "qdrant/qdrant:latest",
        ports={"6333/tcp": 6334},
        detach=True,
        remove=True,
        name="test-qdrant",
        environment={"QDRANT__LOG_LEVEL": "ERROR"},
    )

    for _ in range(30):
        try:
            response = requests.get("http://localhost:6334/health", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)

    yield container
    container.stop()


@pytest.fixture
def test_movie_data():
    """Movie data shared by integration tests."""
    return [
        {
            "id": 1,
            "title": "Inception",
            "description": "A thief who steals corporate secrets using dream invasion technology",
            "year": 2010,
            "rating": 8.8,
            "genres": ["sci-fi", "thriller"],
            "country": "USA",
            "countries": ["USA"],
            "director": "Christopher Nolan",
            "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
            "poster_url": "https://example.com/inception.jpg",
        },
        {
            "id": 2,
            "title": "The Dark Knight",
            "description": "Batman faces the Joker in Gotham City",
            "year": 2008,
            "rating": 9.0,
            "genres": ["action", "crime", "drama"],
            "country": "USA",
            "countries": ["USA"],
            "director": "Christopher Nolan",
            "actors": ["Christian Bale", "Heath Ledger"],
            "poster_url": "https://example.com/dark_knight.jpg",
        },
        {
            "id": 3,
            "title": "Interstellar",
            "description": "A team of explorers travel through a wormhole in space",
            "year": 2014,
            "rating": 8.6,
            "genres": ["sci-fi", "adventure", "drama"],
            "country": "USA",
            "countries": ["USA"],
            "director": "Christopher Nolan",
            "actors": ["Matthew McConaughey", "Anne Hathaway"],
            "poster_url": "https://example.com/interstellar.jpg",
        },
    ]


@pytest.fixture(scope="function")
def qdrant_test_client(qdrant_container):
    """Create an isolated Qdrant collection for one integration test."""
    client = QdrantClient(host="localhost", port=6334)
    collection_name = "test_movies"

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )

    yield client, collection_name

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


@pytest.fixture(scope="session")
def integration_model():
    """Load the real embedding model once for integration tests."""
    return ModelLoader.get_model()


@pytest.fixture
def indexed_integration(qdrant_test_client, test_movies_file, integration_model, monkeypatch):
    """Prepare a real Qdrant collection with test movies before each integration test."""
    client, collection_name = qdrant_test_client

    monkeypatch.setattr(settings, "QDRANT_COLLECTION", collection_name)
    monkeypatch.setattr(QdrantClientSingleton, "_instance", client)
    monkeypatch.setattr(ModelLoader, "get_model", lambda: integration_model)

    indexer = Indexer()
    indexer.index_movies(test_movies_file, batch_size=2)

    get_search_service.cache_clear()
    yield client, collection_name
    get_search_service.cache_clear()


@pytest.fixture
def api_client(indexed_integration):
    """FastAPI client backed by an indexed test collection."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def test_movies_file(tmp_path, test_movie_data):
    """Create a temporary JSON file with integration-test movies."""
    file_path = tmp_path / "test_movies.json"
    file_path.write_text(
        json.dumps(test_movie_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return file_path
