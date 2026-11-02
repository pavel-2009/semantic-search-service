"""Tests for scraper module, API responses processing and data validation."""

from collections.abc import Generator

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

    def generate_paginated_movie_data(
        self,
    ) -> Generator[tuple[int, dict[str, object]], None, None]:
        for requested_page, response_page in ((1, 1), (2, 2), (2, 3)):
            payload = self.get_valid_movie_data()
            payload.update({"page": response_page, "pages": 2})
            yield requested_page, payload


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


def test_get_invalid_response():
    """Test that the spider correctly handles an invalid API response."""
    crawler = get_crawler(MovieSpider)
    spider = MovieSpider.from_crawler(crawler)

    payload = MockKinopoiskAPI().get_invalid_movie_data()

    request = Request(url="https://example.com/api/movies")

    response = TextResponse(
        url=request.url,
        request=request,
        body=json.dumps(payload).encode("utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        list(spider.parse(response))

    assert crawler.stats.get_value("scraper/response_validation_errors") == 1


def test_parse_paginates_two_pages_with_matching_page_numbers():
    crawler = get_crawler(MovieSpider)
    spider = MovieSpider.from_crawler(crawler)
    spider.MAX_PAGES = 2
    api = MockKinopoiskAPI()
    pages = api.generate_paginated_movie_data()

    for expected_page in (1, 2):
        requested_page, payload = next(pages)
        assert requested_page == expected_page

        request = Request(
            url="https://example.com/api/movies",
            meta={"page": requested_page},
        )
        response = TextResponse(
            url=request.url,
            request=request,
            body=json.dumps(payload).encode("utf-8"),
            encoding="utf-8",
        )

        results = list(spider.parse(response))
        movies = [result for result in results if not isinstance(result, Request)]
        next_requests = [result for result in results if isinstance(result, Request)]
        assert len(movies) == 3
        assert len(next_requests) == (1 if expected_page == 1 else 0)
        if expected_page == 1:
            assert next_requests[0].meta["page"] == 2

    assert crawler.stats.get_value("scraper/pages_succeeded") == 2


def test_parse_rejects_response_with_mismatched_page_number():
    crawler = get_crawler(MovieSpider)
    spider = MovieSpider.from_crawler(crawler)
    api = MockKinopoiskAPI()
    pages = api.generate_paginated_movie_data()
    next(pages)
    next(pages)
    requested_page, payload = next(pages)

    request = Request(
        url="https://example.com/api/movies",
        meta={"page": requested_page},
    )
    response = TextResponse(
        url=request.url,
        request=request,
        body=json.dumps(payload).encode("utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Requested page 2, but API returned page 3"):
        list(spider.parse(response))

    assert crawler.stats.get_value("scraper/pagination_errors") == 1
