from collections.abc import Generator
from typing import Any
from urllib.parse import urlencode

import scrapy
from scrapy.http import JsonRequest, Response

from semantic_search_service.core.config import settings
from semantic_search_service.scraper.schemas import Movie

JsonDict = dict[str, Any]


class MovieSpider(scrapy.Spider):
    name = "movies"

    API_BASE = "https://api.poiskkino.dev/v1.4"
    PAGE_SIZE = 50
    MAX_PAGES = 10

    @property
    def api_headers(self) -> dict[str, str]:
        return {"X-API-KEY": settings.POISKKINO_API_KEY, "accept": "application/json"}

    def start_requests(self) -> Generator[JsonRequest, None, None]:
        if not settings.POISKKINO_API_KEY:
            self.logger.error("POISKKINO_API_KEY is not set in .env")
            return
        yield self._movie_list_request(1)

    def parse_movie_list(self, response: Response) -> Generator[JsonRequest, None, None]:
        data: JsonDict = response.json()
        movies = data.get("docs") or []
        page = int(response.meta["page"])

        self.logger.info("Found %d movies on page %d", len(movies), page)
        for movie in movies:
            if not isinstance(movie, dict):
                continue
            movie_id = movie.get("id")
            if movie_id is None:
                continue
            yield JsonRequest(
                url=f"{self.API_BASE}/movie/{movie_id}",
                headers=self.api_headers,
                callback=self.parse_movie_details,
                dont_filter=True,
            )

        total_pages = int(data.get("pages") or page)
        if page < min(total_pages, self.MAX_PAGES):
            yield self._movie_list_request(page + 1)

    def parse_movie_details(self, response: Response) -> Generator[Movie, None, None]:
        data: JsonDict = response.json()
        movie_id = data.get("id")
        if movie_id is None:
            return

        persons = self._as_dict_list(data.get("persons"))
        rating = data.get("rating")
        rating_data = rating if isinstance(rating, dict) else {}

        try:
            movie = Movie(
                id=int(movie_id),
                name=str(data.get("name") or data.get("alternativeName") or "Без названия"),
                year=self._as_int(data.get("year")),
                country=self._extract_countries(self._as_dict_list(data.get("countries"))),
                director=self._extract_director(persons),
                description=str(data.get("description") or data.get("shortDescription") or ""),
                actors=self._extract_actors(persons),
                tags=self._extract_genres(self._as_dict_list(data.get("genres"))),
                rating=self._as_float(rating_data.get("kp")),
            )
        except (TypeError, ValueError) as exc:
            self.logger.error("Failed to parse movie %s: %s", movie_id, exc)
            return

        self.logger.info("Parsed: %s (%s)", movie.name, movie.year)
        yield movie

    def _movie_list_request(self, page: int) -> JsonRequest:
        params = {"page": page, "limit": self.PAGE_SIZE, "sortField": "rating.kp", "sortType": "-1"}
        return JsonRequest(
            url=f"{self.API_BASE}/movie?{urlencode(params)}",
            headers=self.api_headers,
            callback=self.parse_movie_list,
            meta={"page": page},
            dont_filter=True,
        )

    @staticmethod
    def _as_dict_list(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _as_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_countries(countries: list[dict[str, Any]]) -> str | None:
        names = [str(country["name"]) for country in countries if country.get("name") is not None]
        return ", ".join(names) if names else None

    @staticmethod
    def _extract_director(persons: list[dict[str, Any]]) -> str | None:
        for person in persons:
            if person.get("profession") == "режиссеры":
                name = person.get("name") or person.get("enName")
                return str(name) if name else None
        return None

    @staticmethod
    def _extract_actors(persons: list[dict[str, Any]]) -> list[str]:
        result: list[str] = []
        for person in persons:
            if person.get("profession") != "актеры":
                continue
            name = person.get("name") or person.get("enName")
            if name:
                result.append(str(name))
        return result

    @staticmethod
    def _extract_genres(genres: list[dict[str, Any]]) -> list[str]:
        return [str(genre["name"]) for genre in genres if genre.get("name") is not None]
