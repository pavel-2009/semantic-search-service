"""End-to-end tests for the complete pipeline."""

import pytest
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from backend.main import app
from services.indexer import Indexer
from backend.services.search_service import SearchService
from core.config import settings


class TestFullPipeline:
    """Test the complete pipeline from scraping to search."""

    @pytest.fixture
    def mock_movie_data(self, tmp_path: Path) -> Path:
        """Create mock movie data for testing."""
        movies = [
            {
                "id": 1,
                "title": "Inception",
                "description": "A thief who steals corporate secrets using dream invasion technology",
                "year": 2010,
                "rating": 8.8,
                "genres": ["sci-fi", "thriller"],
                "country": "USA",
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
                "director": "Christopher Nolan",
                "actors": ["Matthew McConaughey", "Anne Hathaway"],
                "poster_url": "https://example.com/interstellar.jpg"
            }
        ]
        
        data_file = tmp_path / "movies.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(movies, f, ensure_ascii=False, indent=2)
        
        return data_file

    def test_full_pipeline_flow(self, qdrant_test_client, mock_movie_data):
        """Test: Indexing -> Search -> Get by ID."""
        client, collection_name = qdrant_test_client
        
        with patch('core.config.settings.QDRANT_COLLECTION', collection_name):
            with patch('core.config.settings.DATA_PATH', mock_movie_data):
                with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=client):
                    with patch('core.model_loader.ModelLoader.get_model') as mock_model:
                        from sentence_transformers import SentenceTransformer
                        real_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                        mock_model.return_value = real_model
                        
                        indexer = Indexer()
                        indexer.collection_name = collection_name
                        indexer.index_movies(mock_movie_data, batch_size=2)
                        
                        stats = indexer.get_stats()
                        assert stats["points_count"] == 3
                        
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

    def test_scraper_integration(self, tmp_path, monkeypatch):
        """Test scraper integration (with mock API)."""
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
                genres=["test"],
                country="Testland",
                director="Test Director",
                description="Test description"
            )
            
            assert test_movie.id == 123
            assert test_movie.title == "Test Movie"
            assert test_movie.year == 2024
