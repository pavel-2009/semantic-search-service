"""Schemas for API responces and requests"""

from pydantic import BaseModel
from typing import Optional, List


class Genre(BaseModel):
    genre: str

class Country(BaseModel):
    country: str


class MovieSearchItem(BaseModel):
    """Элемент из поиска (/movie/search)"""
    kinopoiskId: int
    imdbId: Optional[str] = None
    nameRu: Optional[str] = None
    nameEn: Optional[str] = None
    nameOriginal: Optional[str] = None
    year: Optional[int] = None
    ratingKinopoisk: Optional[float] = None
    ratingImdb: Optional[float] = None
    genres: List[Genre] = []
    countries: List[Country] = []
    posterUrl: Optional[str] = None
    posterUrlPreview: Optional[str] = None
    type: Optional[str] = None


class MovieSearchResponse(BaseModel):
    """Ответ на поиск (/movie/search)"""
    total: int
    totalPages: int
    items: List[MovieSearchItem]


class MovieDetailResponse(BaseModel):
    """Детальная информация (/movie/{id})"""
    kinopoiskId: int
    imdbId: Optional[str] = None
    nameRu: Optional[str] = None
    nameEn: Optional[str] = None
    nameOriginal: Optional[str] = None
    year: Optional[int] = None
    filmLength: Optional[int] = None
    slogan: Optional[str] = None
    description: Optional[str] = None
    shortDescription: Optional[str] = None
    ratingKinopoisk: Optional[float] = None
    ratingImdb: Optional[float] = None
    genres: List[Genre] = []
    countries: List[Country] = []
    posterUrl: Optional[str] = None
    posterUrlPreview: Optional[str] = None
    coverUrl: Optional[str] = None
    logoUrl: Optional[str] = None
    reviewsCount: Optional[int] = None
    ratingGoodReview: Optional[float] = None
    webUrl: Optional[str] = None
    type: Optional[str] = None


class MovieDocument(BaseModel):
    """Единый документ для хранения и дальнейшей обработки"""
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
    poster_url: Optional[str] = None
    slogan: Optional[str] = None
    reviews_count: Optional[int] = None
    web_url: Optional[str] = None