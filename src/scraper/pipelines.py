import json
from pathlib import Path
from typing import TextIO

from scrapy.spiders import Spider

from scraper.schemas import Movie

DATA_FILE = Path(__file__).resolve().parent / "data" / "movies.json"


class JsonPipeline:
    """Write scraped movies to a JSON array."""

    file: TextIO
    first_item: bool

    def open_spider(self, spider: Spider) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.file = DATA_FILE.open("w", encoding="utf-8")
        self.file.write("[\n")
        self.first_item = True

    def process_item(self, item: Movie, spider: Spider) -> Movie:
        if not self.first_item:
            self.file.write(",\n")
        json.dump(item.model_dump(), self.file, ensure_ascii=False, indent=2)
        self.first_item = False
        return item

    def close_spider(self, spider: Spider) -> None:
        self.file.write("\n]\n")
        self.file.close()
