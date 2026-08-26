"""Spider for fetching movie data from Poiskkino API."""

from typing import Any, Dict, List, Optional, Generator
from urllib.parse import urlencode

import scrapy
from scrapy.http import JsonRequest, Response

from semantic_search_service.scraper.schemas import Movie


class MovieSpider(scrapy.Spider):
    name = "movies"
    
    start_urls = [
        "https://api.poiskkino.dev/v1.4/movie?page=1&limit=5"
    ]
    
    def start_requests(self):
        self.logger.info("=== START_REQUESTS CALLED ===")
        
        for url in self.start_urls:
            yield JsonRequest(
                url=url,
                headers={
                    "X-API-KEY": "19Y8C8T-1DB4SAP-ND2GYRH-ATGV3A3",
                    "accept": "application/json",
                },
                callback=self.parse
            )
    
    def parse_movie_list(self, response: Response) -> Generator[JsonRequest, None, None]:
        """Parse movie list response."""
        self.logger.info(f"=== PARSE_MOVIE_LIST, status: {response.status} ===")
        
        data = response.json()
        movies = data.get("docs", [])
        
        self.logger.info(f"Found {len(movies)} movies")
        
        if not movies:
            return
        
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
                    dont_filter=True,
                )
        
        # Pagination
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
            url = f"{self.API_BASE}/movie?{urlencode(params)}"
            
            yield JsonRequest(
                url=url,
                headers={
                    "X-API-KEY": self.API_KEY,
                    "accept": "application/json",
                },
                callback=self.parse_movie_list,
                meta={"page": next_page},
                dont_filter=True,
            )
    
    def parse_movie_details(self, response: Response) -> Generator[Movie, None, None]:
        """Parse movie details and yield Movie item."""
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
            
            self.logger.info(f"✅ Parsed: {movie.name} ({movie.year})")
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