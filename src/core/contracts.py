"""Typed contracts shared across service boundaries."""

from pydantic import BaseModel, Field


class Movie(BaseModel):
    """Canonical movie contract: scraper output, JSONL dataset and Qdrant payload."""

    id: int
    title: str = "Без названия"
    year: int | None = None
    countries: list[str] = Field(default_factory=list)
    description: str = ""
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
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
