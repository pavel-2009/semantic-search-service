"""Spider for Kinopoisk search"""

# from typing import Any, Generator

import scrapy
from scrapy.http import Response


class MovieScrapy(scrapy.Spider):
    name = "movies"

    start_urls = [
        "https://www.ivi.ru/movies"
    ]

    def parse(self, response: Response):
        links = response.css(
            'a[data-test="collection_header"]::attr(href)'
        ).getall()

        for link in links:
            yield response.follow(link, callback=self.parse_collections)

    def parse_collections(self, response: Response):
        ...
