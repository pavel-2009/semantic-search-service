"""Typed contracts shared across service boundaries."""

from pydantic import BaseModel, Field


class MovieIndexData(BaseModel):
    """Prebuilt text representations aligned with the project's Qdrant vectors."""

    plot: str | None = None
    vibe: str | None = None
    entities: str | None = None


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


class EnrichedMovie(Movie):
    """Enriched movie record loaded by the indexer for multi-vector indexing."""

    indexing: MovieIndexData

    def to_movie_payload(self) -> Movie:
        """Return the canonical Movie payload stored in Qdrant."""
        return Movie.model_validate(self.model_dump(exclude={"indexing"}))


class IndexerStats(BaseModel):
    """Statistics returned by the indexer."""

    collection: str
    points_count: int
    status: str

    def __getitem__(self, key: str) -> str | int:
        """Support dictionary-style access for existing callers."""
        return self.model_dump()[key]
