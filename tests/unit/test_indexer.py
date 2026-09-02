"""Unit tests for Indexer."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from services.indexer import Indexer
from core.config import settings


class TestIndexer:
    """Test Indexer functionality."""

    def test_initialization(self, mock_qdrant_client, mock_embedding_model):
        """Indexer should initialize correctly."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                
                assert indexer.collection_name == settings.QDRANT_COLLECTION
                assert indexer.embedding_dim == settings.EMBEDDING_DIM
                assert indexer.qdrant is not None
                assert indexer.model is not None

    def test_prepare_text_complete(self, mock_qdrant_client, mock_embedding_model):
        """Should prepare text from complete movie data."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                
                movie = {
                    "id": 1,
                    "title": "Inception",
                    "description": "A thief who steals corporate secrets",
                    "director": "Christopher Nolan",
                    "country": "USA",
                    "year": 2010,
                    "rating": 8.8,
                    "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
                    "genres": ["sci-fi", "thriller"]
                }
                
                text = indexer.prepare_text(movie)
                
                assert "название: inception" in text.lower()
                assert "описание: a thief who steals corporate secrets" in text.lower()
                assert "режиссёр: christopher nolan" in text.lower()
                assert "страна: usa" in text.lower()
                assert "год: 2010" in text
                assert "рейтинг: 8.8" in text
                assert "актёры: leonardo dicaprio" in text.lower()
                assert "жанры: sci-fi" in text.lower()

    def test_prepare_text_minimal(self, mock_qdrant_client, mock_embedding_model):
        """Should handle minimal movie data."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                
                movie = {
                    "id": 1,
                    "title": "Unknown"
                }
                
                text = indexer.prepare_text(movie)
                
                assert "название unknown" in text.lower()
                assert "описание: фильм без описания" not in text.lower()

    def test_prepare_text_empty(self, mock_qdrant_client, mock_embedding_model):
        """Should handle empty movie data."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                
                movie = {}
                
                text = indexer.prepare_text(movie)
                
                assert "фильм без описания" in text.lower()

    def test_normalize_movie(self, mock_qdrant_client, mock_embedding_model):
        """Should normalize legacy movie format."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                
                movie = {
                    "id": 1,
                    "name": "Inception",
                    "country": "USA, UK",
                    "tags": ["sci-fi", "thriller"]
                }
                
                normalized = indexer._normalize_movie(movie)
                
                assert "title" in normalized
                assert normalized["title"] == "Inception"
                assert "name" not in normalized
                assert "tags" not in normalized
                assert normalized["genres"] == ["sci-fi", "thriller"]
                assert len(normalized["countries"]) == 2
                assert "USA" in normalized["countries"]
                assert "UK" in normalized["countries"]

    def test_load_movies(self, mock_qdrant_client, mock_embedding_model, temp_json_file):
        """Should load movies from JSON file."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                movies = indexer.load_movies(temp_json_file)
                
                assert len(movies) == 2
                assert movies[0]["id"] == 1
                assert movies[0]["title"] == "Inception"
                assert movies[1]["id"] == 2
                assert movies[1]["title"] == "The Dark Knight"

    def test_load_movies_file_not_found(self, mock_qdrant_client, mock_embedding_model):
        """Should raise error when file not found."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                
                with pytest.raises(FileNotFoundError):
                    indexer.load_movies(Path("/nonexistent/file.json"))

    def test_load_movies_invalid_json(self, mock_qdrant_client, mock_embedding_model, tmp_path):
        """Should raise error for invalid JSON."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                
                invalid_file = tmp_path / "invalid.json"
                invalid_file.write_text('{"not": "a list"}')
                
                with pytest.raises(ValueError):
                    indexer.load_movies(invalid_file)

    def test_create_collection_new(self, mock_qdrant_client, mock_embedding_model):
        """Should create collection when it doesn't exist."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                # Mock collections list to not include our collection
                mock_qdrant_client.get_collections.return_value.collections = []
                
                indexer = Indexer()
                indexer.create_collection(force_recreate=False)
                
                mock_qdrant_client.create_collection.assert_called_once()

    def test_create_collection_exists(self, mock_qdrant_client, mock_embedding_model):
        """Should not create collection if it already exists."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):

                collection = Mock()
                collection.name = settings.QDRANT_COLLECTION
                mock_qdrant_client.get_collections.return_value.collections = [collection]
                
                indexer = Indexer()
                indexer.create_collection(force_recreate=False)
                
                mock_qdrant_client.create_collection.assert_not_called()

    def test_create_collection_force_recreate(self, mock_qdrant_client, mock_embedding_model):
        """Should recreate collection when force_recreate is True."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                # Mock collections to exist
                collection_obj = Mock()
                collection_obj.name = settings.QDRANT_COLLECTION
                collections_response = Mock()
                collections_response.collections = [collection_obj]
                mock_qdrant_client.get_collections.return_value = collections_response
                
                indexer = Indexer()
                indexer.create_collection(force_recreate=True)
                
                mock_qdrant_client.delete_collection.assert_called_once()
                
                mock_qdrant_client.create_collection.assert_called_once_with(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=unittest.mock.ANY  
                )

    def test_clear_collection(self, mock_qdrant_client, mock_embedding_model):
        """Should delete the collection."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                indexer.clear_collection()
                
                mock_qdrant_client.delete_collection.assert_called_once_with(settings.QDRANT_COLLECTION)

    def test_get_stats(self, mock_qdrant_client, mock_embedding_model):
        """Should return collection statistics."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                indexer = Indexer()
                stats = indexer.get_stats()
                
                assert stats["collection"] == settings.QDRANT_COLLECTION
                assert stats["points_count"] == 100
                assert stats["status"] == "green"