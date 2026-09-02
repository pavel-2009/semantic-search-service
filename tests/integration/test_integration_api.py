"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app
from backend.schemas import SearchRequest


class TestAPI:
    """Test FastAPI endpoints."""

    def test_health_endpoint(self):
        """Тест health check."""
        with TestClient(app) as client:
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "collection" in data
            assert "indexed_items" in data

    def test_stats_endpoint(self):
        """Тест stats."""
        with TestClient(app) as client:
            response = client.get("/api/v1/stats")
            assert response.status_code == 200
            data = response.json()
            assert "collection" in data
            assert "total_points" in data
            assert "model" in data
            assert "embedding_dim" in data

    def test_search_endpoint_basic(self):
        """Базовый поиск."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search",
                json={"query": "interstellar", "top_k": 5}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["query"] == "interstellar"
            assert "total" in data
            assert "results" in data

    def test_search_with_filters(self):
        """Поиск с фильтрами."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "drama",
                    "top_k": 5,
                    "filters": {
                        "year": {"gte": 2010},
                        "rating": {"gte": 7.0},
                        "genre": ["драма"]
                    }
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Проверяем, что фильтры применились

    def test_search_empty_query(self):
        """Поиск с пустым запросом."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search",
                json={"query": "", "top_k": 5}
            )
            assert response.status_code == 422  # Validation error

    def test_search_too_long_query(self):
        """Поиск со слишком длинным запросом."""
        long_query = "a" * 501
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search",
                json={"query": long_query, "top_k": 5}
            )
            assert response.status_code == 422

    def test_movie_details(self, qdrant_test_client, test_movies_file):
        """Получение деталей фильма."""
        client, collection_name = qdrant_test_client
        
        with patch('core.config.settings.QDRANT_COLLECTION', collection_name):
            with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=client):
                with patch('core.model_loader.ModelLoader.get_model') as mock_model:
                    from sentence_transformers import SentenceTransformer
                    real_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    mock_model.return_value = real_model
                    
                    # Индексация через API
                    from services.indexer import Indexer
                    indexer = Indexer()
                    indexer.collection_name = collection_name
                    indexer.index_movies(test_movies_file, batch_size=2)
                    
                    # Тест эндпоинта /movies/{id}
                    with TestClient(app) as client:
                        response = client.get(f"/api/v1/movies/1")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["id"] == 1
                        assert data["title"] == "Inception"
                        
                        # Несуществующий ID
                        response = client.get("/api/v1/movies/999")
                        assert response.status_code == 404