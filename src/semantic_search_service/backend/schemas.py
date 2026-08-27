"""API schemas for the semantic search service."""

from pydantic import BaseModel, Field


class YearFilter(BaseModel):
    gte: int | None = None
    lte: int | None = None


class RatingFilter(BaseModel):
    gte: float | None = None
    lte: float | None = None


class SearchFilters(BaseModel):
    year: YearFilter | None = None
    rating: RatingFilter | None = None
    genre: list[str] | None = None
    country: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Поисковый запрос")
    top_k: int = Field(10, ge=1, le=100, description="Количество результатов")
    filters: SearchFilters | None = None


class MovieResult(BaseModel):
    id: int
    title: str
    year: int | None = None
    rating: float | None = None
    genres: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    director: str | None = None
    actors: list[str] = Field(default_factory=list)
    description: str | None = None
    poster_url: str | None = None
    score: float = Field(..., description="Релевантность от 0 до 1")


class SearchResponse(BaseModel):
    success: bool = True
    query: str
    total: int
    results: list[MovieResult]


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
