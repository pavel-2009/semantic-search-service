from collections.abc import Generator
from typing import Any
from urllib.parse import urlencode

import scrapy
from scrapy.http import JsonRequest, Response

from semantic_search_service.core.config import settings
from semantic_search_service.scraper.schemas import Movie


class MovieSpider(scrapy.Spider):
    name = "movies"

    API_BASE = "https://api.poiskkino.dev/v1.4"
    PAGE_SIZE = 50
    MAX_PAGES = 10

    @property
    def api_headers(self) -> dict[str, str]:
        return {
            "X-API-KEY": settings.POISKKINO_API_KEY,
            "accept": "application/json",
        }

    def start_requests(self) -> Generator[JsonRequest, None, None]:
        if not settings.POISKKINO_API_KEY:
            self.logger.error("POISKKINO_API_KEY is not set in .env")
            return

        yield self._movie_list_request(1)

    def parse_movie_list(self, response: Response) -> Generator[JsonRequest, None, None]:
        data = response.json()
        movies = data.get("docs") or []
        page = response.meta["page"]

        self.logger.info("Found %d movies on page %d", len(movies), page)

        for movie in movies:
            movie_id = movie.get("id")
            if movie_id:
                yield JsonRequest(
                    url=f"{self.API_BASE}/movie/{movie_id}",
                    headers=self.api_headers,
                    callback=self.parse_movie_details,
                    dont_filter=True,
                )

        total_pages = data.get("pages") or page
        if page < min(total_pages, self.MAX_PAGES):
            yield self._movie_list_request(page + 1)

    def parse_movie_details(self, response: Response) -> Generator[Movie, None, None]:
        data = response.json()
        movie_id = data.get("id")
        if not movie_id:
            return

        persons = data.get("persons") or []
        rating = data.get("rating") or {}

        try:
            movie = Movie(
                id=movie_id,
                name=data.get("name") or data.get("alternativeName") or "Без названия",
                year=data.get("year"),
                country=self._extract_countries(data.get("countries") or []),
                director=self._extract_director(persons),
                description=data.get("description") or data.get("shortDescription") or "",
                actors=self._extract_actors(persons),
                tags=self._extract_genres(data.get("genres") or []),
                rating=rating.get("kp"),
            )
        except (TypeError, ValueError) as exc:
            self.logger.error("Failed to parse movie %s: %s", movie_id, exc)
            return

        self.logger.info("Parsed: %s (%s)", movie.name, movie.year)
        yield movie

    def _movie_list_request(self, page: int) -> JsonRequest:
        params = {
            "page": page,
            "limit": self.PAGE_SIZE,
            "sortField": "rating.kp",
            "sortType": "-1",
        }
        return JsonRequest(
            url=f"{self.API_BASE}/movie?{urlencode(params)}",
            headers=self.api_headers,
            callback=self.parse_movie_list,
            meta={"page": page},
            dont_filter=True,
        )

    @staticmethod
    def _extract_countries(countries: list[dict[str, Any]]) -> str | None:
        names = [country["name"] for country in countries if country.get("name")]
        return ", ".join(names) if names else None

    @staticmethod
    def _extract_director(persons: list[dict[str, Any]]) -> str | None:
        for person in persons:
            if person.get("profession") == "режиссеры":
                return person.get("name") or person.get("enName")
        return None

    @staticmethod
    def _extract_actors(persons: list[dict[str, Any]]) -> list[str]:
        return [
            name
            for person in persons
            if person.get("profession") == "актеры"
            for name in [person.get("name") or person.get("enName")]
            if name
        ]

    @staticmethod
    def _extract_genres(genres: list[dict[str, Any]]) -> list[str]:
        return [genre["name"] for genre in genres if genre.get("name")]
