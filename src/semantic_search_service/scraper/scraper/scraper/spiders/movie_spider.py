"""Spider for Kinopoisk search"""

# from typing import Any, Generator

import scrapy
from scrapy.http import Response


class MovieScrapy(scrapy.Spider):
    name = "movies"

    start_urls = [
        "https://www.kinopoisk.ru/lists/categories/movies/"
    ]

    def parse(self, response: Response):
        print("STATUS:", response.status)
        print("URL:", response.url)
