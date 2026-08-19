"""Spider for Kinopoisk search"""

from typing import Set, List

import scrapy
from scrapy.http import Response
import re


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
            )

    def parse(self, response: Response):
        links = response.css(
            'a[data-test="collection_header"]::attr(href)'
        ).getall()

        for link in links:
            yield response.follow(
                link, 
                callback=self.parse_collections,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                },
            )

    async def parse_collections(self, response: Response):
        page = response.meta["playwright_page"]

        while True:
            current_count = await page.locator(
                "a"
            ).count()

            await page.mouse.wheel(0, 2000)

            await page.wait_for_timeout(1000)

            new_count = await page.locator(
                "a"
            ).count()

            if current_count == new_count:
                break

        links = await page.locator("a").evaluate_all(
            "elements => elements.map(el => el.href)"
        )

        movie_links = [
            link
            for link in links
            if re.search(r"/watch/\d+$", link)
        ]

        for link in movie_links:
            with open('links.txt', 'a') as f:
                f.write(link + '\n')

            yield response.follow(
                link,
                callback=self.parse_film
            )

    def parse_film(self, response: Response):
        ...


async def get_movie_links(page) -> Set[str]:
    links: List[str] = await page.locator("a").evaluate_all(
        "elements => elements.map(el => el.href)"
    )

    return {
        link
        for link in links
        if re.search(r"/watch/\d+$", link)
    }