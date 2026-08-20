import re

import scrapy
from playwright.async_api import Page, Locator
from scrapy.http import Response

from semantic_search_service.scraper.schemas import Movie


class MovieSpider(scrapy.Spider):
    name = "movies"

    start_urls = [
        "https://www.ivi.ru/movies",
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

        try:
            movie_links: set[str] = set()
            no_new_movies = 0

            while no_new_movies < 3:
                current_movies = await self.get_movie_links(page)

                old_count = len(movie_links)
                movie_links.update(current_movies)

                if len(movie_links) == old_count:
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

        finally:
            await page.close()

    async def parse_film(self, response: Response):
        page: Page = response.meta["playwright_page"]

        try:
            await page.get_by_text(
                "Показать больше",
                exact=True,
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
            tags = params_list1[1:]

            params_list2 = await page.locator(
                "div.paramsList.params__paramsList "
                "> ul.paramsList__container > *"
            ).all_inner_texts()

            rating: float | None = None

            if params_list2:
                rating = float(params_list2[0].replace(",", "."))

            year = (
                params_list2[1]
                if len(params_list2) > 1
                else None
            )

            description = await page.locator(
                "div.clause__text-inner"
            ).inner_text()

            person_list = page.locator(
                "div.gallery__list > div.persons_item"
            )

            person_count = await person_list.count()

            director = (
                await self.parse_person(person_list.nth(0))
                if person_count > 0
                else None
            )

            actors = [
                await self.parse_person(person_list.nth(i))
                for i in range(1, person_count)
            ]

            movie = Movie(
                name=name,
                year=int(year) if year else None,
                country=country,
                director=director,
                description=description,
                actors=actors,
                tags=tags,
                rating=rating
            )

            yield movie

        except Exception as e:
            with open('errors.log', 'a') as f:
                f.write(str(e) + '\n')

        finally:
            await page.close()

    @staticmethod
    async def parse_person(person: Locator) -> str:
        title = await person.locator(
            "div.nbl-fixedSlimPosterBlock__title"
        ).inner_text()

        second_title = await person.locator(
            "div.nbl-fixedSlimPosterBlock__secondTitle"
        ).inner_text()

        return f"{title} {second_title}".strip()

    @staticmethod
    async def get_movie_links(page: Page) -> set[str]:
        links: list[str] = await page.locator(
            "a"
        ).evaluate_all(
            "elements => elements.map(el => el.href)"
        )

        return {
            link
            for link in links
            if re.search(r"/watch/\d+$", link)
        }