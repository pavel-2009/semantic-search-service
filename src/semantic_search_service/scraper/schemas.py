"""Schemas for scraped movies."""

from pydantic import BaseModel, Field


class Movie(BaseModel):
    """Normalized movie data produced by the spider."""

    id: int
    name: str
    year: int | None = None
    country: str | None = None
    director: str | None = None
    description: str = ""
    actors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rating: float | None = None
