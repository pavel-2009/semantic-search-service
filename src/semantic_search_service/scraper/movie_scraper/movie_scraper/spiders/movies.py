"""Spider for fetching movie data from Poiskkino API."""

from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlencode

import scrapy
from scrapy.http import JsonRequest, Response

from semantic_search_service.core.config import settings
from semantic_search_service.scraper.schemas import Movie


class MovieSpider(scrapy.Spider):
    name = "movies"

    API_BASE = "https://api.poiskkino.dev/v1.4"
    API_KEY = settings.POISKKINO_API_KEY

    def start_requests(self) -> Generator[JsonRequest, None, None]:
        params = {
            "page": 1,
            "limit": 50,
            "sortField": "rating.kp",
            "sortType": "-1",
        }

        url = f"{self.API_BASE}/movie?{urlencode(params)}"

        yield JsonRequest(
            url=url,
            headers={
                "X-API-KEY": self.API_KEY,
                "accept": "application/json",
            },
            callback=self.parse_movie_list,
            meta={"page": 1},
        )

    def parse_movie_list(self, response: Response) -> Generator[JsonRequest, None, None]:
        data = response.json()
        movies = data.get("docs", [])

        for movie in movies:
            movie_id = movie.get("id")
            if movie_id:
                yield JsonRequest(
                    url=f"{self.API_BASE}/movie/{movie_id}",
                    headers={
                        "X-API-KEY": self.API_KEY,
                        "accept": "application/json",
                    },
                    callback=self.parse_movie_details,
                )

        current_page = response.meta.get("page", 1)
        total_pages = data.get("pages", 1)

        if current_page < total_pages and current_page < 10:
            next_page = current_page + 1
            params = {
                "page": next_page,
                "limit": 50,
                "sortField": "rating.kp",
                "sortType": "-1",
            }

            yield JsonRequest(
                url=f"{self.API_BASE}/movie?{urlencode(params)}",
                headers={
                    "X-API-KEY": self.API_KEY,
                    "accept": "application/json",
                },
                callback=self.parse_movie_list,
                meta={"page": next_page},
            )

    def parse_movie_details(self, response: Response) -> Generator[Movie, None, None]:
        data = response.json()

        try:
            movie_id = data.get("id")
            if not movie_id:
                return

            name = data.get("name") or data.get("alternativeName") or "Без названия"
            year = data.get("year")
            description = data.get("description") or data.get("shortDescription") or ""

            countries = data.get("countries", [])
            country = self._extract_countries(countries)

            persons = data.get("persons", [])
            director = self._extract_director(persons)
            actors = self._extract_actors(persons)

            genres = data.get("genres", [])
            tags = self._extract_genres(genres)

            rating = data.get("rating", {}).get("kp")

            yield Movie(
                id=movie_id,
                name=name,
                year=year,
                country=country,
                director=director,
                description=description,
                actors=actors,
                tags=tags,
                rating=rating,
            )

        except Exception as e:
            self.logger.error(f"Error parsing movie {data.get('id')}: {e}")

    @staticmethod
    def _extract_countries(countries: List[Dict[str, str]]) -> Optional[str]:
        if not countries:
            return None
        names = [c.get("name", "") for c in countries if c.get("name")]
        return ", ".join(names) if names else None

    @staticmethod
    def _extract_director(persons: List[Dict[str, Any]]) -> Optional[str]:
        for person in persons:
            if person.get("profession") == "режиссеры":
                return person.get("name") or person.get("enName")
        return None

    @staticmethod
    def _extract_actors(persons: List[Dict[str, Any]]) -> List[str]:
        actors = []
        for person in persons:
            if person.get("profession") == "актеры":
                name = person.get("name") or person.get("enName")
                if name:
                    actors.append(name)
        return actors

    @staticmethod
    def _extract_genres(genres: List[Dict[str, str]]) -> List[str]:
        return [g.get("name", "") for g in genres if g.get("name")]
