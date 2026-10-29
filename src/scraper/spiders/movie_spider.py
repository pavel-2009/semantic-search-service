"""Scrapy spider for collecting movies from the PoiskKino API."""

from collections.abc import AsyncGenerator, Generator
from urllib.parse import urlencode

import scrapy
from scrapy.addons import logger
from scrapy.http import Request, Response
from pydantic import ValidationError

from core.config import settings
from scraper.schemas import (
    Movie,
    PoiskKinoCountry,
    PoiskKinoGenre,
    PoiskKinoMovie,
    PoiskKinoPerson,
    PoiskKinoPoster,
    PoiskKinoResponse,
)


class MovieSpider(scrapy.Spider):
    """Collect normalized movie records from PoiskKino."""

    name = "movies"

    API_BASE = "https://api.poiskkino.dev/v1.4/movie"
    PAGE_SIZE = 50
    MAX_PAGES = settings.MAX_PAGES_SCRAPER

    async def start(self) -> AsyncGenerator[Request, None]:
        """Start ten page ranges, each covering up to ten pages."""
        runs = self.settings.getint("SCRAPER_RUNS", 10)
        pages_per_run = self.settings.getint("SCRAPER_PAGES_PER_RUN", 10)
        for run in range(runs):
            start_page = run * pages_per_run + 1
            if start_page > self.MAX_PAGES:
                break
            end_page = min(start_page + pages_per_run - 1, self.MAX_PAGES)
            yield Request(
                url=self._movie_list_url(start_page),
                callback=self.parse,
                meta={"page": start_page, "run_end_page": end_page},
            )

    def parse(self, response: Response) -> Generator[Request | Movie, None, None]:
        """Parse one paginated PoiskKino response."""
        page = int(response.meta.get("page", 1))
        try:
            data = PoiskKinoResponse.model_validate_json(response.body)
        except ValidationError as exc:
            reason = str(exc)
            self.logger.error(
                "Failed to validate API response: page=%d reason=%s",
                page,
                reason,
            )
            self.crawler.stats.set_value("scraper/failed", True)
            self.crawler.stats.inc_value("scraper/response_validation_errors")
            raise

        if data.page != page:
            self.logger.error(
                "API response page does not match request: requested=%d received=%d",
                page,
                data.page,
            )
            self.crawler.stats.set_value("scraper/failed", True)
            self.crawler.stats.inc_value("scraper/pagination_errors")
            raise ValueError(
                f"Requested page {page}, but API returned page {data.page}"
            )

        self.crawler.stats.inc_value("scraper/pages_succeeded")
        self.logger.info("Found %d movies on page %d", len(data.docs), page)

        for movie_data in data.docs:
            movie = self._parse_movie(movie_data)
            if movie is not None:
                yield movie

        self.logger.info("Page %d of %d", page, data.pages)

        run_end_page = int(response.meta.get("run_end_page", self.MAX_PAGES))
        if page >= run_end_page:
            self.logger.info("Reached run page limit (%d)", run_end_page)
            return

        if page >= data.pages:
            self.logger.info("Reached last page (%d of %d)", page, data.pages)
            return

        next_page = page + 1
        yield Request(
            url=self._movie_list_url(next_page),
            callback=self.parse,
            meta={"page": next_page, "run_end_page": run_end_page},
        )

    def _parse_movie(self, data: PoiskKinoMovie) -> Movie | None:
        """Convert one PoiskKino movie into the normalized movie contract."""
        try:
            return Movie(
                id=data.id,
                title=data.name or data.alternativeName or "Без названия",
                year=data.year,
                country=self._extract_countries(data.countries),
                director=self._extract_director(data.persons),
                description=data.description or data.shortDescription or "",
                actors=self._extract_actors(data.persons),
                genres=self._extract_genres(data.genres),
                rating=data.rating.kp,
                poster_url=self._extract_poster_url(data.poster),
            )
        except (TypeError, ValueError) as exc:
            self.logger.error("Failed to parse movie %s: %s", data.id, exc)
            self.crawler.stats.inc_value("scraper/rejected_records")
            return None

    def closed(self, reason: str) -> None:
        """Log a final summary using Scrapy's standard request and item stats."""
        stats = self.crawler.stats.get_stats()
        response_status_prefix = "downloader/response_status_count/"
        failed_http_responses = sum(
            value
            for key, value in stats.items()
            if key.startswith(response_status_prefix)
            and key.removeprefix(response_status_prefix).isdecimal()
            and int(key.removeprefix(response_status_prefix)) >= 400
        )
        failed_requests = stats.get("downloader/exception_count", 0) + failed_http_responses
        rejected_records = (
            stats.get("scraper/rejected_records", 0)
            + stats.get("item_dropped_count", 0)
        )

        self.logger.info(
            "Scraper summary: successful_pages=%d failed_requests=%d "
            "extracted_movies=%d rejected_records=%d finish_reason=%s",
            stats.get("scraper/pages_succeeded", 0),
            failed_requests,
            stats.get("item_scraped_count", 0),
            rejected_records,
            reason,
        )

    def _movie_list_url(self, page: int) -> str:
        """Build a URL for a specific API page."""
        params = {
            "page": page,
            "limit": self.PAGE_SIZE,
            "sortField": "rating.kp",
            "sortType": "-1",
        }
        return f"{self.API_BASE}?{urlencode(params)}"

    @staticmethod
    def _extract_poster_url(poster: PoiskKinoPoster) -> str | None:
        """Extract a usable poster URL."""
        try:
            url = poster.url or poster.previewUrl
            return str(url) if url else None
        except (TypeError, ValueError) as exc:
            logger.error("Failed to extract poster URL: %s", exc)
            raise

    @staticmethod
    def _extract_countries(countries: list[PoiskKinoCountry]) -> str | None:
        """Extract country names from API objects."""
        try:
            names = [str(country.name) for country in countries if country.name]
            return ", ".join(names) if names else None
        except (TypeError, ValueError) as exc:
            logger.error("Failed to extract countries: %s", exc)
            raise

    @staticmethod
    def _extract_director(persons: list[PoiskKinoPerson]) -> str | None:
        """Extract the first director name."""
        try:
            for person in persons:
                if person.profession != "режиссеры":
                    continue
                name = person.name or person.enName
                if name:
                    return str(name)
            return None
        except (TypeError, ValueError) as exc:
            logger.error("Failed to extract director: %s", exc)
            raise

    @staticmethod
    def _extract_actors(persons: list[PoiskKinoPerson]) -> list[str]:
        """Extract actor names."""
        try:
            return [
                str(name)
                for person in persons
                if person.profession == "актеры"
                for name in [person.name or person.enName]
                if name
            ]
        except (TypeError, ValueError) as exc:
            logger.error("Failed to extract actors: %s", exc)
            raise

    @staticmethod
    def _extract_genres(genres: list[PoiskKinoGenre]) -> list[str]:
        """Extract genre names."""
        try:
            return [str(genre.name) for genre in genres if genre.name]
        except (TypeError, ValueError) as exc:
            logger.error("Failed to extract genres: %s", exc)
            raise
