import json
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TextIO

from scrapy import signals
from scrapy.spiders import Spider

from scraper.schemas import Movie

DATA_FILE = Path(__file__).resolve().parent / "data" / "movies.jsonl"
logger = logging.getLogger(__name__)


class JsonPipeline:
    """Write scraped movies as JSON Lines and commit only successful crawls."""

    file: TextIO | None = None
    temp_file_path: Path | None = None
    failed: bool = False
    item_count: int = 0

    def open_spider(self, spider: Spider) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_FILE.parent,
            prefix=f".{DATA_FILE.name}.",
            suffix=".tmp",
            delete=False,
        )
        self.file = temp_file
        temp_file_path = Path(temp_file.name)
        self.temp_file_path = temp_file_path
        self.failed = False
        self.item_count = 0
        spider.crawler.stats.set_value("scraper/export_committed", False)
        spider.crawler.stats.set_value("scraper/failed", False)
        spider.crawler.signals.connect(self._on_spider_error, signal=signals.spider_error)
        spider.crawler.signals.connect(self._on_spider_closed, signal=signals.spider_closed)

    def process_item(self, item: Movie, spider: Spider) -> Movie:
        try:
            if self.file is None:
                raise RuntimeError("JSON pipeline file is not open")
            self.file.write(json.dumps(item.model_dump(), ensure_ascii=False) + "\n")
            self.item_count += 1
        except Exception:
            self.failed = True
            raise
        return item

    def close_spider(self, spider: Spider) -> None:
        if self.file is None:
            return
        file = self.file
        try:
            file.close()
        except Exception:
            self.failed = True
            raise
        finally:
            self.file = None

    def _on_spider_error(self, failure: object, response: object, spider: Spider) -> None:
        self.failed = True
        spider.crawler.stats.set_value("scraper/failed", True)

    def _on_spider_closed(self, spider: Spider, reason: str) -> None:
        temp_file_path = self.temp_file_path
        if temp_file_path is None:
            return

        stats = spider.crawler.stats
        ignored_http_responses = stats.get_value("httperror/response_ignored_count", 0)
        rate_limited_responses = stats.get_value(
            "httperror/response_ignored_status_count/403", 0
        )
        successful = (
            reason == "finished"
            and self.file is None
            and not self.failed
            and not stats.get_value("scraper/failed", False)
            and stats.get_value("retry/max_reached", 0) == 0
            and ignored_http_responses == rate_limited_responses
            and stats.get_value("scraper/rejected_records", 0) == 0
            and self.item_count > 0
        )
        if successful:
            if rate_limited_responses:
                logger.warning(
                    "API limit reached (HTTP 403); committing partial export: "
                    "responses=%d movies=%d",
                    rate_limited_responses,
                    self.item_count,
                )
            try:
                temp_file_path.replace(DATA_FILE)
            except OSError:
                logger.exception("Failed to replace movie data file")
                self._remove_temp_file(temp_file_path)
                return
            stats.set_value("scraper/export_committed", True)
            logger.info("Committed scraped movie data: path=%s", DATA_FILE)
            return

        logger.error(
            "Scraper export not committed: reason=%s spider_errors=%s "
            "retry_exhausted=%s ignored_http_responses=%s rejected_records=%s "
            "response_validation_errors=%s movies_written=%d",
            reason,
            self.failed,
            stats.get_value("retry/max_reached", 0),
            ignored_http_responses,
            stats.get_value("scraper/rejected_records", 0),
            stats.get_value("scraper/response_validation_errors", 0),
            self.item_count,
        )
        self._remove_temp_file(temp_file_path)

    @staticmethod
    def _remove_temp_file(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to remove temporary movie data file: path=%s", path)
