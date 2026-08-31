"""Schemas for scraped movies."""

from pydantic import BaseModel, Field


class Movie(BaseModel):
    """Normalized movie data shared by scraper and indexer."""

    id: int
    title: str
    year: int | None = None
    country: str | None = None
    director: str | None = None
    description: str = ""
    actors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    rating: float | None = None
    poster_url: str | None = None
