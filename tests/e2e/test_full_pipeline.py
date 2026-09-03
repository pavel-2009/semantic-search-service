"""End-to-end tests for the complete pipeline."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.search_service import SearchService
from core.dependencies import get_search_service
from core.config import settings
from services.indexer import Indexer


class TestFullPipeline:
    """Test the complete pipeline from indexing to search."""

    def test_full_pipeline_flow(self, qdrant_test_client, test_movies_file):
        """Test: Indexing -> Search -> Get by ID."""
        client, collection_name = qdrant_test_client
        
        with patch('core.config.settings.QDRANT_COLLECTION', collection_name):
            with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=client):
                with patch('core.model_loader.ModelLoader.get_model') as mock_model:
                    from sentence_transformers import SentenceTransformer
                    real_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    mock_model.return_value = real_model
                    
                    indexer = Indexer()
                    indexer.collection_name = collection_name
                    indexer.index_movies(test_movies_file, batch_size=2)
                    
                    stats = indexer.get_stats()
                    assert stats.points_count == 3
                    
                    with patch('core.dependencies.get_search_service') as mock_service:
                        service = SearchService()
                        service.collection_name = collection_name
                        service.qdrant = client
                        service.model = real_model
                        mock_service.return_value = service
                        
                        with TestClient(app) as test_client:
                            response = test_client.post(
                                "/api/v1/search",
                                json={"query": "dream technology", "top_k": 2}
                            )
                            assert response.status_code == 200
                            data = response.json()
                            assert data["success"] is True
                            assert data["total"] > 0
                            
                            titles = [r["title"] for r in data["results"]]
                            assert "Inception" in titles
                            
                            movie_id = data["results"][0]["id"]
                            response = test_client.get(f"/api/v1/movies/{movie_id}")
                            assert response.status_code == 200
                            movie = response.json()
                            assert movie["id"] == movie_id
                            assert "description" in movie
                            assert movie["title"] == "Inception"

    def test_search_with_filters_e2e(self, qdrant_test_client, test_movies_file):
        """E2E test: Search with filters."""
        client, collection_name = qdrant_test_client
        
        with patch('core.config.settings.QDRANT_COLLECTION', collection_name):
            with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=client):
                with patch('core.model_loader.ModelLoader.get_model') as mock_model:
                    from sentence_transformers import SentenceTransformer
                    real_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    mock_model.return_value = real_model
                    
                    indexer = Indexer()
                    indexer.collection_name = collection_name
                    indexer.index_movies(test_movies_file, batch_size=2)
                    
                    with patch('core.dependencies.get_search_service') as mock_service:
                        service = SearchService()
                        service.collection_name = collection_name
                        service.qdrant = client
                        service.model = real_model
                        mock_service.return_value = service
                        
                        with TestClient(app) as test_client:
                            response = test_client.post(
                                "/api/v1/search",
                                json={
                                    "query": "space",
                                    "top_k": 3,
                                    "filters": {
                                        "year": {"gte": 2010},
                                        "rating": {"gte": 8.5},
                                        "genre": ["drama"]
                                    }
                                }
                            )
                            assert response.status_code == 200
                            data = response.json()
                            assert data["success"] is True
                            
                            for movie in data["results"]:
                                assert movie["year"] >= 2010
                                assert movie["rating"] >= 8.5
                                assert "drama" in movie["genres"] or "драма" in movie["genres"]

    def test_health_and_stats_e2e(self, qdrant_test_client, test_movies_file):
        """E2E test: Health and stats endpoints."""
        client, collection_name = qdrant_test_client
        
        with patch('core.config.settings.QDRANT_COLLECTION', collection_name):
            with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=client):
                with patch('core.model_loader.ModelLoader.get_model') as mock_model:
                    from sentence_transformers import SentenceTransformer
                    real_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    mock_model.return_value = real_model
                    
                    indexer = Indexer()
                    indexer.collection_name = collection_name
                    indexer.index_movies(test_movies_file, batch_size=2)
                    
                    with patch('core.dependencies.get_search_service') as mock_service:
                        service = SearchService()
                        service.collection_name = collection_name
                        service.qdrant = client
                        service.model = real_model
                        mock_service.return_value = service
                        
                        with TestClient(app) as test_client:
                            response = test_client.get("/api/v1/health")
                            assert response.status_code == 200
                            data = response.json()
                            assert data["status"] == "healthy"
                            assert data["indexed_items"] == 3
                            assert data["collection"] == collection_name
                            
                            response = test_client.get("/api/v1/stats")
                            assert response.status_code == 200
                            data = response.json()
                            assert data["total_points"] == 3
                            assert data["collection"] == collection_name
                            assert data["model"] == settings.EMBEDDING_MODEL
                            assert data["embedding_dim"] == 384

    def test_movie_details_not_found(self, qdrant_test_client, test_movies_file):
        """E2E test: Movie not found."""
        client, collection_name = qdrant_test_client
        
        with patch('core.config.settings.QDRANT_COLLECTION', collection_name):
            with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=client):
                with patch('core.model_loader.ModelLoader.get_model') as mock_model:
                    from sentence_transformers import SentenceTransformer
                    real_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    mock_model.return_value = real_model
                    
                    indexer = Indexer()
                    indexer.collection_name = collection_name
                    indexer.index_movies(test_movies_file, batch_size=2)
                    
                    with patch('core.dependencies.get_search_service') as mock_service:
                        service = SearchService()
                        service.collection_name = collection_name
                        service.qdrant = client
                        service.model = real_model
                        mock_service.return_value = service
                        
                        with TestClient(app) as test_client:
                            response = test_client.get("/api/v1/movies/999")
                            assert response.status_code == 404

    def test_scraper_contract_integration(self, tmp_path, monkeypatch):
        """Test that scraper produces valid movies."""
        monkeypatch.setenv("POISKKINO_API_KEY", "test_key")
        
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        with patch('scraper.pipelines.DATA_FILE', data_dir / "movies.json"):
            from scraper.schemas import Movie
            
            test_movie = Movie(
                id=123,
                title="Test Movie",
                year=2024,
                rating=7.5,
                genres=["test", "drama"],
                country="Testland",
                director="Test Director",
                description="Test description",
                actors=["Actor 1", "Actor 2"]
            )
            
            assert test_movie.id == 123
            assert test_movie.title == "Test Movie"
            assert test_movie.year == 2024
            assert test_movie.rating == 7.5
            assert len(test_movie.genres) == 2
            assert "test" in test_movie.genres
            assert len(test_movie.actors) == 2
            assert test_movie.country == "Testland"
            assert test_movie.director == "Test Director"
            
            movie_dict = test_movie.model_dump()
            assert movie_dict["id"] == 123
            assert movie_dict["title"] == "Test Movie"
            
            restored = Movie.model_validate(movie_dict)
            assert restored.id == test_movie.id
            assert restored.title == test_movie.title

    def test_complete_flow_with_empty_search(self, qdrant_test_client, test_movies_file):
        """E2E test: Search that returns no results."""
        client, collection_name = qdrant_test_client
        
        with patch('core.config.settings.QDRANT_COLLECTION', collection_name):
            with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=client):
                with patch('core.model_loader.ModelLoader.get_model') as mock_model:
                    from sentence_transformers import SentenceTransformer
                    real_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    mock_model.return_value = real_model
                    
                    indexer = Indexer()
                    indexer.collection_name = collection_name
                    indexer.index_movies(test_movies_file, batch_size=2)
                    
                    with patch('core.dependencies.get_search_service') as mock_service:
                        service = SearchService()
                        service.collection_name = collection_name
                        service.qdrant = client
                        service.model = real_model
                        mock_service.return_value = service
                        
                        with TestClient(app) as test_client:
                            response = test_client.post(
                                "/api/v1/search",
                                json={"query": "xyz123nonexistent", "top_k": 5}
                            )
                            assert response.status_code == 200
                            data = response.json()
                            assert data["success"] is True
                            assert data["total"] == 0
                            assert data["results"] == []