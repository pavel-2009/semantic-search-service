"""Spider for fetching movie data from Poiskkino API."""

from typing import Any, Dict, List, Optional, Generator
from urllib.parse import urlencode

import scrapy
from scrapy.http import JsonRequest, Response

from semantic_search_service.scraper.schemas import Movie


class MovieSpider(scrapy.Spider):
    name = "movies"
    
    # API configuration
    API_BASE = "https://api.poiskkino.dev/v1.4"
    API_KEY = ""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        
        # Load API key from settings
        from semantic_search_service.core.config import settings
        self.API_KEY = settings.POISKKINO_API_KEY # type: ignore
        
        if not self.API_KEY:
            self.logger.error("POISKKINO_API_KEY not set! Get your token from @poiskkinodev_bot")
    
    def start_requests(self) -> Generator[JsonRequest, None, None]:
        if not self.API_KEY:
            return
        
        params = {
            "page": 1,
            "limit": 50,
            "sortField": "rating.kp",
            "sortType": "-1",
        }
        
        url = f"{self.API_BASE}/movie?{urlencode(params)}"
        
        yield JsonRequest(
            url=url,
            headers=self._get_headers(),
            callback=self.parse_movie_list,
            meta={"page": 1},
            dont_filter=True,
        )
    
    def parse_movie_list(self, response: Response) -> Generator[JsonRequest, None, None]:
        data = response.json()
        movies = data.get("docs", [])
        
        if not movies:
            self.logger.info("No more movies found")
            return
        
        current_page = response.meta.get("page", 1)
        self.logger.info(f"Processing {len(movies)} movies from page {current_page}")
        
        for movie in movies:
            movie_id = movie.get("id")
            if movie_id:
                yield JsonRequest(
                    url=f"{self.API_BASE}/movie/{movie_id}",
                    headers=self._get_headers(),
                    callback=self.parse_movie_details,
                    dont_filter=True,
                )
        
        # Pagination (demo tariff: first 10 pages)
        total_pages = data.get("pages", 1)
        if current_page < total_pages and current_page < 10:
            next_page = current_page + 1
            params = {
                "page": next_page,
                "limit": 50,
                "sortField": "rating.kp",
                "sortType": "-1",
            }
            url = f"{self.API_BASE}/movie?{urlencode(params)}"
            
            yield JsonRequest(
                url=url,
                headers=self._get_headers(),
                callback=self.parse_movie_list,
                meta={"page": next_page},
                dont_filter=True,
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
            
            # Countries
            countries = data.get("countries", [])
            country = self._extract_countries(countries)
            
            # Persons
            persons = data.get("persons", [])
            director = self._extract_director(persons)
            actors = self._extract_actors(persons)
            
            # Genres
            genres = data.get("genres", [])
            tags = self._extract_genres(genres)
            
            # Rating
            rating_data = data.get("rating", {})
            rating = rating_data.get("kp")
            
            movie = Movie(
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
            
            self.logger.info(f"Parsed: {movie.name} ({movie.year})")
            yield movie
            
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
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-API-KEY": self.API_KEY or "",
            "accept": "application/json",
        }