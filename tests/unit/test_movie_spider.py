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
