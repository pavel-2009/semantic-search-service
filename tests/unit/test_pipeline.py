"""Tests for scraper pipeline components."""

from io import StringIO

from src.scraper.pipelines import JsonPipeline
from src.scraper.schemas import Movie


def test_process_item_returns_item() -> None:
    pipeline = JsonPipeline()

    pipeline.file = StringIO()

    payload = {
        "id": 1,
        "title": "Интерстеллар",
        "year": 2014,
        "country": "США",
        "genres": ["фантастика", "драма"],
        "rating": 8.6,
        "description": "Путешествие через космос и время.",
    }
    item = Movie.model_validate(payload)

    result = pipeline.process_item(item, spider=None)
    assert result == item
