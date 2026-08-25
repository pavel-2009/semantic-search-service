"""API schemas for FastApi app"""

from pydantic import BaseModel, Field
from typing import Optional, List


# === Requests ===
class YearFilter(BaseModel):
    gte: Optional[int] = None
    lte: Optional[int] = None

class RatingFilter(BaseModel):
    gte: Optional[float] = None
    lte: Optional[float] = None

class SearchFilters(BaseModel):
    year: Optional[YearFilter] = None
    rating: Optional[RatingFilter] = None
    genre: Optional[List[str]] = None
    country: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Поисковый запрос")
    top_k: int = Field(10, ge=1, le=100, description="Количество результатов")
    filters: Optional[SearchFilters] = None


# === Responses ===
class MovieResult(BaseModel):
    id: int
    title: str
    year: Optional[int] = None
    rating: Optional[float] = None
    genres: List[str] = []
    countries: List[str] = []
    director: Optional[str] = None
    actors: List[str] = []
    description: Optional[str] = None
    poster_url: Optional[str] = None
    score: float = Field(..., description="Релевантность от 0 до 1")

class SearchResponse(BaseModel):
    success: bool = True
    query: str
    total: int
    results: List[MovieResult]

class HealthResponse(BaseModel):
    status: str
    collection: str
    indexed_items: int

class StatsResponse(BaseModel):
    collection: str
    total_points: int
    status: str
    model: str
    embedding_dim: int