# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json
from contextlib import ExitStack
from pathlib import Path
from typing import TextIO

from scrapy.spiders import Spider

from semantic_search_service.scraper.schemas import Movie

DATA_DIR = Path("data")
MOVIES_FILE = DATA_DIR / "movies.json"


class JsonPipeline:
    def open_spider(self, spider: Spider) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self.exit_stack = ExitStack()
        self.file: TextIO = self.exit_stack.enter_context(MOVIES_FILE.open("w", encoding="utf-8"))
        self.file.write("[\n")
        self.first_item = True

    def process_item(self, item: Movie, spider: Spider) -> Movie:
        if not self.first_item:
            self.file.write(",\n")

        json.dump(
            item.model_dump(),
            self.file,
            ensure_ascii=False,
            indent=2,
        )

        self.first_item = False
        return item

    def close_spider(self, spider: Spider) -> None:
        self.file.write("\n]\n")
        self.exit_stack.close()
