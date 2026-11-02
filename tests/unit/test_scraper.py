"""Tests for scraper module, API responses processing and data validation."""

import pytest
import json

from scrapy.http import TextResponse, Request
from scrapy.utils.test import get_crawler

from src.scraper.schemas import (
    PoiskKinoCountry,
    PoiskKinoGenre,
    PoiskKinoPerson,
    PoiskKinoMovie,
    Movie,
    MoviesDocument
)
from src.scraper.spiders.movie_spider import MovieSpider


class MockKinopoiskAPI:
    """Mock class for KinopoiskAPI to simulate API responses."""

    def get_valid_movie_data(self) -> dict:
        return {
            "docs": [
                {
                    "id": 1,
                    "name": "Интерстеллар",
                    "year": 2014,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "драма"}],
                    "rating": {"kp": 8.6},
                    "description": "Путешествие через космос и время.",
                },
                {
                    "id": 2,
                    "name": "Начало",
                    "year": 2010,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.7},
                    "description": "Вор проникает в сны людей.",
                },
                {
                    "id": 3,
                    "name": "Матрица",
                    "year": 1999,
                    "countries": [{"name": "США"}, {"name": "Австралия"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.5},
                    "description": "Программист узнает правду о реальности.",
                },
            ],
            "page": 1,
            "pages": 1,
        }

    def get_invalid_movie_data(self) -> dict:
        return {
            "docs": [
                {
                    "id": 1,
                    "name": "Интерстеллар",
                    "year": 2014,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "драма"}],
                    "rating": {"kp": 8.6},
                    "description": "Путешествие через космос и время.",
                },
                {
                    "id": "invalid",
                    "name": "Начало",
                    "year": 2010,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.7},
                    "description": "Вор проникает в сны людей.",
                },
                {
                    "id": 3,
                    "name": "Матрица",
                    "year": 1999,
                    "countries": [{"name": "США"}, {"name": "Австралия"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.5},
                    "description": "Программист узнает правду о реальности.",
                },
            ],
            "page": 1,
            "pages": 1,
        }


def test_get_valid_response():
    crawler = get_crawler(MovieSpider)
    spider = MovieSpider.from_crawler(crawler)

    payload = MockKinopoiskAPI().get_valid_movie_data()

    request = Request(url="https://example.com/api/movies")

    response = TextResponse(
        url=request.url,
        request=request,
        body=json.dumps(payload).encode("utf-8"),
        encoding="utf-8",
    )

    results = list(spider.parse(response))

    assert len(results) == 3

    assert results[0].id == 1
    assert results[0].title == "Интерстеллар"
    assert results[0].rating == 8.6
    assert results[0].year == 2014
    assert crawler.stats.get_value("scraper/pages_succeeded") == 1
