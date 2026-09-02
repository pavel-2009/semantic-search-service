"""Unit tests for search service"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from qdrant_client.http import models

from backend.services.search_service import SearchService
from backend.schemas import SearchRequest, SearchFilters, YearFilter, RatingFilter
from core.config import settings


class TestSearchService:
    """Test SearchService functionality."""

    def test_initialization(self, mock_qdrant_client, mock_embedding_model):
        """SearchService should initialize correctly."""

        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                service = SearchService()

                assert service.collection_name == settings.QDRANT_COLLECTION
                assert service.qdrant is not None
                assert service.model is not None

    def test_build_filters_year_only(self):
        """Should build filter with year range."""
        filters = SearchFilters(year=YearFilter(gte=2020, lte=2023))
        result = SearchService._build_filters(filters)
        
        assert result is not None
        assert len(result.must) == 2  
        
        assert result.must[0].key == "year"
        assert result.must[0].range.gte == 2020
        
        assert result.must[1].key == "year"
        assert result.must[1].range.lte == 2023

    def test_build_filters_year_gte_only(self):
        """Should build filter with year gte only."""
        filters = SearchFilters(year=YearFilter(gte=2010))
        result = SearchService._build_filters(filters)
        
        assert result is not None
        assert len(result.must) == 1
        assert result.must[0].key == "year"
        assert result.must[0].range.gte == 2010
        assert result.must[0].range.lte is None

    def test_build_filters_rating(self):
        """Should build filter with rating range."""
        filters = SearchFilters(rating=RatingFilter(gte=7.0, lte=9.0))
        result = SearchService._build_filters(filters)
        
        assert result is not None
        assert len(result.must) == 2
        assert result.must[0].key == "rating"
        assert result.must[0].range.gte == 7.0
        assert result.must[1].key == "rating"
        assert result.must[1].range.lte == 9.0

    def test_build_filters_genre(self):
        """Should build filter with genre match."""
        filters = SearchFilters(genre=["драма", "комедия"])
        result = SearchService._build_filters(filters)
        
        assert result is not None
        assert len(result.must) == 1
        assert result.must[0].key == "genres"
        assert result.must[0].match.any == ["драма", "комедия"]

    def test_build_filters_country(self):
        """Should build filter with country match."""
        filters = SearchFilters(country="США")
        result = SearchService._build_filters(filters)
        
        assert result is not None
        assert len(result.must) == 1
        assert result.must[0].key == "countries"
        assert result.must[0].match.any == ["США"]

    def test_build_filters_multiple(self):
        """Should build filter with multiple conditions."""
        filters = SearchFilters(
            year=YearFilter(gte=2010),
            rating=RatingFilter(gte=7.0),
            genre=["драма"],
            country="США"
        )
        result = SearchService._build_filters(filters)
        
        assert result is not None
        assert len(result.must) == 4

    def test_build_filters_empty(self):
        """Empty filters should return None."""
        result = SearchService._build_filters(None)
        assert result is None
        
        empty_filters = SearchFilters()
        result = SearchService._build_filters(empty_filters)

        assert result is None

    def test_movie_from_payload_complete(self):
        """Should parse complete movie payload."""
        payload = {
            "id": 1,
            "title": "Inception",
            "year": 2010,
            "rating": 8.8,
            "genres": ["sci-fi", "thriller"],
            "countries": ["USA"],
            "director": "Christopher Nolan",
            "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
            "description": "A thief who steals corporate secrets",
            "poster_url": "https://example.com/poster.jpg"
        }
        
        movie = SearchService._movie_from_payload(1, payload, 0.95)
        
        assert movie.id == 1
        assert movie.title == "Inception"
        assert movie.year == 2010
        assert movie.rating == 8.8
        assert len(movie.genres) == 2
        assert len(movie.countries) == 1
        assert movie.countries[0] == "USA"
        assert movie.director == "Christopher Nolan"
        assert len(movie.actors) == 2
        assert movie.description == "A thief who steals corporate secrets"
        assert movie.poster_url == "https://example.com/poster.jpg"
        assert movie.score == 0.95

    def test_movie_from_payload_minimal(self):
        """Should parse minimal movie payload."""
        payload = {
            "title": "Unknown",
        }
        
        movie = SearchService._movie_from_payload(999, payload, 0.5)
        
        assert movie.id == 999
        assert movie.title == "Unknown"
        assert movie.year is None
        assert movie.rating is None
        assert movie.genres == []
        assert movie.countries == []
        assert movie.director is None
        assert movie.actors == []
        assert movie.description is None
        assert movie.score == 0.5

    def test_movie_from_payload_country_string(self):
        """Should handle country as string (legacy format)."""
        payload = {
            "title": "Test",
            "country": "USA, UK"
        }
        
        movie = SearchService._movie_from_payload(1, payload, 0.5)
        
        assert len(movie.countries) == 2
        assert "USA" in movie.countries
        assert "UK" in movie.countries

    def test_movie_from_payload_empty_payload(self):
        """Should handle empty payload."""
        movie = SearchService._movie_from_payload(1, None, 0.5)
        
        assert movie.id == 1
        assert movie.title == "Фильм без названия" 
        assert movie.score == 0.5

    def test_get_stats(self, mock_qdrant_client, mock_embedding_model):
        """Should return collection statistics."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                service = SearchService()
                stats = service.get_stats()
                
                assert stats["collection"] == settings.QDRANT_COLLECTION
                assert stats["total_points"] == 100
                assert stats["status"] == "green"
                assert stats["model"] == settings.EMBEDDING_MODEL
                assert stats["embedding_dim"] == settings.EMBEDDING_DIM

    def test_search_without_filters(self, mock_qdrant_client, mock_embedding_model):
        """Should perform search without filters."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                service = SearchService()
                request = SearchRequest(query="inception", top_k=5)
                
                results = service.search(request)
                
                mock_qdrant_client.query_points.assert_called_once()
                call_args = mock_qdrant_client.query_points.call_args[1]
                assert call_args["collection_name"] == settings.QDRANT_COLLECTION
                assert call_args["limit"] == 5
                assert call_args["query_filter"] is None
                assert call_args["with_payload"] is True
                
                assert len(results) == 1
                assert results[0].title == "Inception"

    def test_search_with_filters(self, mock_qdrant_client, mock_embedding_model):
        """Should perform search with filters."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                service = SearchService()
                
                filters = SearchFilters(
                    year=YearFilter(gte=2010),
                    rating=RatingFilter(gte=7.0),
                    genre=["драма"]
                )
                request = SearchRequest(query="drama", top_k=3, filters=filters)
                
                results = service.search(request)
                
                # Verify Qdrant was called with filter
                mock_qdrant_client.query_points.assert_called_once()
                call_args = mock_qdrant_client.query_points.call_args[1]
                assert call_args["query_filter"] is not None
                
                # Should have 3 conditions (year, rating, genre)
                assert len(call_args["query_filter"].must) >= 3
                
                # Verify results
                assert len(results) == 1

    def test_get_by_id_found(self, mock_qdrant_client, mock_embedding_model):
        """Should retrieve movie by ID when found."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                service = SearchService()
                
                # Mock retrieve to return a point
                point = Mock()
                point.id = 1
                point.payload = {
                    "title": "Inception",
                    "year": 2010,
                    "rating": 8.8,
                    "genres": ["sci-fi"],
                    "countries": ["USA"],
                    "director": "Christopher Nolan",
                    "actors": ["Leonardo DiCaprio"],
                    "description": "A thief who steals corporate secrets"
                }
                mock_qdrant_client.retrieve.return_value = [point]
                
                movie = service.get_by_id(1)
                
                assert movie is not None
                assert movie.id == 1
                assert movie.title == "Inception"
                mock_qdrant_client.retrieve.assert_called_once_with(
                    collection_name=settings.QDRANT_COLLECTION,
                    ids=[1],
                    with_payload=True,
                    with_vectors=False
                )

    def test_get_by_id_not_found(self, mock_qdrant_client, mock_embedding_model):
        """Should return None when movie not found."""
        with patch('core.qdrant_client.QdrantClientSingleton.get_client', return_value=mock_qdrant_client):
            with patch('core.model_loader.ModelLoader.get_model', return_value=mock_embedding_model):
                service = SearchService()
                
                # Mock retrieve to return empty list
                mock_qdrant_client.retrieve.return_value = []
                
                movie = service.get_by_id(999)
                
                assert movie is None
