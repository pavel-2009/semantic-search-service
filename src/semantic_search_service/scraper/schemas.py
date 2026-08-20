"""Scraped movie schemas."""

from pydantic import BaseModel


class Movie(BaseModel):
    name: str
    year: int | None
    country: str | None
    director: str | None
    description: str
    actors: list[str]
    tags: list[str]
    rating: float | None
