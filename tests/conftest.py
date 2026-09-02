"""Common pytest fixtures for all tests"""

import pytest
from pathlib import Path
import json
import tempfile
from unittest.mock import Mock, patch
import numpy as np
import docker
from qdrant_client import QdrantClient
from qdrant_client.http import models
import time
import requests


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
def temp_json_file(sample_movie_data):
    """Create a temporary JSON file with movie data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_movie_data, f, ensure_ascii=False, indent=2)
        f.flush()
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
            "description": "A thief who steals corporate secrets",
            "poster_url": "https://example.com/poster.jpg"
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
    with patch('core.model_loader.ModelLoader.get_model') as mock:
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
    """Запускает Qdrant в Docker для интеграционных тестов."""
    client = docker.from_env()
    
    # Проверяем, есть ли уже запущенный контейнер
    try:
        container = client.containers.get("test-qdrant")
        if container.status == "running":
            yield container
            return
    except docker.errors.NotFound:
        pass
    
    # Запускаем новый контейнер
    container = client.containers.run(
        "qdrant/qdrant:latest",
        ports={"6333/tcp": 6334},  # используем другой порт, чтобы не мешать основному
        detach=True,
        remove=True,
        name="test-qdrant",
        environment={"QDRANT__LOG_LEVEL": "ERROR"}
    )
    
    # Ждём, пока Qdrant запустится
    for _ in range(30):
        try:
            response = requests.get("http://localhost:6334/health")
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    
    yield container
    
    # Останавливаем контейнер после тестов
    container.stop()

@pytest.fixture(scope="function")
def qdrant_test_client(qdrant_container):
    """Создаёт клиент Qdrant для тестов."""
    client = QdrantClient(host="localhost", port=6334)
    
    # Создаём тестовую коллекцию
    test_collection = "test_movies"
    
    # Удаляем, если существует
    try:
        client.delete_collection(test_collection)
    except Exception:
        pass
    
    # Создаём новую
    client.create_collection(
        collection_name=test_collection,
        vectors_config=models.VectorParams(
            size=384,
            distance=models.Distance.COSINE,
        )
    )
    
    yield client, test_collection
    
    # Чистим после теста
    try:
        client.delete_collection(test_collection)
    except Exception:
        pass

@pytest.fixture
def test_movie_data():
    """Тестовые данные для интеграционных тестов."""
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
            "poster_url": "https://example.com/inception.jpg"
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
            "poster_url": "https://example.com/dark_knight.jpg"
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
            "poster_url": "https://example.com/interstellar.jpg"
        }
    ]

@pytest.fixture
def test_movies_file(tmp_path, test_movie_data) -> str:
    """Создаёт временный JSON файл с тестовыми данными."""
    file_path = tmp_path / "test_movies.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(test_movie_data, f, ensure_ascii=False, indent=2)
    return file_path
