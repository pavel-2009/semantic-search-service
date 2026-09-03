"""Shared pytest fixtures."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.main import app
from core.config import settings
from core.dependencies import get_search_service
from core.model_loader import ModelLoader
from core.qdrant_client import QdrantClientSingleton
from services.indexer import Indexer


@pytest.fixture
def sample_movie_data():
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
def temp_json_file(tmp_path, sample_movie_data):
    path = tmp_path / "movies.json"
    path.write_text(json.dumps(sample_movie_data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def mock_qdrant_client():
    with patch("core.qdrant_client.QdrantClientSingleton.get_client") as get_client:
        client = Mock()

        collection = Mock(points_count=100, status="green")
        client.get_collection.return_value = collection

        point = Mock(
            id=1,
            score=0.95,
            payload={
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
            },
        )
        client.query_points.return_value = Mock(points=[point])
        client.retrieve.return_value = [point]
        client.get_collections.return_value = Mock(collections=[Mock(name="movies")])

        get_client.return_value = client
        yield client


@pytest.fixture
def mock_embedding_model():
    with patch("core.model_loader.ModelLoader.get_model") as get_model:
        model = Mock()
        model.encode.return_value = np.zeros(384)
        get_model.return_value = model
        yield model


@pytest.fixture(scope="session")
def qdrant_container():
    """Start the test Qdrant through the same Compose environment as the project."""
    env = os.environ.copy()
    env["QDRANT_PORT"] = "6334"
    project = "semantic-search-tests"

    subprocess.run(
        ["docker", "compose", "-p", project, "up", "-d", "--wait", "qdrant"],
        check=True,
        env=env,
    )
    yield
    subprocess.run(
        ["docker", "compose", "-p", project, "down", "--remove-orphans"],
        check=True,
        env=env,
    )


@pytest.fixture(scope="function")
def qdrant_test_client(qdrant_container):
    client = QdrantClient(host="localhost", port=6334)
    collection_name = "test_movies"

    client.delete_collection(collection_name=collection_name, timeout=10) if client.collection_exists(collection_name) else None
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )

    yield client, collection_name

    client.delete_collection(collection_name=collection_name, timeout=10)
    client.close()


@pytest.fixture
scope="session"
def integration_model():
    return ModelLoader.get_model()


@pytest.fixture
def test_movie_data():
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


@pytest.fixture
def test_movies_file(tmp_path, test_movie_data):
    path = tmp_path / "movies.json"
    path.write_text(json.dumps(test_movie_data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def indexed_integration(qdrant_test_client, test_movies_file, integration_model, monkeypatch):
    client, collection_name = qdrant_test_client
    monkeypatch.setattr(settings, "QDRANT_COLLECTION", collection_name)
    monkeypatch.setattr(settings, "QDRANT_PORT", 6334)
    monkeypatch.setattr(QdrantClientSingleton, "_instance", client)
    monkeypatch.setattr(ModelLoader, "get_model", lambda: integration_model)

    Indexer().index_movies(test_movies_file, batch_size=2)
    get_search_service.cache_clear()
    yield client, collection_name
    get_search_service.cache_clear()


@pytest.fixture
def api_client(indexed_integration):
    with TestClient(app) as client:
        yield client
