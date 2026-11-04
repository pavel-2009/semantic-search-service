"""Tests for core helpers, contracts, and configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config import PROJECT_ROOT, Settings
from core.contracts import IndexerStats, MoviePayload
from core.text_normalizer import clean_text
from core.dependencies import get_search_service
from backend.services.search_service import SearchService


def test_clean_text_returns_empty_for_empty_or_whitespace_input() -> None:
    assert clean_text("") == ""
    assert clean_text(" \t\n ") == ""


def test_clean_text_removes_markup_and_unsupported_punctuation() -> None:
    assert clean_text("<p>Привет &amp; мир!</p>") == "привет мир"


def test_clean_text_normalizes_unicode_and_preserves_cyrillic_letters() -> None:
    assert clean_text("ЁЖ, cafe\u0301, ＡＢＣ") == "ёж cafe abc"


def test_clean_text_replaces_unusual_symbols_and_collapses_whitespace() -> None:
    assert clean_text("  Привет\u2003🌍\n\tмир!!!  ") == "привет мир"


def test_clean_text_can_preserve_supported_punctuation() -> None:
    assert clean_text("  Кино: 2024. Фильм-1! ", preserve_punctuation=True) == (
        "кино: 2024. фильм-1"
    )


def test_movie_payload_defaults_and_accepts_complete_data() -> None:
    payload = MoviePayload()
    assert payload.id is None
    assert payload.title == "Без названия"
    assert payload.description == ""
    assert payload.actors == []
    assert payload.genres == []
    assert payload.countries == []

    populated = MoviePayload(
        id=42,
        title="Фильм",
        year=2024,
        country="Россия",
        countries=["Россия"],
        director="Режиссер",
        description="Описание",
        actors=["Актер"],
        genres=["драма"],
        rating=8.5,
        poster_url="https://example.test/poster.jpg",
    )
    assert populated.id == 42
    assert populated.rating == 8.5
    assert populated.genres == ["драма"]


@pytest.mark.parametrize(
    "data",
    [
        {"id": "not-an-id"},
        {"year": "not-a-year"},
        {"genres": "драма"},
        {"actors": [None]},
    ],
)
def test_movie_payload_rejects_invalid_values(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        MoviePayload.model_validate(data)


def test_indexer_stats_supports_contract_and_mapping_access() -> None:
    stats = IndexerStats(collection="movies", points_count=12, status="green")

    assert stats.collection == "movies"
    assert stats["points_count"] == 12
    assert stats.model_dump() == {
        "collection": "movies",
        "points_count": 12,
        "status": "green",
    }


@pytest.mark.parametrize(
    "data",
    [
        {"points_count": "not-a-count"},
        {"collection": ["movies"]},
        {"status": None},
    ],
)
def test_indexer_stats_reject_invalid_or_missing_fields(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        IndexerStats.model_validate(data)


def test_settings_defaults_and_types_are_valid() -> None:
    settings = Settings(_env_file=None)

    assert settings.QDRANT_HOST == "localhost"
    assert settings.QDRANT_PORT == 6333
    assert settings.QDRANT_COLLECTION == "movies"
    assert settings.EMBEDDING_DIM == 384
    assert settings.DATA_PATH == PROJECT_ROOT / "src/scraper/data/movies.jsonl"
    assert PROJECT_ROOT == Path(__file__).resolve().parents[2]


def test_settings_load_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_HOST", "qdrant.test")
    monkeypatch.setenv("QDRANT_PORT", "6334")
    monkeypatch.setenv("BOT_TOKEN", "test-token")

    settings = Settings(_env_file=None)

    assert settings.QDRANT_HOST == "qdrant.test"
    assert settings.QDRANT_PORT == 6334
    assert settings.BOT_TOKEN == "test-token"


def test_settings_reject_invalid_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QDRANT_PORT", "not-a-port")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_search_service_returns_instance() -> None:
    service = get_search_service()
    assert service is not None
    assert isinstance(service, SearchService)  # Replace with actual type if known