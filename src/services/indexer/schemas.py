from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class MovieCard(BaseModel):
    """Input contract for movie card.

    Also accepts the legacy scraper format (`id`, `description`, `director`).
    """
    movie_id: int
    title: str
    original_title: Optional[str] = None
    synopsis: Optional[str] = None
    year: Optional[int] = None
    rating: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    duration_min: Optional[int] = Field(default=None, gt=0)
    genres: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    country: Optional[str] = None
    poster_url: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _from_legacy_format(cls, data: Any) -> Any:
        """Map legacy scraper fields to the MovieCard contract."""
        if not isinstance(data, dict) or "movie_id" in data:
            return data

        data = dict(data)
        if "id" in data:
            data["movie_id"] = data.pop("id")
        if "description" in data and "synopsis" not in data:
            data["synopsis"] = data.pop("description")
        if "director" in data and "directors" not in data:
            director = data.pop("director")
            data["directors"] = [director] if director else []
        return data

    @field_validator("genres", "keywords", "directors", "actors", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: Any) -> Any:
        return [] if value is None else value

    @property
    def decade(self) -> Optional[int]:
        return (self.year // 10) * 10 if self.year is not None else None


class SparseVectorData(BaseModel):
    indices: list[int]
    values: list[float]


class MoviePayload(BaseModel):
    """Payload contract for Qdrant."""
    movie_id: int
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    rating: Optional[float] = None
    duration_min: Optional[int] = None
    genres: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    country: Optional[str] = None
    poster_url: Optional[str] = None


class IndexedMoviePoint(BaseModel):
    """Point for Qdrant."""
    point_id: int
    plot_vector: Optional[list[float]] = None
    vibe_vector: list[float]
    sparse_vector: SparseVectorData
    payload: MoviePayload
