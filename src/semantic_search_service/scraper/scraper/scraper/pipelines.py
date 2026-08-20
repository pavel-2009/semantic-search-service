# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json

from scrapy.spiders import Spider

from src.semantic_search_service.scraper.schemas import Movie


class JsonPipeline:
    def open_spider(self, spider: Spider):
        self.file = open(
            "data/movies.json",
            "w",
            encoding="utf-8",
        )

        self.file.write("[\n")
        self.first_item = True

    
