"""Scrapy spider for collecting movies from the PoiskKino API."""

from collections.abc import Generator
from urllib.parse import urlencode

import scrapy
from scrapy.addons import logger
from scrapy.http import Request, Response

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

    start_urls = [
        f"{API_BASE}?{urlencode({
            'page': 1,
            'limit': PAGE_SIZE,
            'sortField': 'rating.kp',
            'sortType': '-1',
        })}"
    ]

    def parse(self, response: Response) -> Generator[Request | Movie, None, None]:
        """Parse one paginated PoiskKino response."""
        data = PoiskKinoResponse.model_validate_json(response.body)
        page = int(response.meta.get("page", 1))

        self.logger.info("Found %d movies on page %d", len(data.docs), page)

        for movie_data in data.docs:
            movie = self._parse_movie(movie_data)
            if movie is not None:
                yield movie

        self.logger.info("Page %d of %d", data.page, data.pages)

        if page >= self.MAX_PAGES:
            self.logger.info("Reached max pages limit (%d)", self.MAX_PAGES)
            return

        if data.page >= data.pages:
            self.logger.info("Reached last page (%d of %d)", data.page, data.pages)
            return

        next_page = data.page + 1
        yield Request(
            url=self._movie_list_url(next_page),
            callback=self.parse,
            meta={"page": next_page},
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
            return None

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
