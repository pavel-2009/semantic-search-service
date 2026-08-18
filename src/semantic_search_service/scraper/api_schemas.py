"""Schemas for API responces and requests"""

from pydantic import BaseModel
from typing import Optional, List


class Genre(BaseModel):
    genre: str

class Country(BaseModel):
    country: str

class Person(BaseModel):
    nameRu: Optional[str] = None
    professionText: Optional[str] = None

class MovieSearchItem(BaseModel):
    kinopoiskId: int
    nameRu: Optional[str] = None
    nameOriginal: Optional[str] = None
    year: Optional[int] = None
    ratingKinopoisk: Optional[float] = None
    genres: List[Genre] = []
    countries: List[Country] = []
    posterUrl: Optional[str] = None

class MovieSearchResponse(BaseModel):
    total: int
    items: List[MovieSearchItem]

class MovieDetailResponse(BaseModel):
    kinopoiskId: int
    nameRu: Optional[str] = None
    nameOriginal: Optional[str] = None
    description: Optional[str] = None
    shortDescription: Optional[str] = None
    filmLength: Optional[int] = None
    slogan: Optional[str] = None
    persons: List[Person] = []


class MovieDocument(BaseModel):
    id: int
    title: str
    title_original: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[int] = None
    rating: Optional[float] = None
    genres: List[str] = []
    countries: List[str] = []
    director: Optional[str] = None
    actors: List[str] = []
    poster_url: Optional[str] = None
    slogan: Optional[str] = None
