"""API schemas for FastApi app"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any


# === Requests ===
class YearFilter(BaseModel):
    gte: Optional[int] = None
    lte: Optional[int] = None

class RatingFilter(BaseModel):
    gte: Optional[float] = None
    lte: Optional[float] = None

class SearchFilters(BaseModel):
    year: Optional[YearFilter] = None
    rating: Optional[RatingFilter] = None
    genre: Optional[List[str]] = None
    country: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Поисковый запрос")
    top_k: int = Field(10, ge=1, le=100, description="Количество результатов")
    filters: Optional[SearchFilters] = None
