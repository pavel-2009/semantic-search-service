"""Unit tests for PoiskKino scraper contracts and conversion."""

import pytest
from pydantic import ValidationError
from scrapy.crawler import Crawler
from scrapy.http import Request, Response
from scrapy.statscollectors import MemoryStatsCollector

from scraper.schemas import (
    PoiskKinoCountry,
    PoiskKinoGenre,
    PoiskKinoMovie,
    PoiskKinoPerson,
    PoiskKinoPoster,
    PoiskKinoRating,
)
from scraper.spiders.movie_spider import MovieSpider


def test_parse_movie_uses_typed_poiskkino_contract() -> None:
    """Spider should convert a validated API movie into the normalized contract."""
    movie = PoiskKinoMovie(
        id=1,
        name="Interstellar",
        year=2014,
        countries=[PoiskKinoCountry(name="США")],
        persons=[
            PoiskKinoPerson(name="Christopher Nolan", profession="режиссеры"),
            PoiskKinoPerson(name="Matthew McConaughey", profession="актеры"),
        ],
        genres=[PoiskKinoGenre(name="фантастика")],
        rating=PoiskKinoRating(kp=8.6),
        description="A team travels through a wormhole.",
        poster=PoiskKinoPoster(url="https://example.com/poster.jpg"),
    )

    result = MovieSpider()._parse_movie(movie)

    assert result is not None
    assert result.id == 1
    assert result.title == "Interstellar"
    assert result.country == "США"
    assert result.director == "Christopher Nolan"
    assert result.actors == ["Matthew McConaughey"]
    assert result.genres == ["фантастика"]
    assert result.rating == 8.6


def test_extract_helpers_use_concrete_contracts() -> None:
    """Typed helpers should extract values without dictionary access."""
    countries = [PoiskKinoCountry(name="США"), PoiskKinoCountry(name="Великобритания")]
    persons = [
        PoiskKinoPerson(name="Nolan", profession="режиссеры"),
        PoiskKinoPerson(name="Actor", profession="актеры"),
    ]
    genres = [PoiskKinoGenre(name="драма")]

    assert MovieSpider._extract_countries(countries) == "США, Великобритания"
    assert MovieSpider._extract_director(persons) == "Nolan"
    assert MovieSpider._extract_actors(persons) == ["Actor"]
    assert MovieSpider._extract_genres(genres) == ["драма"]


def test_parse_marks_response_validation_failure_and_logs_page(caplog) -> None:
    crawler = Crawler(MovieSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = crawler._create_spider()
    response = Response(
        url="https://api.poiskkino.dev/v1.4/movie",
        body=b'{"docs":[{}]}',
        request=Request(
            url="https://api.poiskkino.dev/v1.4/movie",
            meta={"page": 7},
        ),
    )

    with caplog.at_level("ERROR"):
        with pytest.raises(ValidationError):
            list(spider.parse(response))

    assert crawler.stats.get_value("scraper/failed") is True
    assert crawler.stats.get_value("scraper/response_validation_errors") == 1
    assert "page=7" in caplog.text
    assert "reason=" in caplog.text


def test_parse_counts_successfully_validated_page() -> None:
    crawler = Crawler(MovieSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = crawler._create_spider()
    response = Response(
        url="https://api.poiskkino.dev/v1.4/movie",
        body=b'{"docs":[],"page":1,"pages":1}',
        request=Request(url="https://api.poiskkino.dev/v1.4/movie"),
    )

    list(spider.parse(response))

    assert crawler.stats.get_value("scraper/pages_succeeded") == 1


def test_closed_logs_final_scraper_statistics(caplog) -> None:
    crawler = Crawler(MovieSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = crawler._create_spider()
    crawler.stats.set_value("scraper/pages_succeeded", 5)
    crawler.stats.set_value("downloader/exception_count", 2)
    crawler.stats.set_value("downloader/response_status_count/429", 3)
    crawler.stats.set_value("downloader/response_status_count/500", 1)
    crawler.stats.set_value("downloader/response_status_count/200", 5)
    crawler.stats.set_value("item_scraped_count", 30)
    crawler.stats.set_value("item_dropped_count", 4)
    crawler.stats.set_value("scraper/rejected_records", 3)

    with caplog.at_level("INFO"):
        spider.closed("finished")

    assert (
        "successful_pages=5 failed_requests=6 extracted_movies=30 "
        "rejected_records=7 finish_reason=finished"
    ) in caplog.text
