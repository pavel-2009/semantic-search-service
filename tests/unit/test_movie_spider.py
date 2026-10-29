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


@pytest.mark.asyncio
async def test_start_creates_ten_page_ranges() -> None:
    crawler = Crawler(
        MovieSpider,
        settings={"SCRAPER_RUNS": 10, "SCRAPER_PAGES_PER_RUN": 10},
    )
    spider = crawler._create_spider()

    requests = [request async for request in spider.start()]

    assert [request.meta["page"] for request in requests] == [
        1,
        11,
        21,
        31,
        41,
        51,
        61,
        71,
        81,
        91,
    ]
    assert [request.meta["run_end_page"] for request in requests] == [
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100,
    ]


def test_parse_queues_next_page_from_requested_page() -> None:
    crawler = Crawler(MovieSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = crawler._create_spider()
    response = Response(
        url="https://api.poiskkino.dev/v1.4/movie?page=4",
        body=b'{"docs":[],"page":4,"pages":5}',
        request=Request(
            url="https://api.poiskkino.dev/v1.4/movie?page=4",
            meta={"page": 4, "run_end_page": 10},
        ),
    )

    result = list(spider.parse(response))

    assert len(result) == 1
    assert isinstance(result[0], Request)
    assert result[0].meta["page"] == 5
    assert result[0].meta["run_end_page"] == 10
    assert "page=5" in result[0].url


def test_parse_stops_at_page_range_boundary() -> None:
    crawler = Crawler(MovieSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = crawler._create_spider()
    response = Response(
        url="https://api.poiskkino.dev/v1.4/movie?page=10",
        body=b'{"docs":[],"page":10,"pages":100}',
        request=Request(
            url="https://api.poiskkino.dev/v1.4/movie?page=10",
            meta={"page": 10, "run_end_page": 10},
        ),
    )

    assert list(spider.parse(response)) == []


def test_parse_fails_when_api_page_does_not_match_requested_page(caplog) -> None:
    crawler = Crawler(MovieSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = crawler._create_spider()
    response = Response(
        url="https://api.poiskkino.dev/v1.4/movie?page=2",
        body=b'{"docs":[],"page":1,"pages":3}',
        request=Request(
            url="https://api.poiskkino.dev/v1.4/movie?page=2",
            meta={"page": 2},
        ),
    )

    with caplog.at_level("ERROR"):
        with pytest.raises(ValueError, match="Requested page 2, but API returned page 1"):
            list(spider.parse(response))

    assert crawler.stats.get_value("scraper/failed") is True
    assert crawler.stats.get_value("scraper/pagination_errors") == 1
    assert crawler.stats.get_value("scraper/pages_succeeded", 0) == 0
    assert "requested=2 received=1" in caplog.text


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
