"""Spider for Kinopoisk search"""

from typing import Set, List

import scrapy
from scrapy.http import Response
import re
from playwright.async_api import Page


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
        page: Page = response.meta["playwright_page"]

        movie_links: set[str] = set()
        no_new_movies = 0

        while no_new_movies < 3:
            links = await page.locator("a").evaluate_all(
                "elements => elements.map(el => el.href)"
            )

            current_movies = {
                link
                for link in links
                if re.search(r"/watch/\d+$", link)
            }

            old_count = len(movie_links)

            movie_links.update(current_movies)

            new_count = len(movie_links)

            if new_count == old_count:
                no_new_movies += 1
            else:
                no_new_movies = 0

            await page.mouse.wheel(0, 2000)

            await page.wait_for_timeout(1500)

        for link in movie_links:

            yield scrapy.Request(
                link,
                callback=self.parse_film,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                },
            )

        await page.close()
        
    async def parse_film(self, response: Response):
        page: Page = response.meta["playwright_page"]
        await page.locator("div.nbl-arrowButton__caption").click()

        name = response.css(
            "h1.title__header::text"
        ).get()

        params_list1 = response.css(
            "div.paramsList.paramsList__badges > ul.paramsList__container > div.nbl-textBadge__text::text"
        ).getall()

        country = params_list[0]
        tags = params_list[1:]

        params_list2 = response.css(
            "div.paramsList.params__paramsList > ul.paramsList__container > *"
        ).getall()
        rating = params_list2[0].get()
        year = params_list2[0].get()

        description = ""

        desc_text = response.css(
            "div.clause__text-inner > p"
        ).getall()
        
        for p in desc_text:
            description += p.get() + '\n\n'

        


    async def get_movie_links(self, page: Page) -> Set[str]:
        links: List[str] = await page.locator("a").evaluate_all(
            "elements => elements.map(el => el.href)"
        )

        return {
            link
            for link in links
            if re.search(r"/watch/\d+$", link)
        }
