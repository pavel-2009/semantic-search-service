"""Tests for scraper pipeline components."""

import json

from src.scraper.pipelines import JsonPipeline
from src.scraper.schemas import Movie


def test_process_item_returns_item() -> None:
    pipeline = JsonPipeline()

    pipeline.file = open("test_output.jsonl", "w", encoding="utf-8")

    payload = {
                "id": 1,
                "name": "Интерстеллар",
                "year": 2014,
                "countries": [{"name": "США"}],
                "genres": [{"name": "фантастика"}, {"name": "драма"}],
                "rating": {"kp": 8.6},
                "description": "Путешествие через космос и время.",
            }
    item = Movie.model_validate(payload)
    
    result = pipeline.process_item(item, spider=None)
    assert result == item
    pipeline.file.close()
