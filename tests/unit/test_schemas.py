"""Unit tests for API schemas"""

import pytest
from pydantic import ValidationError

from backend.schemas import (
    SearchRequest,
    SearchFilters,
    YearFilter,
    RatingFilter,
    MovieResult,
    SearchResponse,
)


class TestSearchRequest:
    """Test search request validation."""

    def test_valid_request(self):
        """Valid search request should pass."""
        request = SearchRequest(query="interstellar", top_k=5)
        assert request.query == "interstellar"
        assert request.top_k == 5
    
    def test_min_query_length(self):
        """Query must be at least 1 character."""
        with pytest.raises(ValidationError):
            SearchRequest(query="")
    
    def test_max_query_length(self):
        """Query cannot exceed 500 characters."""
        long_query = "a" * 501
        with pytest.raises(ValidationError):
            SearchRequest(query=long_query)
    
    def test_top_k_min(self):
        """top_k must be at least 1."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=0)
    
    def test_top_k_max(self):
        """top_k cannot exceed 100."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=101)
    
    def test_with_filters(self):
        """Search request with filters should work."""
        filters = SearchFilters(
            year=YearFilter(gte=2020, lte=2023),
            rating=RatingFilter(gte=7.0),
            genre=["драма", "комедия"],
            country="США"
        )
        request = SearchRequest(query="test", filters=filters)
        assert request.filters.year.gte == 2020
        assert request.filters.rating.gte == 7.0
        assert len(request.filters.genre) == 2


class TestMovieResult:
    """Test movie result schema."""
    
    def test_minimal_movie(self):
        """Minimal movie data should work."""
        movie = MovieResult(
            id=1,
            title="Test",
            score=0.95
        )
        assert movie.id == 1
        assert movie.title == "Test"
        assert movie.score == 0.95
        assert movie.genres == []
        assert movie.countries == []
    
    def test_full_movie(self):
        """Full movie data should work."""
        movie = MovieResult(
            id=1,
            title="Inception",
            year=2010,
            rating=8.8,
            genres=["sci-fi", "thriller"],
            countries=["USA"],
            director="Christopher Nolan",
            actors=["Leonardo DiCaprio"],
            description="A thief who steals corporate secrets",
            poster_url="https://example.com/poster.jpg",
            score=0.95
        )
        assert movie.year == 2010
        assert movie.rating == 8.8
        assert len(movie.genres) == 2
