from pydantic import BaseModel

from core.contracts import Movie


class SparseVectorData(BaseModel):
    indices: list[int]
    values: list[float]


class IndexedMoviePoint(BaseModel):
    """Point for Qdrant; payload is the canonical movie contract."""

    point_id: int
    plot_vector: list[float] | None = None
    vibe_vector: list[float]
    sparse_vector: SparseVectorData
    payload: Movie
