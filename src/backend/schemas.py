"""API schemas for the semantic search service."""

from pydantic import BaseModel, Field


class YearFilter(BaseModel):
    """Year range filter."""

    gte: int | None = Field(None, description="Год от")
    lte: int | None = Field(None, description="Год до")


class RatingFilter(BaseModel):
    """Rating range filter."""

    gte: float | None = Field(None, description="Рейтинг от")
    lte: float | None = Field(None, description="Рейтинг до")


class SearchFilters(BaseModel):
    """Optional metadata filters for movie search."""

    year: YearFilter | None = Field(None, description="Фильтр по году")
    rating: RatingFilter | None = Field(None, description="Фильтр по рейтингу")
    genre: list[str] | None = Field(None, description="Фильтр по жанрам")
    country: str | None = Field(None, description="Фильтр по стране")


class SearchRequest(BaseModel):
    """Semantic movie search request."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Поисковый запрос",
        examples=["интерстеллар"],
    )
    top_k: int = Field(10, ge=1, le=100, description="Количество результатов", examples=[10])
    filters: SearchFilters | None = Field(None, description="Фильтры")


class MovieResult(BaseModel):
    """Movie returned by the search API."""

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
    """Semantic search API response."""

    success: bool = True
    query: str
    total: int
    results: list[MovieResult]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    collection: str
    indexed_items: int


class StatsResponse(BaseModel):
    """Vector collection statistics returned by the API."""

    collection: str
    total_points: int
    status: str
    model: str
    embedding_dim: int
