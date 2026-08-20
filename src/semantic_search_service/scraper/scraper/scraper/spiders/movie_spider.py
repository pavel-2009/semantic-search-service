import re

import scrapy
from playwright.async_api import Locator, Page
from scrapy.http import Response

from semantic_search_service.scraper.schemas import Movie

MAX_COLLECTIONS = 2
MAX_MOVIES_PER_COLLECTION = 10
SCROLL_STALE_LIMIT = 3
MOVIE_LINK_PATTERN = re.compile(r"/watch/\d+$")


class MovieSpider(scrapy.Spider):
    name = "movies"
    start_urls = ["https://www.ivi.ru/movies"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response: Response):
        links = response.css('a[data-test="collection_header"]::attr(href)').getall()

        for link in links[:MAX_COLLECTIONS]:
            yield response.follow(
                link,
                callback=self.parse_collections,
                meta=self.playwright_meta(),
            )

    async def parse_collections(self, response: Response):
        page: Page = response.meta["playwright_page"]

        try:
            movie_links = await self.collect_movie_links(page)
            self.logger.info(
                "Collected %d movie links from %s",
                len(movie_links),
                response.url,
            )

            for link in list(movie_links)[:MAX_MOVIES_PER_COLLECTION]:
                yield scrapy.Request(
                    link,
                    callback=self.parse_film,
                    meta=self.playwright_meta(),
                )
        except Exception:
            self.logger.exception("Failed to parse collection: %s", response.url)
        finally:
            await page.close()

    async def parse_film(self, response: Response):
        page: Page = response.meta["playwright_page"]

        try:
            await self.expand_description(page)

            movie = Movie(
                name=await self.get_text(page, "h1.title__header"),
                year=await self.get_year(page),
                country=await self.get_optional_text(
                    page,
                    "tr:has(th.nbl-plankMeta__title:has-text('Страны')) td",
                ),
                director=await self.get_director(page),
                description=await self.get_description(page),
                actors=await self.get_actors(page),
                tags=await self.get_all_text(
                    page,
                    "tr:has(th.nbl-plankMeta__title:has-text('Жанр')) td a",
                ),
                rating=await self.get_rating(page),
            )

            self.logger.info("Parsed movie: %s (%s)", movie.name, movie.year)
            yield movie
        except Exception:
            self.logger.exception("Failed to parse movie: %s", response.url)
        finally:
            await page.close()

    async def collect_movie_links(self, page: Page) -> list[str]:
        movie_links: set[str] = set()
        stale_scrolls = 0

        while stale_scrolls < SCROLL_STALE_LIMIT:
            current_movies = await self.get_movie_links(page)
            old_count = len(movie_links)
            movie_links.update(current_movies)

            stale_scrolls = stale_scrolls + 1 if len(movie_links) == old_count else 0

            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(1500)

        return sorted(movie_links)

    @staticmethod
    async def expand_description(page: Page) -> None:
        button = page.get_by_text("Показать больше", exact=True).first

        if await button.count() == 0 or not await button.is_visible():
            return

        await button.scroll_into_view_if_needed()
        await button.click()
        await page.wait_for_timeout(300)

    @staticmethod
    async def get_text(page: Page, selector: str) -> str:
        return (await page.locator(selector).first.inner_text()).strip()

    @classmethod
    async def get_optional_text(cls, page: Page, selector: str) -> str | None:
        locator = page.locator(selector).first

        if await locator.count() == 0:
            return None

        value = (await locator.inner_text()).strip()
        return value or None

    @staticmethod
    async def get_all_text(page: Page, selector: str) -> list[str]:
        return [
            text.strip() for text in await page.locator(selector).all_inner_texts() if text.strip()
        ]

    @classmethod
    async def get_year(cls, page: Page) -> int | None:
        value = await cls.get_optional_text(
            page,
            "tr:has(th.nbl-plankMeta__title:has-text('Год')) td",
        )

        return int(value) if value and value.isdigit() else None

    @classmethod
    async def get_rating(cls, page: Page) -> float | None:
        params = await cls.get_all_text(
            page,
            "div.paramsList.params__paramsList > ul.paramsList__container > *",
        )

        if not params:
            return None

        try:
            return float(params[0].replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    async def get_description(page: Page) -> str:
        paragraphs = await page.locator('[data-test="description_text"] p').all_inner_texts()
        return "\n\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())

    @classmethod
    async def get_director(cls, page: Page) -> str | None:
        person_list = page.locator('div.gallery__list > div[data-test="persons_item"]')

        if await person_list.count() == 0:
            return None

        return await cls.parse_person(person_list.nth(0))

    @classmethod
    async def get_actors(cls, page: Page) -> list[str]:
        person_list = page.locator('div.gallery__list > div[data-test="persons_item"]')
        person_count = await person_list.count()

        return [await cls.parse_person(person_list.nth(index)) for index in range(1, person_count)]

    @staticmethod
    async def parse_person(person: Locator) -> str:
        title = await person.locator("div.nbl-fixedSlimPosterBlock__title").inner_text()
        second_title = await person.locator(
            "div.nbl-fixedSlimPosterBlock__secondTitle"
        ).inner_text()

        return f"{title} {second_title}".strip()

    @staticmethod
    async def get_movie_links(page: Page) -> set[str]:
        links: list[str] = await page.locator("a").evaluate_all(
            "elements => elements.map(element => element.href)",
        )

        return {link for link in links if MOVIE_LINK_PATTERN.search(link)}

    @staticmethod
    def playwright_meta() -> dict[str, bool]:
        return {
            "playwright": True,
            "playwright_include_page": True,
        }
