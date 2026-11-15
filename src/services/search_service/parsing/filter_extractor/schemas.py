"""Contract of the filter extractor."""

from pydantic import BaseModel


class ExtractedFilters(BaseModel):
    """Year and rating constraints plus the query text without the matched phrases."""

    text: str
    year_gte: int | None = None
    year_lte: int | None = None
    rating_gte: float | None = None
    rating_lte: float | None = None
