import re

import scrapy
from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError
from scrapy.http import Response
import random

from semantic_search_service.scraper.schemas import Movie

SCROLL_STALE_LIMIT = 3
MOVIE_LINK_PATTERN = re.compile(r"/watch/\d+$")


class MovieSpider(scrapy.Spider):
    name = "movies"
    start_urls = ["https://www.ivi.ru/movies"]

    async def playwright_page_init(self, page: Page) -> None:
        
        await page.add_init_script("""
            // Удаляем признак webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Добавляем плагины 
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin' },
                    { name: 'Chrome PDF Viewer' },
                    { name: 'Native Client' }
                ]
            });
            
            // Добавляем языки
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
            
            // Добавляем историю
            window.history.pushState(null, null, window.location.href);
            
            // Эмулируем реальный экран
            Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
            Object.defineProperty(screen, 'availHeight', { get: () => 1080 });
            
            // Удаляем другие следы автоматизации
            delete navigator.__proto__.webdriver;
        """)
        
        await page.set_viewport_size({"width": 1920, "height": 1080})
        

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse, meta=self.playwright_meta())

    def parse(self, response: Response):
        links = response.css('a[data-test="collection_header"]::attr(href)').getall()

        for link in links:
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

            for link in list(movie_links):
                yield scrapy.Request(
                    link,
                    callback=self.parse_film,
                    meta=self.playwright_meta(),
                    priority=10,
                    dont_filter=True,
                )
                
        except Exception:
            self.logger.exception("Failed to parse collection: %s", response.url)
        finally:
            await page.close()

    async def parse_film(self, response: Response):
        page = response.meta.get("playwright_page")
        
        if not page:
            self.logger.warning("No page for %s, retrying", response.url)
            yield scrapy.Request(
                response.url,
                callback=self.parse_film,
                meta=self.playwright_meta(),
                priority=30,
                dont_filter=True,
            )
            return

        try:
            # ===== ДИАГНОСТИЧЕСКИЙ БЛОК =====
            # Проверяем статус
            if hasattr(response, 'status') and response.status != 200:
                self.logger.warning("Non-200 status %d for %s", response.status, response.url)
                if response.status in [403, 429]:
                    self.logger.warning("Rate limited or blocked, waiting 60s...")
                    await page.wait_for_timeout(60000)
                    yield scrapy.Request(
                        response.url,
                        callback=self.parse_film,
                        meta=self.playwright_meta(),
                        priority=50,
                        dont_filter=True,
                    )
                    return
                elif response.status == 404:
                    self.logger.warning("Movie not found: %s", response.url)
                    return
            
            # Проверяем содержимое
            content = await page.content()
            content_size = len(content)
            
            # Проверяем на капчу
            captcha_keywords = ["captcha", "проверка", "verify", "blocked", "доступ ограничен"]
            if any(keyword in content.lower() for keyword in captcha_keywords):
                self.logger.error("🚨 CAPTCHA or block detected on %s", response.url)
                
                # Сохраняем для анализа
                debug_filename = f"captcha_{response.url.split('/')[-1]}.html"
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info("Saved captcha page to %s", debug_filename)
                
                # Ждем и пробуем снова с большим таймаутом
                await page.wait_for_timeout(30000)
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_film,
                    meta=self.playwright_meta(),
                    priority=60,
                    dont_filter=True,
                )
                return
            
            # Если страница слишком маленькая
            if content_size < 15000:
                self.logger.warning("⚠️ Small page: %d bytes, might be blocked", content_size)
                debug_filename = f"small_{response.url.split('/')[-1]}.html"
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info("Saved small page to %s", debug_filename)
                
                # Пробуем обновить
                await page.reload()
                await page.wait_for_timeout(5000)
                
                # Проверяем снова
                content = await page.content()
                if len(content) < 15000:
                    self.logger.warning("Still small after reload, skipping %s", response.url)
                    return
            
            # ===== ОСНОВНОЙ ПАРСИНГ =====
            # Ждем основные элементы
            try:
                await page.wait_for_selector('h1.title__header', timeout=30000)
            except PlaywrightTimeoutError:
                self.logger.warning("Timeout waiting for title on %s", response.url)
                # Пробуем еще раз
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_film,
                    meta=self.playwright_meta(),
                    priority=30,
                    dont_filter=True,
                )
                return

            # Раскрываем описание (если есть кнопка)
            await self.expand_description(page)

            # Парсим данные
            film_id = int(response.url.rstrip("/").split("/")[-1])

            movie = Movie(
                id=film_id,
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

            self.logger.info("✅ Parsed movie: %s (%s)", movie.name, movie.year)
            
            # Случайная задержка после успешного парсинга
            await page.wait_for_timeout(random.randint(1000, 3000))
            
            yield movie
            
        except PlaywrightTimeoutError as e:
            self.logger.warning("Timeout parsing %s: %s", response.url, str(e))
            yield scrapy.Request(
                response.url,
                callback=self.parse_film,
                meta=self.playwright_meta(),
                priority=40,
                dont_filter=True,
            )
        except Exception as e:
            self.logger.exception("Failed to parse movie: %s", response.url)
            # Сохраняем страницу для отладки
            try:
                content = await page.content()
                with open(f"error_{response.url.split('/')[-1]}.html", "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
                pass
        finally:
            try:
                await page.close()
            except Exception:
                pass

    async def collect_movie_links(self, page: Page) -> list[str]:
        movie_links: set[str] = set()
        stale_scrolls = 0
        
        await page.wait_for_timeout(random.randint(1000, 3000))

        while stale_scrolls < SCROLL_STALE_LIMIT:
            current_movies = await self.get_movie_links(page)
            old_count = len(movie_links)
            movie_links.update(current_movies)

            stale_scrolls = stale_scrolls + 1 if len(movie_links) == old_count else 0

            scroll_distance = random.randint(1500, 2500)
            await page.mouse.wheel(0, scroll_distance)
            
            await page.wait_for_timeout(random.randint(1000, 2000))

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
        parts = await person.locator(
            "div.nbl-fixedSlimPosterBlock__title, "
            "div.nbl-fixedSlimPosterBlock__secondTitle"
        ).all_text_contents()

        return " ".join(part.strip() for part in parts if part.strip())

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
            "playwright_page_init": MovieSpider.playwright_page_init,   # type: ignore
            "playwright_page_goto_kwargs": {
                "wait_until": "domcontentloaded",  
                "timeout": 60000,
            },
            "playwright_context_kwargs": { 
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport": {"width": 1920, "height": 1080},
                "locale": "ru-RU",
                "timezone_id": "Europe/Moscow",
                "geolocation": {"latitude": 55.7558, "longitude": 37.6173},
                "permissions": ["geolocation"],
            }
        }