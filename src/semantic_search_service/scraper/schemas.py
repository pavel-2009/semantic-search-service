"""Film schema"""

from pydantic import BaseModel

from typing import List


class Movie(BaseModel):
    name: str
    year: int | None
    country: str | None
    director: str | None
    description: str
    actors: List[str]
    tags: List[str]
    rating: float | None
