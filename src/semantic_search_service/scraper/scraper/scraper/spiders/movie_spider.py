"""Spider for Kinopoisk search"""

# from typing import Any, Generator

import scrapy
from scrapy.http import Response


class MovieScrapy(scrapy.Spider):
    name = "movies"

    start_urls = [
        "https://www.ivi.ru/movies"
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                },
            )

    def parse(self, response: Response):
        links = response.css(
            'a[data-test="collection_header"]::attr(href)'
        ).getall()

        for link in links:
            print(link)
            yield response.follow(link, callback=self.parse_collections)

    def parse_collections(self, response: Response):
        ...
