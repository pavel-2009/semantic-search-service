# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json

from scrapy.spiders import Spider

from semantic_search_service.scraper.schemas import Movie


class JsonPipeline:
    def open_spider(self, spider: Spider):
        self.file = open(
            "data/movies.json",
            "w",
            encoding="utf-8",
        )

        self.file.write("[\n")
        self.first_item = True

    def process_item(self, item: Movie, spider: Spider):
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

    def close_spider(self, spider: Spider):
        self.file.write("\n]\n")
        self.file.close()
