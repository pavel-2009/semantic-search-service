"""Common pytest fixtures for all tests"""

import pytest
from pathlib import Path
import json
import tempfile
from unittest.mock import Mock, patch


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
            "poster_url": "https://example.com/poster.jpg"
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
            "poster_url": None
        }
    ]

@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file with movie data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_movie_data, f, ensure_ascii=False, indent=2)
        yield Path(f.name)

    Path(f.name).unlink(missing_ok=True)

@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for unit tests."""
    with patch('core.qdrant_client.QdrantClientSingleton.get_client') as mock:
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
            "description": "A thief who steals corporate secrets"
        }

        result = Mock()
        result.points = [point]
        client.query_points.return_value = result

        mock.return_value = client
        yield client

@pytest.fixture
def mock_embedding_model():
    """Mock SentenceTransformer model."""
    with patch('core.model_loader.ModelLoader.get_model') as mock:
        model = Mock()

        model.encode.return_value = [0.0] * 384
        mock.return_value = model
        yield model

@pytest.fixture
def test_collection_name():
    """Return a unique collection name for tests."""
    return "test_movies"
