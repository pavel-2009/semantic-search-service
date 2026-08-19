"""Spider for Kinopoisk search"""

from typing import Any, Generator

import scrapy
from scrapy.http import Response


class MovieScrapy(scrapy.Spider):
    name = "movies"

    def start_requests(self) -> Generator[Any]:
        yield scrapy.Request(
            "https://www.kinopoisk.ru/lists/categories/movies/",
            callback=self.parse
        )

    def parse(self, response: Response):
        print(response.url)
