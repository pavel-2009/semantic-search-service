import json
from pathlib import Path

import pytest
from scrapy import signals
from scrapy.crawler import Crawler
from scrapy.statscollectors import MemoryStatsCollector
from twisted.python.failure import Failure

from scraper.pipelines import JsonPipeline
from scraper.schemas import Movie
from scraper.spiders.movie_spider import MovieSpider


@pytest.fixture
def pipeline_setup(tmp_path, monkeypatch):
    data_file = tmp_path / "movies.json"
    data_file.write_text('[{"id": 99}]', encoding="utf-8")
    monkeypatch.setattr("scraper.pipelines.DATA_FILE", data_file)

    crawler = Crawler(MovieSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = crawler._create_spider()
    pipeline = JsonPipeline()
    pipeline.open_spider(spider)
    return data_file, crawler, spider, pipeline


def close_spider(crawler, spider, pipeline, reason="finished"):
    pipeline.close_spider(spider)
    crawler.signals.send_catch_log(
        signal=signals.spider_closed,
        spider=spider,
        reason=reason,
    )


def test_pipeline_commits_export_after_successful_crawl(pipeline_setup):
    data_file, crawler, spider, pipeline = pipeline_setup
    pipeline.process_item(Movie(id=1, title="Movie"), spider)
    temp_file = pipeline.temp_file_path

    close_spider(crawler, spider, pipeline)

    assert json.loads(data_file.read_text(encoding="utf-8")) == [
        {
            "id": 1,
            "title": "Movie",
            "year": None,
            "country": None,
            "director": None,
            "description": "",
            "actors": [],
            "genres": [],
            "rating": None,
            "poster_url": None,
        }
    ]
    assert temp_file is not None and not temp_file.exists()
    assert crawler.stats.get_value("scraper/export_committed") is True


@pytest.mark.parametrize(
    ("reason", "failure", "stat", "stat_value"),
    [
        ("shutdown", False, None, None),
        ("finished", True, None, None),
        ("finished", False, "retry/max_reached", 1),
        ("finished", False, "httperror/response_ignored_count", 1),
        ("finished", False, "scraper/parse_errors", 1),
    ],
)
def test_pipeline_preserves_previous_export_when_crawl_fails(
    pipeline_setup, reason, failure, stat, stat_value
):
    data_file, crawler, spider, pipeline = pipeline_setup
    original_data = data_file.read_text(encoding="utf-8")
    pipeline.process_item(Movie(id=1, title="New movie"), spider)
    if failure:
        crawler.signals.send_catch_log(
            signal=signals.spider_error,
            failure=Failure(ValueError("parse failed")),
            response=None,
            spider=spider,
        )
    if stat is not None:
        crawler.stats.set_value(stat, stat_value)
    temp_file = pipeline.temp_file_path

    close_spider(crawler, spider, pipeline, reason)

    assert data_file.read_text(encoding="utf-8") == original_data
    assert temp_file is not None and not temp_file.exists()
    assert crawler.stats.get_value("scraper/export_committed") is False


def test_pipeline_preserves_previous_export_if_atomic_replace_fails(
    pipeline_setup, monkeypatch
):
    data_file, crawler, spider, pipeline = pipeline_setup
    original_data = data_file.read_text(encoding="utf-8")
    pipeline.process_item(Movie(id=1, title="New movie"), spider)

    def fail_replace(self, target):
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)
    close_spider(crawler, spider, pipeline)

    assert data_file.read_text(encoding="utf-8") == original_data
    assert crawler.stats.get_value("scraper/export_committed") is False
