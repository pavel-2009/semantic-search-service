from collections.abc import Generator
from typing import Any
from urllib.parse import urlencode

import scrapy
from scrapy.http import Request, Response

from scraper.schemas import Movie

JsonDict = dict[str, Any]


class MovieSpider(scrapy.Spider):
    name = "movies"

    API_BASE = "https://api.poiskkino.dev/v1.4/movie"
    PAGE_SIZE = 50
    MAX_PAGES = 100

    start_urls = [
        f"{API_BASE}?{urlencode({
            'page': 1,
            'limit': PAGE_SIZE,
            'sortField': 'rating.kp',
            'sortType': '-1',
        })}"
    ]

    def parse(self, response: Response) -> Generator[Request | Movie, None, None]:
        data: JsonDict = response.json()
        page = int(response.meta.get("page", 1))
        movies = self._as_dict_list(data.get("docs"))

        self.logger.info("Found %d movies on page %d", len(movies), page)

        for movie_data in movies:
            movie = self._parse_movie(movie_data)
            if movie is not None:
                yield movie

        current_page = data.get("page", 1)
        total_pages = data.get("pages", 1)

        self.logger.info("Page %d of %d", current_page, total_pages)

        if page >= self.MAX_PAGES:
            self.logger.info("Reached max pages limit (%d)", self.MAX_PAGES)
            return

        if current_page >= total_pages:
            self.logger.info("Reached last page (%d of %d)", current_page, total_pages)
            return

        next_page = current_page + 1
        yield Request(
            url=self._movie_list_url(next_page),
            callback=self.parse,
            meta={"page": next_page},
        )

    def _parse_movie(self, data: JsonDict) -> Movie | None:
        movie_id = data.get("id")
        if movie_id is None:
            return None

        persons = self._as_dict_list(data.get("persons"))
        rating = data.get("rating")
        rating_data = rating if isinstance(rating, dict) else {}

        try:
            return Movie(
                id=int(movie_id),
                title=str(data.get("name") or data.get("alternativeName") or "Без названия"),
                year=self._as_int(data.get("year")),
                country=self._extract_countries(self._as_dict_list(data.get("countries"))),
                director=self._extract_director(persons),
                description=str(data.get("description") or data.get("shortDescription") or ""),
                actors=self._extract_actors(persons),
                genres=self._extract_genres(self._as_dict_list(data.get("genres"))),
                rating=self._as_float(rating_data.get("kp")),
                poster_url=self._extract_poster_url(data.get("poster")),
            )
        except (TypeError, ValueError) as exc:
            self.logger.error("Failed to parse movie %s: %s", movie_id, exc)
            return None

    def _movie_list_url(self, page: int) -> str:
        params = {
            "page": page,
            "limit": self.PAGE_SIZE,
            "sortField": "rating.kp",
            "sortType": "-1",
        }
        return f"{self.API_BASE}?{urlencode(params)}"

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
    def _extract_poster_url(poster: object) -> str | None:
        if not isinstance(poster, dict):
            return None
        url = poster.get("url") or poster.get("previewUrl")
        return str(url) if url else None

    @staticmethod
    def _extract_countries(countries: list[dict[str, Any]]) -> str | None:
        names = [str(country["name"]) for country in countries if country.get("name")]
        return ", ".join(names) if names else None

    @staticmethod
    def _extract_director(persons: list[dict[str, Any]]) -> str | None:
        for person in persons:
            if person.get("profession") != "режиссеры":
                continue
            name = person.get("name") or person.get("enName")
            if name:
                return str(name)
        return None

    @staticmethod
    def _extract_actors(persons: list[dict[str, Any]]) -> list[str]:
        return [
            str(name)
            for person in persons
            if person.get("profession") == "актеры"
            for name in [person.get("name") or person.get("enName")]
            if name
        ]

    @staticmethod
    def _extract_genres(genres: list[dict[str, Any]]) -> list[str]:
        return [str(genre["name"]) for genre in genres if genre.get("name")]
