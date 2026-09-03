"""Unit tests for SearchService."""

from unittest.mock import Mock

import pytest

from backend.schemas import RatingFilter, SearchFilters, SearchRequest, YearFilter
from backend.services.search_service import SearchService
from core.config import settings
from core.contracts import MoviePayload


def test_initialization(mock_qdrant_client, mock_embedding_model):
    service = SearchService()

    assert service.collection_name == settings.QDRANT_COLLECTION
    assert service.qdrant is mock_qdrant_client
    assert service.model is mock_embedding_model


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        (SearchFilters(year=YearFilter(gte=2020, lte=2023)), [("year", 2020, None), ("year", None, 2023)]),
        (SearchFilters(year=YearFilter(gte=2010)), [("year", 2010, None)]),
        (SearchFilters(rating=RatingFilter(gte=7.0, lte=9.0)), [("rating", 7.0, None), ("rating", None, 9.0)]),
        (SearchFilters(genre=["драма", "комедия"]), [("genres", ["драма", "комедия"])]),
        (SearchFilters(country="США"), [("countries", ["США"])]),
        (
            SearchFilters(
                year=YearFilter(gte=2010),
                rating=RatingFilter(gte=7.0),
                genre=["драма"],
                country="США",
            ),
            [("year", 2010, None), ("rating", 7.0, None), ("genres", ["драма"]), ("countries", ["США"])],
        ),
    ],
)
def test_build_filters(filters, expected):
    result = SearchService._build_filters(filters)

    assert result is not None
    assert len(result.must) == len(expected)
    for condition, values in zip(result.must, expected):
        assert condition.key == values[0]
        if condition.key in {"year", "rating"}:
            assert condition.range.gte == values[1]
            assert condition.range.lte == values[2]
        else:
            assert condition.match.any == values[1]


def test_build_filters_empty():
    assert SearchService._build_filters(None) is None
    assert SearchService._build_filters(SearchFilters()) is None


@pytest.mark.parametrize(
    "payload",
    [
        MoviePayload(
            id=1,
            title="Inception",
            year=2010,
            rating=8.8,
            genres=["sci-fi", "thriller"],
            countries=["USA"],
            director="Christopher Nolan",
            actors=["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
            description="A thief who steals corporate secrets",
            poster_url="https://example.com/poster.jpg",
        ),
        MoviePayload(title="Unknown"),
    ],
)
def test_movie_from_payload(payload):
    movie = SearchService._movie_from_payload(1, payload, 0.95)

    assert movie.id == 1
    assert movie.title == payload.title
    assert movie.score == 0.95
    assert movie.genres == payload.genres
    assert movie.countries == payload.countries


def test_movie_from_payload_legacy_country_and_empty():
    movie = SearchService._movie_from_payload(1, MoviePayload(title="Test", country="USA, UK"), 0.5)
    assert movie.countries == ["USA", "UK"]

    movie = SearchService._movie_from_payload(1, None, 0.5)
    assert movie.title == "Без названия"
    assert movie.score == 0.5


def test_get_stats(mock_qdrant_client):
    stats = SearchService().get_stats()

    assert stats.collection == settings.QDRANT_COLLECTION
    assert stats.total_points == 100
    assert stats.status == "green"
    assert stats.model == settings.EMBEDDING_MODEL
    assert stats.embedding_dim == settings.EMBEDDING_DIM


def test_search(mock_qdrant_client, mock_embedding_model):
    results = SearchService().search(SearchRequest(query="inception", top_k=5))

    call = mock_qdrant_client.query_points.call_args.kwargs
    assert call["collection_name"] == settings.QDRANT_COLLECTION
    assert call["limit"] == 5
    assert call["query_filter"] is None
    assert call["with_payload"] is True
    assert len(results) == 1
    assert results[0].title == "Inception"
    mock_embedding_model.encode.assert_called_once_with("inception")


def test_search_with_filters(mock_qdrant_client):
    request = SearchRequest(
        query="drama",
        top_k=3,
        filters=SearchFilters(
            year=YearFilter(gte=2010),
            rating=RatingFilter(gte=7.0),
            genre=["драма"],
        ),
    )

    results = SearchService().search(request)

    query_filter = mock_qdrant_client.query_points.call_args.kwargs["query_filter"]
    assert len(query_filter.must) == 3
    assert len(results) == 1


def test_get_by_id_found(mock_qdrant_client):
    mock_qdrant_client.retrieve.return_value = [
        Mock(id=1, payload=MoviePayload(title="Inception", year=2010))
    ]

    movie = SearchService().get_by_id(1)

    assert movie is not None
    assert movie.id == 1
    assert movie.title == "Inception"
    mock_qdrant_client.retrieve.assert_called_once_with(
        collection_name=settings.QDRANT_COLLECTION,
        ids=[1],
        with_payload=True,
        with_vectors=False,
    )


def test_get_by_id_not_found(mock_qdrant_client):
    mock_qdrant_client.retrieve.return_value = []

    assert SearchService().get_by_id(999) is None
