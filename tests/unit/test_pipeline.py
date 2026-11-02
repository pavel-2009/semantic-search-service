"""Tests for scraper pipeline components."""

import json
from io import StringIO
from pathlib import Path

from scrapy.utils.test import get_crawler

import src.scraper.pipelines as pipeline_module
from src.scraper.pipelines import JsonPipeline
from src.scraper.schemas import Movie
from src.scraper.spiders.movie_spider import MovieSpider


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


def test_pipeline_writes_movies_to_json():
    pipeline = JsonPipeline()

    file = Path("test_movies.json")
    pipeline.file = file.open("w", encoding="utf-8")

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

    pipeline.process_item(item, spider=None)
    pipeline.close_spider(spider=None)

    with file.open("r", encoding="utf-8") as f:
        content = f.read()
        assert content == (
            '{"id": 1, "title": "Интерстеллар", "year": 2014, "country": "США", "director": null, "description": "Путешествие через космос и время.", "actors": [], "genres": ["фантастика", "драма"], "rating": 8.6, "poster_url": null}\n'
        )


def test_pipeline_writes_multiple_movies(tmp_path):
    pipeline = JsonPipeline()
    file = tmp_path / "test_movies.jsonl"
    pipeline.file = file.open("w", encoding="utf-8")
    movies = [
        Movie(id=1, title="Интерстеллар"),
        Movie(id=2, title="Начало"),
    ]

    for movie in movies:
        pipeline.process_item(movie, spider=None)
    pipeline.close_spider(spider=None)

    written_movies = [
        json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()
    ]
    assert written_movies == [movie.model_dump() for movie in movies]


def test_pipeline_writes_empty_list(tmp_path):
    pipeline = JsonPipeline()
    file = tmp_path / "test_movies.jsonl"
    pipeline.file = file.open("w", encoding="utf-8")

    pipeline.close_spider(spider=None)

    assert file.read_text(encoding="utf-8") == ""


def test_pipeline_creates_output_directory(tmp_path, monkeypatch):
    output_file = tmp_path / "missing" / "directory" / "movies.jsonl"
    monkeypatch.setattr(pipeline_module, "DATA_FILE", output_file)
    crawler = get_crawler(MovieSpider)
    spider = MovieSpider.from_crawler(crawler)
    pipeline = JsonPipeline()

    pipeline.open_spider(spider)

    assert output_file.parent.is_dir()
    assert pipeline.temp_file_path is not None
    assert pipeline.temp_file_path.parent == output_file.parent
    pipeline.close_spider(spider)
    pipeline._on_spider_closed(spider, "cancelled")


def test_pipeline_overwrites_existing_file(tmp_path, monkeypatch):
    output_file = tmp_path / "movies.jsonl"
    output_file.write_text("old contents\n", encoding="utf-8")
    monkeypatch.setattr(pipeline_module, "DATA_FILE", output_file)
    crawler = get_crawler(MovieSpider)
    spider = MovieSpider.from_crawler(crawler)
    pipeline = JsonPipeline()
    movie = Movie(id=1, title="Новый фильм")

    pipeline.open_spider(spider)
    pipeline.process_item(movie, spider)
    pipeline.close_spider(spider)
    pipeline._on_spider_closed(spider, "finished")

    assert output_file.read_text(encoding="utf-8") == (
        json.dumps(movie.model_dump(), ensure_ascii=False) + "\n"
    )
    assert crawler.stats.get_value("scraper/export_committed") is True


def test_pipeline_writes_valid_json():
    pipeline = JsonPipeline()
    pipeline.file = StringIO()
    movie = Movie(id=1, title="Интерстеллар")

    pipeline.process_item(movie, spider=None)

    assert json.loads(pipeline.file.getvalue()) == movie.model_dump()
