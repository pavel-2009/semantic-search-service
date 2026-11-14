from typing import Optional
from pydantic import BaseModel, Field


class MovieCard(BaseModel):
    """Input conract for movie card."""
    movie_id: int
    title: str
    original_title: Optional[str] = None
    synopsis: Optional[str] = None
    year: int
    rating: float = Field(ge=0.0, le=10.0)
    duration_min: int = Field(gt=0)
    genres: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    country: Optional[str] = None
    poster_url: Optional[str] = None

    @property
    def decade(self) -> int:
        return (self.year // 10) * 10


class SparseVectorData(BaseModel):
    indices: list[int]
    values: list[float]


class MoviePayload(BaseModel):
    """Payload contract for Qdrant."""
    movie_id: int
    title: str
    original_title: Optional[str]
    year: int
    rating: float
    duration_min: int
    genres: list[str]
    directors: list[str]
    actors: list[str]
    country: Optional[str]
    poster_url: Optional[str]


class IndexedMoviePoint(BaseModel):
    """Point for Qdrant."""
    point_id: int
    plot_vector: Optional[list[float]] = None
    vibe_vector: list[float]
    sparse_vector: SparseVectorData
    payload: MoviePayload
