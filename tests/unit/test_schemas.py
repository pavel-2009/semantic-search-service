"""Unit tests for data contracts."""

import pytest
from pydantic import ValidationError

from backend.schemas import (
    MovieResult,
    RatingFilter,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    YearFilter,
)
from core.contracts import IndexerStats, MoviePayload
from scraper.schemas import Movie, MoviesDocument, PoiskKinoResponse


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
            country="США",
        )
        request = SearchRequest(query="test", filters=filters)
        assert request.filters is not None
        assert request.filters.year is not None
        assert request.filters.year.gte == 2020
        assert request.filters.rating is not None
        assert request.filters.rating.gte == 7.0
        assert request.filters.genre is not None
        assert len(request.filters.genre) == 2


class TestMovieResult:
    """Test movie result schema."""

    def test_minimal_movie(self):
        """Minimal movie data should work."""
        movie = MovieResult(id=1, title="Test", score=0.95)
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
            score=0.95,
        )
        assert movie.year == 2010
        assert movie.rating == 8.8
        assert len(movie.genres) == 2


class TestMovieContracts:
    """Test normalized and external movie contracts."""

    def test_movie_accepts_legacy_keys(self):
        """Movie contract should normalize legacy name and tags keys."""
        movie = Movie.model_validate(
            {
                "id": 1,
                "name": "Inception",
                "country": "USA, UK",
                "tags": ["sci-fi", "thriller"],
            }
        )
        assert movie.title == "Inception"
        assert movie.country == "USA, UK"
        assert movie.genres == ["sci-fi", "thriller"]

    def test_movies_document_requires_list(self):
        """Movies document must contain a list of valid movies."""
        with pytest.raises(ValidationError):
            MoviesDocument.model_validate({"id": 1})

    def test_poiskkino_response_contract(self):
        """PoiskKino response should expose typed nested structures."""
        response = PoiskKinoResponse.model_validate(
            {
                "page": 1,
                "pages": 2,
                "docs": [
                    {
                        "id": 1,
                        "name": "Interstellar",
                        "rating": {"kp": 8.6},
                        "countries": [{"name": "США"}],
                        "genres": [{"name": "фантастика"}],
                        "persons": [
                            {"name": "Christopher Nolan", "profession": "режиссеры"}
                        ],
                        "poster": {"url": "https://example.com/poster.jpg"},
                    }
                ],
            }
        )
        movie = response.docs[0]
        assert movie.id == 1
        assert movie.rating.kp == 8.6
        assert movie.countries[0].name == "США"
        assert movie.persons[0].profession == "режиссеры"


class TestMoviePayload:
    """Test the Qdrant payload contract."""

    def test_defaults(self):
        """Payload should provide safe defaults for optional fields."""
        payload = MoviePayload()
        assert payload.title == "Без названия"
        assert payload.countries == []
        assert payload.actors == []
        assert payload.genres == []

    def test_full_payload(self):
        """Payload should validate all persisted movie fields."""
        payload = MoviePayload(
            id=1,
            title="Inception",
            year=2010,
            countries=["USA"],
            genres=["sci-fi"],
            actors=["Leonardo DiCaprio"],
            rating=8.8,
        )
        assert payload.id == 1
        assert payload.countries == ["USA"]
        assert payload.rating == 8.8

    def test_invalid_id(self):
        """Payload should reject invalid identifiers."""
        with pytest.raises(ValidationError):
            MoviePayload(id="not-an-id")


class TestIndexerStats:
    """Test indexer statistics contract."""

    def test_stats(self):
        """Indexer statistics should expose typed fields."""
        stats = IndexerStats(collection="movies", points_count=42, status="green")
        assert stats.collection == "movies"
        assert stats.points_count == 42
        assert stats.status == "green"
