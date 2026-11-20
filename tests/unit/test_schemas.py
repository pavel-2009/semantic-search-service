"""Tests for backend and scraper Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.backend.schemas import (
    HealthResponse,
    MovieResult,
    RatingFilter,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    StatsResponse,
    YearFilter,
)
from src.core.contracts import Movie
from src.scraper.schemas import (
    PoiskKinoCountry,
    PoiskKinoGenre,
    PoiskKinoMovie,
    PoiskKinoPoster,
    PoiskKinoRating,
    PoiskKinoResponse,
)


def test_year_filter_accepts_range_and_rejects_invalid_year() -> None:
    assert YearFilter().model_dump() == {"gte": None, "lte": None}
    assert YearFilter(gte=1990, lte=2024).gte == 1990

    with pytest.raises(ValidationError):
        YearFilter(gte="not-a-year")


def test_rating_filter_accepts_range_and_rejects_invalid_rating() -> None:
    assert RatingFilter(gte=0.0, lte=10.0).lte == 10.0

    with pytest.raises(ValidationError):
        RatingFilter(lte="not-a-rating")


def test_search_filters_accept_nested_and_optional_values() -> None:
    filters = SearchFilters(
        year={"gte": 2000},
        rating={"gte": 7.5},
    )

    assert filters.year is not None and filters.year.gte == 2000
    assert filters.rating is not None and filters.rating.gte == 7.5
    assert SearchFilters().year is None
    assert SearchFilters().rating is None


@pytest.mark.parametrize(
    "data",
    [
        {"year": {"gte": "unknown"}},
    ],
)
def test_search_filters_reject_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SearchFilters.model_validate(data)


def test_search_request_accepts_valid_request_and_defaults() -> None:
    request = SearchRequest(query="интерстеллар")
    assert request.top_k == 10
    assert request.filters is None

    request = SearchRequest(
        query="космическая фантастика",
        top_k=25,
        filters={"year": {"gte": 2000}, "rating": {"gte": 7.5}},
    )
    assert request.top_k == 25
    assert request.filters is not None
    assert request.filters.year is not None
    assert request.filters.year.gte == 2000
    assert request.filters.rating is not None
    assert request.filters.rating.gte == 7.5


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"query": ""},
        {"query": "q" * 501},
        {"query": "фильм", "top_k": 0},
        {"query": "фильм", "top_k": 101},
    ],
)
def test_search_request_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SearchRequest.model_validate(data)


def test_movie_result_accepts_required_and_optional_fields() -> None:
    minimal = MovieResult(id=1, title="Фильм", score=0.9)
    assert minimal.genres == []
    assert minimal.countries == []
    assert minimal.year is None

    complete = MovieResult(
        id=1,
        title="Фильм",
        year=2024,
        rating=8.2,
        genres=["драма"],
        countries=["Россия"],
        description="Описание",
        poster_url="https://example.test/poster.jpg",
        score=0.9,
    )
    assert complete.rating == 8.2
    assert complete.countries == ["Россия"]


@pytest.mark.parametrize(
    "data",
    [
        {"id": "not-an-id", "title": "Фильм", "score": 0.9},
        {"id": 1, "title": "Фильм", "score": "not-a-score"},
        {"id": 1, "title": "Фильм", "genres": "драма", "score": 0.9},
        {"id": 1, "title": "Фильм"},
    ],
)
def test_movie_result_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        MovieResult.model_validate(data)


def test_search_response_accepts_nested_results_and_defaults_success() -> None:
    response = SearchResponse(
        query="фильм",
        total=1,
        results=[{"id": 1, "title": "Фильм", "score": 0.8}],
    )

    assert response.success is True
    assert response.results[0].title == "Фильм"


@pytest.mark.parametrize(
    "data",
    [
        {"query": "фильм", "total": "unknown", "results": []},
        {"query": "фильм", "total": 1, "results": [{"id": 1}]},
        {"query": "фильм", "total": 0},
    ],
)
def test_search_response_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SearchResponse.model_validate(data)


def test_health_response_accepts_valid_values() -> None:
    response = HealthResponse(
        status="healthy",
        collection="movies",
        indexed_items=12,
    )
    assert response.indexed_items == 12


@pytest.mark.parametrize(
    "data",
    [
        {"status": "healthy", "collection": "movies"},
        {"status": "healthy", "collection": "movies", "indexed_items": "unknown"},
    ],
)
def test_health_response_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HealthResponse.model_validate(data)


def test_stats_response_accepts_valid_values() -> None:
    response = StatsResponse(
        collection="movies",
        total_points=12,
        status="green",
        model="embedding-model",
        embedding_dim=384,
    )
    assert response.embedding_dim == 384


@pytest.mark.parametrize(
    "data",
    [
        {"collection": "movies", "total_points": "unknown"},
        {
            "collection": "movies",
            "total_points": 12,
            "status": "green",
            "model": "embedding-model",
        },
    ],
)
def test_stats_response_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        StatsResponse.model_validate(data)


def test_poiskkino_rating_accepts_optional_rating() -> None:
    assert PoiskKinoRating().kp is None
    assert PoiskKinoRating(kp=8.1).kp == 8.1

    with pytest.raises(ValidationError):
        PoiskKinoRating(kp="bad-rating")


@pytest.mark.parametrize(
    ("schema", "valid_data", "invalid_data"),
    [
        (PoiskKinoCountry, {"name": "Россия"}, {"name": ["Россия"]}),
        (PoiskKinoGenre, {"name": "драма"}, {"name": ["драма"]}),
        (
            PoiskKinoPoster,
            {"url": "https://example.test/poster.jpg"},
            {"url": ["not-a-url"]},
        ),
    ],
)
def test_poiskkino_nested_schemas_accept_valid_and_reject_invalid_values(
    schema: type,
    valid_data: dict[str, object],
    invalid_data: dict[str, object],
) -> None:
    assert schema.model_validate(valid_data)

    with pytest.raises(ValidationError):
        schema.model_validate(invalid_data)


def test_poiskkino_movie_accepts_nested_data_and_null_defaults() -> None:
    movie = PoiskKinoMovie.model_validate(
        {
            "id": 123,
            "name": "Название",
            "countries": [{"name": "Россия"}],
            "genres": [{"name": "драма"}],
            "rating": {"kp": 8.2},
            "poster": {"url": "https://example.test/poster.jpg"},
            "extra": "ignored",
        }
    )
    assert movie.countries[0].name == "Россия"
    assert movie.genres[0].name == "драма"
    assert movie.rating.kp == 8.2

    legacy = PoiskKinoMovie.model_validate(
        {
            "id": 124,
            "countries": None,
            "genres": None,
            "rating": None,
            "poster": None,
        }
    )
    assert legacy.countries == []
    assert legacy.genres == []
    assert legacy.rating.kp is None
    assert legacy.poster.url is None


@pytest.mark.parametrize(
    "data",
    [
        {"id": "bad-id"},
        {"id": 1, "countries": [{"name": ["Россия"]}]},
        {"id": 1, "rating": {"kp": "bad-rating"}},
        {"id": 1, "poster": {"url": ["not-a-url"]}},
    ],
)
def test_poiskkino_movie_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PoiskKinoMovie.model_validate(data)


def test_poiskkino_response_accepts_defaults_and_nested_documents() -> None:
    assert PoiskKinoResponse().model_dump() == {"docs": [], "page": 1, "pages": 1}

    response = PoiskKinoResponse.model_validate(
        {"docs": [{"id": 1, "name": "Фильм"}], "page": 2, "pages": 5}
    )
    assert response.docs[0].name == "Фильм"
    assert response.page == 2

    legacy = PoiskKinoResponse.model_validate({"docs": None})
    assert legacy.docs == []


@pytest.mark.parametrize(
    "data",
    [
        {"docs": [{"id": "bad-id"}]},
        {"docs": "not-a-list"},
        {"page": "not-a-page"},
    ],
)
def test_poiskkino_response_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PoiskKinoResponse.model_validate(data)
