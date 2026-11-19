"""Base contracts of the search engine pipeline: query -> parsed -> encoded."""

from pydantic import BaseModel, Field

from src.services.indexer.schemas import SparseVectorData


class SearchQuery(BaseModel):
    """Raw user search request."""

    text: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, object] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search response with document IDs and scores."""

    documents: list[dict] = Field(default_factory=list)


class ParsedQuery(BaseModel):
    """Query split into semantic text and structured filters (Movie fields)."""

    text: str
    year_gte: int | None = None
    year_lte: int | None = None
    rating_gte: float | None = None
    genres: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)


class EncodedQuery(BaseModel):
    """Query vectors ready for Qdrant search."""

    dense_vector: list[float]
    sparse_vector: SparseVectorData
    parsed: ParsedQuery
