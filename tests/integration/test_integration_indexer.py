"""Integration tests for Indexer with real Qdrant."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch

from services.indexer import Indexer
from backend.services.search_service import SearchService
from backend.schemas import SearchRequest
from core.config import settings


class TestIndexerIntegration:
    """Test Indexer with real Qdrant"""

    def test_index_and_search_roundtrip(self, qdrant_test_client, test_movies_file):
        """Full cicle: indexing -> search"""
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
                    assert stats["points_count"] == 3
                    
                    search_service = SearchService()
                    search_service.collection_name = collection_name
                    search_service.qdrant = client
                    search_service.model = real_model
                    
                    request = SearchRequest(query="dream technology", top_k=2)
                    results = search_service.search(request)
                    
                    assert len(results) > 0
                    assert results[0].title == "Inception"

    def test_search_with_filters(self, qdrant_test_client, test_movies_file):
        """Search with filters."""
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
                    
                    search_service = SearchService()
                    search_service.collection_name = collection_name
                    search_service.qdrant = client
                    search_service.model = real_model
                    
                    from backend.schemas import SearchFilters, YearFilter, RatingFilter
                    
                    filters = SearchFilters(
                        year=YearFilter(gte=2010),
                        rating=RatingFilter(gte=8.5)
                    )
                    request = SearchRequest(
                        query="space",
                        top_k=3,
                        filters=filters
                    )
                    
                    results = search_service.search(request)
                    
                    for movie in results:
                        assert movie.year >= 2010
                        assert movie.rating >= 8.5

    def test_get_movie_by_id(self, qdrant_test_client, test_movies_file):
        """Getting film by id"""
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
                    
                    search_service = SearchService()
                    search_service.collection_name = collection_name
                    search_service.qdrant = client
                    
                    movie = search_service.get_by_id(1)
                    
                    assert movie is not None
                    assert movie.id == 1
                    assert movie.title == "Inception"
                    assert movie.year == 2010
                    assert movie.director == "Christopher Nolan"
                    
                    movie = search_service.get_by_id(999)
                    assert movie is None

    def test_stats_endpoint(self, qdrant_test_client, test_movies_file):
        """Test collection stats"""
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
                    
                    assert stats["collection"] == collection_name
                    assert stats["points_count"] == 3
                    assert stats["status"] == "green"

