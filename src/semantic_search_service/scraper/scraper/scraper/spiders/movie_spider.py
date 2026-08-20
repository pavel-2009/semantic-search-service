"""Spider for Kinopoisk search"""
import re

import scrapy
from playwright.async_api import Page
from scrapy.http import Response

from src.semantic_search_service.scraper.schemas import Movie


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
            current_movies = await self.get_movie_links(page)

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

        await page.locator(
            "div.nbl-arrowButton__caption"
        ).click()

        name = await page.locator(
            "h1.title__header"
        ).inner_text()

        params_list1 = await page.locator(
            "div.paramsList.paramsList__badges "
            "> ul.paramsList__container "
            "> div.nbl-textBadge__text"
        ).all_inner_texts()

        country = params_list1[0] if params_list1 else None
        tags = params_list1[1:] if len(params_list1) > 1 else []

        params_list2 = await page.locator(
            "div.paramsList.params__paramsList "
            "> ul.paramsList__container > *"
        ).all_inner_texts()

        rating = params_list2[0] if len(params_list2) > 0 else None
        year = params_list2[1] if len(params_list2) > 1 else None

        description = "\n\n".join(
            " ".join(p.css("::text").getall()).strip()
            for p in response.css(
                "div.clause__text-inner > p"
            )
        )

        person_list = response.css(
            "div.gallery__list > div.persons_item"
        )
        director = person_list[0].css(
            "div.nbl-fixedSlimPosterBlock__title"
        ).get() + " " + person_list[0].css(
            "div.nbl-fixedSlimPosterBlock__secondTitle"
        ).get()

        actors = [
            p.css(
                "div.nbl-fixedSlimPosterBlock__title"
            ).get() + " " + p.css(
                "div.nbl-fixedSlimPosterBlock__secondTitle"
            ).get()
            for p in person_list[1:]
        ]

        movie = Movie(
            name=name,
            year=int(year),
            country=country,
            director=director,
            description=description,
            actors=actors,
            tags=tags,
            rating=rating
        )

        await page.close()

    async def get_movie_links(self, page: Page) -> set[str]:
        links: list[str] = await page.locator("a").evaluate_all(
            "elements => elements.map(el => el.href)"
        )

        return {
            link
            for link in links
            if re.search(r"/watch/\d+$", link)
        }