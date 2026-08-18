"""Film schema"""

from pydantic import BaseModel

from typing import List, Optional


class Movie(BaseModel):
    name: str
    year: int
    country: str
    director: str
    description: str
    actors: List[str]
    genre: str
    rating: Optional[float]
    watchers: Optional[int]
    status: Optional[str]
