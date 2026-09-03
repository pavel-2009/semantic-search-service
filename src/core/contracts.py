"""Typed contracts shared across service boundaries."""

from pydantic import BaseModel, Field


class MoviePayload(BaseModel):
    """Canonical movie payload stored in Qdrant."""

    id: int | None = None
    title: str = "Без названия"
    year: int | None = None
    country: str | None = None
    countries: list[str] = Field(default_factory=list)
    director: str | None = None
    description: str = ""
    actors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    rating: float | None = None
    poster_url: str | None = None


class IndexerStats(BaseModel):
    """Statistics returned by the indexer."""

    collection: str
    points_count: int
    status: str

    def __getitem__(self, key: str) -> str | int:
        """Support dictionary-style access for existing callers."""
        return self.model_dump()[key]
